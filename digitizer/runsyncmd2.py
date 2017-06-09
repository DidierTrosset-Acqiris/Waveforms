#!/usr/bin/python3

"""
    Runs continuous acquisitions in synchronized M9730B instruments

    Copyright (C) Keysight Technologies 2015-2017
   
    Started: April 16th, 2013
    By:      Didier Trosset
    Label:   Agilent Confidential

"""

from AgMD2 import *
from waveforms.trace import OutputTraces
from waveforms import MultiRecord, DDCMultiRecord
from digitizer.argparser import DigitizerParser, DigitizerArgs
import sys
import os
from time import sleep
from random import random
from signal import signal, SIGTERM, SIGINT
from numpy import mean, std
from math import pi

try:
    from SineFit import CalcFittedSine3, CalcTimeSine4
    sineFitAvailable = True
except:
    sineFitAvailable = False


def SignalEndLoop( sig, frame ):
    global _Continue
    _Continue = False


def DontContinue():
    global _Continue
    return not _Continue


def Loops( nbrLoops, breaker=None  ):
    loop = 0
    while loop<nbrLoops or nbrLoops<0:
        yield loop
        if breaker and breaker():
            break
        loop += 1


def RunSyncAcq():
    global _Continue, _Failure

    parser = DigitizerParser()
    parser.add_argument( "--outer-loops", "-ol", nargs='?', type=int, default=1 )
    parser.add_argument( "--skew", default=False, action='store_true' )
    parser.add_argument( "--moving-sine-fit", default=False, action='store_true' )
    parser.add_argument( "--sine-fit-width", "-sfw", nargs=None, type=int, default=0 )
    parser.add_argument( "--sine-fit-step", "-sfs", nargs=None, type=int, default=0 )
    parser.add_argument( "--frequency", "-f", nargs=None, type=float, default=100e6 )
    parser.add_argument( "--ddc-output-phase", default=False, action='store_true' )
    parser.add_argument( "--send-axie-triggers", default=False, action='store_true' )
    parser.add_argument( "--read-tdc", default=False, action='store_true' )
    parser.add_argument( "--rotate-master", default=False, action='store_true' )
    parser.add_argument( "--check-continuity", default=False, action='store_true' )
    parser.add_argument( "--no-tdc", default=False, action='store_true' )
    parser.add_argument( "--clock-restart-period", "-ksp", nargs='?', type=int, default=0 )
    parser.add_argument( "--dpu-bitfile", "-db", nargs=None, type=str )
    args = DigitizerArgs( parser )

    if ( args.skew or args.moving_sine_fit ) and not sineFitAvailable:
        print( "ERROR: Cannot calculate skew as scipy is not available.", file=sys.stderr )
        return

    options = ""
    if args.dpu_bitfile:
        bf = args.dpu_bitfile
        options = options+", UserDpuA=%s, UserDpuB=%s, UserDpuC=%s, UserDpuD=%s"%( bf, bf, bf, bf )

    try:
        reset = 1 if args.reset else 0
        Instrs = []
        for rsrc in args.resources:
            Vi = AgMD2_InitWithOptions( rsrc, 0, reset, options )
            Instrs.append( Vi )
            AgMD2_SetAttributeViString( Vi, "", AGMD2_ATTR_PRIVATE_ACCESS_PASSWORD, "We1ssh0rn" )
            print( "Driver:  ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_SPECIFIC_DRIVER_REVISION, 256 ), file=sys.stderr )
            print( "IOLS:    ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_IO_VERSION, 256 ), file=sys.stderr )
            print( "Model:   ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_MODEL, 256 ), file=sys.stderr )
            print( "Serial:  ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_SERIAL_NUMBER_STRING, 256 ), file=sys.stderr )
            print( "Options: ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_OPTIONS, 256 ), file=sys.stderr )
            print( "Firmware:", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_FIRMWARE_REVISION, 256 ), file=sys.stderr )
    except RuntimeError:
        _Failure = True
        raise

    nbrRecords = args.records
    try: nbrSamples = args.samples[0]
    except: nbrSamples = args.samples
    calcSkew =   args.skew
    sendAXIeTriggers = args.send_axie_triggers
    calcMovingSineFit = args.moving_sine_fit
    sineFitWidth = args.sine_fit_width if args.moving_sine_fit else 0
    sineFitStep = args.sine_fit_step if args.moving_sine_fit and args.sine_fit_step else sineFitWidth

    RecordSize = nbrSamples if nbrSamples>4096 else 4096

    Serials = [AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_SERIAL_NUMBER_STRING, 32 ) for Vi in Instrs]
    Handles = [AgMD2_GetAttributeViInt32( Vi, "", AGMD2_ATTR_MODULE_SYNCHRONIZATION_HANDLE ) for Vi in Instrs]

    # Manages conbination
    if args.interleave:
        ch, sub = args.interleave[:2]
        for Vi in Instrs: AgMD2_SetAttributeViString( Vi, "Channel%d"%( ch ), AGMD2_ATTR_TIME_INTERLEAVED_CHANNEL_LIST, "Channel%d"%( sub ) )

    if args.mode=='DDC':
        ddcSampFreq = args.sampling_frequency/args.ddc_decimation_numerator
        nbrCores = AgMD2_GetAttributeViInt32( Instrs[0], "", AGMD2_ATTR_DDCCORE_COUNT )
        DDCCores = ["DDCCore%d"%( core+1 ) for core in range( nbrCores )]
        for Vi in Instrs:
            AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_ACQUISITION_MODE, AGMD2_VAL_ACQUISITION_MODE_DIGITAL_DOWN_CONVERSION )
            for ddcc in DDCCores:
                AgMD2_SetAttributeViReal64( Vi, ddcc, AGMD2_ATTR_DDCCORE_CENTER_FREQUENCY, args.ddc_local_oscillator_frequency )
                if args.ddc_decimation_numerator:
                    AgMD2_SetAttributeViInt64( Vi, ddcc, AGMD2_ATTR_DDCCORE_DECIMATION_NUMERATOR, args.ddc_decimation_numerator )
                if args.ddc_decimation_denominator:
                    AgMD2_SetAttributeViInt64( Vi, ddcc, AGMD2_ATTR_DDCCORE_DECIMATION_DENOMINATOR, args.ddc_decimation_denominator )

    if args.clock_external:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_SOURCE, AGMD2_VAL_SAMPLE_CLOCK_SOURCE_EXTERNAL )
        for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_EXTERNAL_FREQUENCY, args.clock_external )
        for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_EXTERNAL_DIVIDER, args.clock_ext_divider )
    elif args.clock_ref_axie:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_AXIE_CLK100 )
    elif args.clock_ref_pxi:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_PXIE_CLK100 )
    elif args.clock_ref_external:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_EXTERNAL )

    sampFreq = args.sampling_frequency if args.sampling_frequency else 1.6e9
    for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, "", AGMD2_ATTR_SAMPLE_RATE, sampFreq )
    for Vi in Instrs: AgMD2_SetAttributeViInt64(  Vi, "", AGMD2_ATTR_RECORD_SIZE, RecordSize )
    for Vi in Instrs: AgMD2_SetAttributeViInt64(  Vi, "", AGMD2_ATTR_NUM_RECORDS_TO_ACQUIRE, nbrRecords )

    # Manages trigger
    if args.immediate_trigger:
        ActiveTrigger = "Immediate"
    else:
        if args.trigger_external:
            ActiveTrigger = "External%d"%( args.trigger_external ) if args.trigger_external!=4 else "AXIe_SYNC"
        elif args.trigger_internal:
            ActiveTrigger = "Internal%d"%( args.trigger_internal )
        elif args.trigger_name:
            ActiveTrigger = args.trigger_name
        else:
            ActiveTrigger = "Internal1"

        if args.trigger_level!=None:
            for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, ActiveTrigger, AGMD2_ATTR_TRIGGER_LEVEL, args.trigger_level )
        if args.trigger_delay!=None:
            for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, "", AGMD2_ATTR_TRIGGER_DELAY, args.trigger_delay )
        if args.trigger_slope!=None:
            if args.trigger_slope in ["negative", "n"]:
                for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, ActiveTrigger, AGMD2_ATTR_TRIGGER_SLOPE, AGMD2_VAL_NEGATIVE )
            else:
                for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, ActiveTrigger, AGMD2_ATTR_TRIGGER_SLOPE, AGMD2_VAL_POSITIVE )

    for Vi in Instrs: AgMD2_SetAttributeViString( Vi, "", AGMD2_ATTR_ACTIVE_TRIGGER_SOURCE , ActiveTrigger )

    #for Vi in Instrs: AgMD2_SetAttributeViBoolean( Vi, "Channel6", AGMD2_ATTR_CHANNEL_ENABLED, False )

    # Manages channels
    for Vi in Instrs:
        for ch in range( 1, 9 ):#args.read_channels:
            channel = "Channel%d"%( ch )
            if args.vertical_range:  AgMD2_SetAttributeViReal64( Vi, channel, AGMD2_ATTR_VERTICAL_RANGE,  args.vertical_range )
            if args.vertical_offset: AgMD2_SetAttributeViReal64( Vi, channel, AGMD2_ATTR_VERTICAL_OFFSET, args.vertical_offset )

    InstrsToRead = list( Instrs )
    ChannelsToRead = ["DDCCore%d"%( ch ) for ch in args.read_channels] if args.mode=="DDC" else ["Channel%d"%( ch ) for ch in args.read_channels]

    oldSigTerm = signal( SIGTERM, SignalEndLoop )
    oldSigInt  = signal( SIGINT,  SignalEndLoop )

    Channels = []
    for Vi in InstrsToRead:
        for Ch in ChannelsToRead:
            Channels.append( ( Vi, Ch ) )

    for sync in Loops( args.outer_loops, breaker=DontContinue ):

        def Normalize( diff, period ):
            if diff>period/2:
                diff = diff-period
            if diff<-period/2:
                diff = diff+period
            return diff

        def SendAXIeTriggers( InstrId, count=1 ):
            for i in range( count ):
                AgMD2_UserControlWriteControlRegisterInt32( InstrId, 0xac0, 0x10001 )
                AgMD2_UserControlWriteControlRegisterInt32( InstrId, 0xac4, 0 )
                AgMD2_UserControlWriteControlRegisterInt32( InstrId, 0xac4, 1 )
                AgMD2_UserControlWriteControlRegisterInt32( InstrId, 0xac4, 0 )
                AgMD2_UserControlWriteControlRegisterInt32( InstrId, 0xac0, 0x10000 )
                # Duration of one record, doubled for security
                delay = max( 0.001, 2 * nbrSamples/sampFreq )
                sleep( delay )


        for Vi in Instrs:
            AgMD2_InitiateAcquisition( Vi )
        if sendAXIeTriggers:
            SendAXIeTriggers( Instrs[0], nbrRecords )
        for Vi in Instrs:
            AgMD2_WaitForAcquisitionComplete( Vi, 20 )

        for Vi in Instrs: AgMD2_SelfCalibrate( Vi )

        for Vi in Instrs:
            AgMD2_InitiateAcquisition( Vi )
        if sendAXIeTriggers:
            SendAXIeTriggers( Instrs[0], nbrRecords )
        for Vi in Instrs:
            AgMD2_WaitForAcquisitionComplete( Vi, 20 )

        if len( Instrs )>1:
            AgMD2_ModuleSynchronizationConfigureSlaves( Instrs[0], Handles[1:] )

        signalFreq = args.frequency

        if args.calibration_signal:
            for Vi in Instrs: AgMD2_SetAttributeViString( Vi, "", AGMD2_ATTR_PRIVATE_CALIBRATION_USER_SIGNAL, "Signal"+args.calibration_signal )

        for measure in Loops( args.loops, breaker=DontContinue ):

            AgMD2_InitiateAcquisition( Instrs[0] )

            if sendAXIeTriggers:
                SendAXIeTriggers( Instrs[0], nbrRecords )

            AgMD2_WaitForAcquisitionComplete( Instrs[0], 20000 )
            for Vi in Instrs[1:]: AgMD2_IsIdle( Vi ) # Required temporarily
                
            # Read data on master and slaves.
            if args.mode=='DDC':
                if args.ddc_decimation_numerator and args.ddc_decimation_numerator>4:
                    wfmSize = 2*AgMD2_QueryMinWaveformMemory( Vi, 32, nbrRecords, 0, nbrSamples )
                    Fetchs = [AgMD2_DDCCoreFetchWaveformInt32Py( Vi, Ch, 0, nbrRecords, 0, nbrSamples, wfmSize, nbrRecords ) for Vi, Ch in Channels ]
                else:
                    wfmSize = 2*AgMD2_QueryMinWaveformMemory( Vi, 16, nbrRecords, 0, nbrSamples )
                    Fetchs = [AgMD2_DDCCoreFetchWaveformInt16Py( Vi, Ch, 0, nbrRecords, 0, nbrSamples, wfmSize, nbrRecords ) for Vi, Ch in Channels ]
                mrec = DDCMultiRecord( Fetchs )
            else:
                wfmSize = AgMD2_QueryMinWaveformMemory( Vi, 16, nbrRecords, 0, nbrSamples )
                Fetchs = [AgMD2_FetchMultiRecordWaveformInt16Py( Vi, Ch, 0, nbrRecords, 0, nbrSamples, wfmSize, nbrRecords ) for Vi, Ch in Channels ]
                mrec = MultiRecord( Fetchs, checkXOffset=not args.no_check_x_offset, nbrAdcBits=16 )

            tdcString = ""
            if args.read_tdc:
                Tdcs = [AgMD2_UserControlReadControlRegisterInt32( Vi, 0xa88 ) % 0x10000 for Vi, Ch in Channels]
                tdcString = " "+" ".join( [str(tdc) for tdc in Tdcs] )

            if calcMovingSineFit:
                omega = 2.0*pi*signalFreq/sampFreq

                for rec in mrec:
                    assert( len(rec)==len(Fetchs) )

                    actualSamples = min( [wfm.ActualPoints for wfm in rec] )

                    for sample in range( 0, actualSamples-sineFitWidth, sineFitStep ):
                        Chunks = [wfm.Samples[sample:sample+sineFitWidth] for wfm in rec]

                        if args.check_continuity:
                            try:
                                for chunk in Chunks: CheckSineContinuity( chunk )
                            except DiscontinuityException as e:
                                sys.stderr.write( "ERROR: Discontinuity in Waveform (%s)\n"%( str(e) ) )

                        Sines = [CalcFittedSine3( chunk, omega ) for chunk in Chunks]
                        assert( len(Sines)==len(Fetchs) )

                        for Sine in Sines:
                            if Sine.rms>2: # 120
                                sys.stderr.write( "ERROR: RMS too large %g (amp:%g)\n"%( Sine.rms, Sine.amplitude ) )
                            if Sine.amplitude<6: #3000
                                sys.stderr.write( "ERROR: Sine amplitude too small %s\n"%( str(Sine) ) )


                        NoTdcDelays= [CalcTimeSine4( Sine, sampFreq ).delay for Sine in Sines]

                        if args.no_tdc:
                            Delays = list( NoTdcDelays )
                        else:
                            Delays = [delay-wfm.InitialXOffset for wfm, delay in zip( rec, NoTdcDelays)]

                        try:
                            DelaysPs = [delay*1e12 for delay in Delays]
                            sys.stdout.write( "\t".join( map( str, DelaysPs ) )+tdcString+"\n" )
                            sys.stdout.flush()
                        except BrokenPipeError:
                            _Continue = False

                        #minDelay = min( Delays )
                        #maxDelay = max( Delays )
                        #if abs( maxDelay-minDelay ) > 300:
                        #    sys.stderr.write( "\n\n\n==> Error %d-%d > 300\n\n\n\n"%( maxDelay, minDelay ))
                        #    _Failure = True
                        #    _Continue = False
                        #    break

            elif args.ddc_output_phase:
                assert args.mode=='DDC'

                mrec.view = 'PHASE'

                measuredFreq = signalFreq-args.ddc_local_oscillator_frequency
                for rec in mrec:
                    assert( len(rec)==len(Fetchs) )

                    for phases in zip( *rec ):
                        delays = map( lambda p: p/2/pi/measuredFreq, phases )
                        sys.stdout.write( " ".join( map( str, delays ) )+"\n" )
                
                    sys.stdout.write( "\n" )

            elif calcSkew:
                omega = 2.0*pi*signalFreq/sampFreq

                DelaysAll = [[] for Fetch in Fetchs]

                for rec in mrec:
                    assert( len(rec)==len(Fetchs) )

                    Sines = [CalcFittedSine3( wfm.Samples, omega ) for wfm in rec]
                    assert( len(Sines)==len(Fetchs) )

                    for Sine in Sines:
                        if Sine.rms> 2200: #8:
                            sys.stderr.write( "ERROR: RMS too large %g (amp:%g)\n"%( Sine.rms, Sine.amplitude ) )
                        if Sine.amplitude<5000: #6:
                            sys.stderr.write( "ERROR: Sine amplitude too small %s\n"%( str(Sine) ) )


                    NoTdcDelays= [CalcTimeSine4( Sine, sampFreq ).delay for Sine in Sines]

                    if args.no_tdc:
                        Delays = list( NoTdcDelays )
                    else:
                        Delays = [delay-wfm.InitialXOffset for wfm, delay in zip( rec, NoTdcDelays)]

                    try:
                        DelaysPs = [delay*1e12 for delay in Delays]
                        sys.stdout.write( "\t".join( map( str, DelaysPs ) )+tdcString+"\n" )
                        sys.stdout.flush()
                    except BrokenPipeError:
                        _Continue = False

                    for index, Delay in enumerate( Delays ):
                        DelaysAll[index].append( Delay )

                assert( len(DelaysAll)==len(Fetchs) )

