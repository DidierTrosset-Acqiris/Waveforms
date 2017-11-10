#!/usr/bin/python3

"""
    Runs continuous acquisitions

    Copyright (C) Acqiris SA 2017
   
    Started: September 27th, 2017
    By:      Didier Trosset
    Label:   Acqiris Confidential

"""


from AqMD3 import *
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
    """ Initializes all the given resources using InitWithOptions,
        using the given options string.
        @return the list of vi.
    """
    reset = 1 if args.reset else 0
    resources = args.resources
    if isinstance( resources, str ):
        resources = [resources]
    vis = []
    for a in [1]:#try:
        for rsrc in resources:
            if rsrc[:3]=="SIM":
                model = rsrc[5:11]
                options = "Simulate=1, DriverSetup= Model="+model
                rsrc = ""
                print( "INIT:", rsrc, model, file=stderr )
            vi = AqMD3( rsrc, 0, reset, options )
            vis.append( vi )
            # Always set private access.
            vi.Private.PrivateAccessPassword = "We1ssh0rn"
            #print( "Driver:  ", vi.Identity.Description, file=stderr )
            print( "IOLS:    ", vi.InstrumentInfo.IOVersion, file=stderr )
            print( "Model:   ", vi.Identity.InstrumentModel, file=stderr )
            print( "Serial:  ", vi.InstrumentInfo.SerialNumberString, file=stderr )
            print( "Options: ", vi.InstrumentInfo.Options, file=stderr )
            print( "Firmware:", vi.Identity.InstrumentFirmwareRevision, file=stderr )
            if args.info_cores:
                def PrintCoreVersion( vi, msg, core ):
                    try:
                        version, versionString = AgMD2_LogicDeviceGetCoreVersion ( vi, "DpuA", core, 32 )
                    except:
                        return
                    print( msg, versionString, file=stderr )
                PrintCoreVersion( vi, "Core PCIe:   ", AGMD2_VAL_LOGIC_DEVICE_CORE_PCIE )
                PrintCoreVersion( vi, "Core DDR3A:  ", AGMD2_VAL_LOGIC_DEVICE_CORE_DDR3A )
                PrintCoreVersion( vi, "Core DDR3B:  ", AGMD2_VAL_LOGIC_DEVICE_CORE_DDR3B )
                PrintCoreVersion( vi, "Core CalDig: ", AGMD2_VAL_LOGIC_DEVICE_CORE_CALIBRATION_DIGITIZER )
                PrintCoreVersion( vi, "Core IfdlUp: ", AGMD2_VAL_LOGIC_DEVICE_CORE_IFDL_UP )
                PrintCoreVersion( vi, "Core IfdlDn: ", AGMD2_VAL_LOGIC_DEVICE_CORE_IFDL_DOWN )
                PrintCoreVersion( vi, "Core IfdlCt: ", AGMD2_VAL_LOGIC_DEVICE_CORE_IFDL_CONTROL )
                PrintCoreVersion( vi, "Core QDR2:   ", AGMD2_VAL_LOGIC_DEVICE_CORE_QDR2 )
                PrintCoreVersion( vi, "Core AdcInt: ", AGMD2_VAL_LOGIC_DEVICE_CORE_ADC_INTERFACE )
                PrintCoreVersion( vi, "Core StrPr:  ", AGMD2_VAL_LOGIC_DEVICE_CORE_STREAM_PREPARE )
                PrintCoreVersion( vi, "Core TrgMgr: ", AGMD2_VAL_LOGIC_DEVICE_CORE_TRIGGER_MANAGER )

    #except:
    #    for vi in vis:
    #        try: vi.Close()
    #        except: pass
    #    raise
    return vis


