#!/usr/bin/python3

from sys import stderr, stdin, stdout
from waveforms.trace import ReadTrace, OutputTrace
from argparse import ArgumentParser
import numpy as np
import math

# Takes as input a .trc file, and output a .skew file.

def FindPrevNext( samples, level ):
    belowLevel = False
    for index, sample in enumerate( samples ):
        if belowLevel:
            if sample>=level:
                return ( (index-1, samples[index-1]), (index, samples[index]) )
        else:
            if sample<=level:
                belowLevel = True
    raise RuntimeError( "No edge found" )


def AverageEdges( records, level=None ):
    result = []
    if not level:
        if records[0].TraceType=="Accumulated":
            level = records[0].NbrAdcBits * records[0].ActualAverages / 2.0
        else:
            level = 0.0
    for rec in records:
        edges = []
        for wfm in rec:
            pnPairs = []
            try:
                pn = FindPrevNext( wfm, level )
                pnPairs.append( ( pn[0], pn[1], rec.InitialXOffset/rec.XIncrement ) )
            except RuntimeError:
                OutputTrace( rec, file=stderr )
                pass
            if len( pnPairs )==0:
                edges.append( None )
            if len( pnPairs )==1:
                p, n, o = pnPairs[0]
            edges.append( p[0] + o + ((level-p[1])/(n[1]-p[1])), )
        return edges
    raise NotImplementedError()

#    size = record.ActualPoints
#    width = width if width else size
#    step = step if step else width
#    for it in range( 0, size-width+1, step ):
#        f, l = it, it+width # Shortened names for first and last.
#        #print( size, width, step, it, l, file=stderr )
#        for wfm in record:
#            mean = np.mean( wfm.Samples[f:l] )
#            sdev = np.std(  wfm.Samples[f:l] )
#            result.append( (mean, sdev) )
#    return result



def main():
    parser = ArgumentParser()
    parser.add_argument( "--falling",    "-f",   default=False, action='store_true' )
    parser.add_argument( "--level",      "-l",   type=float )
    parser.add_argument( "--average",    "-a",   type=int )
    parser.add_argument( "--step",       "-s",   type=int )
    parser.add_argument( "--output",     "-o",   type=str )
    parser.add_argument( "--x-time",     "-xt",  default=False, action='store_true')
    parser.add_argument( "files", nargs='*', type=str       )

    args = parser.parse_args()

    if len( args.files )==0:
        trcfiles = [stdin]
    else:
        trcfiles = [open( name, 'rt' ) for name in args.files]

    out = open( args.output, 'wt' ) if args.output else stdout

    for trcfile in trcfiles:
        for rec in ReadTrace( trcfile ):
            if args.falling:
                for wfm in rec:
                    wfm.Samples *= -1
            edges = AverageEdges( [rec], level=args.level )
            if edges:
                if args.x_time:
                    edges.insert( 0, rec.InitialXTimeSeconds+rec.InitialXTimeFraction )
                try:
                    print( *edges, file=out, flush=True )
                except BrokenPipeError:
                    break



if __name__=="__main__":
    main()

