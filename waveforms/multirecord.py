#!/usr/bin/python3

from numpy import float64, int8, int16, int32, array
from sys import stderr
from waveforms.trace import ReadTrace, FullScale


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
    def FullScale( self ):
        return FullScale( SampleType( self.mwfm.fetch[0].dtype ) )

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
    def NbrAdcBits( self ):
        return self.mrec.NbrAdcBits

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
    def FullScale( self ):
        return self.mrec.FullScale

    @property
    def TraceType( self ):
        return self.mrec.TraceType


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
        self.TraceType = "Digitizer"
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
        mwfm = _MultiWaveform( fetch )
        if len( self.mwfms )>0 and self.mwfms[0].ActualRecords != mwfm.ActualRecords:
            raise RuntimeError( "ActualRecords do not match." )
        if len( self.mwfms )>0:
            for r in range( mwfm.ActualRecords ):
                if self.mwfms[0].ActualPoints[r] != mwfm.ActualPoints[r]:
                    raise RuntimeError( "ActualPoints do not match." )
            if self.checkXOffset:
                for r in range( mwfm.ActualRecords ):
                    if self.mwfms[0].InitialXOffset[r] != mwfm.InitialXOffset[r]:
                        raise RuntimeError( "InitialXOffset do not match. %g <> %g"%( self.mwfms[0].InitialXOffset[r], mwfm.InitialXOffset[r] ) )
                    if self.mwfms[0].InitialXTimeSeconds[r] != mwfm.InitialXTimeSeconds[r]:
                        raise RuntimeError( "InitialXTimeSeconds do not match. %g <> %g"%( self.mwfms[0].InitialXTimeSeconds[r], mwfm.InitialXTimeSeconds[r] ) )
                    if self.mwfms[0].InitialXTimeFraction[r] != mwfm.InitialXTimeFraction[r]:
                        raise RuntimeError( "InitialXTimeFraction do not match. %g <> %g"%( self.mwfms[0].InitialXTimeFraction[r], mwfm.InitialXTimeFraction[r] ) )
            if self.mwfms[0].XIncrement != mwfm.XIncrement:
                raise RuntimeError( "XIncrement do not match." )
        self.mwfms.append( mwfm )

    @property
    def XIncrement( self ):
        return self.mwfms[0].XIncrement

    @property
    def FullScale( self ):
        return FullScale( self.SampleType )



