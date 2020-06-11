#!/usr/bin/python3

from sys import stdin, stdout
from waveforms import Record
from waveforms.trace import ReadTrace, OutputTrace
from argparse import ArgumentParser

# Takes as input a .trc file, and output a .skew file.


def main():
    parser = ArgumentParser()
    parser.add_argument( "--split", "-s",    type=int, default=2 )
    parser.add_argument( "--channel", "-c",  type=int, default=1 )
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
                if c+1 != args.channel:
                    continue
                if args.split==1:
                    rec.append( (wfm.Samples,
                                  len( wfm.Samples ),
                                  0,
                                  trc.InitialXOffset,
                                  trc.InitialXTimeSeconds,
                                  trc.InitialXTimeFraction,
                                  trc.XIncrement,
                                  1.0, #trc.ScaleFactor,
                                  0.0 ) ) #trc.ScaleOffset ) )
                else:
                    decim = args.split
                    for i in range( decim ):
                        recSamples = wfm.Samples.reshape((decim,wfm.Samples.size//decim), order='F')[i]
                        rec.append( (recSamples,
                                      len( recSamples ),
                                      0,
                                      trc.InitialXOffset,
                                      trc.InitialXTimeSeconds,
                                      trc.InitialXTimeFraction,
                                      trc.XIncrement * decim,
                                      1.0, #trc.ScaleFactor if trc.ScaleFactor else 1.0,
                                      0.0 ) ) #trc.ScaleOffset if trc.ScaleOffset else 0.0 ) )
            try:
                OutputTrace( rec, out )
            except BrokenPipeError:
                return


if __name__=="__main__":
    main()

