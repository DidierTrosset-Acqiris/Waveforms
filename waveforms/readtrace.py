#!/usr/bin/python3

from sys import stdin, stdout
from waveforms import Record
from waveforms.trace import ReadTrace, OutputTrace
from argparse import ArgumentParser

# Takes as input a .trc file, and output a .skew file.


def main():
    parser = ArgumentParser()
    parser.add_argument( "--record-start",  "-rs",  type=int,   default=0   )
    parser.add_argument( "--record-count",  "-rc",  type=int,   default=1000000   )
    parser.add_argument( "--output",        "-o",   type=str )
    parser.add_argument( "files", nargs='*', type=str )

    args = parser.parse_args()


    r_enumerate= lambda iterable: zip( reversed( range( len(iterable) ) ), reversed( iterable ) )

    if len( args.files )==0:
        traces = [stdin]
    else:
        traces = [open( name, 'rt' ) for name in args.files]

    out = open( args.output, 'wt' ) if args.output else stdout

    riStart = args.record_start
    riCount = args.record_count

    siStart = 0
    siCount = 20

    ri = 0
    for trace in traces:
        for ri, rec in enumerate( ReadTrace( trace ) ):
            if ri<riStart:
                continue
            if riCount>0 and ri>=riStart+riCount:
                break
            rec2 = Record()
            for c, wfm in r_enumerate( rec ):
                rec2.append( (wfm.Samples[siStart:siStart+siCount],
                              siCount,
                              0,
                              wfm.InitialXOffset,
                              wfm.InitialXTimeSeconds,
                              wfm.InitialXTimeFraction,
                              wfm.XIncrement,
                              wfm.ScaleFactor,
                              wfm.ScaleOffset) )
            try:
                OutputTrace( rec2, out )
            except BrokenPipeError:
                return


if __name__=="__main__":
    main()

