#!/usr/bin/python3

from numpy import int16, int32, array, zeros, resize, fromfunction, sqrt, arctan2
from sys import stderr
from waveforms.trace import ReadTrace


class _AccMultiWaveform():
    """ Private class that directly gather the values retreived by the FetchAccumulatedWaveform functions.

    >>> samples = array( [ 12315,     -1,     97,     -1, -11877,      3,   -408,     -1, \
                           12283,     -2,     65,      0, -11957,      3,   -409,      0, \
                           12307,     -3,     89,     -1, -11887,      3,   -411,      1, \
                           12285,     -3,     79,     -1, -11957,      2,   -421,      1, \
                           12313,     -1,     39,      1, -11923,      1,   -418,      0, \
                           12289,     -3,     99,      1, -11793,      3,   -331,     -1, \
                           12287,     -3,     93,      0, -11816,      1,   -399,     -1, \
                           12293,     -3,     87,     -1, -11859,      1,   -392,      1 ], dtype=int32 )
    >>> w = _AccMultiWaveform( ( samples, 1024, 2, [12, 12], [0, 32], -7e-11, [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, 2.0/32768, 0.0, [0, 0] ) )
    >>> print( w.ActualAverages )
    1024
    >>> print( w.ActualRecords )
    2
    >>> print( w.ActualPoints )
    [12, 12]
    >>> print( w.InitialXOffset )
    -7e-11
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
    >>> print( w.Flags )
    [0, 0]
    >>> w = _AccMultiWaveform( ( samples, 32, 2, [12, 12], [0, 16], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, [0, 0] ) )
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
        if fetch[2] != len( fetch[6] ):
            raise RuntimeError( "Bad number of InitialXTimeSeconds." )
        if fetch[2] != len( fetch[7] ):
            raise RuntimeError( "Bad number of InitialXTimeFraction." )
        self.fetch = fetch
        self.SampleArray          = self.fetch[0]
        self.ActualAverages       = self.fetch[1]
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
            self.Flags            = self.fetch[11]
        except (IndexError): 
            self.ScaleFactor      = 1.0
            self.ScaleOffset      = 0.0
            self.Flags            = self.fetch[9]


class _AccSubWaveform:
    def __init__( self, mwfm, index ):
        if index<0 or index>=mwfm.ActualRecords:
            raise IndexError( "index out of bounds" )
        self.mwfm = mwfm
        self.index = index

    @property
    def ActualPoints( self ):
        return self.mwfm.ActualPoints[self.index]

    @property
    def ActualAverages( self ):
        return self.mwfm.ActualAverages

    @property
    def InitialXOffset( self ):
        return self.mwfm.InitialXOffset

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
        first = self.mwfm[self.index].FirstValidSample
        actual = self.mwfm[self.index].ActualSamples
        return self.mwfm[self.index].Samples


class _AccSubRecord:
    def __init__( self, mrec, index ):
        if index<0 or index>=len( mrec ):
            raise IndexError( "index out of bounds" )
        self.TraceType = "Accumulated"
        self.mrec = mrec
        self.index = index

    def __len__( self ):
        return len( self.mrec.mwfms )

    def __getitem__( self, index ):
        return _AccSubWaveform( self.mrec.mwfms[index], self.index )

    @property
    def NbrAdcBits( self ):
        return self.mrec.NbrAdcBits

    @property
    def ActualPoints( self ):
        return self.mrec.mwfms[0].ActualPoints[self.index]

    @property
    def ActualAverages( self ):
        return self.mrec.mwfms[0].ActualAverages

    @property
    def InitialXOffset( self ):
        return self.mrec.mwfms[0][0].InitialXOffset#[self.index]

    @property
    def InitialXTimeSeconds( self ):
        return self.mrec.mwfms[0].InitialXTimeSeconds[self.index]

    @property
    def InitialXTimeFraction( self ):
        return self.mrec.mwfms[0].InitialXTimeFraction[self.index]

    @property
    def XIncrement( self ):
        return self.mrec.mwfms[0][0].XIncrement

    @property
    def FullScale( self ):
        try: nbrAdcBits = self.mrec.NbrAdcBits+1 if self.mrec.NbrAdcBits==12 else self.mrec.NbrAdcBits
        except: nbrAdcBits = 8
        return 2**nbrAdcBits * self.ActualAverages if self.mrec.mwfms[0].SampleArray.dtype==int32 else 1


class AccMultiRecord():
    """
    >>> samples = array( [ 12315,     -1,     97,     -1, -11877,      3,   -408,     -1, \
                           12283,     -2,     65,      0, -11957,      3,   -409,      0, \
                           12313,     -3,     39,      1, -11923,      1,   -418,      0, \
                           12293,     -4,     87,     -1, -11859,      1,   -392,      1 ], dtype=int32 )
    >>> mr = AccMultiRecord( ( samples, 1024, 2, [12, 12], [0, 16], -7e-11, [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, 2.0/32768, 0.0, 0 ) )
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
    >>> len( r0[0] )
    12
    >>> len( r1[0] )
    12
    >>> print( r0[0][0] )
    12315
    >>> print( r0[0][1] )
    -1
    >>> print( r0[0][12] )
    Traceback (most recent call last):
    ...
    IndexError: index 12 is out of bounds for axis 0 with size 12
    >>> print( r1[0][0] )
    12313
    >>> print( r1[0][1] )
    -3
    >>> print( r1[0][12] )
    Traceback (most recent call last):
    ...
    IndexError: index 12 is out of bounds for axis 0 with size 12
    >>> r0.InitialXOffset
    -7e-11
    >>> r1.InitialXOffset
    -7e-11
    >>> print( r0[0].Samples )
    [ 12315     -1     97     -1 -11877      3   -408     -1  12283     -2
         65      0]
    >>> print( r1[0].Samples )
    [ 12313     -3     39      1 -11923      1   -418      0  12293     -4
         87     -1]

    """

    def __init__( self, fetch=None, checkXOffset=True, nbrAdcBits=None ):
        self.TraceType = "Accumulated"
        self.checkXOffset = checkXOffset
        self.NbrAdcBits = nbrAdcBits
        self.mwfms = []
        if fetch:
            if isinstance( fetch, list ) and isinstance( fetch[0], list ):
                for f in fetch:
                    self.append( f )
            else:
                self.append( fetch )

    def __len__( self ):
        return self.ActualRecords

    def __getitem__( self, index ):
        return _AccSubRecord( self, index )

    @property
    def ActualRecords( self ):
        return self.mwfms[0].ActualRecords

    @property
    def ActualAverages( self ):
        return self.mwfms[0].ActualAverages

    def append( self, fetch ):
        mwfm = fetch if fetch.__class__.__name__=="AqMD3AccumulatedWaveformCollection" else _AccMultiWaveform( fetch )
        if len( self.mwfms )>0 and self.mwfms[0].ActualRecords != mwfm.ActualRecords:
            raise RuntimeError( "ActualRecords do not match." )
        if len( self.mwfms )>0:
            if self.checkXOffset:
                if self.mwfms[0].InitialXOffset != mwfm.InitialXOffset:
                    raise RuntimeError( "InitialXOffset do not match." )
            for r in range( mwfm.ActualRecords ):
                if self.mwfms[0].ActualPoints[r] != mwfm.ActualPoints[r]:
                    raise RuntimeError( "ActualPoints do not match." )
                if self.checkXOffset:
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



def _test_ReadAccRecords( f ):
    """ Read AccRecord objects from a file
    
    >>> from io import StringIO
    >>> trace = '''$TraceType Accumulated
    ... $SampleType Int32
    ... $ActualChannels 2
    ... $ActualAverages 256
    ... $Model U5309A
    ... $XIncrement 1.0e-9
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
    >>> recs = ReadAccRecords( f )
    >>> rec = next( recs )
    >>> print( len( rec ), rec.ActualPoints, rec.ActualAverages, rec.InitialXOffset, rec.InitialXTimeSeconds, rec.InitialXTimeFraction, rec.XIncrement )
    2 32 256 -7.93457e-11 0.0 0.002 1e-09
    >>> wfm = rec[0]
    >>> print( wfm.ActualPoints, wfm.InitialXOffset, wfm.InitialXTimeSeconds, wfm.InitialXTimeFraction, wfm.XIncrement, wfm.ScaleFactor, wfm.ScaleOffset )
    32 -7.93457e-11 0.0 0.002 1e-09 6.103515625e-05 0.0
    >>> print( wfm.Samples )
    [ -2243   3171   8093  11667  13533  13203  10973   6947   1869  -3485
      -8403 -11933 -13571 -13213 -10755  -6573  -1427   4019   8701  12067
      13581  12979  10429   6195   1053  -4333  -9011 -12349 -13667 -12941
     -10179  -5757]
    """
    for trc in ReadTrace( f ):
        record = AccMultiRecord()
        record.SampleType = trc.SampleType
        for wfm in trc:
            record.append( ( wfm.Samples, trc.ActualAverages, 1, [trc.ActualPoints], [0], trc.InitialXOffset, [trc.InitialXTimeSeconds], [trc.InitialXTimeFraction], trc.XIncrement, wfm.ScaleFactor, wfm.ScaleOffset, [0] ) )
        yield record[0]



if __name__ == "__main__":
    import doctest
    doctest.IGNORE_EXCEPTION_DETAIL = True
    doctest.testmod()

