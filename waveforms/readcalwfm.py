#!/usr/bin/python3

from sys import stdin, stdout, stderr
from waveforms import Record
from waveforms.trace import ReadTrace, OutputTrace
from argparse import ArgumentParser
from numpy import array, int8, int16

# Takes as input a .trc file, and output a .skew file.


def main():
    parser = ArgumentParser()
    parser.add_argument( "--record-start",  "-rs",  type=int,   default=0   )
    parser.add_argument( "--record-count",  "-rc",  type=int,   default=1000000   )
    parser.add_argument( "--sample-start",  "-ss",  type=int,   default=0   )
    parser.add_argument( "--sample-count",  "-sc",  type=int,   default=1000000   )
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
    siStart = args.sample_start
    siCount = args.sample_count

    for trace in traces:
        ri = -1
        for line in trace:
            line = line.strip()
            if line=="" or "==" in line or "^^" in line:
                continue
            values = line.split( ";" )[:-1]
            InitialXOffset = 0.0
            try:
                v = int( values[0] )
            except:
                try:
                    xoff, sample = values[0].split( ":" )
                    InitialXOffset = float( xoff )
                    values = [sample]+values[1:]
                except:
                    continue
            try:
                samples = array( list( map( int, values[siStart:siStart+siCount] ) ), dtype=int16 )
            except:
                print( "ERROR on line", ri, line, file=stderr )
                raise
            ri = ri+1
            if ri<riStart:
                continue
            if riCount>0 and ri>=riStart+riCount:
                break
            rec = Record()
            rec.append( (samples,
                          len( samples ),
                          0,
                          InitialXOffset,  # InitialXOffset
                          0.0,  # InitialXTimeSeconds
                          0.0,  # InitialXTimeFraction
                          1e-9, # XIncrement
                          5.0/256.0,  # ScaleFactor
                          0.0 ) )     # ScaleOffset
            try:
                OutputTrace( rec, out )
            except BrokenPipeError:
                return


if __name__=="__main__":
    main()