#                Ds = [mean( D ) for D in DelaysAll]
#                Ss = [std( D ) for D in DelaysAll]
#
#                for Std, D in zip( Ss, Ds ):
#                    if Std>80e-12:
#                        sys.stderr.write( "\t".join( map( str, [Std*1e12 for Std in Ss] ) )+"\n" )
#                        sys.stderr.write( " ".join( [str( d*1e12 ) for d in D] )+"\n" )
#                        break
#                        
#                minDelay = min( Delays )
#                maxDelay = max( Delays )
#                diffDelay = maxDelay-minDelay
#                signalPeriod = 1e12/signalFreq
#                if diffDelay>signalPeriod/2:
#                    diffDelay = diffDelay-signalPeriod
#                if abs( diffDelay ) > 300:
#                    sys.stderr.write( "\n\n\n==> Error %d-%d > 300\n\n\n\n"%( maxDelay, minDelay ))
#                    _Failure = True
#                    _Continue = False
#                    break

            else:
                try:
                    OutputTraces( mrec, sys.stdout )
                except BrokenPipeError:
                    _Continue = False
                    break

            measure = measure+1
            Fetchs = None
            mrec = None

        if args.calibration_signal:
            for Vi in Instrs: AgMD2_SetAttributeViString( Vi, "", AGMD2_ATTR_PRIVATE_CALIBRATION_USER_SIGNAL, "" )

        if len( Instrs )>1:
            AgMD2_ModuleSynchronizationConfigureSlaves( Instrs[0], None )

        # Swap cards to test changing master
        if args.rotate_master:
            Instrs   = Instrs[1:]   + [Instrs[0]]
            Handles  = Handles[1:]  + [Handles[0]]

    signal( SIGTERM, oldSigTerm )
    signal( SIGINT,  oldSigInt )

    # Unsynchronize and close modules

    for Vi in Instrs: AgMD2_close( Vi )


if __name__=="__main__":
    global _Continue, _Failure
    _Continue = True
    _Failure = False

    RunSyncAcq()

    # Flush the buffers 
    try:
        sys.stdout.close()
    except:
        pass
    try:
        sys.stderr.close()
    except:
        pass    

    if _Failure:
        sys.exit( 1 )

