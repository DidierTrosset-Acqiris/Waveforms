#!/usr/bin/python3

from sys import stderr, stdout
from waveforms.trace import Trace, OutputTrace
from argparse import ArgumentParser
from math import sin
import numpy as np


def main():
    parser = ArgumentParser()
    parser.add_argument( "--freq", "-f",      type=float, default=100e6 )
    parser.add_argument( "--amplitude", "-a", type=float, default=6e3 )
    parser.add_argument( "--offset", "-o",    type=float, default=0.0 )
    parser.add_argument( "--bits", "-b",      type=int,   default=14 )
    parser.add_argument( "--sampling", "-s",  type=float, default=2e9 )
    parser.add_argument( "--cores", "-c",     type=int,   default=1 )
    parser.add_argument( "--width", "-w",     type=int,   default=16 )
    parser.add_argument( "--length", "-l",    type=int,   default=1000 )
    parser.add_argument( "--delays", "-p", nargs="*", type=float, default=[0.0])

    args = parser.parse_args()


    waveform = np.zeros( args.length, dtype=np.int16 )

    for n in range( args.length ):
        t = n / args.sampling
        p = args.delays[n % args.cores]
        w = 2 * np.pi * args.freq * ( t + p )
        v = args.offset + args.amplitude * sin( w )
        s = int( v ) * 2**( args.width - args.bits )
        waveform[n] = s

    wave = Trace.Wave()
    wave._Samples = waveform
    wave.ScaleFactor = 2.0/65536
    wave.ScaleOffset = 0.0

    trace = Trace()
    trace._Waves = [wave]
    trace.TraceType = "Digitizer"
    trace.SampleType = "Int16"
    trace.NbrAdcBits = 10
    trace.FullScale = 65536
    trace.ActualChannels = 1
    trace.Model = "GENERATOR"
    trace.XIncrement = 1.0 / args.sampling
    trace.InitialXOffset = 0.0
    trace.InitialXTimeSeconds = 0.0
    trace.InitialXTimeFraction = 0.0

    OutputTrace( trace, file=stdout )

if __name__=="__main__":
    main()


