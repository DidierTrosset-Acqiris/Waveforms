#!/usr/bin/python3

from sys import stdin, stdout
from waveforms.trace import ReadTrace
from numpy import ones, float32
from matplotlib import pyplot
from math import fmod
from argparse import ArgumentParser

# Takes as input a .trc file, and output a .skew file.


def main():
    parser = ArgumentParser()
    parser.add_argument( "--width",   "-w",  type=int,   default=256   )
    parser.add_argument( "--height",  "-k",  type=int,   default=256   )
    parser.add_argument( "--scale",   "-s",  type=int,   default=65536 )
    parser.add_argument( "--length",  "-l",  type=float, default=1e-9  )
    parser.add_argument( "--offset",  "-o",  type=float, default=0.0   )
    parser.add_argument( "--zero-delay", "-zd", action='store_true', help="Warning: Use only with trigger delay multiple of sampling interval." )
    parser.add_argument( "files", nargs='*', type=str )

    args = parser.parse_args()


    # Take usual colors, and translate them to tuple of three floats.
    C = ['#e90029', '#009fe3', '#8b3c8f', '#019642', '#ed5e1a', '#9c9c9c', '#fdc206', '#000000']
    #     Kt Red     Kt Blue    Kt Purple   Kt Green  Kt Orange  Kt MedGray Kt Yellow  Kt Black
    CC = [( int( c[1:3], 16 )/255, int( c[3:5], 16 )/255, int( c[5:7], 16 )/255 ) for c in C]

    height = args.height
    width = args.width

    scale = args.scale
    length = args.length
    offset = args.offset

    bmp = ones( (height, width, 3), dtype=float32 )

    r_enumerate= lambda iterable: zip( reversed( range( len(iterable) ) ), reversed( iterable ) )

    if len( args.files )==0:
        traces = [stdin]
    else:
        traces = [open( name, 'rt' ) for name in args.files]

    c0 = 0
    for trace in traces:
        cr0 = 0
        for record in ReadTrace( trace ):
            InitialXOffset = fmod( record.InitialXOffset, record.XIncrement ) if args.zero_delay else record.InitialXOffset
            cr0 = len(record)
            for c, waveform in r_enumerate( record ):
                for i in range( len(waveform) ):
                    time = InitialXOffset+i*record.XIncrement
                    sample = waveform[i]
                    x = int( ( -offset+time )/length*width )
                    y = height//2-int( sample/scale*height )
                    if x>width:
                        break
                    if 0<=x<width and 0<=y<height:
                        bmp[y, x] = CC[c+c0]
        c0 = c0+cr0

    pyplot.xlabel( "Time (ns)" )
    pyplot.xticks( [0, width-1], ["%g"%(offset*1e9), "%g"%(( offset+length )*1e9)] )
    pyplot.yticks( [0, height//2-1, height-1], [str(scale//2-1), "0", str(-scale//2)] )
    pyplot.imshow( bmp, interpolation='hanning' )
    pyplot.show()


if __name__=="__main__":
    main()

