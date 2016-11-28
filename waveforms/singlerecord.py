#!/usr/bin/python3

from numpy import int16, int32, float64, array, zeros, resize, fromfunction, sqrt, arctan2
from sys import stderr


class _Waveform:
    """ Private class that directly gather the values retreived by the FetchWaveform functions.

    >>> samples = array( [ -2243,   3171,   8093,  11667,  13533,  13203,  10973,   6947, \
                            1869,  -3485,  -8403, -11933, -13571, -13213, -10755,  -6573, \
                           -1427,   4019,   8701,  12067,  13581,  12979,  10429,   6195, \
                            1053,  -4333,  -9011, -12349, -13667, -12941, -10179,  -5757], dtype=int16 )
    >>> fetch = ( samples, 32, 0, -7e-11, 0.0, 2e-3, 6.25e-10, 2.0/32768, 0.0 )
    >>> w = _Waveform( fetch )
    >>> assert( len( w.Samples )==w.ActualPoints )
    >>> print( w.Samples )
    [ -2243   3171   8093  11667  13533  13203  10973   6947   1869  -3485
      -8403 -11933 -13571 -13213 -10755  -6573  -1427   4019   8701  12067
      13581  12979  10429   6195   1053  -4333  -9011 -12349 -13667 -12941
     -10179  -5757]
    >>> print( w[0] )
    -2243
    >>> print( w[1] )
    3171
    >>> print( w[32] )
    Traceback (most recent call last):
        ...
    IndexError: index 32 is out of bounds for axis 0 with size 32
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    32 -7e-11 0.0 0.002 6.25e-10 6.103515625e-05 0.0
    >>> fetch = ( samples, 32, 0, -7e-11, 0.0, 2e-3, 6.25e-10 )
    >>> w = _Waveform( fetch )
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    32 -7e-11 0.0 0.002 6.25e-10 1.0 0.0

    """
    def __init__( self, fetch ):
        self.fetch = fetch
        self.SampleArray          = self.fetch[0]
        self.ActualPoints         = self.fetch[1]
        self.FirstValidPoint      = self.fetch[2]
        self.InitialXOffset       = self.fetch[3]
        self.InitialXTimeSeconds  = self.fetch[4]
        self.InitialXTimeFraction = self.fetch[5]
        self.XIncrement           = self.fetch[6]
        # Special case for FetchWaveformViReal64 that do not return scale parameters.
        try:
            self.ScaleFactor      = self.fetch[7]
            self.ScaleOffset      = self.fetch[8]
        except (IndexError): 
            self.ScaleFactor      = 1.0
            self.ScaleOffset      = 0.0

    def __len__( self ):
        return self.ActualPoints

    def __getitem__( self, index ):
        return self.Samples[index]

    def __iter__( self ):
        return iter( self.Samples )

    @property
    def Samples( self ):
        first = self.FirstValidPoint
        actual = self.ActualPoints
        return self.SampleArray[first:first+actual]


