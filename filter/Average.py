#!/usr/bin/python3

from sys import stderr, stdin, stdout
from waveforms.trace import ReadTrace
from argparse import ArgumentParser
import numpy as np
import math

# Takes as input a .trc file, and output a .skew file.


def main():
    parser = ArgumentParser()
    parser.add_argument( "--windows", "-w",  type=int, nargs='+' )
    parser.add_argument( "--step", "-s",     type=int )
    parser.add_argument( "--output", "-o",   type=str )
    parser.add_argument( "files", nargs='*', type=str )

    args = parser.parse_args()

    if len( args.files )==0:
        trcfiles = [stdin]
    else:
        trcfiles = [open( name, 'rt' ) for name in args.files]

    out = open( args.output, 'wt' ) if args.output else stdout

    for trc in trcfiles:
        for rec in ReadTrace( trc ):
            try:
                if len( args.windows )!=0:
                    windows = args.windows
                    step =  args.step if args.step else min( windows )
                    width = max( windows )
                    for s in range( 0, len(rec[0].Samples)-width+1, step ):
                        wfm = rec[0]
                        averages = [np.mean(wfm.Samples[s:s+w]) for w in windows]
                        print( *averages, file=out )
                else:
                    averages = [np.mean(wfm.Samples) for wfm in rec]
                    print( *averages, file=out )
            except (BrokenPipeError):
                return


if __name__=="__main__":
    main()

