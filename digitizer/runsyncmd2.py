#!/usr/bin/python3

"""
    Runs continuous acquisitions in synchronized M9730B instruments

    Copyright (C) Agilent Technologies, Inc. 2015
   
    Started: April 16th, 2013
    By:      Didier Trosset
    Label:   Agilent Confidential

"""

from __future__ import print_function

from AgMD2 import *
from waveforms.trace import OutputTrace
from waveforms import Record, MultiRecord
from digitizer.argparser import DigitizerParser, DigitizerArgs
#from UtilsAgMD2 import Waveform, Waveforms
#from ArgParser import DigitizerParser, DigitizerArgs
#from UtilsCheck import CheckSineContinuity, DiscontinuityException
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


def RunSyncAcq():
    global _Continue, _Failure

    parser = DigitizerParser()
    parser.add_argument( "--inner-loops", "-ll", nargs='?', type=int, default=1 )
    parser.add_argument( "--skew", default=False, action='store_true' )
    parser.add_argument( "--moving-sine-fit", default=False, action='store_true' )
    parser.add_argument( "--sine-fit-width", "-sfw", nargs=None, type=int, default=0 )
    parser.add_argument( "--sine-fit-step", "-sfs", nargs=None, type=int, default=0 )
    parser.add_argument( "--frequency", "-f", nargs=None, type=float, default=100e6 )
    parser.add_argument( "--cal100", default=False, action='store_true' )
    parser.add_argument( "--send-axie-triggers", default=False, action='store_true' )
    parser.add_argument( "--read-tdc", default=False, action='store_true' )
    parser.add_argument( "--rotate-master", default=False, action='store_true' )
    parser.add_argument( "--check-continuity", default=False, action='store_true' )
    parser.add_argument( "--no-tdc", default=False, action='store_true' )
    parser.add_argument( "--clock-restart-period", "-ksp", nargs='?', type=int, default=0 )
    parser.add_argument( "--dpu-bitfile", "-db", nargs=None, type=str )
    parser.add_argument( "--immediate-trigger", "-it", default=False, action='store_true' )
    args = DigitizerArgs( parser )

    if ( args.skew or args.moving_sine_fit ) and not sineFitAvailable:
        print( "ERROR: Cannot calculate skew as scipy is not available.", file=sys.stderr )
        return

    options = ""
    if args.dpu_bitfile:
        bf = args.dpu_bitfile
        options = options+", UserDpuA=%s, UserDpuB=%s, UserDpuC=%s, UserDpuD=%s"%( bf, bf, bf, bf )

    try:
        Instrs = [AgMD2_InitWithOptions( rsrc, 0, 0, options ) for rsrc in args.resources]
    except RuntimeError:
        _Failure = True
        raise

    for Vi in Instrs:
        print( "Driver:  ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_SPECIFIC_DRIVER_REVISION, 256 ), file=sys.stderr )
        print( "IOLS:    ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_IO_VERSION, 256 ), file=sys.stderr )
        print( "Model:   ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_MODEL, 256 ), file=sys.stderr )
        print( "Serial:  ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_SERIAL_NUMBER_STRING, 256 ), file=sys.stderr )
        print( "Options: ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_OPTIONS, 256 ), file=sys.stderr )
        print( "Firmware:", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_FIRMWARE_REVISION, 256 ), file=sys.stderr )

    nbrRecords = args.records
    try: nbrSamples = args.samples[0]
    except: nbrSamples = args.samples
    nbrLoops =   args.loops
    calcSkew =   args.skew
    useCal100 =  args.cal100
    sendAXIeTriggers = args.send_axie_triggers
    calcMovingSineFit = args.moving_sine_fit
    sineFitWidth = args.sine_fit_width if args.moving_sine_fit else 0
    sineFitStep = args.sine_fit_step if args.moving_sine_fit and args.sine_fit_step else sineFitWidth

    RecordSize = nbrSamples if nbrSamples>4096 else 4096

    Serials = [AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_SERIAL_NUMBER_STRING, 32 ) for Vi in Instrs]
    Handles = [AgMD2_GetAttributeViInt32( Vi, "", AGMD2_ATTR_MODULE_SYNCHRONIZATION_HANDLE ) for Vi in Instrs]

    if args.clock_external:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_SOURCE, AGMD2_VAL_SAMPLE_CLOCK_SOURCE_EXTERNAL )
        for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_EXTERNAL_FREQUENCY, args.clock_external )
        for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_EXTERNAL_DIVIDER, args.clock_ext_divider )
    elif args.clock_ref_axie:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_AXIE_CLK100 )
    elif args.clock_ref_external:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_EXTERNAL )

    sampFreq = args.sampling_frequency if args.sampling_frequency else 1.6e9
    for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, "", AGMD2_ATTR_SAMPLE_RATE, sampFreq )
    for Vi in Instrs: AgMD2_SetAttributeViInt64(  Vi, "", AGMD2_ATTR_RECORD_SIZE, RecordSize )
    for Vi in Instrs: AgMD2_SetAttributeViInt64(  Vi, "", AGMD2_ATTR_NUM_RECORDS_TO_ACQUIRE, nbrRecords )

    triggerSource = "External%d"%( args.trigger_external ) if args.trigger_external else "Internal%d"%( args.trigger_internal )
    triggerLevel = args.trigger_level if args.trigger_level else 0.0
    if args.immediate_trigger:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, triggerSource, AGMD2_ATTR_TRIGGER_TYPE, AGMD2_VAL_IMMEDIATE_TRIGGER )   
    else:
        for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, triggerSource, AGMD2_ATTR_TRIGGER_TYPE, AGMD2_VAL_EDGE_TRIGGER )   
        if triggerSource!="External4":
            for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, triggerSource, AGMD2_ATTR_TRIGGER_LEVEL, triggerLevel )   
    for Vi in Instrs: AgMD2_SetAttributeViString( Vi, "", AGMD2_ATTR_ACTIVE_TRIGGER_SOURCE, triggerSource )

    triggerDelay = args.trigger_delay if args.trigger_delay else 0.0
    for Vi in Instrs: AgMD2_SetAttributeViReal64( Vi, "", AGMD2_ATTR_TRIGGER_DELAY, triggerDelay )

    InstrsToRead = list( Instrs )
    ChannelsToRead = ["Channel%d"%( ch ) for ch in args.read_channels]

    oldSigTerm = signal( SIGTERM, SignalEndLoop )
    oldSigInt  = signal( SIGINT,  SignalEndLoop )

    nbrMeasures = args.inner_loops

    Channels = []
    for Vi in InstrsToRead:
        for Ch in ChannelsToRead:
            Channels.append( ( Vi, Ch ) )

    loop = 0
    while _Continue:

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

        if args.clock_restart_period and loop%args.clock_restart_period==0:
            sampleClockSources =  [AgMD2_GetAttributeViInt32( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_SOURCE ) for Vi in Instrs]
            sampleRefOscSources = [AgMD2_GetAttributeViInt32( Vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE ) for Vi in Instrs]
            for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_SOURCE, AGMD2_VAL_SAMPLE_CLOCK_SOURCE_INTERNAL )
            for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_INTERNAL )

            for Vi in Instrs: AgMD2_InitiateAcquisition( Vi )

            if sendAXIeTriggers:
                SendAXIeTriggers( Instrs[0], nbrRecords )

            for Vi in Instrs: AgMD2_WaitForAcquisitionComplete( Vi, 20000 )

            for Vi, scs  in zip( Instrs, sampleClockSources ):  AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_SAMPLE_CLOCK_SOURCE, scs )
            for Vi, sros in zip( Instrs, sampleRefOscSources ): AgMD2_SetAttributeViInt32( Vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, sros )

            for Vi in Instrs: AgMD2_SelfCalibrate( Vi )

        if loop==0 or args.calibrate_period and loop%args.calibrate_period==0:
            for Vi in Instrs: AgMD2_SelfCalibrate( Vi )

        AgMD2_ModuleSynchronizationConfigureSlaves( Instrs[0], Handles[1:] )

        if useCal100:
            signalFreq = 100e6
            for Vi in Instrs: AgMD2_SetAttributeViInt32( Vi, "Channel1", AGMD2_ATTR_INPUT_CONNECTOR_SELECTION, 103 ) # Sets CalSignalMode to 100 MHz
        else:
            signalFreq = args.frequency

        for acq in range( nbrMeasures ):

            AgMD2_InitiateAcquisition( Instrs[0] )

            if sendAXIeTriggers:
                SendAXIeTriggers( Instrs[0], nbrRecords )

            AgMD2_WaitForAcquisitionComplete( Instrs[0], 20000 )

            # Read data on master and slaves.
            wfmSize = AgMD2_QueryMinWaveformMemory( Vi, 16, nbrRecords, 0, nbrSamples )
            Fetchs = [AgMD2_FetchMultiRecordWaveformInt16Py( Vi, Ch, 0, nbrRecords, 0, nbrSamples, wfmSize, nbrRecords ) for Vi, Ch in Channels ]
            mrec = MultiRecord( Fetchs )

            tdcString = ""
            if args.read_tdc:
                Tdcs = [AgMD2_UserControlReadControlRegisterInt32( Vi, 0xa88 ) % 0x10000 for Vi, Ch in Channels]
                tdcString = " "+" ".join( [str(tdc) for tdc in Tdcs] )

            if calcMovingSineFit:
                omega = 2.0*pi*signalFreq/sampFreq

                for Wfms in zip( *MRecs ):
                    assert( len(Wfms)==len(Fetchs) )

                    actualSamples = min( [Wfm.ActualPoints for Wfm in Wfms] )

                    for sample in range( 0, actualSamples-sineFitWidth, sineFitStep ):
                        Chunks = [Wfm.GetSamples()[sample:sample+sineFitWidth] for Wfm in Wfms]

                        if args.check_continuity:
                            try:
                                for Chunk in Chunks: CheckSineContinuity( Chunk )
                            except DiscontinuityException as e:
                                sys.stderr.write( "ERROR: Discontinuity in Waveform (%s)\n"%( str(e) ) )

                        Sines = [CalcFittedSine3( Chunk, omega ) for Chunk in Chunks]
                        assert( len(Sines)==len(Fetchs) )

                        for Sine in Sines:
                            if Sine.rms> 1200:
                                sys.stderr.write( "ERROR: RMS too large %g (amp:%g)\n"%( Sine.rms, Sine.amplitude ) )
                            if Sine.amplitude<3000:
                                sys.stderr.write( "ERROR: Sine amplitude too small %s\n"%( str(Sine) ) )


                        NoTdcDelays= [CalcTimeSine4( Sine, sampFreq ).delay for Sine in Sines]

                        if args.no_tdc:
                            Delays = list( NoTdcDelays )
                        else:
                            Delays = [Delay-Wfm.InitialXOffset for Wfm, Delay in zip( Wfms, NoTdcDelays)]

                        assert( len(Delays)==len(Fetchs) )

                        try:
                            DelaysPs = [delay*1e12 for delay in Delays]
                            sys.stdout.write( "\t".join( map( str, DelaysPs ) )+tdcString+"\n" )
                            sys.stdout.flush()
                        except BrokenPipeError:
                            _Continue = False

                        minDelay = min( Delays )
                        maxDelay = max( Delays )
                        if abs( maxDelay-minDelay ) > 300:
                            sys.stderr.write( "\n\n\n==> Error %d-%d > 300\n\n\n\n"%( maxDelay, minDelay ))
                            _Failure = True
                            _Continue = False
                            break

            elif calcSkew:
                omega = 2.0*pi*signalFreq/sampFreq

                DelaysAll = [[] for Fetch in Fetchs]

                for Wfms in zip( *MRecs ):
                    assert( len(Wfms)==len(Fetchs) )

                    Sines = [CalcFittedSine3( Wfm.GetSamples(), omega ) for Wfm in Wfms]
                    assert( len(Sines)==len(Fetchs) )

                    for Sine in Sines:
                        if Sine.rms> 2200:
                            sys.stderr.write( "ERROR: RMS too large %g (amp:%g)\n"%( Sine.rms, Sine.amplitude ) )
                        if Sine.amplitude<5000:
                            sys.stderr.write( "ERROR: Sine amplitude too small %s\n"%( str(Sine) ) )


                    NoTdcDelays= [CalcTimeSine4( Sine, sampFreq ).delay for Sine in Sines]

                    if args.no_tdc:
                        Delays = list( NoTdcDelays )
                    else:
                        Delays = [Delay-Wfm.InitialXOffset for Wfm, Delay in zip( Wfms, NoTdcDelays)]

                    try:
                        DelaysPs = [delay*1e12 for delay in Delays]
                        sys.stdout.write( "\t".join( map( str, DelaysPs ) )+tdcString+"\n" )
                        sys.stdout.flush()
                    except BrokenPipeError:
                        _Continue = False

                    for index, Delay in enumerate( Delays ):
                        DelaysAll[index].append( Delay )

                assert( len(DelaysAll)==len(Fetchs) )

                Ds = [mean( D ) for D in DelaysAll]
                Ss = [std( D ) for D in DelaysAll]

                for Std, D in zip( Ss, Ds ):
                    if Std>80e-12:
                        sys.stderr.write( "\t".join( map( str, [Std*1e12 for Std in Ss] ) )+"\n" )
                        sys.stderr.write( " ".join( [str( d*1e12 ) for d in D] )+"\n" )
                        break
                        
                minDelay = min( Delays )
                maxDelay = max( Delays )
                diffDelay = maxDelay-minDelay
                signalPeriod = 1e12/signalFreq
                if diffDelay>signalPeriod/2:
                    diffDelay = diffDelay-signalPeriod
                if abs( diffDelay ) > 300:
                    sys.stderr.write( "\n\n\n==> Error %d-%d > 300\n\n\n\n"%( maxDelay, minDelay ))
                    _Failure = True
                    _Continue = False
                    break

            else:
                try:
                    sampIval = mrec.XIncrement

                    for rec in mrec:
                        horPos = rec.InitialXOffset
                        print( "$#ADCS",      1 )
                        print( "$#CHANNELS",  "%d"%( len(rec) ) )
                        print( "$SIGNED",     1 )
                        print( "$FORMATTING", "DECIMAL" )
                        print( "$FULLSCALE",  "65536" )
                        print( "$MODEL",      "M9703A" )
                        print( "$SERIALNO",   " ".join( Serials ) )
                        print( "$SAMPIVAL",   sampIval )
                        print( "$CHANNELFSR", -1 )
                        print( "$HORPOS",     horPos )

                        for n in range( nbrSamples ):
                            print( " ".join( [ str( wfm[n] ) for wfm in rec ] ) )

                        print()
                        sys.stdout.flush()

                except BrokenPipeError:
                    _Continue = False
                    break

            Fetchs = None
            mrec = None

        if not _Continue:
            break

        loop = loop+1

        AgMD2_ModuleSynchronizationConfigureSlaves( Instrs[0], None )

        # Swap cards to test changing master
        if args.rotate_master:
            Instrs   = Instrs[1:]   + [Instrs[0]]
            Handles  = Handles[1:]  + [Handles[0]]

        if nbrLoops<0:
            continue

        if loop>=nbrLoops:
            break

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

