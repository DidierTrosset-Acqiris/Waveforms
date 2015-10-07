#!/usr/bin/python3

from numpy import int16, int32, array, zeros, resize
from sys import stderr


""" The waveforms package provides classes to help dealing with records and waveforms acquired
    from IVI Digitizer instruments.

    The main classes are Record and MultiRecord, that are used to store and access data
    retreived by using the IVI Digitizer Fetch functions.

    Record holds an array of waveforms that have been acquired at the same time. It means
    the waveforms must share the same type of samples, number of points, sampling period,
    and trigger information. Record should be used as an array of waveforms.

    MultiRecord holds several records. It is purpose made to gather the waveforms retreived
    using the FetchMultiRecordWaveform functions of IVI Digitizer. MultiRecord should be used
    as an array of records, which in turn should be used as an array of waveforms.
    
    The waveform objects accessed through the Record and MultiRecord classes all provide the
    usual properties of IVI Digitizer waveforms: Samples, ActualPoints, InitialXOffset,
    InitialXTimeSeconds, InitialXTimeFraction, XIncrement, ScaleFactor, and ScaleOffset.
    
"""

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
    IndexError: index out of bounds
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
    """
    def __init__( self, fetch=None ):
        self.wfms = []
        if fetch:
            self.append( fetch )

    def __len__( self ):
        return len( self.wfms )

    def __getitem__( self, index ):
        return self.wfms[index]

    def __iter__( self ):
        return iter( self.wfms )

    def append( self, fetch ):
        wfm = _Waveform( fetch )
        if len( self.wfms )>0 and self.wfms[0].ActualPoints != wfm.ActualPoints:
            raise RuntimeError( "ActualPoints do not match." )
        if len( self.wfms )>0 and self.wfms[0].InitialXOffset != wfm.InitialXOffset:
            raise RuntimeError( "InitialXOffset do not match. "+str( self.wfms[0].InitialXOffset )+" "+str( wfm.InitialXOffset ) )
        if len( self.wfms )>0 and self.wfms[0].InitialXTimeSeconds != wfm.InitialXTimeSeconds:
            raise RuntimeError( "InitialXTimeSeconds do not match." )
        if len( self.wfms )>0 and self.wfms[0].InitialXTimeFraction != wfm.InitialXTimeFraction:
            raise RuntimeError( "InitialXTimeFraction do not match." )
        if len( self.wfms )>0 and self.wfms[0].XIncrement != wfm.XIncrement:
            raise RuntimeError( "XIncrement do not match." )
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
    def FullScale( self ):
        return 2**16 if self.wfms[0][0].dtype==int16 else 2**8


class _MultiWaveform():
    """ Private class that directly gather the values retreived by the FetchMultiRecordWaveform functions.

    >>> samples = array( [ -2243,   3171,   8093,  11667,  13533,  13203,  10973,   6947, \
                            1869,  -3485,  -8403, -11933, -13571, -13213, -10755,  -6573, \
                           -1427,   4019,   8701,  12067,  13581,  12979,  10429,   6195, \
                            1053,  -4333,  -9011, -12349, -13667, -12941, -10179,  -5757], dtype=int16 )
    >>> w = _MultiWaveform( ( samples, 32, 2, [12, 12], [0, 16], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, 2.0/32768, 0.0 ) )
    >>> print( w.ActualPoints )
    [12, 12]
    >>> print( w.InitialXOffset )
    [-7e-11, -3e-11]
    >>> print( w.InitialXTimeSeconds )
    [0.0, 0.0]
    >>> print( w.InitialXTimeFraction )
    [0.002, 0.003]
    >>> print( w.XIncrement )
    6.25e-10
    >>> print( w.ScaleFactor )
    6.103515625e-05
    >>> print( w.ScaleOffset )
    0.0
    >>> w = _MultiWaveform( ( samples, 32, 2, [12, 12], [0, 16], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10 ) )
    >>> print( w.ScaleFactor )
    1.0
    >>> print( w.ScaleOffset )
    0.0

    """
    def __init__( self, fetch ):
        if fetch[2] != len( fetch[3] ):
            raise RuntimeError( "Bad number of ActualPoints." )
        if fetch[2] != len( fetch[4] ):
            raise RuntimeError( "Bad number of FirstValidPoint." )
        if fetch[2] != len( fetch[5] ):
            raise RuntimeError( "Bad number of InitialXOffset." )
        if fetch[2] != len( fetch[6] ):
            raise RuntimeError( "Bad number of InitialXTimeSeconds." )
        if fetch[2] != len( fetch[7] ):
            raise RuntimeError( "Bad number of InitialXTimeFraction." )
        self.fetch = fetch
        self.SampleArray          = self.fetch[0]
        self.ActualWaveformSize   = self.fetch[1]
        self.NumRecords           = self.fetch[2]
        self.ActualPoints         = self.fetch[3]
        self.FirstValidPoint      = self.fetch[4]
        self.InitialXOffset       = self.fetch[5]
        self.InitialXTimeSeconds  = self.fetch[6]
        self.InitialXTimeFraction = self.fetch[7]
        self.XIncrement           = self.fetch[8]
        # Special case for FetchMultiRecordWaveformViReal64 that do not return scale parameters.
        try:
            self.ScaleFactor      = self.fetch[9]
            self.ScaleOffset      = self.fetch[10]
        except (IndexError): 
            self.ScaleFactor      = 1.0
            self.ScaleOffset      = 0.0


class _SubWaveform:
    def __init__( self, mwfm, index ):
        if index<0 or index>=mwfm.NumRecords:
            raise IndexError( "index out of bounds" )
        self.mwfm = mwfm
        self.index = index

    @property
    def ActualPoints( self ):
        return self.mwfm.ActualPoints[self.index]

    @property
    def InitialXOffset( self ):
        return self.mwfm.InitialXOffset[self.index]

    @property
    def InitialXTimeSeconds( self ):
        return self.mwfm.InitialXTimeSeconds[self.index]

    @property
    def InitialXTimeFraction( self ):
        return self.mwfm.InitialXTimeFraction[self.index]

    @property
    def XIncrement( self ):
        return self.mwfm.XIncrement

    @property
    def ScaleFactor( self ):
        return self.mwfm.ScaleFactor

    @property
    def ScaleOffset( self ):
        return self.mwfm.ScaleOffset

    def __len__( self ):
        return self.ActualPoints

    def __getitem__( self, index ):
        return self.Samples[index]

    def __iter__( self ):
        return iter( self.Samples )

    @property
    def Samples( self ):
        first = self.mwfm.FirstValidPoint[self.index]
        actual = self.mwfm.ActualPoints[self.index]
        return self.mwfm.SampleArray[first:first+actual]


class _SubRecord:
    def __init__( self, mrec, index ):
        if index<0 or index>=len( mrec ):
            raise IndexError( "index out of bounds" )
        self.mrec = mrec
        self.index = index

    def __len__( self ):
        return len( self.mrec.mwfms )

    def __getitem__( self, index ):
        return _SubWaveform( self.mrec.mwfms[index], self.index )

    @property
    def ActualPoints( self ):
        return self.mrec.mwfms[0].ActualPoints[self.index]

    @property
    def InitialXOffset( self ):
        return self.mrec.mwfms[0].InitialXOffset[self.index]

    @property
    def InitialXTimeSeconds( self ):
        return self.mrec.mwfms[0].InitialXTimeSeconds[self.index]

    @property
    def InitialXTimeFraction( self ):
        return self.mrec.mwfms[0].InitialXTimeFraction[self.index]

    @property
    def XIncrement( self ):
        return self.mrec.mwfms[0].XIncrement

    @property
    def ScaleFactor( self ):
        return self.mrec.mwfms[0].ScaleFactor

    @property
    def ScaleOffset( self ):
        return self.mrec.mwfms[0].ScaleOffset


class MultiRecord():
    """
    >>> samples = array( [ -2243,   3171,   8093,  11667,  13533,  13203,  10973,   6947, \
                            1869,  -3485,  -8403, -11933, -13571, -13213, -10755,  -6573, \
                           -1427,   4019,   8701,  12067,  13581,  12979,  10429,   6195, \
                            1053,  -4333,  -9011, -12349, -13667, -12941, -10179,  -5757], dtype=int16 )
    >>> mr = MultiRecord( ( samples, 32, 2, [12, 12], [0, 16], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, 2.0/32768, 0.0 ) )
    >>> len( mr )
    2
    >>> r0 = mr[0]
    >>> r1 = mr[1]
    >>> r2 = mr[2]
    Traceback (most recent call last):
    ...
    IndexError: index out of bounds
    >>> len( r0 )
    1
    >>> len( r1 )
    1
    >>> print( r0[0][0] )
    -2243
    >>> print( r0[0][1] )
    3171
    >>> print( r0[0][12] )
    Traceback (most recent call last):
    ...
    IndexError: index out of bounds
    >>> print( r1[0][0] )
    -1427
    >>> print( r1[0][1] )
    4019
    >>> r0.InitialXOffset
    -7e-11
    >>> r1.InitialXOffset
    -3e-11
    >>> print( r0[0].Samples )
    [ -2243   3171   8093  11667  13533  13203  10973   6947   1869  -3485
      -8403 -11933]
    >>> print( r1[0].Samples )
    [ -1427   4019   8701  12067  13581  12979  10429   6195   1053  -4333
      -9011 -12349]

    """

    def __init__( self, fetch=None ):
        self.mwfms = []
        if fetch:
            if isinstance( fetch, list ):
                for f in fetch:
                    self.append( f )
            else:
                self.append( fetch )

    def __len__( self ):
        return self.NumRecords

    def __getitem__( self, index ):
        return _SubRecord( self, index )

    @property
    def NumRecords( self ):
        return self.mwfms[0].NumRecords

    def append( self, fetch ):
        mwfm = _MultiWaveform( fetch )
        if len( self.mwfms )>0 and self.mwfms[0].NumRecords != mwfm.NumRecords:
            raise RuntimeError( "NumRecords do not match." )
        if len( self.mwfms )>0:
            for r in range( mwfm.NumRecords ):
                if self.mwfms[0].ActualPoints[r] != mwfm.ActualPoints[r]:
                    raise RuntimeError( "ActualPoints do not match." )
                if self.mwfms[0].InitialXOffset[r] != mwfm.InitialXOffset[r]:
                    raise RuntimeError( "InitialXOffset do not match." )
                if self.mwfms[0].InitialXTimeSeconds[r] != mwfm.InitialXTimeSeconds[r]:
                    raise RuntimeError( "InitialXTimeSeconds do not match." )
                if self.mwfms[0].InitialXTimeFraction[r] != mwfm.InitialXTimeFraction[r]:
                    raise RuntimeError( "InitialXTimeFraction do not match." )
            if self.mwfms[0].XIncrement != mwfm.XIncrement:
                raise RuntimeError( "XIncrement do not match." )
        self.mwfms.append( mwfm )

    @property
    def XIncrement( self ):
        return self.mwfms[0].XIncrement



if __name__ == "__main__":
    import doctest
    doctest.testmod()

