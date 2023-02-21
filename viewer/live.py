#!/usr/bin/python3

try:
    from Tkinter import *
except:
    from tkinter import *

from subprocess import *

from waveforms.trace import ReadTrace, FullScale
from threading import Thread
from queue import Queue
import socket
import sys
import os
import re
from os.path import expanduser
import math
import time
import select
import warnings

# Try to import SciPy, disables calculations if not
try:
    from scipy import arange, array, double, fft, log10, pi, polyfit, optimize, sin, sqrt
    from numpy import maximum, minimum, linspace
    USE_SCIPY = 1
except ImportError:
    sys.stderr.write("Live Viewer requires scipy for better experience. See http://www.scipy.org/\n")
    USE_SCIPY = 0

import matplotlib
matplotlib.use('TkAgg')   # Plot to TkInter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas
from matplotlib.figure import Figure


def CalcFourier( record, nbrSamples ):
    record.spectrums = []
    if len( record )>0 and len( record[0] )>0 and nbrSamples>0:
        for wfm in record:
            record.spectrums.append( abs( fft( wfm.Samples[:nbrSamples:1] )/(nbrSamples/2) ) )

class Ratios:
    def __init__(self):
        pass

def CalcRatios(trace, nbrHarmonics=6):
    if len( trace.spectrums )==0 or len( trace.spectrums[0] )==0:
        return None
    ratios = Ratios()
    nbrFreq = len( trace.spectrums[0] )
    first = ( 0, 0.0 )
    second = ( 0, 0.0 )
    # Find the first and second higher frequencies
    for freq in range(1, nbrFreq // 2):
        val = trace.spectrums[0][freq]
        if val > first[1]:
            second = first
            first = ( freq, val )
        elif val > second[1]:
            second = ( freq, val )
    # Calculate the list of harmonic frequencies
    harmonicLst = []
    assert(trace.fittedSine)
    fsamp = 1.0 / trace.XIncrement
    fsig = trace.fittedSine.all[1] / 2.0 / pi * fsamp
    for h in range(0, nbrHarmonics):
        fharm = fsig * (h + 2)
        while fharm > fsamp:
            fharm = fharm - fsamp
        if fharm > fsamp / 2.0:
            fharm = fsamp - fharm
        freq = int(fharm * float(nbrFreq) / fsamp)
        #assert(freq >= 0 and freq < nbrFreq / 2)
        if freq >= 0 and freq < nbrFreq / 2:
            harmonicLst.append(freq)
    # Calculate the THD
    powThd = 0.0
    ratios.powHarmLst = []
    for freq in harmonicLst:
        val = trace.spectrums[0][freq]
        vals = trace.spectrums[0][max(0, freq-5):min(trace.spectrums[0].size-1, freq+5)]
        val2 = max(vals)
        #assert(val <= second[1])
        ratios.powHarmLst.append(val2 ** 2.0)
        powThd = powThd + val2**2.0
    ratios.powThd = powThd
    # Calculate the harmonics
    carrier = first[0]
    harms = [ (i*carrier)%nbrFreq for i in range(1, nbrHarmonics) ]
    # Calculate the noise
    powNoise = 0.0
    for freq in range(1, nbrFreq // 2):
        if freq != first[0]:
            val = trace.spectrums[0][freq]
            assert(val <= second[1])
            powNoise = powNoise + val**2.0
    ratios.powNoise = powNoise - powThd
    # Calculate the signal
    ratios.binSignal = first[0]
    ratios.powSignal = float(first[1])**2.0
    ratios.binSecond = second[0]
    ratios.powSecond = float(second[1])**2.0
    ratios.powFS = (trace.FullScale / 2) ** 2.0
    return ratios


spectrumReset = False
spectrumMax = []

def Clear():
    global spectrumReset
    spectrumReset = True


GAIN = 0
OMEGA = 1
PHASE = 2
OFFSET = 3
RMS = 4

class FittedSine:

    def __init__(self):
        self.success = 0
        self.all = [ 1., 1., 0., 0., 0. ]
        self.adc = []
        self.XIncrement = 0
        self.FullScale = 0


def CalcZeroCross(samples):
    levelMin, levelMax = int( min(samples) ), int( max(samples) )
    levelMean, levelGain = (levelMin + levelMax) / 2, (levelMax - levelMin) / 2
    levelUp, levelDn = levelMean + levelGain * 0.1, levelMean - levelGain * 0.1
    level = 0
    phase = 0
    crossLst = []
    phaseLst = []
    samplePrev = samples[0]
    n = 0
    for sample in samples[1:]:
        if sample > levelUp:
            if level == -1:
                cross = (n - 1) + (levelMean - samplePrev) / (sample - samplePrev)
                crossLst.append(cross)
                phaseLst.append(phase)
                phase = phase + pi
            level = 1
        if sample < levelDn:
            if phase == 0:
                phase = pi
            if level == 1:
                cross = (n - 1) + (levelMean - samplePrev) / (sample - samplePrev)
                crossLst.append(cross)
                phaseLst.append(phase)
                phase = phase + pi
            level = -1
        if len(crossLst) > 50:
            break
        samplePrev = sample
        n = n + 1
    if len(crossLst) & 1:
        crossLst = crossLst[:-1]
        phaseLst = phaseLst[:-1]
    return (crossLst, phaseLst)


def CalcSinFitGuess(samples):
    levelMin, levelMax = int( min(samples) ), int( max(samples) )
    levelMean, levelGain = (levelMin + levelMax) / 2, (levelMax - levelMin) / 2
    crossLst, phaseLst = CalcZeroCross(samples)
    if len(crossLst) < 2:
        return [ levelGain, 0.01, 0, levelMean ]
    slope, cross = polyfit(crossLst, phaseLst, 1)
    if cross > pi:
        cross = cross - 2 * pi
    return [ levelGain, slope, cross, levelMean ]


def CalcFittedSine(trace):
    if trace.ActualPoints<50:
        return None
    fittedSine = FittedSine()
    nbrPoints = trace.ActualPoints
    if nbrPoints > 100000:
        nbrPoints = 100000
    tx = linspace(0, nbrPoints-1, nbrPoints)
    ty = trace[0].Samples[:nbrPoints]
    # Fit the first set
    fitfunc = lambda p, x: p[0] * sin(p[1]*x + p[2]) + p[3]  # Target function
    errfunc = lambda p, x, y: fitfunc(p,x) -y                # Distance to the target function
    p0 = CalcSinFitGuess(trace[0].Samples)                      # Initial guess for the parameters
    p1, fittedSine.success = optimize.leastsq(errfunc, p0[:], args = (tx, ty))
    if p1[0] < 0:
        p1[0] = -p1[0]
        p1[2] = p1[2] - pi
    rms = sqrt(sum((errfunc(p1, tx, ty))**2) / nbrPoints)
    fittedSine.all = [ p1[0], p1[1], p1[2], p1[3], rms ]

    try:
        nbrAdc = trace.nbrAdc
        nbrPoints = nbrPoints - (nbrPoints % nbrAdc)
        if nbrAdc > 1:
            fittedSine.adc = []
            for adc in range(0, nbrAdc):
                atx = linspace(0, nbrPoints-nbrAdc, nbrPoints/nbrAdc)
                aty = trace.samples[adc:nbrPoints:nbrAdc]
                ap0 = p1
                ap1, success = optimize.leastsq(errfunc, ap0[:], args = (atx, aty))
                if ap1[0] < 0:
                    ap1[0] = -ap1[0]
                    ap1[2] = ap1[2] - pi
                arms = sqrt(sum((errfunc(ap1, atx, aty))**2) / (nbrPoints/nbrAdc))
                fittedSine.adc.append(  [ ap1[0], ap1[1], ap1[2], ap1[3], arms ]  )
    except:
        pass
    fittedSine.XIncrement = trace.XIncrement
    fittedSine.FullScale = trace.FullScale
    return fittedSine


def CalcBestNbrSamples(trace, fsig):
    fsamp = 1 / trace.XIncrement
    best = [ 1, 1, 0 ] 
    nbrSamples = int(trace.ActualPoints / 4) * 4
    for pts in range(nbrSamples, 100, -4):
        per = pts * fsig / fsamp
        err = per - int(per)
        if err > 0.5:
            err = 1.0 - err
        if err/pts**1.5 <= best[0]/best[1]**1.5:
            best = [ err, pts, per ]
    return best[1]
    

class SocketReader:

    def __init__(self, sock):
        self.sock = sock
        self.buff = ""

    def read(self, count):
        global ReadSocket, IncomingAddr
        assert(count == 1)
        if len(self.buff) == 0:
            self.buff = self.sock.recv(4096)
            self.buff = self.buff.decode('utf-8')
        if len(self.buff) == 0:
            IncomingAddr = None
            ReadSocket = None
            return ""
        ch = self.buff[0]
        self.buff = self.buff[1:]
        return ch

    def readline(self):
        global ReadSocket, IncomingAddr
        line = ""
        while True:
            if len(self.buff) == 0:
                self.buff = self.sock.recv(4096)
                self.buff = self.buff.decode('utf-8')
            if len(self.buff) == 0:
                IncomingAddr = None
                ReadSocket = None
                return line
            eolpos = self.buff.find("\n")
            if eolpos != -1:
                line = line + self.buff[:eolpos+1]
                self.buff = self.buff[eolpos+1:]
                break
            line = line + self.buff
            self.buff = ""
        return line


SubProcess = None
ListenSocket = None
ReadSocket = None
IncomingAddr = None

def GetTraceFromSource():
    global RunCommand, InputFile, SubProcess, TcpPort, TcpBind, TcpHost, ReadSocket, ListenSocket, IncomingAddr, Pause
    input = None
    filename = ""
    if InputFile and InputFile != "-":
        filename = InputFile
        input = open(InputFile)
    elif TcpPort and TcpHost:
        filename = "TCP: %s : %s" % (TcpHost, TcpPort)
        if not ReadSocket:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((TcpHost, TcpPort))
                ReadSocket = SocketReader(sock)
            except:
                sys.stderr.write("ERROR: Cannot connect to '%s' port %d\n" % (TcpHost, TcpPort))
                filename = "ERROR: Cannot connect to '%s' port %d" % (TcpHost, TcpPort)
                ReadSocket = None
            # Cannot use the following on Windows, thus the SocketReader class
            #input = os.fdopen(sock.fileno(), "ru")
        input = ReadSocket
    elif RunCommand:
        if SubProcess and not SubProcess.poll():
            filename = "<" + RunCommand + ">"
            input = SubProcess.stdout
        else:
            filename = "<" + RunCommand + ">"
            SubProcess = Popen(RunCommand, shell=True, stdout=PIPE)
            input = SubProcess.stdout
    elif TcpPort and not TcpHost:
        if IncomingAddr:
            filename = "Incoming TCP connection from %s:%d" % IncomingAddr
        else:
            filename = "Listening TCP connection on %s:%d" % (TcpBind, TcpPort)
        if not ReadSocket:
            if not ListenSocket:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind((TcpBind, TcpPort))
                sock.listen(1)
                ListenSocket = sock
            sock = ListenSocket
            rlist, wlist, xlist = select.select([sock], [], [], 0)
            if len(rlist) > 0:
                try:
                    sockrecv, IncomingAddr = sock.accept()
                    filename = "Incoming TCP connection from %s:%d" % IncomingAddr
                    ReadSocket = SocketReader(sockrecv)
                    Pause = False
                except:
                    sys.stderr.write("ERROR: Cannot bind to '%s' port %d\n" % (TcpBind, TcpPort))
                    filename = "ERROR: Cannot bind to '%s' port %d" % (TcpBind, TcpPort)
                    ReadSocket = None
            # Cannot use the following on Windows, thus the SocketReader class
            #input = os.fdopen(sock.fileno(), "ru")
        input = ReadSocket
    else:
        filename = "<STDIN>"
        input = sys.stdin
    if input:
        for rec in ReadTrace( input ):
            rec.filename = filename
            if not hasattr(rec, 'FullScale'):
                rec.FullScale = FullScale( rec.SampleType );
            yield rec
#        if not TcpPort or TcpHost: # We are not listening
#            Pause = True
    if SubProcess and SubProcess.poll() != None:
        SubProcess = None


def CalculateTrace(trace):
    global ShowSignal, ShowRatios, ShowSpectrum, ShowFittedSine
    # Calculate sine fit
    if USE_SCIPY and ShowFittedSine:
        try:
            trace.fittedSine = CalcFittedSine(trace)
        except:
            trace.fittedSine = None
    # Calculate FFT
    trace.nbrFftSamples = trace.ActualPoints if trace.ActualPoints<65536 else 65536
#    CalcFourier(trace, trace.nbrFftSamples)
    # Calculate ratios
    trace.ratios = None
    if ShowRatios:
        try: trace.ratios = CalcRatios(trace, 1)
        except: pass
    return trace


def tkUpdateLabel(label, txt):
    label.configure(text = txt)
    label.text = txt


nameRow = [ "freq", "phase", "gain", "offset", "rms", "enob" ]

class Mismatch:

    def __init__(self):
        self.adc = []

def _GetColor(index, light=False):
    def _light( c ):
        r, g, b = int( c[1:3], 16 ), int( c[3:5], 16 ), int( c[5:7], 16 )
        return '#'+'%02x'%( 255-( 255-r )//2 )+'%02x'%( 255-( 255-g )//2 )+'%02x'%( 255-( 255-b )//2 )
    #                Kt Red     Kt Blue    Kt Purple   Kt Green  Kt Orange  Kt MedGray Kt Yellow  Kt Black
    colorsNormal = ['#e90029', '#009fe3', '#8b3c8f', '#019642', '#ed5e1a', '#9c9c9c', '#fdc206', '#000000']
    colorsLight = [_light( c ) for c in colorsNormal]
    if light:
        colors = colorsLight
    else:
        colors = colorsNormal
    if index<len( colors ):
        return colors[index]
    return colors[index%len( colors )]


def ShowImages(trace):
    global ShowSignal, ShowSpectrum, ShowFittedSine
    global tkHeader, tkSignal, plotSignal, figSignal, linesSignals, plotMinSignal, lineMinSignals, minSignals, plotMaxSignal, lineMaxSignals, maxSignals, tkSpectrum, plotSpectrum, lineSpectrum, plotMaxSpectrum, lineMaxSpectrum, specMax, spectrumReset
    tkHeader.itemconfigure("NAME", text="Name: %s" % (trace.filename))
    if len( trace )==0 or len( trace[0] )==0:
        return
    # MODEL
    try:
        tkHeader.itemconfigure("VMODEL", text="%s" % (trace.model))
    except:
        tkHeader.itemconfigure("VMODEL", text="%s" % ("<unknown>"))
    # TEMPERATURE
    try:
        text = "Temp (C):"
        for temp in trace.temperatures:
            text = text + (" %d" % (temp))
        tkHeader.itemconfigure("VTEMP", text=text)
    except:
        tkHeader.itemconfigure("VTEMP", text="")
    # FPGA IDs
    try:
        text = "ID:"
        for fpga in trace.fpgaids:
            text = text + " " + fpga
        tkHeader.itemconfigure("VIDS", text=text)
    except:
        tkHeader.itemconfigure("VIDS", text="")
    # NBR SAMPLES
    try:
        if trace.ActualPoints == 0:
            tkHeader.itemconfigure("VCOUNT", text="%d" % (trace.ActualPoints))
        else:
            tkHeader.itemconfigure("VCOUNT", text="%d (%d for FFT)" % (trace.ActualPoints, trace.nbrFftSamples))
            tkHeader.itemconfigure("VFULLSCALE", text="%d LSB" % (trace.FullScale))
            tkHeader.itemconfigure("VSAMPIVAL", text="%5.3g ns" % (trace.XIncrement * 1e9))
            tkHeader.itemconfigure("VNBRADC", text="")
    except:
        tkHeader.itemconfigure("VCOUNT", text="" )
        tkHeader.itemconfigure("VFULLSCALE", text="" )
        tkHeader.itemconfigure("VSAMPIVAL", text="" )
        tkHeader.itemconfigure("VNBRADC", text="" )
    # RATIOS
    if trace.ratios:
        ratios = trace.ratios
        try: vsig = "%.3f" % (10.0 * math.log(ratios.powFS / ratios.powSignal) / math.log(10.0))
        except: vsig = "###"
        tkHeader.itemconfigure("VSIG", text="Signal: %s dBFS" % (vsig))
        try: vsnr="%.3f" % (10.0 * math.log(ratios.powFS / ratios.powNoise) / math.log(10.0))
        except: vsnr = "###"
        tkHeader.itemconfigure("VSNR", text="SNR: %s dBFS" % (vsnr))
        try: vthd="%.3f" % (10.0 * math.log(ratios.powFS / ratios.powThd) / math.log(10.0))
        except: vthd = "###"
        tkHeader.itemconfigure("VTHD", text="THD: %s dBFS" % (vthd))
        try:
            sinad = 10.0 * math.log(ratios.powFS / (ratios.powNoise + ratios.powThd)) / math.log(10.0)
            vsinad = "%.3f" % (sinad)
        except: vsinad = "###"
        tkHeader.itemconfigure("VSINAD", text="SINAD: %s dBFS" % (vsinad))
        try: venob = "%.3f" % ((sinad - 1.76) / 6.02)
        except: venob = "###"
        tkHeader.itemconfigure("VENOB", text="ENOB: %s LSB" % (venob))
        try: vsfdr = "%5.3f" % (10.0 * math.log(ratios.powSignal / ratios.powSecond) / math.log(10.0))
        except: vsfdr = "#####"
        tkHeader.itemconfigure("VSFDR", text="SFDR: %s dBc" % (vsfdr))
    if USE_SCIPY:
        nbrChannels = len( trace )
        if ShowSignal:
            if linesSignals and len( linesSignals )>0 and linesSignals[0] and \
                    (   len(linesSignals[0].get_xdata()) != len( trace[0] ) \
                     or (linesSignals[0].get_xdata()[1] - linesSignals[0].get_xdata()[0]) != trace.XIncrement   ):
                plotSignal.clear()
                linesSignals = []
                minSignals = []
                lineMinSignals = []
                maxSignals = []
                lineMaxSignals = []
            while len( linesSignals ) < nbrChannels:
                linesSignals.append( None )
                if plotMinSignal:
                    minSignals.append( None )
                    lineMinSignals.append( None )
                if plotMaxSignal:
                    maxSignals.append( None )
                    lineMaxSignals.append( None )
            marker = None
            if trace.ActualPoints <= 100:
                marker = "."
            for ch, wfm in enumerate( trace ):
                if plotMinSignal:
                    if not lineMinSignals[ch] or len(lineMinSignals[ch].get_xdata()) != len(minSignals[ch]):
                        minSignals[ch] = wfm.Samples
                        timeFirst = 0.0 if trace.InitialXOffset == 0.0 else -trace.XIncrement*1e6
                        timeFull  = trace.XIncrement * ( trace.ActualPoints-1 ) * 1e6 - timeFirst
                        time = linspace(timeFirst, timeFull, trace.ActualPoints)
                        try: lineMinSignals[ch], = plotMinSignal.plot(time, minSignals[ch], color=_GetColor(ch, light=True))
                        except: pass
                    elif spectrumReset:
                        minSignals[ch] = wfm.Samples
                    else:
                        minSignals[ch] = minimum(wfm.Samples, minSignals[ch])
                        lineMinSignals[ch].set_ydata(minSignals[ch])
                if plotMaxSignal:
                    if not lineMaxSignals[ch] or len(lineMaxSignals[ch].get_xdata()) != len(maxSignals[ch]):
                        maxSignals[ch] = wfm.Samples
                        timeFirst = 0.0 if trace.InitialXOffset == 0.0 else -trace.XIncrement*1e6
                        timeFull = trace.XIncrement * ( trace.ActualPoints-1 ) * 1e6 - timeFirst
                        time = linspace(timeFirst, timeFull , trace.ActualPoints)
                        try: lineMaxSignals[ch], = plotMaxSignal.plot(time, maxSignals[ch], color=_GetColor(ch, light=True))
                        except: pass
                    elif spectrumReset:
                        maxSignals[ch] = wfm.Samples
                    else:
                        maxSignals[ch] = maximum(wfm.Samples, maxSignals[ch])
                        lineMaxSignals[ch].set_ydata(maxSignals[ch])
                if not linesSignals[ch]:
                    plotSignal.set_title('Signal (us)')
                    plotSignal.set_ylabel('magnitude')
                    plotSignal.grid( which='both', linestyle='-' )
                    timeFirst = -trace.XIncrement*1e6 #0.0 if trace.InitialXOffset == 0.0 else -trace.XIncrement*1e6
                    timeFull = trace.XIncrement * ( trace.ActualPoints-1 ) * 1e6 - timeFirst
                    time = linspace(timeFirst, timeFull, trace.ActualPoints)
                    time = time + trace.InitialXOffset%trace.XIncrement * 1e6
                    linesSignals[ch], = plotSignal.plot(time, wfm.Samples, color=_GetColor(ch), marker=marker)
                    plotSignal.get_xaxis().axes.set_xlim(timeFirst, timeFull)
                    try:
                        yscale = 2**trace.NbrAdcBits * trace.ActualAverages
                        ylim = ( 0, yscale )
                    except:
                        yscale = trace.FullScale
                        if yscale>100: # Big: raw sample value; Small: voltage/phase
                            ylim = (-yscale/2, yscale/2 - 1)
                        else:
                            ylim = (-yscale/2, yscale/2)
                    plotSignal.get_yaxis().axes.set_ylim(*ylim)
                    plotSignal.get_yaxis().axes.set_yticks([ylim[0]+n*yscale/8 for n in range(0, 8)] + [ylim[1]])
                else:
                    if trace.InitialXOffset!=0.0:
                        timeFirst = 0.0 if trace.InitialXOffset == 0.0 else -trace.XIncrement*1e6
                        timeFull = trace.XIncrement * ( trace.ActualPoints-1 ) * 1e6 - timeFirst
                        time = linspace(timeFirst, timeFull, trace.ActualPoints)
                        time = time + trace.InitialXOffset%trace.XIncrement * 1e6
                        linesSignals[ch].set_xdata(time)
                    linesSignals[ch].set_ydata( wfm.Samples )
            tkSignal.draw()
        if ShowSpectrum:
            spec = 20.0 * log10(trace.spectrums[0][0:trace.ActualPoints // 2 + 1] / (trace.FullScale / 2))
            if spectrumReset or not lineSpectrum or len(lineSpectrum.get_xdata()) != len(spec):
                plotSpectrum.clear()
                lineSpectrum = None
                lineMaxSpectrum = None
                freqHalf = 0.5 / trace.XIncrement / 1e6
                freq = linspace(0.0, freqHalf, len(spec))
                specMax = spec
                try: lineMaxSpectrum, = plotMaxSpectrum.plot(freq, specMax, color='#9cdbd8')
                except: pass
                try: lineSpectrum, = plotSpectrum.plot(freq, spec, color='#0085d5')
                except: pass
                plotSpectrum.set_title('Spectrum (MHz)')
                plotSpectrum.set_ylabel('dBFS')
                plotSpectrum.grid( which='both', linestyle='-' )
                plotSpectrum.get_xaxis().axes.set_xlim(0, freqHalf)
                plotSpectrum.get_yaxis().axes.set_ylim(-120, 0)
            else:
                lineSpectrum.set_ydata(spec)
                specMax = maximum(spec, specMax)
                lineMaxSpectrum.set_ydata(specMax)
            tkSpectrum.draw()
        if spectrumReset:
            spectrumReset = False
    # Fitted sine values
    mismatch = Mismatch()
    if ShowFittedSine and trace.fittedSine:
        psine = trace.fittedSine.all
        FullScale = max(1, trace.fittedSine.FullScale)
        sampival = max(1e-12, trace.fittedSine.XIncrement)
        frequency = psine[OMEGA] / 2.0 / pi / sampival
        delay = psine[PHASE] / 2.0 / pi / frequency
        mismatch.frequency = frequency
        tkUpdateLabel(tkFitted.children["allfreq"], '%7.3f MHz' % (frequency/1e6))
        tkUpdateLabel(tkFitted.children["allphase"], '%7.5f rad' % (psine[PHASE]))
        tkUpdateLabel(tkFitted.children["allgain"], '%7.0f LSB' % (psine[GAIN]))
        tkUpdateLabel(tkFitted.children["alloffset"], '%7.2f LSB' % (psine[OFFSET]))
        tkUpdateLabel(tkFitted.children["allrms"], '%7.3f LSB' % (psine[RMS]))
        try: vallenob = "%5.2f" % (math.log(FullScale / (sqrt(12) * psine[RMS] )) / math.log(2.0))
        except: vallenob = "#####"
        tkUpdateLabel(tkFitted.children["allenob"], '%s bits' % (vallenob))
        for adc in range(0, len(trace.fittedSine.adc)):
            if not tkFitted.children.has_key("adc%dfreq"%(adc)):
                Label(tkFitted, name="adc%dhead"%(adc), text='ADC %d' % (adc)).grid(row=0, column=adc+2)
                for n in range(0, 6):
                    Label(tkFitted, name="adc%d%s"%(adc,nameRow[n]), text='').grid(row=n+1, column=adc+2)
            psine = trace.fittedSine.adc[adc]
            frequencyAdc = psine[OMEGA] / 2.0 / pi / sampival
            phaseCorr = [ 0.0, 1.0, 2.0, 3.0 ]
            phaseAdc = psine[PHASE] - phaseCorr[adc] * psine[OMEGA]
            delayAdc = phaseAdc / 2.0 / pi / frequency
            while delayAdc > 0.2 / frequency:
                delayAdc = delayAdc - 1.0 / frequency
            while delayAdc < (-0.2 / frequency):
                delayAdc = delayAdc + 1.0 / frequency
            if adc == 0: delayAdc0 = delayAdc; gainAdc0 = psine[GAIN]; offsetAdc0 = psine[OFFSET]
            tkUpdateLabel(tkFitted.children["adc%dfreq"%(adc)], '%7.3f MHz' % (psine[OMEGA]/2.0/pi/sampival/1e6))
            #tkUpdateLabel(tkFitted.children["adc%dphase"%(adc)], '%7.5f rad' % (phaseAdc))
            tkUpdateLabel(tkFitted.children["adc%dphase"%(adc)], '%7.2f ps' % ((delayAdc - delayAdc0) * 1e12))
            tkUpdateLabel(tkFitted.children["adc%dgain"%(adc)], '%7.0f LSB' % (psine[GAIN]))
            tkUpdateLabel(tkFitted.children["adc%doffset"%(adc)], '%7.2f LSB' % (psine[OFFSET]))
            tkUpdateLabel(tkFitted.children["adc%drms"%(adc)], '%7.3f LSB' % (psine[RMS]))
            try: vadcenob = "%5.2f" % (math.log(FullScale / (sqrt(12) * psine[RMS] )) / math.log(2.0))
            except: vadcenob = "#####"
            tkUpdateLabel(tkFitted.children["adc%denob"%(adc)], '%s bits' % (vadcenob))
            mismatch.adc.append(  ((delayAdc - delayAdc0) * 1e12, (psine[GAIN] - gainAdc0) / gainAdc0 * 100, (psine[OFFSET] - offsetAdc0) / gainAdc0 * 100)  )


tkMain = None
Pause = False
Force = True

def ReadInput( queue ):
    global ShowAll
    for trace in GetTraceFromSource():
        if not ShowAll and not Pause:
            while not queue.empty():
                queue.get_nowait()
        queue.put( trace )
        time.sleep( 1e-3 )


def Update():
    global queue
    global Pause, Force
    if Pause and not Force:
        return
    if queue.empty() and not Pause:
        tkMain.after(20, Update)
        return
    Force = False
    if not queue.empty():
        trace = queue.get()#_nowait()
        CalculateTrace(trace)
        ShowImages(trace)
    if not Pause:
        tkMain.after(0, Update)


def PauseText():
    global Pause
    if Pause:
        return "Unpause"
    return "Pause"


def RunPause():
    global Pause
    Pause = not Pause
    if not Pause:
        Update()
    tkMain.tkPause.configure(text=PauseText())


def RunNext():
    global Pause, Force
    if Pause:
        Force = True
        Update()


def main():
    global ShowRatios, ShowSignal, ShowSpectrum, ShowFittedSine, ShowAll
    global Pause, RunCommand, InputFile, TcpPort, TcpBind, TcpHost
    global queue

    from argparse import ArgumentParser
    parser = ArgumentParser( "Live Viewer" )
    parser.add_argument( "--signal", action='store_true', default=None )
    parser.add_argument( "--spectrum", action='store_true' )
    parser.add_argument( "--ratios", action='store_true' )
    parser.add_argument( "--fitted-sine", action='store_true' )
    parser.add_argument( "--size", type=str, default="640x320" )
    parser.add_argument( "--pause", action='store_true', default=False )
    parser.add_argument( "--run", nargs="+", type=str )
    parser.add_argument( "--tcp", type=str, default=None )
    parser.add_argument( "--listen", type=int, default=None )
    parser.add_argument( "--bind", type=str, default=None )
    parser.add_argument( "--min-max-signal", action='store_true', default=False )
    parser.add_argument( "--nolive", action='store_true', default=False )
    parser.add_argument( "inputs", type=str, nargs="*" )

    args = parser.parse_args()
    args.width, args.height = map( int, args.size.split("x") )

    Pause = args.pause
    ShowAll = args.nolive
    ImgWidth = args.width
    ImgHeight = args.height
    InputFile = args.inputs[0] if len( args.inputs )>0 else None
    RunCommand = " ".join( args.run ) if args.run else None
    TcpHost = args.tcp
    TcpBind = args.bind if args.bind else ""
    TcpPort = args.listen
    ShowRatios = args.ratios
    ShowSignal = args.signal if args.spectrum else True
    ShowSpectrum = args.spectrum
    ShowFittedSine = args.fitted_sine
        

    global tkMain, tkHeader, tkSignal, figSignal, plotSignal, linesSignals, plotMinSignal, lineMinSignals, minSignals, plotMaxSignal, lineMaxSignals, maxSignals, tkSpectrum, plotSpectrum, lineSpectrum, plotMaxSpectrum, lineMaxSpectrum, specMax, tkFitted

    tk = Tk()
    try:
        with open( expanduser( "~/.viewer_live.cfg" ), "rt" ) as f:
            line = f.readline()
            geometry = re.match( r"geometry\s*=\s*(\S*)\s*", line ).group(1)
            tk.geometry( geometry )
    except FileNotFoundError:
        pass


    tkMain = Frame(tk, name="main")
    tkMain.pack(fill=BOTH, expand=1)
    tkMain.master.title("Live Viewer")

    # Within tkMain, use Grid Geometry
    tkHeader = Canvas(tkMain, name="header", height=4+80+4, width=ImgWidth+80)
    tkHeader.pack(side=TOP, fill=Y)
    tkHeader.create_text(164, 4+0,  tag="LMODEL", anchor=NE, width=160, text="Model:")
    tkHeader.create_text(164, 4+16, tag="LCOUNT", anchor=NE, width=160, text="Number of samples:")
    tkHeader.create_text(164, 4+32, tag="LFULLSCALE", anchor=NE, width=160, text="Fullscale:")
    tkHeader.create_text(164, 4+48, tag="LSAMPIVAL", anchor=NE, width=160, text="Sampling interval:")
    tkHeader.create_text(164, 4+64, tag="LNBRADC", anchor=NE, width=160, text="Number of ADC:")
    tkHeader.create_text(168, 4+0,  tag="VMODEL", anchor=NW, width=160)
    tkHeader.create_text(168, 4+16, tag="VCOUNT", anchor=NW, width=160)
    tkHeader.create_text(168, 4+32, tag="VFULLSCALE", anchor=NW, width=160)
    tkHeader.create_text(168, 4+48, tag="VSAMPIVAL", anchor=NW, width=160)
    tkHeader.create_text(168, 4+64, tag="VNBRADC", anchor=NW, width=160)
    tkHeader.create_text(328, 4+0,  tag="NAME", anchor=NW, width=640)
    tkHeader.create_text(328, 4+16, tag="VSIG", anchor=NW, width=160)
    tkHeader.create_text(492, 4+16, tag="VIDS", anchor=NW, width=240)
    tkHeader.create_text(328, 4+32, tag="VSNR", anchor=NW, width=160)
    tkHeader.create_text(492, 4+32, tag="VTHD", anchor=NW, width=160)
    tkHeader.create_text(328, 4+48, tag="VSINAD", anchor=NW, width=160)
    tkHeader.create_text(492, 4+48, tag="VENOB", anchor=NW, width=160)
    tkHeader.create_text(328, 4+64, tag="VSFDR", anchor=NW, width=160)
    tkHeader.create_text(492, 4+64, tag="VTEMP", anchor=NW, width=160)
    
    if USE_SCIPY:
        if ShowSignal:
            figSignal = Figure(figsize=(5, 2.5), dpi=100)
            plotSignal = figSignal.add_subplot(111)
            linesSignals = []
            if args.min_max_signal:
                plotMinSignal = figSignal.add_subplot(111)
                lineMinSignals = []
                minSignals = []
                plotMaxSignal = figSignal.add_subplot(111)
                lineMaxSignals = []
                maxSignals = []
            else:
                plotMinSignal = None
                plotMaxSignal = None

            plotSignal.set_title('Signal (us)')
            plotSignal.set_ylabel('magnitude')
            plotSignal.grid( which='both', linestyle='-' )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                figSignal.tight_layout()

            tkSignal = FigureCanvas(figSignal, master=tkMain)
            tkSignal.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        if ShowSpectrum:
            figSpectrum = Figure(figsize=(5, 2.5), dpi=100)
            plotSpectrum = figSpectrum.add_subplot(111)
            lineSpectrum = None
            specMax = None
            plotMaxSpectrum = figSpectrum.add_subplot(111)
            lineMaxSpectrum = None

            plotSpectrum.set_title('Spectrum (MHz)')
            plotSpectrum.set_ylabel('dBFS')
            plotSpectrum.get_yaxis().axes.set_ylim(-120, 0)
            plotSpectrum.grid( which='both', linestyle='-' )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                figSpectrum.tight_layout()

            tkSpectrum = FigureCanvas(figSpectrum, master=tkMain)
            tkSpectrum.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        tkMain.pack()

    if ShowFittedSine:
        tkFitted = Frame(tkMain, name="fitted")
        tkFitted.pack(side=TOP, fill=Y)

        Label(tkFitted, text='All ADC').grid(row=0, column=1)

        Label(tkFitted, name="labfreq", text='Frequency').grid(row=1, column=0, sticky=W)
        Label(tkFitted, name="labphase", text='Phase').grid(row=2, column=0, sticky=W)
        Label(tkFitted, name="labgain", text='Amplitude').grid(row=3, column=0, sticky=W)
        Label(tkFitted, name="laboffset", text='Offset').grid(row=4, column=0, sticky=W)
        Label(tkFitted, name="labrms", text='RMS').grid(row=5, column=0, sticky=W)
        Label(tkFitted, name="labenob", text='ENOB').grid(row=6, column=0, sticky=W)

        Label(tkFitted, name="allfreq", text='').grid(row=1, column=1)
        Label(tkFitted, name="allphase", text='').grid(row=2, column=1)
        Label(tkFitted, name="allgain", text='').grid(row=3, column=1)
        Label(tkFitted, name="alloffset", text='').grid(row=4, column=1)
        Label(tkFitted, name="allrms", text='').grid(row=5, column=1)
        Label(tkFitted, name="allenob", text='').grid(row=6, column=1)

    # Within tkMain, use Pack Geometry
    if InputFile and InputFile != '-':
        tkMain.master.title("Live Viewer - " + InputFile)
        tkButton = Button(tkMain, text="Refresh", command=Update)
        tkButton.pack(side=BOTTOM)
    else:
        tkMain.tkPause = Button(tkMain, text=PauseText(), command=RunPause)
        tkMain.tkPause.pack(side=RIGHT)
        tkNext = Button(tkMain, text="Next", command=RunNext)
        tkNext.pack(side=RIGHT)

    if USE_SCIPY:
        tkClear = Button(tkMain, text="Clear", command=Clear)
        tkClear.pack(side=LEFT)


    queue = Queue()
    cmdthread = Thread( target=ReadInput, args=( queue, ), daemon=True )
    cmdthread.start()

    tkMain.after(20, Update)

    def _OnWmDeleteWindow():
        geom = tk.geometry()
        with open( expanduser( "~/.viewer_live.cfg" ), "wt" ) as f:
            f.write( "geometry="+geom+"\n" )
        tk.destroy()


    tk.protocol("WM_DELETE_WINDOW", _OnWmDeleteWindow)

    tkMain.mainloop()



if __name__ == '__main__':
    import cProfile
    cProfile.run( 'main()', 'live.prof' )
    #main()

