#!/usr/bin/python3

from sys import stdin, stdout
from waveforms import Record
from waveforms.trace import ReadTrace, OutputTrace
from argparse import ArgumentParser
import numpy as np

# Takes as input a .trc file, and output a .skew file.


def main():
    parser = ArgumentParser()
    parser.add_argument( "--taps", "-t", nargs="*", type=float, default=[1] )
    parser.add_argument( "--output", "-o",   type=str )
    parser.add_argument( "files", nargs='*', type=str )

    args = parser.parse_args()


    if len( args.files )==0:
        traces = [stdin]
    else:
        traces = [open( name, 'rt' ) for name in args.files]

    out = open( args.output, 'wt' ) if args.output else stdout

    for trace in traces:
        for trc in ReadTrace( trace ):
            rec = Record()
            for c, wfm in enumerate( trc ):
                samples = np.zeros(wfm.Samples.size - len(args.taps) + 1, dtype=wfm.Samples.dtype )
                for s in range( samples.size ):
                    for t in range( len(args.taps) ):
                        samples[s] = samples[s] + wfm.Samples[s+t] * args.taps[t]
                rec.append( (samples,
                              len( samples ),
                              0,
                              trc.InitialXOffset,
                              trc.InitialXTimeSeconds,
                              trc.InitialXTimeFraction,
                              trc.XIncrement,
                              1.0, #trc.ScaleFactor if trc.ScaleFactor else 1.0,
                              0.0 ) ) #trc.ScaleOffset if trc.ScaleOffset else 0.0 ) )
            try:
                OutputTrace( rec, out )
            except BrokenPipeError:
                return


if __name__=="__main__":
    main()

