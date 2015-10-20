#!/usr/bin/python3

"""
    Runs continuous acquisitions

    Copyright (C) Keysight Technologies 2015
   
    Started: August 24th, 2015
    By:      Didier Trosset
    Label:   Agilent Confidential

"""


from AgMD2 import *
from waveforms.trace import OutputTrace
from waveforms import Record, MultiRecord
from digitizer.argparser import DigitizerArgs, RefreshArgs
from sys import stdin, stdout, stderr
from time import sleep
from signal import signal, SIGTERM, SIGINT
from threading import Thread
from queue import Queue
import json


def Initialize( resources, options ):
    """ Initializes all the given resources using AgMD2_InitWithOptions,
        using the given options string.
        @return the list of vi.
    """
    if isinstance( resources, str ):
        resources = [resources]
    vis = []
    try:
        for rsrc in resources:
            vis.append( AgMD2_InitWithOptions( rsrc, 0, 0, options ) )
            # Always set private access.
            AgMD2_SetAttributeViString( vis[-1], "", AGMD2_ATTR_PRIVATE_ACCESS_PASSWORD, "We1ssh0rn" )
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


def ApplyArgs( vis, args ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        # Manages the clocking scheme
        if args.clock_external:
            AgMD2_SetAttributeViInt32(  vi, "", AGMD2_ATTR_SAMPLE_CLOCK_SOURCE , AGMD2_VAL_SAMPLE_CLOCK_SOURCE_EXTERNAL )   
            AgMD2_SetAttributeViReal64( vi, "", AGMD2_ATTR_SAMPLE_CLOCK_EXTERNAL_FREQUENCY , args.clock_external )   
            AgMD2_SetAttributeViReal64( vi, "", AGMD2_ATTR_SAMPLE_CLOCK_EXTERNAL_DIVIDER , args.clock_ext_divider )   
        else:
            if args.clock_ref_external:
                AgMD2_SetAttributeViInt32(  vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_EXTERNAL )
            elif args.clock_ref_axie:
                AgMD2_SetAttributeViInt32(  vi, "", AGMD2_ATTR_REFERENCE_OSCILLATOR_SOURCE, AGMD2_VAL_REFERENCE_OSCILLATOR_SOURCE_AXIE_CLK100 )

        # Manages conbination
        if args.interleave:
            ch, sub = args.interleave[:2]
            AgMD2_SetAttributeViString( vi, "Channel%d"%( ch ), AGMD2_ATTR_TIME_INTERLEAVED_CHANNEL_LIST, "Channel%d"%( sub ) )

        # Manages sample rate: set to the max, and then adjust if required
        #try: AgMD2_SetAttributeViReal64(  vi, "", AGMD2_ATTR_SAMPLE_RATE, 1e10 )
        #except: pass
        if args.sampling_frequency:
            AgMD2_SetAttributeViReal64(  vi, "", AGMD2_ATTR_SAMPLE_RATE, args.sampling_frequency )   
        AgMD2_SetAttributeViInt64(  vi, "", AGMD2_ATTR_RECORD_SIZE, args.samples )
        AgMD2_SetAttributeViInt64(  vi, "", AGMD2_ATTR_NUM_RECORDS_TO_ACQUIRE, args.records )
        assert args.records == AgMD2_GetAttributeViInt64(  vi, "", AGMD2_ATTR_NUM_RECORDS_TO_ACQUIRE )

        # Manages trigger
        if args.trigger_external:
            ActiveTrigger = "External%d"%( args.trigger_external )
        elif args.trigger_internal:
            ActiveTrigger = "Internal%d"%( args.trigger_internal )
        else:
            ActiveTrigger = "Internal1"

        AgMD2_SetAttributeViString( vi, "", AGMD2_ATTR_ACTIVE_TRIGGER_SOURCE , ActiveTrigger )
        if args.trigger_level:
            AgMD2_SetAttributeViReal64( vi, ActiveTrigger, AGMD2_ATTR_TRIGGER_LEVEL, args.trigger_level )
        if args.trigger_delay:
            AgMD2_SetAttributeViReal64( vi, "", AGMD2_ATTR_TRIGGER_DELAY, args.trigger_delay )
            stderr.write( "==>td:%g\n"%AgMD2_GetAttributeViReal64( vi, "", AGMD2_ATTR_TRIGGER_DELAY ) )

        # Manages calibration
        if not args.no_calibrate:
            AgMD2_SelfCalibrate( vi )

        if args.calibration_signal:
            AgMD2_SetAttributeViString( vi, "", AGMD2_ATTR_PRIVATE_CALIBRATION_USER_SIGNAL, "Signal"+args.calibration_signal )


def Calibrate( vis, args, loop ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        if not args.no_calibrate and args.calibrate_period and loop!=0 and loop%args.calibrate_period==0:
            if args.calibration_signal:
                AgMD2_SetAttributeViString( vi, "", AGMD2_ATTR_PRIVATE_CALIBRATION_USER_SIGNAL, "" )
            AgMD2_SelfCalibrate( vi )
            if args.calibration_signal:
                AgMD2_SetAttributeViString( vi, "", AGMD2_ATTR_PRIVATE_CALIBRATION_USER_SIGNAL, "Signal"+args.calibration_signal )


def Acquire( vis, args ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        AgMD2_InitiateAcquisition( vi )

        # Manages wait/poll
        if args.poll_timeout:
            acqDone = False
            fullwait = float( args.poll_timeout )
            while fullwait>=0 and _Continue and not acqDone:
                oncewait = min( 0.2, fullwait )
                sleep( oncewait/1000.0 )
                fullwait = fullwait-oncewait
                isIdle = AgMD2_GetAttributeViInt32( vi, "", AGMD2_ATTR_IS_IDLE )
                acqDone = isIdle==AGMD2_VAL_ACQUISITION_STATUS_RESULT_TRUE
        else:
            AgMD2_WaitForAcquisitionComplete( vi, int( args.wait_timeout*1000 )+1 )


def FetchChannels( vis, args ):
    global _Continue
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        # Manages readout
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
            nbrSamplesToRead = AgMD2_QueryMinWaveformMemory( vi, DataWidth, 1, 0, args.read_samples )

            rec = Record()
            for ch in args.read_channels:
                rec.append( Fetch( vi, "Channel%d"%( ch ), nbrSamplesToRead ) )

            try:
                OutputTrace( rec, stdout )
            except BrokenPipeError:
                _Continue = False
                break

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
            nbrSamplesToRead = AgMD2_QueryMinWaveformMemory( vi, DataWidth, args.read_records, 0, args.read_samples )

            mrec = MultiRecord()
            for ch in args.read_channels:
                mrec.append( Fetch( vi, "Channel%d"%( ch ), 0, args.read_records, 0, args.read_samples, nbrSamplesToRead, args.read_records ) )

            try:
                OutputTrace( mrec, stdout )
            except BrokenPipeError:
                _Continue = False
                break


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

    vis = Initialize( args.resources, "" )
    ShowInfo( vis )
    ApplyArgs( vis, args )

    oldSigTerm = signal( SIGTERM, _SignalEndLoop )
    oldSigInt  = signal( SIGINT,  _SignalEndLoop )

    loop = 0
    while _Continue:

        if UpdateArgs( args, queue ):
            ApplyArgs( vis, args )
            
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


def ReadCommands( ins, queue ):
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

