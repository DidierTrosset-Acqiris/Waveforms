#!/usr/bin/python3

"""
    Runs continuous acquisitions

    Copyright (C) Keysight Technologies 2015
   
    Started: August 24th, 2015
    By:      Didier Trosset
    Label:   Agilent Confidential

"""


from AgMD1 import *
from waveforms.trace import OutputTrace
from waveforms import Record, MultiRecord
from digitizer import DigitizerArgs
from sys import stdout, stderr
from time import sleep
from signal import signal, SIGTERM, SIGINT


def Initialize( resources, options ):
    """ Initializes all the given resources using AgMD1_InitWithOptions,
        using the given options string.
        @return the list of vi.
    """
    if isinstance( resources, str ):
        resources = [resources]
    vis = []
    try:
        for rsrc in resources:
            vis.append( AgMD1_InitWithOptions( rsrc, 0, 0, options ) )
    except:
        for vi in vis:
            try: AgMD1_close( vi )
            except: pass
        raise
    return vis


def Close( vis ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        for vi in vis:
            try: AgMD1_close( vi )
            except: pass


def ShowInfo( vis ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        print( "Model:   ", AgMD1_GetAttributeViString( vi, "", AGMD1_ATTR_INSTRUMENT_MODEL, 256 ), file=stderr )
        print( "Serial:  ", AgMD1_GetAttributeViString( vi, "", AGMD1_ATTR_INSTRUMENT_INFO_SERIAL_NUMBER_STRING, 256 ), file=stderr )
        print( "Options: ", AgMD1_GetAttributeViString( vi, "", AGMD1_ATTR_INSTRUMENT_INFO_OPTIONS, 256 ), file=stderr )
        print( "Firmware:", AgMD1_GetAttributeViString( vi, "", AGMD1_ATTR_INSTRUMENT_FIRMWARE_REVISION, 256 ), file=stderr )


def ApplyArgs( vis, args ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        # Manages the clocking scheme
        if args.clock_external:
            AgMD1_SetAttributeViInt32(  vi, "", AGMD1_ATTR_SAMPLE_CLOCK_SOURCE , AGMD1_VAL_SAMPLE_CLOCK_SOURCE_EXTERNAL )   
            AgMD1_SetAttributeViReal64( vi, "", AGMD1_ATTR_SAMPLE_CLOCK_EXTERNAL_FREQUENCY , args.clock_external )   
            AgMD1_SetAttributeViReal64( vi, "", AGMD1_ATTR_SAMPLE_CLOCK_EXTERNAL_DIVIDER , args.clock_ext_divider )   
        else:
            if args.clock_ref_external:
                AgMD1_SetAttributeViInt32(  vi, "", AGMD1_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD1_VAL_REFERENCE_OSCILLATOR_SOURCE_EXTERNAL )
            elif args.clock_ref_axie:
                AgMD1_SetAttributeViInt32(  vi, "", AGMD1_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD1_VAL_REFERENCE_OSCILLATOR_SOURCE_AXIE_CLK100 )

        # Manages conbination
        #AgMD1_SetAttributeViString( vi, "Channel1", AGMD1_ATTR_TIME_INTERLEAVED_CHANNEL_LIST, "Channel2" )

        # Manages sample rate: set to the max, and then adjust if required
        AgMD1_SetAttributeViReal64(  vi, "", AGMD1_ATTR_SAMPLE_RATE, 1e10 )
        if args.sampling_frequency:
            AgMD1_SetAttributeViReal64(  vi, "", AGMD1_ATTR_SAMPLE_RATE, args.sampling_frequency )   
        AgMD1_SetAttributeViInt64(  vi, "", AGMD1_ATTR_RECORD_SIZE, args.samples )
        AgMD1_SetAttributeViInt64(  vi, "", AGMD1_ATTR_NUM_RECORDS_TO_ACQUIRE, args.records )
        assert args.records == AgMD1_GetAttributeViInt64(  vi, "", AGMD1_ATTR_NUM_RECORDS_TO_ACQUIRE )

        # Manages trigger
        if args.trigger_external:
            ActiveTrigger = "External%d"%( args.trigger_external )
        elif args.trigger_internal:
            ActiveTrigger = "Channel%d"%( args.trigger_internal )
        else:
            ActiveTrigger = "Channel1"

        AgMD1_SetAttributeViString( vi, "", AGMD1_ATTR_ACTIVE_TRIGGER_SOURCE , ActiveTrigger )
        if args.trigger_level:
            AgMD1_SetAttributeViReal64( vi, ActiveTrigger, AGMD1_ATTR_TRIGGER_LEVEL, args.trigger_level )
        if args.trigger_delay:
            AgMD1_SetAttributeViReal64( vi, "", AGMD1_ATTR_TRIGGER_DELAY, args.trigger_delay )
            stderr.write( "==>td:%g\n"%AgMD1_GetAttributeViReal64( vi, "", AGMD1_ATTR_TRIGGER_DELAY ) )

        # Manages calibration
        if not args.no_calibrate:
            AgMD1_CalibrationSelfCalibrate( vi, 4 if args.calibrate_fast else 0, args.calibrate_channel )


def Calibrate( vis, args, loop ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        if not args.no_calibrate and args.calibrate_period and loop!=0 and loop%args.calibrate_period==0:
            AgMD1_CalibrationSelfCalibrate( vi, 4 if args.calibrate_fast else 0, args.calibrate_channel )


def Acquire( vis, args ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        AgMD1_InitiateAcquisition( vi )

        # Manages wait/poll
        if args.poll_timeout:
            acqDone = False
            fullwait = float( args.poll_timeout )
            while fullwait>=0 and _Continue and not acqDone:
                oncewait = min( 0.2, fullwait )
                sleep( oncewait/1000.0 )
                fullwait = fullwait-oncewait
                isIdle = AgMD1_GetAttributeViInt32( vi, "", AGMD1_ATTR_IS_IDLE )
                acqDone = isIdle==AGMD1_VAL_ACQUISITION_STATUS_RESULT_TRUE
        else:
            AgMD1_WaitForAcquisitionComplete( vi, int( args.wait_timeout*1000 )+1 )


def FetchChannels( vis, args ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        # Manages readout
        if args.records<=1:
            if args.read_type=='int16':
                DataWidth = 16
                Fetch = AgMD1_FetchWaveformInt16
            elif args.read_type=='real64':
                DataWidth = 64
                Fetch = AgMD1_FetchWaveformReal64
            else:
                DataWidth = 8
                Fetch = AgMD1_FetchWaveformInt8
            nbrSamplesToRead = AgMD1_QueryMinWaveformMemory( vi, DataWidth, 1, 0, args.read_samples )

            rec = Record()
            for ch in args.read_channels[:1]:
                rec.append( Fetch( vi, "Channel%d"%( ch ), nbrSamplesToRead ) )
            try:
                OutputTrace( rec, stdout )
            except BrokenPipeError:
                break;

        else:
            if args.read_type=='int16':
                DataWidth = 16
                Fetch = AgMD1_FetchMultiRecordWaveformInt16Py
            elif args.read_type=='real64':
                DataWidth = 64
                Fetch = AgMD1_FetchMultiRecordWaveformReal64Py
            else:
                DataWidth = 8
                Fetch = AgMD1_FetchMultiRecordWaveformInt8
            nbrSamplesToRead = AgMD1_QueryMinWaveformMemory( vi, DataWidth, args.read_records, 0, args.read_samples )

            mrec = MultiRecord()
            for ch in args.read_channels[:1]:
                mrec.append( Fetch( vi, "Channel%d"%( ch ), 0, args.read_records, 0, args.read_samples, nbrSamplesToRead, args.read_records ) )
            try:
                for rec in mrec:
                    OutputTrace( rec, stdout )
            except BrokenPipeError:
                break;


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



_Continue = True


def _SignalEndLoop( sig, frame ):
    global _Continue
    _Continue = False


def Run( args ):
    global _Continue

    args = DigitizerArgs()

    vis = Initialize( args.resources, "DriverSetup= cal=0" )
    ShowInfo( vis )
    ApplyArgs( vis, args )

    oldSigTerm = signal( SIGTERM, _SignalEndLoop )
    oldSigInt  = signal( SIGINT,  _SignalEndLoop )

    loop = 0
    while _Continue:

        Calibrate( vis, args, loop )

        Acquire( vis, args )
        
        FetchChannels( vis, args )

        # Manages looping
        loop = loop+1

        if args.loops<0:
            continue

        if loop>=args.loops:
            break

    signal( SIGTERM, oldSigTerm )
    signal( SIGINT,  oldSigInt )

    # Close modules
    Close( vis )


if __name__=="__main__":
    Run( DigitizerArgs() )
    # Ignore if the output file has been broken (receiver command stopped)
    try: stdout.close()
    except BrokenPipeError: pass

