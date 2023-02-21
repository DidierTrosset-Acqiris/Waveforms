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
    parser.add_argument( "--record-decim",  "-rd",  type=int,   default=1   )
    parser.add_argument( "--sample-start",  "-ss",  type=int,   default=0   )
    parser.add_argument( "--sample-count",  "-sc",  type=int,   default=1000000   )
    parser.add_argument( "--sample-decim",  "-sd",  type=int,   default=1   )
    parser.add_argument( "--sample-first",  "-sf",  type=int,   default=0   )
    parser.add_argument( "--output",        "-o",   type=str )
    parser.add_argument( "--data-type", "-dt",      type=str,   default="int16", choices=["int8", "int16"] )
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
    riDecim = args.record_decim
    siStart = args.sample_start
    siCount = args.sample_count
    siDecim = args.sample_decim
    siFirst = args.sample_first
    dataType = int8 if args.data_type=="int8" else int16

    recs = []
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
                samples = array( list( map( int, values[siStart:siStart+siCount] ) ), dtype=dataType )
            except:
                print( "ERROR on line", ri, line, file=stderr )
                raise
            ri = ri+1
            if ri<riStart:
                continue
            if ( ( ri-riStart )%riDecim )!=0:
                continue
            if riCount>0 and ri>=riStart+riCount:
                break
            if siDecim>1:
                recSamples = samples.reshape((siDecim,samples.size//siDecim), order='F')[siFirst]
            else:
                recSamples = samples
            rec = Record( FullScale=256 if dataType==int8 else 65536 )
            rec.append( (recSamples,
                          len( recSamples ),
                          0,
                          InitialXOffset,  # InitialXOffset
                          0.0,  # InitialXTimeSeconds
                          0.0,  # InitialXTimeFraction
                          1e-9, # XIncrement
                          5.0/256.0,  # ScaleFactor
                          0.0 ) )     # ScaleOffset
            if riCount<0:
                recs.append( rec )
                if len( recs )>-riCount:
                    recs = recs[1:]
                continue
            try:
                OutputTrace( rec, out )
            except BrokenPipeError:
                return
    if riCount<0:
        for rec in recs:
            try:
                OutputTrace( rec, out )
            except BrokenPipeError:
                return


if __name__=="__main__":
    main()