def Close( vis ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        for vi in vis:
            try: vi.Close()
            except: pass


def ShowInfo( vis ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        #print( "Driver:  ", vi.Identity.Description, file=stderr )
        print( "Model:   ", vi.Identity.InstrumentModel, file=stderr )
        print( "Serial:  ", vi.InstrumentInfo.SerialNumberString, file=stderr )
        print( "Options: ", vi.InstrumentInfo.Options, file=stderr )
        print( "Firmware:", vi.Identity.InstrumentFirmwareRevision, file=stderr )


def ApplyArgs( vis, args ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        if vi.Acquisition.Status.IsIdle != AcquisitionStatusResult.ResultTrue:
            vi.Acquisition.Abort()
        # Manages the clocking scheme
        if args.clock_external:
            vi.SampleClock.Source = SampleClockSource.External
            vi.SampleClock.ExternalFrequency = args.clock_external
            vi.SampleClock.ExternalDivider =       args.clock_ext_divider      
        else:
            vi.SampleClock.Source = SampleClockSource.Internal
            if args.clock_ref_external:
                vi.ReferenceOscillator.Source = ReferenceOscillatorSource.External
            elif args.clock_ref_pxi:
                vi.ReferenceOscillator.Source = ReferenceOscillatorSource.PxiExpressClk100
            elif args.clock_ref_axie:
                vi.ReferenceOscillator.Source = ReferenceOscillatorSource.AXIeClk100
            else:
                vi.ReferenceOscillator.Source = ReferenceOscillatorSource.Internal

        # Manages acquisition mode
        if args.mode=='DDC':
            vi.Acquisition.Mode = AcquisitionMode.DownConversion
            for ddcCore in vi.DDCCores:
                ddcCore.CenterFrequency = args.ddc_local_oscillator_frequency
                if args.ddc_decimation_numerator:
                    ddcCore.DecimationNumerator = args.ddc_decimation_numerator
                if args.ddc_decimation_denominator:
                    ddcCore.DecimationDenominator = args.ddc_decimation_denominator

        if args.mode=='AVG':
            vi.Acquisition.Mode = AcquisitionMode.Averager
            vi.Acquisition.NumberOfAverages = args.averages

        # Manages conbination
        if args.interleave:
            ch, sub = args.interleave[:2]
            vi.Channels["Channel%d"%( ch )].TimeInterleavedChannelList = "Channel%d"%( sub )

        # Manages TSR
        if args.tsr:
            vi.Acquisition.TSR.Enabled = args.tsr

        # Manages streaming
        if args.streaming_continuous or args.streaming_triggered:
            vi.Acquisition.Streaming.Mode = StreamingMode.Continuous if args.streaming_continuous else StreamingMode.Triggerred

        # Manages sample rate
        if args.sampling_frequency:
            vi.Acquisition.SampleRate = args.sampling_frequency
        vi.Acquisition.RecordSize = args.samples
        vi.Acquisition.NumberOfRecordsToAcquire = args.records
        assert args.records == vi.Acquisition.NumberOfRecordsToAcquire

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
                vi.Trigger.Sources[ActiveTrigger].Level = args.trigger_level
            if args.trigger_delay!=None:
                vi.Trigger.Delay = args.trigger_delay
            if args.trigger_slope!=None:
                vi.Trigger.Sources[ActiveTrigger].Slope = TriggerSlope.Negative if args.trigger_slope in ["negative", "n"] else TriggerSlope.Positive

        vi.Trigger.ActiveSource = ActiveTrigger

        if args.trigger_output_enabled!=None:
            vi.Trigger.OutputEnabled = args.trigger_output_enabled
        if args.trigger_output_source!=None:
            vi.Trigger.Output.Source = args.trigger_output_source
        if args.trigger_output_offset!=None:
            vi.Trigger.Output.Offset = args.trigger_output_offset

        # Manages channels
        for ch in vi.Channels:
            if args.vertical_range:
                ch.Range = args.vertical_range
            if args.vertical_offset:
                ch.Offset = args.vertical_offset
            #if args.filter_max_frequency:
            #    ch.Filter.MaxFrequency = args.vertical_offset

        if args.calibration_signal:
            vi.Private.Calibration.UserSignal = "Signal"+args.calibration_signal

        # Manages ControlIO
        for ctrlio, iosignal in zip( vi.ControlIOs, [args.control_io1, args.control_io2, args.control_io3] ):
            if iosignal:
                ctrlio.Signal = iosignal

        # Manages SelfTrigger
        if args.self_trigger_square_wave:
            st = vi.Trigger.Sources["SelfTrigger"]
            st.SelfTrigger.Mode = SelfTriggerMode.SquareWave
            st.SelfTrigger.SquareWave.Frequency = args.self_trigger_wave_frequency
            st.SelfTrigger.SquareWave.DutyCycle = args.self_trigger_wave_duty_cycle
        elif args.self_trigger_armed_pulse:
            st = vi.Trigger.Sources["SelfTrigger"]
            try: # Either we have the armed pulse mode and pulse duration attribute, or we revert to AgMD2-2.4 hack
                st.SelfTrigger.Mode = SelfTriggerMode.ArmedPulse
                if args.self_trigger_pulse_duration:
                    st.SelfTrigger.PulseDuration = args.self_trigger_pulse_duration
            except AttributeError as e:
                print( "ERROR for Armed Pulse", e, file=stderr )
                st.SelfTrigger.Mode = SelfTriggerMode.SquareWave
                st.SelfTrigger.SquareWave.Frequency = args.self_trigger_wave_frequency
                st.SelfTrigger.SquareWave.DutyCycle = args.self_trigger_wave_duty_cycle
                st.SelfTrigger.Mode = 2 # SelfTriggerMode.ArmedPulse

#        for ch in [0, 1, 2, 3, 4, 5, 23, 24, 25, 26, 30, 31]:
#            vi.Channels[ch].Enabled = False 

        # Manages the calibration offset target
        if args.cal_offset_target:
            vi.Calibration.TargetVoltageEnabled = True
            for ch in vi.Channels:
                ch.CalibrationTargetVoltage = args.cal_offset_target

        vi.Acquisition.ApplySetup()
        print( "Firmware:", vi.Identity.InstrumentFirmwareRevision, file=stderr )


def Calibrate( vis, args, loop ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        calibrate = False
        if vi.Calibration.IsRequired:
            calibrate = True
        if loop==0 or args.calibrate_period and loop%args.calibrate_period==0:
            calibrate = True

        if not calibrate:
            continue

        #print( "==> Calibration required.", file=stderr )
        if args.calibration_signal:
            vi.Private.Calibration.UserSignal = ""

        vi.Calibration.SelfCalibrate()

        if args.calibration_signal:
            vi.Private.Calibration.UserSignal = "Signal"+args.calibration_signal


def Acquire( vis, args, queue, loop ):
    global _Continue
    if isinstance( vis, int ):
        vis = [vis]
    if args.tsr:
        for vi in vis:
            # To find whether the acquisition is already started, try to continue it. In case of error, start it.
            try:
                #print( "TSR Continue", file=stderr )
                vi.Acquisition.TSR.Continue()
                if vi.Acquisition.TSR.OverflowOccurred:
                    print( "ERROR: TSR MEMORY OVERFLOW", file=stderr )
                    _Continue = False
                    vi.Acquisition.Abort()
                    #return False
            except:
                #print( "\nPress ENTER", file=stderr )
                #stdin.readline()
                #print( "Initiate Acquistion", file=stderr )
                vi.Acquisition.Initiate()

            polls = 0
            #while _Continue:
            for a in range(10000):
                complete = vi.Acquisition.TSR.IsAcquisitionComplete
                if a==9999 or complete:
                    print( "GetAttribute TSR_IS_ACQUISITION_COMPLETE", polls, " :", "0 -> ", complete, file=stderr )
                if complete:
                    return True
                polls = polls + 1
                sleep( 0.0001 )

    elif args.streaming_continuous or args.streaming_triggered:
        for vi in vis:
            if vi.Acquisition.Status.IsIdle == AcquisitionStatusResult.ResultTrue:
                vi.Acquisition.Initiate()
        return True

    else:
        for vi in vis:
            vi.Acquisition.Initiate()
            if args.trigger_name=="SelfTrigger":
                vi.Trigger.Sources["SelfTrigger"].SelfTrigger.InitiateGeneration()

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
                        isIdle = vi.Acquisition.Status.IsIdle
                        acqDone = isIdle==AcquisitionStatusResult.ResultTrue
                    if acqDone:
                        return True
                    else:
                        vi.Acquisition.Abort()
                        return False
            else:
                try:
                    for vi in vis:
                        vi.Acquisition.WaitForAcquisitionComplete( int( args.wait_timeout*1000 )+1 )
                    return True
                except RuntimeError as e:
                    if args.wait_failure:
                        raise
                    else:
                        print( "WaitForAcquisitionComplete: MAX_TIME_EXCEEDED.", file=stderr )
                        if not _Continue or not queue.empty():
                            vi.Acquisition.Abort()
                            return False



def FetchChannels( vis, args ):
    global _Continue
    if isinstance( vis, int ):
        vis = [vis]
        # Manages readout
    nbrAdcBits = vis[0].InstrumentInfo.NbrADCBits

    if args.streaming_continuous or args.streaming_triggered:
        sleep( 0.01 )
        for vi in vis:
            tsCount = 32*1024
            fetch = AgMD2_StreamFetchDataInt32( vi, "StreamTriggers", tsCount, tsCount )
            if fetch[3] == tsCount:
                print( "Fetch: ", fetch[1], fetch[2], fetch[3], fetch[4], file=stderr )
                with open( "ts.txt", "at" ) as f:
                  for ts in fetch[0][fetch[4]:fetch[4]+fetch[3]].view( 'uint64' ):
                      print( ts//256, file=f )
            else:
                print( "Available: ", fetch[1], fetch[2], fetch[3], fetch[4], file=stderr )
            chCount = 8*1024*1024
            fetchCh1 = AgMD2_StreamFetchDataInt32( vi, "StreamCh1", chCount, chCount )
            if fetchCh1[3] == chCount:
                print( "FetchCh1: ", fetchCh1[1], fetchCh1[2], fetchCh1[3], fetchCh1[4], file=stderr )
            fetchCh2 = AgMD2_StreamFetchDataInt32( vi, "StreamCh2", chCount, chCount )
            if fetchCh2[3] == chCount:
                print( "FetchCh2: ", fetchCh2[1], fetchCh2[2], fetchCh2[3], fetchCh2[4], file=stderr )
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
                readType = 'real64'
            else:
                readType = 'int32'

            mrec = AccMultiRecord( checkXOffset=not args.no_check_x_offset, nbrAdcBits=nbrAdcBits )
            for ch in args.read_channels:
                channel = vi.Channels["Channel%d"%ch]
                try:
                    wfms = channel.Measurement.FetchAccumulatedWaveform( 0, args.read_records, 0, args.read_samples, dtype=readType)
                except RuntimeError:
                    vi.Acquisition.ErrorOnOverrangeEnabled = False
                    wfms = channel.Measurement.FetchAccumulatedWaveform( 0, args.read_records, 0, args.read_samples, dtype=readType)
                    vi.Acquisition.ErrorOnOverrangeEnabled = True
                #mrec.append( fetch )

            try:
                OutputTraces( wfms, stdout, FirstRecord=args.output_1st_record, NbrRecords=args.output_records, NbrSamples=args.output_samples )
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
        if args.records<=0:
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
            mrec = MultiRecord( checkXOffset=not args.no_check_x_offset, nbrAdcBits=nbrAdcBits ) 
            for vi in vis:
                for ch in args.read_channels:
                    channel = vi.Channels["Channel%d"%ch]
                    fetch = channel.MultiRecordMeasurement.FetchMultiRecordWaveform( 0, args.read_records, 0, args.read_samples, dtype=args.read_type)
                    #mrec.append( Fetch( vi, "Channel%d"%( ch ), 0, args.read_records, 0, args.read_samples, nbrSamplesToRead, args.read_records ) )
                    print( "==>", "Fetch:", fetch, file=stderr )
                    print( "==>", "Fetch:", fetch[0], file=stderr )
                    for rec in fetch:
                        print( "==>", "Fetch:", "Record:", rec, file=stderr )
                        print( "==>", "Fetch:", "Record:", rec.Samples, file=stderr )


            try:
                OutputTraces( mrec, fetch )
                print( "==>", "Output", file=stderr )
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
                    vi.Acquisition.Abort()
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