def ReadRecords( f ):
    """ Read Records from a file

    >>> from io import StringIO
    >>> trace = '''$TraceType Digitizer
    ... $SampleType Int16
    ... $ActualChannels 2
    ... $Model U5303A
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93457e-11
    ... $InitialXTimeSeconds 0.0
    ... $InitialXTimeFraction 0.002
    ... $$ScaleFactor 0 6.103515625e-05
    ... $$ScaleOffset 0 0.0
    ... $$ScaleFactor 1 3.0517578125e-05
    ... $$ScaleOffset 1 0.0
    ... -2243 -5486  
    ... 3171  -18    
    ... 8093  5394   
    ... 11667 9902   
    ... 13533 12962  
    ... 13203 13966  
    ... 10973 12850  
    ... 6947  9598   
    ... 1869  5074   
    ... -3485 -370   
    ... -8403 -5742  
    ... -11933 -10242
    ... -13571 -13118
    ... -13213 -14034
    ... -10755 -12734
    ... -6573 -9378  
    ... -1427 -4670  
    ... 4019  846    
    ... 8701  6162   
    ... 12067 10542  
    ... 13581 13250  
    ... 12979 13918  
    ... 10429 12482  
    ... 6195  8926   
    ... 1053  4258   
    ... -4333 -1202  
    ... -9011 -6542  
    ... -12349 -10818
    ... -13667 -13406
    ... -12941 -13938
    ... -10179 -12366
    ... -5757 -8770
    ... '''
    >>> f = StringIO( trace )
    >>> recs = ReadRecords( f )
    >>> rec = next( recs )
    >>> print( len( rec ), rec.ActualPoints, rec.InitialXOffset, rec.InitialXTimeSeconds, rec.InitialXTimeFraction, rec.XIncrement )
    2 32 -7.93457e-11 0.0 0.002 6.25e-10
    >>> wfm = rec[0]
    >>> print( wfm.ActualPoints, wfm.InitialXOffset, wfm.InitialXTimeSeconds, wfm.InitialXTimeFraction, wfm.XIncrement, wfm.ScaleFactor, wfm.ScaleOffset )
    32 -7.93457e-11 0.0 0.002 6.25e-10 6.103515625e-05 0.0
    >>> print( wfm.Samples )
    [ -2243   3171   8093  11667  13533  13203  10973   6947   1869  -3485
      -8403 -11933 -13571 -13213 -10755  -6573  -1427   4019   8701  12067
      13581  12979  10429   6195   1053  -4333  -9011 -12349 -13667 -12941
     -10179  -5757]
    >>> wfm = rec[1]
    >>> print( wfm.ActualPoints, wfm.InitialXOffset, wfm.InitialXTimeSeconds, wfm.InitialXTimeFraction, wfm.XIncrement, wfm.ScaleFactor, wfm.ScaleOffset )
    32 -7.93457e-11 0.0 0.002 6.25e-10 3.0517578125e-05 0.0
    >>> print( wfm.Samples )
    [ -5486    -18   5394   9902  12962  13966  12850   9598   5074   -370
      -5742 -10242 -13118 -14034 -12734  -9378  -4670    846   6162  10542
      13250  13918  12482   8926   4258  -1202  -6542 -10818 -13406 -13938
     -12366  -8770]
    >>> trace = '''$TraceType Digitizer
    ... $SampleType Int16
    ... $ActualChannels 2
    ... $Model U5303A
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93457e-11
    ... $InitialXTimeSeconds 0.0
    ... $InitialXTimeFraction 0.002
    ... -2243 -5486  
    ... 3171  -18    
    ... 8093  5394   
    ... 11667 9902   
    ... 13533 12962  
    ... 13203 13966  
    ... 10973 12850  
    ... 6947  9598   
    ...
    ... $TraceType Digitizer
    ... $SampleType Int16
    ... $ActualChannels 2
    ... $Model U5303A
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93457e-11
    ... $InitialXTimeSeconds 0.0
    ... $InitialXTimeFraction 0.002
    ... 1869  5074   
    ... -3485 -370   
    ... -8403 -5742  
    ... -11933 -10242
    ... -13571 -13118
    ... -13213 -14034
    ... -10755 -12734
    ... -6573 -9378  
    ...
    ... $TraceType Digitizer
    ... $SampleType Int16
    ... $ActualChannels 2
    ... $Model U5303A
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93457e-11
    ... $InitialXTimeSeconds 0.0
    ... $InitialXTimeFraction 0.002
    ... -1427 -4670  
    ... 4019  846    
    ... 8701  6162   
    ... 12067 10542  
    ... 13581 13250  
    ... 12979 13918  
    ... 10429 12482  
    ... 6195  8926   
    ...
    ... $TraceType Digitizer
    ... $SampleType Int16
    ... $ActualChannels 2
    ... $Model U5303A
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93457e-11
    ... $InitialXTimeSeconds 0.0
    ... $InitialXTimeFraction 0.002
    ... 1053  4258   
    ... -4333 -1202  
    ... -9011 -6542  
    ... -12349 -10818
    ... -13667 -13406
    ... -12941 -13938
    ... -10179 -12366
    ... -5757 -8770
    ... '''
    >>> f = StringIO( trace )
    >>> recs = ReadRecords( f )
    >>> rec = next( recs )
    >>> print( len( rec ), rec.ActualPoints, rec.InitialXOffset, rec.InitialXTimeSeconds, rec.InitialXTimeFraction, rec.XIncrement )
    2 8 -7.93457e-11 0.0 0.002 6.25e-10
    >>> w = rec[0]
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    8 -7.93457e-11 0.0 0.002 6.25e-10 1.0 0.0
    >>> print( w.Samples )
    [-2243  3171  8093 11667 13533 13203 10973  6947]
    >>> w = rec[1]
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    8 -7.93457e-11 0.0 0.002 6.25e-10 1.0 0.0
    >>> print( w.Samples )
    [-5486   -18  5394  9902 12962 13966 12850  9598]
    >>> rec = next( recs )
    >>> print( len( rec ), rec.ActualPoints, rec.InitialXOffset, rec.InitialXTimeSeconds, rec.InitialXTimeFraction, rec.XIncrement )
    2 8 -7.93457e-11 0.0 0.002 6.25e-10
    >>> w = rec[0]
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    8 -7.93457e-11 0.0 0.002 6.25e-10 1.0 0.0
    >>> print( w.Samples )
    [  1869  -3485  -8403 -11933 -13571 -13213 -10755  -6573]
    >>> w = rec[1]
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    8 -7.93457e-11 0.0 0.002 6.25e-10 1.0 0.0
    >>> print( w.Samples )
    [  5074   -370  -5742 -10242 -13118 -14034 -12734  -9378]
    >>> rec = next( recs )
    >>> print( len( rec ), rec.ActualPoints, rec.InitialXOffset, rec.InitialXTimeSeconds, rec.InitialXTimeFraction, rec.XIncrement )
    2 8 -7.93457e-11 0.0 0.002 6.25e-10
    >>> w = rec[0]
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    8 -7.93457e-11 0.0 0.002 6.25e-10 1.0 0.0
    >>> print( w.Samples )
    [-1427  4019  8701 12067 13581 12979 10429  6195]
    >>> w = rec[1]
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    8 -7.93457e-11 0.0 0.002 6.25e-10 1.0 0.0
    >>> print( w.Samples )
    [-4670   846  6162 10542 13250 13918 12482  8926]
    >>> rec = next( recs )
    >>> print( len( rec ), rec.ActualPoints, rec.InitialXOffset, rec.InitialXTimeSeconds, rec.InitialXTimeFraction, rec.XIncrement )
    2 8 -7.93457e-11 0.0 0.002 6.25e-10
    >>> w = rec[0]
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    8 -7.93457e-11 0.0 0.002 6.25e-10 1.0 0.0
    >>> print( w.Samples )
    [  1053  -4333  -9011 -12349 -13667 -12941 -10179  -5757]
    >>> w = rec[1]
    >>> print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    8 -7.93457e-11 0.0 0.002 6.25e-10 1.0 0.0
    >>> print( w.Samples )
    [  4258  -1202  -6542 -10818 -13406 -13938 -12366  -8770]
    """
    for trc in ReadTrace( f ):
        record = MultiRecord()
        record.SampleType = trc.SampleType
        for wfm in trc:
            if not hasattr( trc, 'InitialXTimeSeconds'): trc.InitialXTimeSeconds = 0.0
            if not hasattr( trc, 'InitialXTimeFraction'): trc.InitialXTimeFraction = 0.0
            record.append( ( wfm.Samples, len( wfm.Samples ), 1, [len( wfm.Samples )], [0], [trc.InitialXOffset], [trc.InitialXTimeSeconds], [trc.InitialXTimeFraction], trc.XIncrement, getattr( wfm, 'ScaleFactor', 1.0 ), getattr( wfm, 'ScaleOffset', 0.0 ) ) )
        yield record[0]


if __name__ == "__main__":
    import doctest
    doctest.IGNORE_EXCEPTION_DETAIL = True
    doctest.testmod()

