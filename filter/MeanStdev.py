#!/usr/bin/python3

from sys import stderr, stdin, stdout
from waveforms.trace import ReadTrace
from argparse import ArgumentParser
import numpy as np
import math

# Takes as input a .trc file, and output a .skew file.


def MeanStdev( record, width=None, step=None ):
    result = []
    size = record.ActualPoints
    width = width if width else size
    step = step if step else width
    for it in range( 0, size-width+1, step ):
        f, l = it, it+width # Shortened names for first and last.
        #print( size, width, step, it, l, file=stderr )
        for wfm in record:
            mean = np.mean( wfm.Samples[f:l] )
            sdev = np.std(  wfm.Samples[f:l] )
            result.append( (mean, sdev) )
    return result



def main():
    parser = ArgumentParser()
    parser.add_argument( "--width",      "-w",   type=int )
    parser.add_argument( "--step",       "-s",   type=int )
    parser.add_argument( "--output",     "-o",   type=str   )
    parser.add_argument( "files", nargs='*', type=str       )

    args = parser.parse_args()

    if len( args.files )==0:
        trcfiles = [stdin]
    else:
        trcfiles = [open( name, 'rt' ) for name in args.files]

    out = open( args.output, 'wt' ) if args.output else stdout

    for trcfile in trcfiles:
        for rec in ReadTrace( trcfile ):
            mds = MeanStdev( rec, width=args.width, step=args.step )
            for md in mds:
                print( md[0], md[1], file=out )


if __name__=="__main__":
    main()

