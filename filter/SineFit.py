#!/usr/bin/python3

from sys import stderr, stdin, stdout
from waveforms.trace import ReadTrace, OutputTrace
from argparse import ArgumentParser
import numpy as np
import math

# Takes as input a .trc file, and output a .skew file.


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
    return fittedSine


# Sine fit function copied from EX NUMERUS website (http://exnumerus.blogspot.de/search/label/Curve%20Fitting)
def fitSine(tList,yList,freq):
   '''
       freq in Hz
       tList in sec
   returns
       phase in degrees
   '''
   b = matrix(yList).T
   rows = [ [sin(freq*2*pi*t), cos(freq*2*pi*t), 1] for t in tList]
   A = matrix(rows)
   (w,residuals,rank,sing_vals) = linalg.lstsq(A,b)
   phase = atan2(w[1,0],w[0,0])*180/pi
   amplitude = linalg.norm([w[0,0],w[1,0]],2)
   bias = w[2,0]
   return (phase,amplitude,bias)


def SineFit3( record, omega, width=None, step=None ):
    result = []
    size = record.ActualPoints
    times = np.arange( 0, size, dtype=np.float64 )
    coses = np.cos( np.copy( times*omega ) )
    sines = np.sin( np.copy( times*omega ) )
    cocos = coses*coses
    sisis = sines*sines
    cosis = coses*sines
    width = width if width else size
    step = step if step else width
    for it in range( 0, size-width+1, step ):
        f, l = it, it+width # Shortened names for first and last.
        #print( size, width, step, it, l, file=stderr )
        A = np.matrix( [ [np.add.reduce( cocos[f:l] ), np.add.reduce( cosis[f:l] ), np.add.reduce( coses[f:l] )],
                         [np.add.reduce( cosis[f:l] ), np.add.reduce( sisis[f:l] ), np.add.reduce( sines[f:l] )],
                         [np.add.reduce( coses[f:l] ), np.add.reduce( sines[f:l] ), np.add.reduce( width )] ], dtype=np.float64 )
        Z = np.linalg.inv( A )
        for wfm in record:
            coxes = coses*wfm.Samples
            sixes = sines*wfm.Samples
            xes   = wfm.Samples
            V = np.array( [np.add.reduce( coxes[f:l] ), np.add.reduce( sixes[f:l] ), np.add.reduce( xes[f:l] )], dtype=np.float64 ).transpose()
            R = np.matmul( Z, V ).T
            R0 = float( R[0] )
            R1 = float( R[1] )
            R2 = float( R[2] )
            amp = math.sqrt( R0*R0 + R1*R1 )
            phy = math.atan2( R0, R1 )
            off = R2
            result.append( (omega, off, amp, phy) )
    return result



def main():
    parser = ArgumentParser()
    parser.add_argument( "--sine-freq",  "-sf",  type=float )
    parser.add_argument( "--width",      "-w",   type=int )
    parser.add_argument( "--step",       "-s",   type=int )
    parser.add_argument( "--output",     "-o",   type=str   )
    parser.add_argument( "--output-comp", "-oc",   default=False, action='store_true' )
    parser.add_argument( "--output-diff", "-od",   default=False, action='store_true' )
    parser.add_argument( "--output-sine", "-os",   default=False, action='store_true' )
    parser.add_argument( "--minimum-amplitude", "-mina", type=float )
    parser.add_argument( "files", nargs='*', type=str       )

    args = parser.parse_args()

    if len( args.files )==0:
        trcfiles = [stdin]
    else:
        trcfiles = [open( name, 'rt' ) for name in args.files]

    out = open( args.output, 'wt' ) if args.output else stdout

    #if args.output_comp or args.output_diff:


    nbrErr = 0
    for trcfile in trcfiles:
        for rec in ReadTrace( trcfile ):
            if hasattr( rec, 'SineFreq' ) or args.sine_freq:
                sineFreq = getattr( rec, 'SineFreq', args.sine_freq )
                omega = 2*np.pi*sineFreq*rec.XIncrement
                fits = SineFit3( rec, omega, width=args.width, step=args.step )
                omega, offset, amplitude, phase = fits[0]
            else:
                # SineFit4
                print( "SineFit without signal frequency information is not supported", file=stderr )
                continue
            try:
                if args.output_sine:
                    print( offset, amplitude, omega/2/np.pi/rec.XIncrement, *[(fit[3]/2/np.pi/args.sine_freq-rec.InitialXOffset)*1e12 for fit in fits] )
                elif args.output_comp:
                    OutputTrace(rec)
                else:
                    for omega, offset, amplitude, phase in fits:
                        print( offset, amplitude, omega/2/np.pi/rec.XIncrement, (phase/2/np.pi/args.sine_freq-rec.InitialXOffset)*1e12 )
                        if args.minimum_amplitude and amplitude < args.minimum_amplitude:
                            fname = "SineFit-Error-%02d.trc"%( nbrErr )
                            print( "ERROR: amplitude is too low. Output trace in", fname )
                            OutputTrace( rec, open( fname, 'wt' ) )
                            nbrErr = nbrErr+1
                            if nbrErr == 100:
                                return
            except (BrokenPipeError):
                return



if __name__=="__main__":
    main()

