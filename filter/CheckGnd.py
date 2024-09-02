#!/usr/bin/python3

from sys import stderr, stdin, stdout
from waveforms.trace import ReadTrace
from argparse import ArgumentParser
import numpy as np
import math

# Takes as input a .trc file, and output a .skew file.


def main():
    parser = ArgumentParser()
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
                wavs = [wav.Samples for wav in rec]
                cnts = list( map( len, wavs ) )
                avgs = list( map( np.mean,  wavs ) )
                stds = list( map( np.std,   wavs ) )
                print( *[f"{avg:.2f} ({std:.2f} - {cnt})" for avg, std, cnt in zip( avgs, stds, cnts )] )
            except (BrokenPipeError):
                return


if __name__=="__main__":
    main()


