#!/usr/bin/python3


from subprocess import check_output, Popen, PIPE
from sys import exit, stdout, stderr, argv
from argparse import ArgumentParser


parser = ArgumentParser( "SFP" )
parser.add_argument( "--synchronize", "-s", action='store_true', default=None )
parser.add_argument( "inputs", type=str, nargs="*" )
args = parser.parse_args()

rsrc = args.inputs
if not args.synchronize:
    if len( args.inputs )>1:
        rsrc = args.inputs[0]

cmd = ['digitizer/chooser.py']
if args.synchronize:
    cmd.append( '--multiple' )
cmd.extend( rsrc )
rsrc = check_output( cmd )
rsrc = rsrc.decode( "ASCII" ).strip()
rsrcList = rsrc.split()

if rsrc=="":
    exit( 0 )

runcmd = ['digitizer/runnermd2.py', '-rt', 'int16', rsrc]
if args.synchronize:
    runcmd = ['digitizer/runsyncmd2.py', '-kra', '-ll', '10000']
    runcmd.extend( rsrcList )

pctl = Popen( ['digitizer/runcontrol.py'], stdout=PIPE )
prun = Popen( runcmd, stdin=pctl.stdout, stdout=PIPE )
pliv = Popen( ['viewer/live.py', '--live'], stdin=prun.stdout )
#pliv = Popen( ['tee', "sfp.trc"], stdin=prun.stdout )

pliv.wait()
pctl.kill()

