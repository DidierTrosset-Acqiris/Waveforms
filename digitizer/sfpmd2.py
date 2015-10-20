#!/usr/bin/python3


from subprocess import check_output, Popen, PIPE
from sys import exit, stdout, stderr


rsrc = check_output( 'digitizer/chooser.py' )
rsrc = rsrc.decode( "ASCII" ).strip()

if rsrc=="":
    exit( 0 )

pctl = Popen( ['digitizer/runcontrol.py'], stdout=PIPE )
prun = Popen( ['digitizer/runnermd2.py', '-rt', 'int16', rsrc], stdin=pctl.stdout, stdout=PIPE )
pliv = Popen( ['viewer/live.py'], stdin=prun.stdout )
#pliv = Popen( ['tee', "sfp.trc"], stdin=prun.stdout )

pliv.wait()
pctl.kill()

