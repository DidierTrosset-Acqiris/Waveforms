#!/usr/bin/python3

"""
    Runs continuous acquisitions

    Copyright (C) Acqiris SA 2017-2024
   
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
from numpy import empty, int8, int16, float64
from datetime import datetime
import json

class InitOptions:
    def __init__( self ):
        self.stdopts = []
        self.drvstps = []
    def __str__( self ):
        if len(self.drvstps) == 0:
            return ", ".join( self.stdopts )
        return ", ".join( self.stdopts+["DriverSetup="] ) + ", ".join( self.drvstps )


def Initialize( args, initopts ):
    """ Initializes all the given resources using InitWithOptions,
        using the given options string.
        @return the list of vi.
    """
    if not isinstance( initopts, InitOptions ):
        raise RuntimeError("Init Options wrong type")
    reset = 1 if args.reset else 0
    resources = args.resources
    if isinstance( resources, str ):
        resources = [resources]
    vis = []
    for a in [1]:#try:
        for rsrc in resources:
            if rsrc[:3]=="SIM":
                model = rsrc[5:11]
                initopts.stdopts.append( "Simulate=1" )
                initopts.drvstps.append( "Model="+model )
                rsrc = ""
                print( "INIT:", rsrc, model, file=stderr )
            if args.retain_power_on_close:
                initopts.drvstps.append( "RetainPowerOnClose=1" )
            vi = AqMD3( rsrc, 0, reset, str(initopts) )
            vis.append( vi )
            # Always set private access.
            vi.Private.PrivateAccessPassword = "w31ss#orN2"
            if args.info_driver:
                #print( "Driver:  ", vi.Identity.Description, file=stderr )
                #print( "IOLS:    ", vi.InstrumentInfo.IOVersion, file=stderr )
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

            #vi.Private.PrivateCalibration.PrivateCalibrationSteps["Trim"].Characterize( "Characterize-Trim-OnInit.txt" )

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

def Reset( vis ):
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        for vi in vis:
            vi.Utility.ResetWithDefaults()


lastFirmwareRevision = None

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
                vi.ReferenceOscillator.ExternalFrequency = 10e6
            elif args.clock_ref_pxi:
                vi.ReferenceOscillator.Source = ReferenceOscillatorSource.PxiExpressClk100
            elif args.clock_ref_axie:
                vi.ReferenceOscillator.Source = ReferenceOscillatorSource.AXIeClk100
            else:
                vi.ReferenceOscillator.Source = ReferenceOscillatorSource.Internal

        # Manages sample rate
        if args.sampling_frequency:
            vi.Acquisition.SampleRate = args.sampling_frequency

        if args.disable_channel1:
            vi.Channels["Channel1"].Enabled = False
        if args.disable_channel2:
            vi.Channels["Channel2"].Enabled = False

        # Manages TSR
        if args.tsr:
            vi.Acquisition.NumberOfAverages = args.averages
            vi.Acquisition.TSR.Enabled = args.tsr

        # Manages acquisition mode DDC
        if args.mode=='DDC':
            vi.Acquisition.Mode = AcquisitionMode.DownConversion
            for ddcCore in vi.DDCCores:
                ddcCore.CenterFrequency = args.ddc_local_oscillator_frequency
                if args.ddc_decimation_numerator:
                    ddcCore.DecimationNumerator = args.ddc_decimation_numerator
                if args.ddc_decimation_denominator:
                    ddcCore.DecimationDenominator = args.ddc_decimation_denominator

        # Manages conbination
        if args.interleave:
            ch, sub = args.interleave[:2]
            vi.Channels["Channel%d"%( ch )].TimeInterleavedChannelList = "Channel%d"%( sub )
        else:
            for ch in vi.Channels:
                ch.TimeInterleavedChannelList = ""
        args.sampling_frequency = vi.Acquisition.SampleRate # Get SampleRate from instrument as it may have been changed by the interleaving

        # Manages acquisition mode AVG
        if args.mode=='AVG':
            vi.Acquisition.Mode = AcquisitionMode.Averager
            vi.Acquisition.NumberOfAverages = args.averages
        elif args.mode=='DGT':
            vi.Acquisition.Mode = AcquisitionMode.Normal

        # Manages streaming
        if args.streaming_continuous or args.streaming_triggered:
            vi.Acquisition.Streaming.Mode = StreamingMode.Continuous if args.streaming_continuous else StreamingMode.Triggered
            if args.data_truncation:
                for st in [vi.Streams[0]]:
                    if st.Type == StreamType.Samples:
                        st.Samples.DataTruncationEnabled = True
                        st.Samples.DataTruncationBitCount = args.data_truncation
        else:
            vi.Acquisition.Streaming.Mode = StreamingMode.Disabled

        # Manages records
        vi.Acquisition.RecordSize = args.samples
        vi.Acquisition.NumberOfRecordsToAcquire = args.records
        assert args.records == vi.Acquisition.NumberOfRecordsToAcquire

        # Manages trigger
        if args.immediate_trigger:
            ActiveTrigger = "Immediate"
            if args.trigger_level!=None:
                vi.Trigger.Sources["Internal1"].Level = args.trigger_level
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
                vi.Trigger.Sources[ActiveTrigger].Edge.Slope = TriggerSlope.Negative if args.trigger_slope in ["negative", "n"] else TriggerSlope.Positive

        vi.Trigger.ActiveSource = ActiveTrigger

        if args.trigger_output_enabled!=None:
            vi.Trigger.OutputEnabled = args.trigger_output_enabled
        if args.trigger_output_source!=None:
            vi.Trigger.Output.Source = args.trigger_output_source
        if args.trigger_output_offset!=None:
            vi.Trigger.Output.Offset = args.trigger_output_offset

        # Manages ZeroSuppress
        if args.zero_suppress:
            vi.Acquisition.DataReductionMode = DataReductionMode.ZeroSuppress
            for ch in vi.Channels:
                ch.ZeroSuppress.Threshold =       0   if args.zs_threshold      is None else args.zs_threshold
                ch.ZeroSuppress.Hysteresis =      248 if args.zs_hysteresis     is None else args.zs_hysteresis
                ch.ZeroSuppress.ZeroValue =       0   if args.zs_zero_value     is None else args.zs_zero_value
                ch.ZeroSuppress.PreGateSamples =  0   if args.pre_gate_samples  is None else args.pre_gate_samples
                ch.ZeroSuppress.PostGateSamples = 0   if args.post_gate_samples is None else args.post_gate_samples
                #if args.zero_value:
                #    ch.ZeroSuppress.ZeroValue = args.zero_value

        # Manages channels
        for ch in vi.Channels:
            if args.vertical_range!=None:
                ch.Range = args.vertical_range
            if args.vertical_offset!=None:
                ch.Offset = args.vertical_offset
            if args.input_max_frequency:
                ch.Filter.Bypass = False
                ch.Filter.MaxFrequency = args.input_max_frequency
            if args.bypass_anti_aliasing is not None:
                ch.Filter.BypassAntiAliasing = args.bypass_anti_aliasing
            if args.no_bypass_moving_average is not None:
                ch.Filter.BypassMovingAverage = not args.no_bypass_moving_average
            #ch.BaselineCorrection.Mode = 1
            if args.data_inversion is not None:
                if args.data_inversion_channels is not None:
                    if int( ch.Name[7:] ) in args.data_inversion_channels:
                        ch.DataInversionEnabled = args.data_inversion
                else:
                    ch.DataInversionEnabled = args.data_inversion
        #vi.Channels["Channel1"].Filter.BypassAntiAliasing = True
        #vi.Channels["Channel2"].Filter.BypassAntiAliasing = True

        if args.inter_channel_delay_enabled is not None:
            vi.Calibration.InterChannelDelayEnabled = args.inter_channel_delay_enabled
        if args.channel_sampling_delay_1 is not None:
            vi.Channels['Channel1'].SamplingDelay = args.channel_sampling_delay_1
        if args.channel_sampling_delay_2 is not None:
            vi.Channels['Channel2'].SamplingDelay = args.channel_sampling_delay_2

        if args.calibration_signal!=None:
            vi.Private.PrivateCalibration.UserSignal = "Signal"+args.calibration_signal

        if args.equalization:
            vi.Calibration.Equalization = CalibrationEqualization.SharpRollOff if args.equalization=="Sharp" else \
                                          CalibrationEqualization.SmoothRollOff if args.equalization=="Smooth" else \
                                          CalibrationEqualization.Custom if args.equalization=="Custom" else 0

        # Manages ControlIO
        if args.control_io1 or args.control_io2 or args.control_io3:
            for ctrlio, iosignal in zip( [vi.ControlIOs[0], vi.ControlIOs[1], vi.ControlIOs[2]], [args.control_io1, args.control_io2, args.control_io3] ):
                if iosignal:
                    ctrlio.Signal = iosignal
                    #ctrlio.OutSoftwareState = 0

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
                if args.self_trigger_pulse_duration!=None:
                    st.SelfTrigger.PulseDuration = args.self_trigger_pulse_duration
            except AttributeError as e:
                print( "ERROR for Armed Pulse", e, file=stderr )
                st.SelfTrigger.Mode = SelfTriggerMode.SquareWave
                st.SelfTrigger.SquareWave.Frequency = args.self_trigger_wave_frequency
                st.SelfTrigger.SquareWave.DutyCycle = args.self_trigger_wave_duty_cycle
                st.SelfTrigger.Mode = 2 # SelfTriggerMode.ArmedPulse

        if args.timestamp_reset and args.timestamp_reset != 'OnInitiate':
            #vi.TimeReference.ResetMode =    TimeResetMode.OnTriggerEnable if args.timestamp_reset == "OnTriggerEnable" \
            #                           else TimeResetMode.OnFirstTrigger  if args.timestamp_reset == "OnFirstTrigger"  \
            #                           else TimeResetMode.Immediate
            vi.TimeReference.ResetMode =    TimeResetMode.OnTriggerEnable if args.timestamp_reset == "OnTriggerEnable" \
                                       else TimeResetMode.OnFirstTrigger  if args.timestamp_reset == "OnFirstTrigger"  \
                                       else TimeResetMode.Immediate

#        for ch in [0, 1, 2, 3, 4, 5, 23, 24, 25, 26, 30, 31]:
#            vi.Channels[ch].Enabled = False 

        # Manages the calibration offset target
        if args.cal_offset_target!=None:
            vi.Calibration.TargetVoltageEnabled = True
            for ch in vi.Channels:
                ch.CalibrationTargetVoltage = args.cal_offset_target

        if args.mode=='CFW':
            vi.Acquisition.Mode = AcquisitionMode.UserFDK

        if args.no_digital_gain:
            vi.Private.PrivateCalibration.SetCalibrationValueBoolean( "DigitalGain:Disable", True )
        if args.no_adc_lut:
            vi.Private.PrivateCalibration.SetCalibrationValueBoolean( "AdcLut:Disable", True )
        if args.no_ric_filter:
            vi.Private.PrivateCalibration.SetCalibrationValueBoolean( "RicFilter:Disable", True )
        #vi.Private.PrivateCalibration.SetCalibrationValueBoolean( "RicFilter:ForceIdentityNoEqualizationFilter", True )
        #vi.Private.PrivateCalibration.SetCalibrationValueBoolean( "RicFilter:ForceDefaultNoEqualizationFilter", True )

        #vi.Private.PrivateCalibration.SetCalibrationValueBoolean( "SampleAveraging:Disable", True )
        #vi.Private.PrivateCalibration.SetCalibrationValueInt32( "SampleAveraging:ReadChannel", 1 )

        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["OffsetPrecal"].DumpWaveforms = True
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["DC"].DumpWaveforms = True
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["AC"].DumpWaveforms = True
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["StreamAlign"].DumpWaveforms = True
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["T0"].DumpWaveforms = True
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["DC"].Enabled = False
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["StreamAlign"].Enabled = False
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["PhaseMismatch"].Enabled = False
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["GainOffsetMismatch"].Enabled = False
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["AC"].Enabled = False
        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["T0"].Enabled = False

        #vi.Private.PrivateCalibration.PrivateCalibrationSteps["DC"].DumpWaveforms = True

        vi.Acquisition.ApplySetup()

        global lastFirmwareRevision
        newFirmwareRevision = vi.Identity.InstrumentFirmwareRevision
        if args.info_driver and newFirmwareRevision != lastFirmwareRevision:
            print( "Firmware:", vi.Identity.InstrumentFirmwareRevision, file=stderr )
            lastFirmwareRevision = newFirmwareRevision


def Calibrate( vis, args, loop, force ):
    if args.no_calibrate:
        return
    if isinstance( vis, int ):
        vis = [vis]
    for vi in vis:
        calibrate = False
        if vi.Calibration.IsRequired:
            calibrate = True
        if loop==0 or args.calibrate_period and loop%args.calibrate_period==0:
            calibrate = True

        if not calibrate and not force:
            continue
        if loop!=0 and args.calibrate_once:
            continue

        #print( "==> Calibration required.", file=stderr )
        if args.calibration_signal:
            vi.Private.PrivateCalibration.UserSignal = ""

        try:
            vi.Calibration.SelfCalibrate()
            pass
        except RuntimeError as e:
            print( e, file=stderr )
            if args.calibrate_fails:
                raise

        if args.calibration_signal:
            vi.Private.PrivateCalibration.UserSignal = "Signal"+args.calibration_signal


def Acquire( vis, args, queue, loop ):
    global _Continue
    if args.acquire_none:
        return False
    if isinstance( vis, int ):
        vis = [vis]
    if args.tsr:
        for vi in vis:
            # To find whether the acquisition is already started, try to continue it. In case of error, start it.
            try:
                #print( "TSR Continue", file=stderr )
                vi.Acquisition.TSR.Continue()
                if vi.Acquisition.TSR.MemoryOverflowOccurred:
                    print( "ERROR: TSR MEMORY OVERFLOW", file=stderr )
                    _Continue = False
                    #vi.Acquisition.Abort()
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
                sleep( 0.001 )

    elif args.streaming_continuous or args.streaming_triggered:
        for vi in vis:
            if vi.Acquisition.Status.IsIdle == AcquisitionStatusResult.ResultTrue:
                vi.Acquisition.Initiate()
        return True

    else:
        for vi in vis:
            if args.timestamp_reset == 'OnInitiate':
                vi.TimeReference.Time = datetime.utcfromtimestamp( 0 )
            vi.Acquisition.Initiate()
            #print( vi.ControlIOs[0].OutSoftwareState, vi.ControlIOs[1].OutSoftwareState, vi.ControlIOs[2].OutSoftwareState, file=stderr )
            #print( vi.ControlIOs[0].InSoftwareState,  vi.ControlIOs[1].InSoftwareState,  vi.ControlIOs[2].InSoftwareState,  file=stderr )
            #vi.ControlIOs[0].OutSoftwareState = 1
            #print( vi.ControlIOs[0].OutSoftwareState, vi.ControlIOs[1].OutSoftwareState, vi.ControlIOs[2].OutSoftwareState, file=stderr )
            #print( vi.ControlIOs[0].InSoftwareState,  vi.ControlIOs[1].InSoftwareState,  vi.ControlIOs[2].InSoftwareState,  file=stderr )
            if args.trigger_name=="SelfTrigger":
                sleep( 0.200 )
                vi.Trigger.Sources["SelfTrigger"].SelfTrigger.InitiateGeneration()

        while True:
            # Manages wait/poll
            if args.poll_timeout:
                for vi in vis:
                    acqDone = False
                    fullwait = float( args.poll_timeout )
                    while fullwait>=0.0 and _Continue and queue.empty() and not acqDone:
                        oncewait = min( 0.2, fullwait )
                        sleep( oncewait/1000.0 )
                        fullwait = fullwait-oncewait
                        isIdle = vi.Acquisition.Status.IsIdle
                        acqDone = isIdle==AcquisitionStatusResult.ResultTrue
                        nn = vi.Acquisition.NumberOfAcquiredRecords
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


class StreamWaveform( object ):
    def __init__( self, elmt, bits, dt, args ):
        self.SampleType = "Int16"
        self.NbrAdcBits = 16
        self.ActualRecords = 1
        self.RecordSize = args.output_samples
        self.XIncrement = 5e-10
        self.InitialXOffset = 0.0
        self.InitialXTimeSeconds = 0.0
        self.InitialXTimeFraction = 0.0
        self.ScaleOffset = 0.0
        self.ScaleFactor = 1.0
        self.dataTruncation = dt#args.data_truncation
        if self.dataTruncation == 12:
            self.Samples = empty(args.output_samples if args.output_samples else args.samples, dtype=int16)
            for n in range( min( len(elmt)//3, len(self.Samples)//8 ) ):
                e0 = elmt[3*n]
                e1 = elmt[3*n+1]
                e2 = elmt[3*n+2]
                s0 = e0 & 0x00000fff
                s1 = (e0 & 0x00fff000) >> 12
                s2 = ((e1 & 0x0000000f) << 8) | ((e0 & 0xff000000) >> 24)
                s3 = (e1 & 0x0000fff0) >> 4
                s4 = (e1 & 0x0fff0000) >> 16
                s5 = ((e2 & 0x000000ff) << 4) | ((e1 & 0xf0000000) >> 28)
                s6 = (e2 & 0x000fff00) >> 8
                s7 = (e2 & 0xfff00000) >> 20
                for i, s in enumerate([s0, s1, s2, s3, s4, s5, s6, s7]):
                    self.Samples[8*n+i] = s << 4 #(s if s <= 0x000007ff else s | 0xfffff000)
        elif bits==8:
            s = args.output_samples if args.output_samples else args.samples
            self.Samples = elmt[:(s//4)+1].view(dtype=int8)[:s].astype(dtype=int16)*256
        else:
            self.Samples = elmt.view(dtype=int16)[:args.output_samples]
    def __len__( self ):
        return len(self.Samples)
    def __getitem__( self, arg ):
        return self.Samples[arg]
    def __iter__( self ):
        return self.Samples.__iter__()

class StreamRecord( object ):
    def __init__( self, args ):
        self.SampleType = "Int16"
        self.NbrAdcBits = 16
        self.ActualRecords = 1
        self.RecordSize = args.output_samples
        self.XIncrement = 5e-10
        self.InitialXOffset = 0.0
        self.InitialXTimeSeconds = 0.0
        self.InitialXTimeFraction = 0.0
        self.ScaleOffset = 0.0
        self.ScaleFactor = 1.0
        self.Waveforms = []
    def __len__( self ):
        return len(self.Waveforms)
    def __getitem__( self, arg ):
        return self.Waveforms[arg]
    def __iter__(self):
        return self.Waveforms.__iter__()

def FetchChannels( vis, args ):
    global _Continue
    if isinstance( vis, int ):
        vis = [vis]
        # Manages readout
    nbrAdcBits = vis[0].InstrumentInfo.NbrADCBits

    if args.streaming_continuous or args.streaming_triggered:
        for vi in vis:
            #tsCount = 32*1024
            #data = vi.Streams["StreamTriggers"].FetchDataInt32( tsCount )
            #if data.ActualElements > 0:
            #    print( "FetchTriggers: ", data.ActualElements, data.AvailableElements, data.Elements.view( 'uint64' ), file=stderr )
            #    #with open( "ts.txt", "at" ) as f:
            #    #  for ts in fetch[0][fetch[4]:fetch[4]+fetch[3]].view( 'uint64' ):
            #    #      print( ts//256, file=f )
            #else:
            #    print( "Available Triggers: ", data.AvailableElements, file=stderr )
            numberOfWaveforms = args.read_records
            elmts = [None] * len(args.read_channels)
            for i, ch in enumerate(args.read_channels):
                elementsPerWaveform = args.read_samples//2
                if i==0 and args.data_truncation:
                    elementsPerWaveform = elementsPerWaveform * args.data_truncation // 16
                readElmts = numberOfWaveforms*elementsPerWaveform
                streamName = "StreamCh%d"%(ch)
                stream = vi.Streams[streamName]
                elmt = stream.FetchDataInt32( readElmts )
                if elmt.ActualElements > 0:
                    if args.output_info: print( streamName, ":", elmt.AvailableElements, elmt.ActualElements, len(elmt.Elements), file=stderr )
                    elmts[i] = elmt
                else:
                    if args.output_info: print( streamName, ":", elmt.AvailableElements, file=stderr )
                    sleep( 0.2 )
                    if elmt.AvailableElements < 0:
                        _Continue = False
            if all(elmts):
                first_record  = args.output_1st_record if args.output_1st_record else 0
                count_records = args.output_records if args.output_records else args.read_records
                for w in range( first_record, min(numberOfWaveforms, first_record + count_records) ):
                    rec = StreamRecord( args )
                    for i, elmt in enumerate( elmts ):
                        elementsPerWaveform = args.read_samples//2
                        if i==0 and args.data_truncation:
                            elementsPerWaveform = elementsPerWaveform * args.data_truncation // 16
                        rec.Waveforms.append( StreamWaveform(elmt.Elements[w*elementsPerWaveform:(w+1)*elementsPerWaveform], nbrAdcBits, 12 if args.data_truncation and i==0 else None, args) )
                    OutputTrace( rec, stdout, NbrSamples=args.output_samples )
                    #elmt = vi.Streams["StreamCh2"].FetchDataInt32( readElmts )
                    #if elmt.ActualElements > 0:
                    #    print( "FetchCh2: ", elmt.ActualElements, elmt.AvailableElements, elmt.Elements, file=stderr )
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
                    if args.output_info: print( channel.Name, "InitialXOffset:", wfms[0].InitialXOffset*1e12, "sample", *wfms[0].Samples[0:16], file=stderr )
                except RuntimeError:
                    vi.Acquisition.ErrorOnOverrangeEnabled = False
                    wfms = channel.Measurement.FetchAccumulatedWaveform( 0, args.read_records, 0, args.read_samples, dtype=readType)
                    vi.Acquisition.ErrorOnOverrangeEnabled = True
                mrec.append( wfms )

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
        if args.records==0:
            rec = Record( checkXOffset=not args.no_check_x_offset, nbrAdcBits=nbrAdcBits )
            try:
                for vi in vis:
                    for ch in args.read_channels:
                        channel = vi.Channels["Channel%d"%ch]
                        wfm = channel.Measurement.FetchWaveform( dtype=args.read_type )
            except RuntimeError:
                pass
                #for vi in vis:
                #    vi.Acquisition.ErrorOnOverrangeEnabled = False
                #    try:
                #        for ch in args.read_channels:
                #            channel = vi.Channels["Channel%d"%ch]
                #            wfm = channel.Measurement.FetchWaveform( dtype=args.read_type )
                #    except:
                #        continue
                #    vi.Acquisition.ErrorOnOverrangeEnabled = True
            try:
                if args.output_info: print( "InitialXOffset:", wfm.InitialXOffset, file=stderr )
                OutputTraces( [wfm], stdout, FirstRecord=args.output_1st_record, NbrRecords=args.output_records, NbrSamples=args.output_samples )
            except BrokenPipeError:
                _Continue = False

        else:
            mrec = MultiRecord( checkXOffset=not args.no_check_x_offset, nbrAdcBits=nbrAdcBits ) 
            for vi in vis:
                for ch in args.read_channels:
                    channel = vi.Channels["Channel%d"%ch]
                    try:
                        wfms = channel.MultiRecordMeasurement.FetchMultiRecordWaveform( 0, args.read_records, 0, args.read_samples, dtype=args.read_type)
                        #print( channel.Name, "InitialXOffset:", wfms[0].InitialXOffset*1e12, "ps, samples:", *wfms[0].Samples[0:8], file=stderr )
                    except RuntimeError:
                        canReadAgain = True
                        try: vi.Acquisition.ErrorOnOverrangeEnabled = False
                        except RuntimeError: canReadAgain = False

                        if not canReadAgain:
                            raise

                        wfms = channel.MultiRecordMeasurement.FetchMultiRecordWaveform( 0, args.read_records, 0, args.read_samples, dtype=args.read_type)
                        vi.Acquisition.ErrorOnOverrangeEnabled = True
                    mrec.append( wfms )
                    prevts = 0.0
                    for rec in wfms:
                        ts = rec.InitialXTimeSeconds+rec.InitialXTimeFraction
                        #print( ts if prevts==0.0 else 1e6*(ts-prevts), file=stderr )
                        prevts = ts
            try:
                if args.output_info: print( "InitialXOffset:", mrec[0].InitialXOffset*1e12, file=stderr )
                OutputTraces( mrec, stdout, FirstRecord=args.output_1st_record, NbrRecords=args.output_records, NbrSamples=args.output_samples )
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

    vis = Initialize( args, InitOptions() )
    #ShowInfo( vis )
    ApplyArgs( vis, args )

    oldSigTerm = signal( SIGTERM, _SignalEndLoop )
    oldSigInt  = signal( SIGINT,  _SignalEndLoop )

    loop = 0
    _Continue = False if args.loops == 0 else True
    while _Continue:

        forceCal = False

        if args.reset_period and loop>0:
            if loop % args.reset_period == 0:
                Reset( vis )
                ApplyArgs( vis, args )
                #forceCal = True

        if UpdateArgs( args, queue ):
            ApplyArgs( vis, args )
            forceCal = args.calibrate_always
            
        Calibrate( vis, args, loop, forceCal )

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

