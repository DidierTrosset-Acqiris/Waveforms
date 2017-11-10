#!/usr/bin/python3

"""
    Runs continuous acquisitions

    Copyright (C) Keysight Technologies 2015-2017
   
    Started: August 24th, 2015
    By:      Didier Trosset
    Label:   Agilent Confidential

"""


from AgMD2 import *
from waveforms.trace import OutputTrace, OutputTraces
from waveforms import Record, MultiRecord, DDCMultiRecord, AccMultiRecord
from digitizer.argparser import DigitizerArgs, RefreshArgs
from sys import stdin, stdout, stderr
from time import sleep
from signal import signal, SIGTERM, SIGINT
from threading import Thread
from queue import Queue
import json


def Initialize( args, options ):
    """ Initializes all the given resources using AgMD2_InitWithOptions,
        using the given options string.
        @return the list of vi.
    """
    reset = 1 if args.reset else 0
    resources = args.resources
    if isinstance( resources, str ):
        resources = [resources]
    vis = []
    try:
        for rsrc in resources:
            if rsrc[:3]=="SIM":
                model = rsrc[5:11]
                options = "Simulate=1, DriverSetup= Model="+model
                rsrc = ""
                print( "INIT:", rsrc, model, file=stderr )
            Vi = AgMD2_InitWithOptions( rsrc, 0, reset, options )
            vis.append( Vi )
            # Always set private access.
            AgMD2_SetAttributeViString( Vi, "", AGMD2_ATTR_PRIVATE_ACCESS_PASSWORD, "We1ssh0rn" )
            print( "Driver:  ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_SPECIFIC_DRIVER_REVISION, 256 ), file=stderr )
            print( "IOLS:    ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_IO_VERSION, 256 ), file=stderr )
            print( "Model:   ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_MODEL, 256 ), file=stderr )
            print( "Serial:  ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_SERIAL_NUMBER_STRING, 256 ), file=stderr )
            print( "Options: ", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_INFO_OPTIONS, 256 ), file=stderr )
            print( "Firmware:", AgMD2_GetAttributeViString( Vi, "", AGMD2_ATTR_INSTRUMENT_FIRMWARE_REVISION, 256 ), file=stderr )
            if args.info_cores:
                def PrintCoreVersion( Vi, msg, core ):
                    try:
                        version, versionString = AgMD2_LogicDeviceGetCoreVersion ( Vi, "DpuA", core, 32 )
                    except:
                        return
                    print( msg, versionString, file=stderr )
                PrintCoreVersion( Vi, "Core PCIe:   ", AGMD2_VAL_LOGIC_DEVICE_CORE_PCIE )
                PrintCoreVersion( Vi, "Core DDR3A:  ", AGMD2_VAL_LOGIC_DEVICE_CORE_DDR3A )
                PrintCoreVersion( Vi, "Core DDR3B:  ", AGMD2_VAL_LOGIC_DEVICE_CORE_DDR3B )
                PrintCoreVersion( Vi, "Core CalDig: ", AGMD2_VAL_LOGIC_DEVICE_CORE_CALIBRATION_DIGITIZER )
                PrintCoreVersion( Vi, "Core IfdlUp: ", AGMD2_VAL_LOGIC_DEVICE_CORE_IFDL_UP )
                PrintCoreVersion( Vi, "Core IfdlDn: ", AGMD2_VAL_LOGIC_DEVICE_CORE_IFDL_DOWN )
                PrintCoreVersion( Vi, "Core IfdlCt: ", AGMD2_VAL_LOGIC_DEVICE_CORE_IFDL_CONTROL )
                PrintCoreVersion( Vi, "Core QDR2:   ", AGMD2_VAL_LOGIC_DEVICE_CORE_QDR2 )
                PrintCoreVersion( Vi, "Core AdcInt: ", AGMD2_VAL_LOGIC_DEVICE_CORE_ADC_INTERFACE )
                PrintCoreVersion( Vi, "Core StrPr:  ", AGMD2_VAL_LOGIC_DEVICE_CORE_STREAM_PREPARE )
                PrintCoreVersion( Vi, "Core TrgMgr: ", AGMD2_VAL_LOGIC_DEVICE_CORE_TRIGGER_MANAGER )

    except:
        for vi in vis:
            try: AgMD2_close( vi )
            except: pass
        raise
    return vis


def Close( vis ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        for vi in vis:
            try: AgMD2_close( vi )
            except: pass


def ShowInfo( vis ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        print( "Driver:  ", AgMD2_GetAttributeViString( vi, "", AGMD2_ATTR_SPECIFIC_DRIVER_REVISION, 256 ), file=stderr )
        print( "Model:   ", AgMD2_GetAttributeViString( vi, "", AGMD2_ATTR_INSTRUMENT_MODEL, 256 ), file=stderr )
        print( "Serial:  ", AgMD2_GetAttributeViString( vi, "", AGMD2_ATTR_INSTRUMENT_INFO_SERIAL_NUMBER_STRING, 256 ), file=stderr )
        print( "Options: ", AgMD2_GetAttributeViString( vi, "", AGMD2_ATTR_INSTRUMENT_INFO_OPTIONS, 256 ), file=stderr )
        print( "Firmware:", AgMD2_GetAttributeViString( vi, "", AGMD2_ATTR_INSTRUMENT_FIRMWARE_REVISION, 256 ), file=stderr )


def AgMD2_UpdateAttributeViInt8( vi, repCap, attr, value ):
    if AgMD2_GetAttributeViInt8(  vi, repCap, attr )!=value:
        AgMD2_SetAttributeViInt8(  vi, repCap, attr , value )   

def AgMD2_UpdateAttributeViInt16( vi, repCap, attr, value ):
    if AgMD2_GetAttributeViInt16(  vi, repCap, attr )!=value:
        AgMD2_SetAttributeViInt16(  vi, repCap, attr , value )   

def AgMD2_UpdateAttributeViInt32( vi, repCap, attr, value ):
    if AgMD2_GetAttributeViInt32(  vi, repCap, attr )!=value:
        AgMD2_SetAttributeViInt32(  vi, repCap, attr , value )   

def AgMD2_UpdateAttributeViInt64( vi, repCap, attr, value ):
    if AgMD2_GetAttributeViInt64(  vi, repCap, attr )!=value:
        AgMD2_SetAttributeViInt64(  vi, repCap, attr , value )   

def AgMD2_UpdateAttributeViReal64( vi, repCap, attr, value ):
    if AgMD2_GetAttributeViReal64(  vi, repCap, attr )!=value:
        AgMD2_SetAttributeViReal64(  vi, repCap, attr , value )   

def AgMD2_UpdateAttributeViBoolean( vi, repCap, attr, value ):
    if AgMD2_GetAttributeViBoolean(  vi, repCap, attr )!=value:
        AgMD2_SetAttributeViBoolean(  vi, repCap, attr , value )   

def AgMD2_UpdateAttributeViString( vi, repCap, attr, value ):
    if AgMD2_GetAttributeViString(  vi, repCap, attr, 256 )!=value:
        AgMD2_SetAttributeViString(  vi, repCap, attr , value )   


def ApplyArgs( vis, args ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        if AgMD2_GetAttributeViInt32( vi, "", AGMD2_ATTR_IS_IDLE ) != AGMD2_VAL_ACQUISITION_STATUS_RESULT_TRUE:
            AgMD2_Abort( vi )
        # Manages the clocking scheme
        if args.clock_external:
            AgMD2_UpdateAttributeViInt32(  vi, "", AGMD2_ATTR_SAMPLE_CLOCK_SOURCE , AGMD2_VAL_SAMPLE_CLOCK_SOURCE_EXTERNAL )   
            AgMD2_UpdateAttributeViReal64( vi, "", AGMD2_ATTR_SAMPLE_CLOCK_EXTERNAL_FREQUENCY , args.clock_external )   
            AgMD2_UpdateAttributeViReal64( vi, "", AGMD2_ATTR_SAMPLE_CLOCK_EXTERNAL_DIVIDER , args.clock_ext_divider )   
        else:
            AgMD2_UpdateAttributeViInt32(  vi, "", AGMD2_ATTR_SAMPLE_CLOCK_SOURCE , AGMD2_VAL_SAMPLE_CLOCK_SOURCE_INTERNAL )   
            if args.clock_ref_external:
                AgMD2_UpdateAttributeViInt32(  vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_EXTERNAL )
            elif args.clock_ref_pxi:
                AgMD2_UpdateAttributeViInt32(  vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_PXIE_CLK100 )
            elif args.clock_ref_axie:
                AgMD2_UpdateAttributeViInt32(  vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_AXIE_CLK100 )
            else:
                AgMD2_UpdateAttributeViInt32(  vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_INTERNAL )

        # Manages acquisition mode
        if args.mode=='DDC':
            AgMD2_UpdateAttributeViInt32( vi, "", AGMD2_ATTR_ACQUISITION_MODE, AGMD2_VAL_ACQUISITION_MODE_DIGITAL_DOWN_CONVERSION )
            nbrDDCCores = AgMD2_GetAttributeViInt32( vi, "", AGMD2_ATTR_DDCCORE_COUNT )
            DDCCores = ["DDCCore%d"%( core+1 ) for core in range( nbrDDCCores )]
            for ddcCore in DDCCores:
                AgMD2_UpdateAttributeViReal64( vi, ddcCore, AGMD2_ATTR_DDCCORE_CENTER_FREQUENCY, args.ddc_local_oscillator_frequency )
                if args.ddc_decimation_numerator:
                    AgMD2_UpdateAttributeViInt64( vi, ddcCore, AGMD2_ATTR_DDCCORE_DECIMATION_NUMERATOR, args.ddc_decimation_numerator )
                if args.ddc_decimation_denominator:
                    AgMD2_UpdateAttributeViInt64( vi, ddcCore, AGMD2_ATTR_DDCCORE_DECIMATION_DENOMINATOR, args.ddc_decimation_denominator )

        if args.mode=='AVG':
            AgMD2_UpdateAttributeViInt32( vi, "", AGMD2_ATTR_ACQUISITION_MODE, AGMD2_VAL_ACQUISITION_MODE_AVERAGER )
            AgMD2_UpdateAttributeViInt32( vi, "", AGMD2_ATTR_ACQUISITION_NUMBER_OF_AVERAGES, args.averages )

        # Manages conbination
        if args.interleave:
            ch, sub = args.interleave[:2]
            AgMD2_UpdateAttributeViString( vi, "Channel%d"%( ch ), AGMD2_ATTR_TIME_INTERLEAVED_CHANNEL_LIST, "Channel%d"%( sub ) )

        # Manages TSR
        if args.tsr:
            AgMD2_UpdateAttributeViBoolean( vi, "", AGMD2_ATTR_TSR_ENABLED, VI_TRUE if args.tsr else VI_FALSE )

        # Manages streaming
        if args.streaming_continuous or args.streaming_triggered:
            streamingMode = AGMD2_VAL_STREAMING_MODE_CONTINUOUS if args.streaming_continuous else AGMD2_VAL_STREAMING_MODE_TRIGGERED
            AgMD2_UpdateAttributeViInt32( vi, "", AGMD2_ATTR_STREAMING_MODE, streamingMode )

        # Manages sample rate: set to the max, and then adjust if required
        #try: AgMD2_UpdateAttributeViReal64(  vi, "", AGMD2_ATTR_SAMPLE_RATE, 1e10 )
        #except: pass
        if args.sampling_frequency:
            AgMD2_UpdateAttributeViReal64(  vi, "", AGMD2_ATTR_SAMPLE_RATE, args.sampling_frequency )   
        AgMD2_UpdateAttributeViInt64(  vi, "", AGMD2_ATTR_RECORD_SIZE, args.samples )
        AgMD2_UpdateAttributeViInt64(  vi, "", AGMD2_ATTR_NUM_RECORDS_TO_ACQUIRE, args.records )
        assert args.records == AgMD2_GetAttributeViInt64(  vi, "", AGMD2_ATTR_NUM_RECORDS_TO_ACQUIRE )

        # Manages trigger
        if args.immediate_trigger:
            ActiveTrigger = "Immediate"
        else:
            if args.trigger_name:
                ActiveTrigger = args.trigger_name
            elif args.trigger_external:
                ActiveTrigger = "External%d"%( args.trigger_external ) if args.trigger_external!=4 else "AXIe_SYNC"
            elif args.trigger_internal:
                ActiveTrigger = "Internal%d"%( args.trigger_internal )
            else:
                ActiveTrigger = "Internal1"

            if args.trigger_level!=None:
                AgMD2_UpdateAttributeViReal64( vi, ActiveTrigger, AGMD2_ATTR_TRIGGER_LEVEL, args.trigger_level )
            if args.trigger_delay!=None:
                AgMD2_UpdateAttributeViReal64( vi, "", AGMD2_ATTR_TRIGGER_DELAY, args.trigger_delay )
                #stderr.write( "==>td:%g\n"%AgMD2_GetAttributeViReal64( vi, "", AGMD2_ATTR_TRIGGER_DELAY ) )
            if args.trigger_slope!=None:
                if args.trigger_slope in ["negative", "n"]:
                    AgMD2_UpdateAttributeViInt32( vi, ActiveTrigger, AGMD2_ATTR_TRIGGER_SLOPE, AGMD2_VAL_NEGATIVE )
                else:
                    AgMD2_UpdateAttributeViInt32( vi, ActiveTrigger, AGMD2_ATTR_TRIGGER_SLOPE, AGMD2_VAL_POSITIVE )

        AgMD2_UpdateAttributeViString( vi, "", AGMD2_ATTR_ACTIVE_TRIGGER_SOURCE , ActiveTrigger )

        if args.trigger_output_enabled!=None:
            AgMD2_UpdateAttributeViBoolean( vi, "", AGMD2_ATTR_TRIGGER_OUTPUT_ENABLED, VI_TRUE if args.trigger_output_enabled else VI_FALSE )
        if args.trigger_output_source!=None:
            AgMD2_UpdateAttributeViString( vi, "", AGMD2_ATTR_TRIGGER_OUTPUT_SOURCE, args.trigger_output_source )
        if args.trigger_output_offset!=None:
            AgMD2_UpdateAttributeViReal64( vi, "", AGMD2_ATTR_TRIGGER_OUTPUT_OFFSET, args.trigger_output_offset )

        # Manages channels
        for ch in args.read_channels:
            channel = "Channel%d"%( ch )
            if args.vertical_range:  AgMD2_UpdateAttributeViReal64( vi, channel, AGMD2_ATTR_VERTICAL_RANGE,  args.vertical_range )
            if args.vertical_offset: AgMD2_UpdateAttributeViReal64( vi, channel, AGMD2_ATTR_VERTICAL_OFFSET, args.vertical_offset )

        #AgMD2_UpdateAttributeViReal64( vi, "Channel3", AGMD2_ATTR_INPUT_FILTER_MAX_FREQUENCY, 650e6 )

        if args.calibration_signal:
            AgMD2_UpdateAttributeViString( vi, "", AGMD2_ATTR_PRIVATE_CALIBRATION_USER_SIGNAL, "Signal"+args.calibration_signal )

        # Manages ControlIO
        if args.control_io1:
            AgMD2_UpdateAttributeViString( vi, "ControlIO1", AGMD2_ATTR_CONTROL_IO_SIGNAL, args.control_io1 )
        if args.control_io2:
            AgMD2_UpdateAttributeViString( vi, "ControlIO2", AGMD2_ATTR_CONTROL_IO_SIGNAL, args.control_io2 )
        if args.control_io3:
            AgMD2_UpdateAttributeViString( vi, "ControlIO3", AGMD2_ATTR_CONTROL_IO_SIGNAL, args.control_io3 )

        # Manages SelfTrigger
        if args.self_trigger_square_wave:
            AgMD2_UpdateAttributeViInt32( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_MODE, AGMD2_VAL_SELF_TRIGGER_MODE_SQUARE_WAVE )
            AgMD2_UpdateAttributeViReal64( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_SQUARE_WAVE_FREQUENCY, args.self_trigger_wave_frequency )
            AgMD2_UpdateAttributeViReal64( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_SQUARE_WAVE_DUTY_CYCLE, args.self_trigger_wave_duty_cycle )
        elif args.self_trigger_armed_pulse:
            try: # Either we have the armed pulse mode and pulse duration attribute, or we revert to AgMD2-2.4 hack
                AgMD2_UpdateAttributeViInt32( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_MODE, AGMD2_VAL_SELF_TRIGGER_MODE_ARMED_PULSE )
                if args.self_trigger_pulse_duration:
                    AgMD2_UpdateAttributeViReal64( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_PULSE_DURATION, args.self_trigger_pulse_duration )
            except NameError as e:
                print( "ERROR for Armed Pulse", e, file=stderr )
                AgMD2_UpdateAttributeViInt32( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_MODE, AGMD2_VAL_SELF_TRIGGER_MODE_SQUARE_WAVE )
                AgMD2_UpdateAttributeViReal64( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_SQUARE_WAVE_FREQUENCY, args.self_trigger_wave_frequency )
                AgMD2_UpdateAttributeViReal64( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_SQUARE_WAVE_DUTY_CYCLE, args.self_trigger_wave_duty_cycle )
                AgMD2_UpdateAttributeViInt32( vi, "SelfTrigger", AGMD2_ATTR_SELF_TRIGGER_MODE, 2 )#AGMD2_VAL_SELF_TRIGGER_MODE_ARMED_PULSE )

#        from random import randint
#        for ch in [1, 2, 3, 4, 5, 6, 24, 25, 26, 27, 31, 32]:#+[randint(1, 32) for a in range(12)]:
#            AgMD2_SetAttributeViBoolean( vi, "Channel%d"%ch, AGMD2_ATTR_CHANNEL_ENABLED, False )

        # Manages the calibration offset target
        if args.cal_offset_target:
            AgMD2_UpdateAttributeViBoolean( vi, "", AGMD2_ATTR_CALIBRATION_TARGET_VOLTAGE_ENABLED, True )
            for ch in args.read_channels:
                channel = "Channel%d"%( ch )
                AgMD2_UpdateAttributeViReal64( vi, channel, AGMD2_ATTR_CHANNEL_CALIBRATION_TARGET_VOLTAGE,  args.cal_offset_target )

        AgMD2_ApplySetup( vi )
        print( "Firmware:", AgMD2_GetAttributeViString( vi, "", AGMD2_ATTR_INSTRUMENT_FIRMWARE_REVISION, 256 ), file=stderr )


def Calibrate( vis, args, loop ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        calibrate = False
        if AgMD2_GetAttributeViBoolean( vi, "", AGMD2_ATTR_CALIBRATION_IS_REQUIRED ):
            calibrate = True
        if loop==0 or args.calibrate_period and loop%args.calibrate_period==0:
            calibrate = True

        if not calibrate:
            continue

        #print( "==> Calibration required.", file=stderr )
        if args.calibration_signal:
            AgMD2_SetAttributeViString( vi, "", AGMD2_ATTR_PRIVATE_CALIBRATION_USER_SIGNAL, "" )

        AgMD2_SelfCalibrate( vi )

        if args.calibration_signal:
            AgMD2_SetAttributeViString( vi, "", AGMD2_ATTR_PRIVATE_CALIBRATION_USER_SIGNAL, "Signal"+args.calibration_signal )

        if args.trigger_name=="SelfTrigger":
            AgMD2_SelfTriggerInitiateGeneration( vi, "SelfTrigger" )


def Acquire( vis, args, queue, loop ):
    global _Continue
    if isinstance( vis, int ):
        vis = [vis]
    if args.tsr:
        for vi in vis:
            # To find whether the acquisition is already started, try to continue it. In case of error, start it.
            try:
                #print( "TSR Continue", file=stderr )
                AgMD2_TSRContinue( vi )
                overflow = AgMD2_GetAttributeViBoolean( vi, "", AGMD2_ATTR_TSR_MEMORY_OVERFLOW_OCCURRED )
                if overflow:
                    print( "ERROR: TSR MEMORY OVERFLOW", file=stderr )
                    _Continue = False
                    AgMD2_Abort( vi )
                    #return False
            except:
                #print( "\nPress ENTER", file=stderr )
                #stdin.readline()
                #print( "Initiate Acquistion", file=stderr )
                AgMD2_InitiateAcquisition( vi )

            polls = 0
            #while _Continue:
            for a in range(10000):
                complete = AgMD2_GetAttributeViBoolean( vi, "", AGMD2_ATTR_TSR_IS_ACQUISITION_COMPLETE )
                #print( "GetAttribute TSR_IS_ACQUISITION_COMPLETE :", complete, file=stderr )
                if a==9999 or complete:
                    print( "GetAttribute TSR_IS_ACQUISITION_COMPLETE", polls, " :", "0 -> ", complete, file=stderr )
                if complete:
                    return True
                polls = polls + 1
                sleep( 0.0001 )

    elif args.streaming_continuous or args.streaming_triggered:
        for vi in vis:
            if AgMD2_GetAttributeViInt32( vi, "", AGMD2_ATTR_IS_IDLE ) == AGMD2_VAL_ACQUISITION_STATUS_RESULT_TRUE:
                AgMD2_InitiateAcquisition( vi )
        return True

    else:
        for vi in vis:
            #if args.trigger_name=="SelfTrigger":
            #    AgMD2_SelfTriggerInitiateGeneration( vi, "SelfTrigger" )
            AgMD2_InitiateAcquisition( vi )

        while True:
            # Manages wait/poll
            if args.poll_timeout:
                for vi in vis:
                    acqDone = False
                    fullwait = float( args.poll_timeout )
                    while fullwait>=0 and _Continue and queue.empty() and not acqDone:
                        oncewait = min( 0.2, fullwait )
                        sleep( oncewait/1000.0 )
                        fullwait = fullwait-oncewait
                        isIdle = AgMD2_GetAttributeViInt32( vi, "", AGMD2_ATTR_IS_IDLE )
                        acqDone = isIdle==AGMD2_VAL_ACQUISITION_STATUS_RESULT_TRUE
                    if acqDone:
                        return True
                    else:
                        AgMD2_Abort( vi )
                        return False
            else:
                try:
                    for vi in vis:
                        AgMD2_WaitForAcquisitionComplete( vi, int( args.wait_timeout*1000 )+1 )
                    return True
                except RuntimeError as e:
                    if args.wait_failure:
                        raise
                    else:
                        #print( "WaitForAcquisitionComplete: MAX_TIME_EXCEEDED.", file=stderr )
                        #if not _Continue or not queue.empty():
                            AgMD2_Abort( vi )
                            _Continue = False
                            return True#False



def FetchChannels( vis, args ):
    global _Continue
    if isinstance( vis, int ):
        vis = [vis]
        # Manages readout
    nbrAdcBits = AgMD2_GetAttributeViInt32( vis[0], "", AGMD2_ATTR_INSTRUMENT_INFO_NBR_ADC_BITS )

    if args.streaming_continuous or args.streaming_triggered:
        sleep( 0.01 )
        for vi in vis:
            tsCount = 32*1024
            fetch = AgMD2_StreamFetchDataInt32( vi, "StreamTriggers", tsCount, tsCount )
            if fetch[3] == tsCount:
                print( "Fetch: ", 0, fetch[2], fetch[3], fetch[4], file=stderr )
                with open( "ts.txt", "at" ) as f:
                  for ts in fetch[0][fetch[4]:fetch[4]+fetch[3]].view( 'uint64' ):
                      print( ts/256, file=f )
            else:
                print( "Available: ", 0, fetch[2], fetch[3], fetch[4], file=stderr )
            chCount = 8*1024*1024
            fetchCh1 = AgMD2_StreamFetchDataInt32( vi, "StreamCh1", chCount, chCount )
            if fetchCh1[3] == chCount:
                print( "FetchCh1: ", 0, fetchCh1[2], fetchCh1[3], fetchCh1[4], file=stderr )
            fetchCh2 = AgMD2_StreamFetchDataInt32( vi, "StreamCh2", chCount, chCount )
            if fetchCh2[3] == chCount:
                print( "FetchCh2: ", 0, fetchCh2[2], fetchCh2[3], fetchCh2[4], file=stderr )
        return
    
    if args.mode=='DDC':
        for vi in vis:
            if args.ddc_decimation_numerator==4:
                DataWidth = 16
                Fetch = AgMD2_DDCCoreFetchWaveformInt16Py
            else:
                DataWidth = 32
                Fetch = AgMD2_DDCCoreFetchWaveformInt32Py
            nbrSamplesToRead = AgMD2_QueryMinWaveformMemory( vi, DataWidth, 1, 0, args.read_samples )

            mrec = DDCMultiRecord( checkXOffset=not args.no_check_x_offset, nbrAdcBits=nbrAdcBits )
            mrec.view = args.ddc_sample_view
            for ch in args.read_channels:
                mrec.append( Fetch( vi, "DDCCore%d"%( ch ), 0, args.read_records, 0, args.read_samples, 2*nbrSamplesToRead, args.read_records ) )

            try:
                OutputTraces( mrec, stdout )
            except BrokenPipeError:
                _Continue = False
                break

    elif args.mode=='AVG':
        for vi in vis:
            if args.read_type == 'real64':
                DataWidth = 64
                Fetch = AgMD2_FetchAccumulatedWaveformReal64Py
            else:
                DataWidth = 32
                Fetch = AgMD2_FetchAccumulatedWaveformInt32Py
            nbrSamplesToRead = AgMD2_QueryMinWaveformMemory( vi, DataWidth, args.read_records, 0, args.read_samples )

            mrec = AccMultiRecord( checkXOffset=not args.no_check_x_offset, nbrAdcBits=nbrAdcBits )
            #print( "Fetch", file=stderr )
            for ch in args.read_channels:
                try:
                    #mrec.append( Fetch( vi, "Channel%d"%( ch ), 0, args.read_records, 0, args.read_samples, nbrSamplesToRead, args.read_records ) )
                    fetch = Fetch( vi, "Channel%d"%( ch ), 0, args.read_records, 0, args.read_samples, nbrSamplesToRead, args.read_records )
                    #fetch[1] = args.averages
                except RuntimeError:
                    AgMD2_SetAttributeViBoolean( vi, "", AGMD2_ATTR_ERROR_ON_OVERRANGE_ENABLED, False )
                    fetch = Fetch( vi, "Channel%d"%( ch ), 0, args.read_records, 0, args.read_samples, nbrSamplesToRead, args.read_records )
                    AgMD2_SetAttributeViBoolean( vi, "", AGMD2_ATTR_ERROR_ON_OVERRANGE_ENABLED, True )
                mrec.append( fetch )

            try:
                OutputTraces( mrec, stdout, FirstRecord=args.output_1st_record, NbrRecords=args.output_records, NbrSamples=args.output_samples )
                stdout.write( "\n" )
                stdout.flush()
                #print( "$InitialXTimeSeconds", fetch[6][0], file=stdout )
                #print( "$InitialXTimeFraction", fetch[7][0], file=stdout )
            except BrokenPipeError:
                _Continue = False
                break

    else:
        if not args.read_type:
            args.read_type = 'int8' if nbrAdcBits<=8 else 'int16'
        if args.records<=1:
            if args.read_type=='int16':
                DataWidth = 16
                Fetch = AgMD2_FetchWaveformInt16
            elif args.read_type=='real64':
                DataWidth = 64
                Fetch = AgMD2_FetchWaveformReal64
            else:
                DataWidth = 8
                Fetch = AgMD2_FetchWaveformInt8
            nbrSamplesToRead = AgMD2_QueryMinWaveformMemory( vis[0], DataWidth, 1, 0, args.read_samples )

            rec = Record( checkXOffset=not args.no_check_x_offset, nbrAdcBits=nbrAdcBits )
            try:
                for vi in vis:
                    for ch in args.read_channels:
                        rec.append( Fetch( vi, "Channel%d"%( ch ), nbrSamplesToRead ) )
            except RuntimeError:
                for vi in vis:
                    try:
                        AgMD2_SetAttributeViBoolean( vi, "", AGMD2_ATTR_ERROR_ON_OVERRANGE_ENABLED, False )
                    except:
                        continue
                for vi in vis:
                    for ch in args.read_channels:
                        rec.append( Fetch( vi, "Channel%d"%( ch ), nbrSamplesToRead ) )
                for vi in vis:
                    AgMD2_SetAttributeViBoolean( vi, "", AGMD2_ATTR_ERROR_ON_OVERRANGE_ENABLED, True )

            try:
                OutputTrace( rec, stdout )
            except BrokenPipeError:
                _Continue = False

        else:
            if args.read_type=='int16':
                DataWidth = 16
                Fetch = AgMD2_FetchMultiRecordWaveformInt16Py
            elif args.read_type=='real64':
                DataWidth = 64
                Fetch = AgMD2_FetchMultiRecordWaveformReal64Py
            else:
                DataWidth = 8
                Fetch = AgMD2_FetchMultiRecordWaveformInt8
            nbrSamplesToRead = AgMD2_QueryMinWaveformMemory( vis[0], DataWidth, args.read_records, 0, args.read_samples )

            mrec = MultiRecord( checkXOffset=not args.no_check_x_offset, nbrAdcBits=nbrAdcBits ) 
            for vi in vis:
                for ch in args.read_channels:
                    mrec.append( Fetch( vi, "Channel%d"%( ch ), 0, args.read_records, 0, args.read_samples, nbrSamplesToRead, args.read_records ) )

            try:
                OutputTraces( mrec, stdout )
            except BrokenPipeError:
                _Continue = False


class Runner():
    """
    >>> args = {}
    >>> r = Runner( args )
    >>> r.Run()
    """
    def __init__( self, args ):
        self.args = args

    def Run( self ):
        Run( self.args )


def UpdateArgs( args, queue ):
    hasChanged = False
    while not queue.empty():
        commands = queue.get_nowait()
        for attribute, value in commands.items():
            try:
                oldvalue = getattr( args, attribute )
                setattr( args, attribute, value )
                if oldvalue!=value:
                    print( "Setting parameter", attribute, value, file=stderr )
                    hasChanged = True
            except AttributeError as e:
                print( "Unknown parameter", attribute, file=stderr )
    if hasChanged:
        RefreshArgs( args )
    return hasChanged


_Continue = True


def _SignalEndLoop( sig, frame ):
    global _Continue
    _Continue = False


def Run( args, queue ):
    global _Continue

    args = DigitizerArgs()

    vis = Initialize( args, "" )
    #ShowInfo( vis )
    ApplyArgs( vis, args )

    oldSigTerm = signal( SIGTERM, _SignalEndLoop )
    oldSigInt  = signal( SIGINT,  _SignalEndLoop )

    loop = 0
    while _Continue:

        if UpdateArgs( args, queue ):
            ApplyArgs( vis, args )
            
        Calibrate( vis, args, loop )

        if Acquire( vis, args, queue, loop ):
            FetchChannels( vis, args )

        # Manages looping
        loop = loop+1

        if args.loops<0:
            continue

        if loop>=args.loops:
            if args.tsr:
                for vi in vis:
                    AgMD2_Abort( vi )
            break

    signal( SIGTERM, oldSigTerm )
    signal( SIGINT,  oldSigInt )

    # Close modules
    Close( vis )


def ReadCommands( ins, queue ):
    global _Continue

    for bytecmd in ins:
        if bytecmd=="":
            break
        strcmd = bytecmd.strip()
        if bytecmd=="":
            continue
        try:
            cmd = json.loads( strcmd )
            queue.put( cmd )
        except Exception as e:
            print( e, file=stderr )
    # Exit when input closes
    _Continue = False


def main():
    queue = Queue()
    cmdthread = Thread( target=ReadCommands, args=( stdin, queue ), daemon=True )
    cmdthread.start()
    Run( DigitizerArgs(), queue )


if __name__=="__main__":
    main()
    # Ignore if the output file has been broken (receiver command stopped)
    try: stdout.close()
    except BrokenPipeError: pass

