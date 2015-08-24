#!/usr/bin/python3


from argparse import ArgumentParser
from sys import argv



class DigitizerParser( ArgumentParser ):

    def __init__( self ):
        ArgumentParser.__init__( self )

        self.add_argument( "resources",                    nargs='+',  type=str )

        self.add_argument( "--reset",                                              default=False, action='store_true' )

        self.add_argument( "--loops", "-l",                            type=int,   default=-1 )
        self.add_argument( "--records", "-r",                          type=int,   default=1 )
        self.add_argument( "--samples", "-s",                          type=int,   default=200 )

        self.add_argument( "--no-calibrate", "-nc",                                default=False, action='store_true' )
        self.add_argument( "--calibrate-fast", "-cf",                              default=False, action='store_true' )
        self.add_argument( "--calibrate-channel", "-cc",   nargs='?',  type=int,   default=0 )
        self.add_argument( "--calibrate-period", "-cp",    nargs=None, type=int )

        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--clock-internal", "-ki",                              default=False, action='store_true' )
        grps.add_argument( "--clock-external", "-ke",      nargs=None, type=float )
        self.add_argument( "--clock-ext-divider", "-ked",  nargs='?',  type=float, default=1.0 )
        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--clock-ref-internal", "-kri",                         default=False, action='store_true' )
        grps.add_argument( "--clock-ref-external", "-kre",                         default=False, action='store_true' )
        grps.add_argument( "--clock-ref-axie", "-kra",                             default=False, action='store_true' )

        self.add_argument( "--interleave", "-i",           nargs='*',  type=int )

        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--sampling-interval", "-si",   nargs=None, type=float )
        grps.add_argument( "--sampling-frequency", "-sf",  nargs=None, type=float )

        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--trigger-internal", "-ti",    nargs=None, type=int,   default=None )
        grps.add_argument( "--trigger-external", "-te",    nargs=None, type=int,   default=None )
        self.add_argument( "--trigger-level", "-tl",       nargs=None, type=float, default=None )
        self.add_argument( "--trigger-delay", "-td",       nargs=None, type=float, default=None )

        grps = self.add_mutually_exclusive_group()
        grps.add_argument( "--wait-timeout", "-wt",        nargs='?',  type=float, default=1.0 )
        grps.add_argument( "--poll-timeout", "-pt",        nargs=None, type=float, default=None )

        self.add_argument( "--read-records", "-rr",        nargs=None, type=int,   default=None )
        self.add_argument( "--read-samples", "-rs",        nargs=None, type=int,   default=None )
        self.add_argument( "--read-type", "-rt",           nargs=None, type=str,   default=None, choices=['int8', 'int16', 'real64'] )
        self.add_argument( "--read-channels", "-rc",       nargs='*',  type=int,   default=[1] )


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

    if args.interleave and len( args.interleave )<2:
        parser.error( "argument --interleave/-i: expected at least 2 arguments" )

    return args



if __name__ == "__main__":
    import doctest
    doctest.testmod()

