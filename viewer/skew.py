#!/usr/bin/python3

from sys import stdin, stderr, argv, exit
from numpy import array, float64, mean, std
from matplotlib.pyplot import xkcd, plot, ylabel, show, ylim, xticks, grid
from matplotlib.pyplot import xlim, xticks


DIFFNONE=-1
DIFFZERO=0
DIFFMEAN=8
DIFFDIV2=9

def _Style( c ):
    C = ['#e90029', '#009fe3', '#8b3c8f', '#019642', '#ed5e1a', '#9c9c9c', '#fdc206', '#000000']
    #     Kt Red     Kt Blue    Kt Purple  Kt Green   Kt Orange  Kt MedGray Kt Yellow  Kt Black
    return { 'color':C[ c%len(C) ], 'marker':'x', 'linestyle':'-' }


from argparse import ArgumentParser

parser = ArgumentParser()
grpSignal = parser.add_mutually_exclusive_group()
grpSignal.add_argument( "--signal-period", "-sp", nargs=None, type=float )
grpSignal.add_argument( "--signal-frequency", "-sf", nargs=None, type=float )
grpDiff = parser.add_mutually_exclusive_group()
grpDiff.add_argument( "--diff-with-zero",  "-d0", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-one",   "-d1", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-two",   "-d2", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-three", "-d3", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-four",  "-d4", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-five",  "-d5", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-six",   "-d6", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-seven", "-d7", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-mean",  "-dm", default=False, action='store_true' )
grpDiff.add_argument( "--diff-with-median", "-dd", default=False, action='store_true' )
parser.add_argument( "--picoseconds", "-ps", default=False, action='store_true' )
parser.add_argument( "--vertical-range", "-vr", type=float )

args = parser.parse_args()

if   args.diff_with_zero:   showDiff = DIFFZERO
elif args.diff_with_one:    showDiff = DIFFZERO+1
elif args.diff_with_two:    showDiff = DIFFZERO+2
elif args.diff_with_three:  showDiff = DIFFZERO+3
elif args.diff_with_four:   showDiff = DIFFZERO+4
elif args.diff_with_five:   showDiff = DIFFZERO+5
elif args.diff_with_six:    showDiff = DIFFZERO+6
elif args.diff_with_seven:  showDiff = DIFFZERO+7
elif args.diff_with_mean:   showDiff = DIFFMEAN
elif args.diff_with_median: showDiff = DIFFDIV2
else:                       showDiff = DIFFNONE

unit = 1.0
if args.picoseconds:
    unit = 1e12

if   args.signal_period:    signalPeriod = unit*args.signal_period
elif args.signal_frequency: signalPeriod = unit/args.signal_frequency
else:                       signalPeriod = None
halfSignalPeriod = signalPeriod/2.0 if signalPeriod else None

#xkcd()

delays = None
for line in stdin:
    line = line.strip()
    if len(line)<1 or line[1]=='#':
        continue
    dd = list( map( float, line.split() ) )
    # First check if values of a same line are not too far apart
    if signalPeriod:
        refDelay = dd[0]
        for i, delay in enumerate( dd[1:] ):
            diff = delay-refDelay
            diff = ( ( diff+halfSignalPeriod )% signalPeriod )-halfSignalPeriod
            dd[i+1] = refDelay+diff
    # Calculate the mean/avg according to choice
    if showDiff>=DIFFZERO and showDiff<DIFFMEAN:
        dm = dd[showDiff-DIFFZERO]
    elif showDiff==DIFFMEAN:
        dm = mean( dd )
    elif showDiff==DIFFDIV2:
        dm = ( max( dd )+min( dd ) )/2
    else:
        dm = 0.0
    # Calculate delays
    if not delays:
        delays = [[] for _ in dd]
    for i, d in enumerate( dd ):
        diff = d-dm
        delays[i].append( diff )

if not delays:
    print( "ERROR: No data.", file=stderr )
    exit( 1 )

print( " ".join( [ str( mean(d) ) for d in delays ] ) )
print( " ".join( [ str( std(d) ) for d in delays ] ) )

minval =  10e10
maxval = -10e10
for c, d in enumerate( delays ):
    minval = min( minval, *d )
    maxval = max( maxval, *d )
    plot( d, **_Style( c ) )
meanval = 0#( minval+maxval )/2
if args.vertical_range:
    vr = args.vertical_range
    ylim( -vr/2, vr/2 )
#ylim( meanval-75.0e-12, meanval+75.0e-12 )
#xlim( 0, 12500 )
#xticks( range( 0, 12501, 2500 ) )
grid( True )
show()

