#!/usr/bin/python3

from numpy import float64, int8, int16, int32, array
from sys import stderr
from waveforms.trace import ReadTrace


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
            raise RuntimeError( "Bad number of ActualPoints"+str( fetch[2] )+" vs. "+str( len( fetch[3] ) )+"." )
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
        self.ActualRecords        = self.fetch[2]
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
        if index<0 or index>=mwfm.ActualRecords:
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
    def SampleType( self ):
        return SampleType( self.mwfm.fetch[0].dtype )

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
        return self.mrec.mwfms[index][self.index] if self.mrec.mwfms[index].__class__.__name__=="AqMD3WaveformCollection" else _SubWaveform( self.mrec.mwfms[index], self.index )

    @property
    def NbrAdcBits( self ):
        return self.mrec.NbrAdcBits

    @property
    def ActualPoints( self ):
        try:
            return self.mrec.mwfms[0][self.index].ActualPoints
        except:
            return self.mrec.mwfms[0][self.index].ActualSamples

    @property
    def InitialXOffset( self ):
        return self.mrec.mwfms[0][self.index].InitialXOffset

    @property
    def InitialXTimeSeconds( self ):
        return self.mrec.mwfms[0][self.index].InitialXTimeSeconds

    @property
    def InitialXTimeFraction( self ):
        return self.mrec.mwfms[0][self.index].InitialXTimeFraction

    @property
    def XIncrement( self ):
        return self.mrec.mwfms[0][self.index].XIncrement

    @property
    def SampleType( self ):
        return self.mrec.SampleType


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
    IndexError: index 12 is out of bounds for axis 0 with size 12
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

    def __init__( self, fetch=None, checkXOffset=True, nbrAdcBits=None ):
        self.NbrAdcBits = nbrAdcBits
        self.mwfms = []
        self.checkXOffset = checkXOffset
        if fetch:
            if isinstance( fetch, list ) and isinstance( fetch[0], list ):
                for f in fetch:
                    self.append( f )
            else:
                self.append( fetch )

    def __len__( self ):
        return self.ActualRecords

    def __getitem__( self, index ):
        return _SubRecord( self, index )

    @property
    def ActualRecords( self ):
        return self.mwfms[0].ActualRecords

    def append( self, fetch ):
        mwfm = fetch if fetch.__class__.__name__=="AqMD3WaveformCollection" else _MultiWaveform( fetch )
        if len( self.mwfms )>0 and self.mwfms[0].ActualRecords != mwfm.ActualRecords:
            raise RuntimeError( "ActualRecords do not match." )
        if len( self.mwfms )>0:
            for r, wfm in enumerate( mwfm ):
                if len( self.mwfms[0][r].Samples ) != len( wfm.Samples ):
                    raise RuntimeError( "ActualPoints do not match." )
            if self.checkXOffset:
                for r in range( mwfm.ActualRecords ):
                    if self.mwfms[0][r].InitialXOffset != mwfm[r].InitialXOffset:
                        raise RuntimeError( "InitialXOffset do not match. %g <> %g"%( self.mwfms[0][r].InitialXOffset, mwfm[r].InitialXOffset ) )
                    if self.mwfms[0][r].InitialXTimeSeconds != mwfm[r].InitialXTimeSeconds:
                        raise RuntimeError( "InitialXTimeSeconds do not match. %g <> %g"%( self.mwfms[0][r].InitialXTimeSeconds, mwfm[r].InitialXTimeSeconds ) )
                    if self.mwfms[0][r].InitialXTimeFraction != mwfm[r].InitialXTimeFraction:
                        raise RuntimeError( "InitialXTimeFraction do not match. %g <> %g"%( self.mwfms[0][r].InitialXTimeFraction, mwfm[r].InitialXTimeFraction ) )
            if self.mwfms[0][0].XIncrement != mwfm[0].XIncrement:
                raise RuntimeError( "XIncrement do not match." )
        self.mwfms.append( mwfm )

    @property
    def XIncrement( self ):
        return self.mwfms[0].XIncrement



if __name__ == "__main__":
    import doctest
    doctest.IGNORE_EXCEPTION_DETAIL = True
    doctest.testmod()

