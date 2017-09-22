#!/usr/bin/python3


from argparse import ArgumentParser
from sys import argv



class DigitizerParser( ArgumentParser ):

    def __init__( self ):
        ArgumentParser.__init__( self )

        self.add_argument( "resources",                    nargs='+',  type=str )

        self.add_argument( "--reset",                                              default=False, action='store_true' )
        self.add_argument( "--info-cores", "-ic",                                  default=False, action='store_true' )

        self.add_argument( "--loops", "-l",                            type=int,   default=-1 )
        self.add_argument( "--records", "-r",                          type=int,   default=1 )
        self.add_argument( "--samples", "-s",                          type=int,   default=200 )
        self.add_argument( "--averages", "-a",                         type=int,   default=1 )
        self.add_argument( "--mode", "-m",                             type=str,   default='DGT', choices=['DGT', 'DDC', 'AVG'] )

        self.add_argument( "--streaming-continuous", "-csr",                       default=False, action='store_true' )
        self.add_argument( "--streaming-triggered", "-cst",                        default=False, action='store_true' )

        self.add_argument( "--no-calibrate", "-nc",                                default=False, action='store_true' )
        self.add_argument( "--calibrate-fast", "-cf",                              default=False, action='store_true' )
        self.add_argument( "--calibrate-channel", "-cc",   nargs='?',  type=int,   default=0 )
        self.add_argument( "--calibrate-period", "-cp",    nargs=None, type=int )
        self.add_argument( "--cal-offset-target", "-cot",              type=float )

        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--clock-internal", "-ki",                              default=False, action='store_true' )
        grps.add_argument( "--clock-external", "-ke",      nargs=None, type=float )
        self.add_argument( "--clock-ext-divider", "-ked",  nargs='?',  type=float, default=1.0 )
        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--clock-ref-internal", "-kri",                         default=False, action='store_true' )
        grps.add_argument( "--clock-ref-external", "-kre",                         default=False, action='store_true' )
        grps.add_argument( "--clock-ref-axie", "-kra",                             default=False, action='store_true' )
        grps.add_argument( "--clock-ref-pxi", "-krp",                              default=False, action='store_true' )

        self.add_argument( "--interleave", "-i",           nargs='*',  type=int )

        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--sampling-interval", "-si",   nargs=None, type=float )
        grps.add_argument( "--sampling-frequency", "-sf",  nargs=None, type=float )

        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--trigger-internal", "-ti",    nargs=None, type=int,   default=1 )
        grps.add_argument( "--trigger-external", "-te",    nargs=None, type=int,   default=None )
        grps.add_argument( "--trigger-name", "-tn",        nargs=None, type=str )
        self.add_argument( "--trigger-level", "-tl",       nargs=None, type=float, default=None )
        self.add_argument( "--trigger-delay", "-td",       nargs=None, type=float, default=None )
        self.add_argument( "--trigger-slope", "-ts",                   type=str,   default=None, choices=["positive", "p", "negative", "n"] )
        self.add_argument( "--immediate-trigger", "-it",                           default=False, action='store_true' )
        self.add_argument( "--trigger-output-enabled", "-toe",                     default=False, action='store_true' )
        self.add_argument( "--trigger-output-source", "-tos",          type=str,   default=None )
        self.add_argument( "--trigger-output-offset", "-too", nargs=None, type=float, default=None )

        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--wait-timeout", "-wt",        nargs='?',  type=float, default=1.0 )
        grps.add_argument( "--poll-timeout", "-pt",        nargs=None, type=float, default=None )
        self.add_argument( "--wait-failure", "-wf",                                default=False, action='store_true' )

        self.add_argument( "--read-records", "-rr",        nargs=None, type=int,   default=None )
        self.add_argument( "--read-samples", "-rs",        nargs=None, type=int,   default=None )
        self.add_argument( "--read-type", "-rt",           nargs=None, type=str,   default=None, choices=['int8', 'int16', 'int32', 'real64'] )
        self.add_argument( "--read-channels", "-rc",       nargs='*',  type=int,   default=[1] )

        self.add_argument( "--output-1st-record", "-o1r",  nargs=None, type=int,   default=None )
        self.add_argument( "--output-records", "-or",      nargs=None, type=int,   default=None )
        self.add_argument( "--output-samples", "-os",      nargs=None, type=int,   default=None )

        self.add_argument( "--vertical-range", "-vr",                  type=float, default=None )
        self.add_argument( "--vertical-offset", "-vo",                 type=float, default=None )

        self.add_argument( "--calibration-signal", "-cs",              type=str  , default=None, choices=['Gnd', 'T0', 'Cal100', '100MHz', 'InterleavingDelay'] )

        self.add_argument( "--tsr", "-tsr",                                        default=False, action='store_true' )

        self.add_argument( "--control-io1", "-io1",                    type=str,   default=None )
        self.add_argument( "--control-io2", "-io2",                    type=str,   default=None )

        self.add_argument( "--ddc-decimation-numerator", "-ddn",       type=int )
        self.add_argument( "--ddc-decimation-denominator", "-ddd",     type=int )
        self.add_argument( "--ddc-local-oscillator-frequency", "-ddf", type=float, default=0.0 )
        self.add_argument( "--ddc-sample-view", "-dsv",                type=str,   default="REAL", choices=['REAL', 'IMAGINARY', 'COMPLEX', 'PHASE'] )

        self.add_argument( "--no-check-x-offset", "-ncxo",                         default=False, action='store_true' )


    def parse_args( self, *largs, **kwargs ):
        args = ArgumentParser.parse_args( self, *largs, **kwargs )
        args.initial_read_records = args.read_records if hasattr( args, "read_records" ) else None
        args.initial_read_samples = args.read_samples if hasattr( args, "read_samples" ) else None
        return args


def DigitizerArgs( parser=None ):
    if not parser:
        parser = DigitizerParser()
    args = parser.parse_args()

    if args.sampling_interval!=None:
        args.sampling_frequency = 1.0/args.sampling_interval
    elif args.sampling_frequency!=None:
        args.sampling_interval = 1.0/args.sampling_frequency

    if not args.read_records:
        args.read_records = args.records
    if not args.read_samples:
        args.read_samples = args.samples

    if args.trigger_name:
        args.trigger_internal = None
        args.trigger_external = None

    if args.interleave and len( args.interleave )<2:
        parser.error( "argument --interleave/-i: expected at least 2 arguments" )

    return args


def RefreshArgs( args ):
    if not args.initial_read_records:
        args.read_records = args.records
    if not args.initial_read_samples:
        args.read_samples = args.samples


if __name__ == "__main__":
    import doctest
    doctest.testmod()

