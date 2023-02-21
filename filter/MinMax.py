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

    for trcfile in trcfiles:
        try:
            for rec in ReadTrace( trcfile ):
                try:
                    mins = [np.min(wfm.Samples) for wfm in rec]
                    maxs = [np.max(wfm.Samples) for wfm in rec]
                    print( *mins, file=out )
                    print( *maxs, file=out )
                except (BrokenPipeError):
                    return
        except AttributeError:
            count = 0
            for index, line in enumerate( trcfile ):
                count = count + 1
                values = list( map( float, line.split() ) )
                if index == 0:
                    mins = [ 4e9 for v in values]
                    maxs = [-4e9 for v in values]
                    means = [0.0 for v in values ]
                    sqsums = [0.0 for v in values ]
                for i, v in enumerate( values ):
                    if v<mins[i]: mins[i] = v
                    if v>maxs[i]: maxs[i] = v
                    delta = v - means[i]
                    means[i] += delta/count
                    sqsums[i] += delta*( v-means[i] )
            sdevs = [math.sqrt( sqs/(count-1) ) for sqs in sqsums]
            print( *mins, *maxs, *means, *sdevs, file=out )
            #print( *maxs, file=out )
            #print( *means, file=out )
            #print( *sdevs, file=out )



if __name__=="__main__":
    main()

