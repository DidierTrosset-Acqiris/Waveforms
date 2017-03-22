#!/usr/bin/python3

from sys import stdin, stdout
from waveforms import Record
from waveforms.trace import ReadTrace, OutputTrace
from argparse import ArgumentParser

# Takes as input a .trc file, and output a .skew file.


def main():
    parser = ArgumentParser()
    parser.add_argument( "--record-start",  "-rs",  type=int,   default=0   )
    parser.add_argument( "--record-count",  "-rc",  type=int,   default=-1   )
    parser.add_argument( "--sample-start",  "-ss",  type=int,   default=0   )
    parser.add_argument( "--sample-count",  "-sc",  type=int,   default=-1   )
    parser.add_argument( "--channels",      "-c",   type=int,   default=None,   nargs="*" )
    parser.add_argument( "--output",        "-o",   type=str )
    parser.add_argument( "files", nargs='*', type=str )

    args = parser.parse_args()


    if len( args.files )==0:
        traces = [stdin]
    else:
        traces = [open( name, 'rt' ) for name in args.files]

    out = open( args.output, 'wt' ) if args.output else stdout

    riStart = args.record_start
    riCount = args.record_count

    siStart = args.sample_start
    siCount = args.sample_count

    ri = 0
    for trace in traces:
        for ri, rec in enumerate( ReadTrace( trace ) ):
            if ri<riStart:
                continue
            if riCount>0 and ri>=riStart+riCount:
                break
            for c, wfm in enumerate( rec ):
                if args.channels and c+1 not in args.channels:
                    continue
                if siStart==0 and  siCount<0:
                    samples = wfm.Samples
                elif siCount<0:
                    samples = wfm.Samples[siStart:]
                else:
                    samples = wfm.Samples[siStart:siStart+siCount]
                wfm.Samples = samples
            try:
                OutputTrace( rec, out )
            except BrokenPipeError:
                return


if __name__=="__main__":
    main()