class Record():
    """
    >>> samples = array( [ -2243,   3171,   8093,  11667,  13533,  13203,  10973,   6947, \
                            1869,  -3485,  -8403, -11933, -13571, -13213, -10755,  -6573, \
                           -1427,   4019,   8701,  12067,  13581,  12979,  10429,   6195, \
                            1053,  -4333,  -9011, -12349, -13667, -12941, -10179,  -5757], dtype=int16 )
    >>> fetch = ( samples, 32, 0, -7e-11, 0.0, 2e-3, 6.25e-10, 2.0/32768, 0.0 )
    >>> r = Record( fetch )
    >>> len( r )
    1
    >>> print( r.ActualPoints, r.InitialXOffset, r.InitialXTimeSeconds, r.InitialXTimeFraction, r.XIncrement )
    32 -7e-11 0.0 0.002 6.25e-10
    >>> r = Record()
    >>> r.append( fetch )
    >>> r.append( fetch )
    >>> len( r )
    2
    >>> r.append( ( samples, 31, 0, -7e-11, 0.0, 2e-3, 6.25e-10, 1.0, 0.0 ) )
    Traceback (most recent call last):
    ...
    RuntimeError: ActualPoints do not match.
    >>> r.append( ( samples, 32, 0, -3e-11, 0.0, 2e-3, 6.25e-10, 1.0, 0.0 ) )
    Traceback (most recent call last):
    ...
    RuntimeError: InitialXOffset do not match. -7e-11 -3e-11
    >>> r.append( ( samples, 32, 0, -3e-11, 0.0, 2e-3, 6.25e-10, 1.0, 0.0 ), checkXOffset=False )
    >>> r.append( ( samples, 32, 0, -7e-11, 1.0, 2e-3, 6.25e-10, 1.0, 0.0 ) )
    Traceback (most recent call last):
    ...
    RuntimeError: InitialXTimeSeconds do not match.
    >>> r.append( ( samples, 32, 0, -7e-11, 0.0, 3e-3, 6.25e-10, 1.0, 0.0 ) )
    Traceback (most recent call last):
    ...
    RuntimeError: InitialXTimeFraction do not match.
    >>> r.append( ( samples, 32, 0, -7e-11, 0.0, 2e-3, 3.125e-10, 1.0, 0.0 ) )
    Traceback (most recent call last):
    ...
    RuntimeError: XIncrement do not match.
    >>> print( r[0].Samples )
    [ -2243   3171   8093  11667  13533  13203  10973   6947   1869  -3485
      -8403 -11933 -13571 -13213 -10755  -6573  -1427   4019   8701  12067
      13581  12979  10429   6195   1053  -4333  -9011 -12349 -13667 -12941
     -10179  -5757]
    >>> print( r.FullScale )
    65536
    >>> print( r.ScaleFactor, r.ScaleOffset )
    6.103515625e-05 0.0
    >>> # Check that Record level checkXOffset is used if defined.
    >>> r = Record( checkXOffset=False )
    >>> r.append( fetch )
    >>> r.append( ( samples, 32, 0, -3e-11, 0.0, 2e-3, 6.25e-10, 1.0, 0.0 ), checkXOffset=True )
    Traceback (most recent call last):
    ...
    RuntimeError: InitialXOffset do not match. -7e-11 -3e-11
    >>> r.append( ( samples, 32, 0, -3e-11, 0.0, 2e-3, 6.25e-10, 1.0, 0.0 ) )
    >>> # Check with float values
    >>> samples = array( [ -0.2, -0.1,  0.0,  0.1,  0.2,  0.3,  0.4,  0.3, \
                            0.2,  0.1,  0.0, -0.1, -0.2, -0.3, -0.4, -0.3, \
                           -0.2, -0.1,  0.0,  0.1,  0.2,  0.3,  0.4,  0.3, \
                            0.2,  0.1,  0.0, -0.1, -0.2, -0.3, -0.4, -0.3 ], dtype=float64 )
    >>> fetch = ( samples, 30, 1, -7e-11, 0.0, 2e-3, 6.25e-10 )
    >>> r = Record( fetch, FullScale=1.0 )
    >>> len( r )
    1
    >>> print( r.ActualPoints, r.InitialXOffset, r.InitialXTimeSeconds, r.InitialXTimeFraction, r.XIncrement )
    30 -7e-11 0.0 0.002 6.25e-10
    >>> print( r.FullScale )
    1.0
    >>> print( r.ScaleFactor, r.ScaleOffset )
    1.0 0.0
    """
    def __init__( self, fetch=None, checkXOffset=True, FullScale=None ):
        self.wfms = []
        self._FullScale = FullScale
        self._checkXOffset = checkXOffset
        if fetch:
            self.append( fetch, checkXOffset )

    def __len__( self ):
        return len( self.wfms )

    def __getitem__( self, index ):
        return self.wfms[index]

    def __iter__( self ):
        return iter( self.wfms )

    def append( self, fetch, checkXOffset=None ):
        wfm = _Waveform( fetch )
        if len( self.wfms )>0 and self.wfms[0].ActualPoints != wfm.ActualPoints:
            raise RuntimeError( "ActualPoints do not match." )
        if len( self.wfms )>0 and self.wfms[0].XIncrement != wfm.XIncrement:
            raise RuntimeError( "XIncrement do not match." )
        if checkXOffset is None and self._checkXOffset or checkXOffset:
            if len( self.wfms )>0 and self.wfms[0].InitialXOffset != wfm.InitialXOffset:
                raise RuntimeError( "InitialXOffset do not match. "+str( self.wfms[0].InitialXOffset )+" "+str( wfm.InitialXOffset ) )
            if len( self.wfms )>0 and self.wfms[0].InitialXTimeSeconds != wfm.InitialXTimeSeconds:
                raise RuntimeError( "InitialXTimeSeconds do not match." )
            if len( self.wfms )>0 and self.wfms[0].InitialXTimeFraction != wfm.InitialXTimeFraction:
                raise RuntimeError( "InitialXTimeFraction do not match." )
        self.wfms.append( wfm )

    @property
    def ActualPoints( self ):
        return self.wfms[0].ActualPoints

    @property
    def InitialXOffset( self ):
        return self.wfms[0].InitialXOffset

    @property
    def InitialXTimeSeconds( self ):
        return self.wfms[0].InitialXTimeSeconds

    @property
    def InitialXTimeFraction( self ):
        return self.wfms[0].InitialXTimeFraction

    @property
    def XIncrement( self ):
        return self.wfms[0].XIncrement

    @property
    def ScaleOffset( self ):
        return self.wfms[0].ScaleOffset

    @property
    def ScaleFactor( self ):
        return self.wfms[0].ScaleFactor

    @property
    def FullScale( self ):
        if self._FullScale:
            return self._FullScale
        return 2**32 if self.wfms[0].SampleArray.dtype==int32 else 2**16 if self.wfms[0].SampleArray.dtype==int16 else 2**8


if __name__ == "__main__":
    import doctest
    doctest.IGNORE_EXCEPTION_DETAIL = True
    doctest.testmod()

