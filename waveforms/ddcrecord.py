#!/usr/bin/python3

from numpy import pi, int16, int32, array, zeros, resize, fromfunction, sqrt, arctan2
from sys import stderr
from waveforms.trace import ReadTrace


class _DDCMultiWaveform():
    """ Private class that directly gather the values retreived by the DDCFetchWaveform functions.

    >>> samples = array( [ 12315,     -1,     97,     -1, -11877,      3,   -408,     -1, \
                           12283,     -2,     65,      0, -11957,      3,   -409,      0, \
                           12307,     -3,     89,     -1, -11887,      3,   -411,      1, \
                           12285,     -3,     79,     -1, -11957,      2,   -421,      1, \
                           12313,     -1,     39,      1, -11923,      1,   -418,      0, \
                           12289,     -3,     99,      1, -11793,      3,   -331,     -1, \
                           12287,     -3,     93,      0, -11816,      1,   -399,     -1, \
                           12293,     -3,     87,     -1, -11859,      1,   -392,      1 ], dtype=int16 )
    >>> w = _DDCMultiWaveform( ( samples, 2, [12, 12], [0, 32], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, 2.0/32768, 0.0, [0, 0] ) )
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
    >>> print( w.Flags )
    [0, 0]
    >>> w = _DDCMultiWaveform( ( samples, 2, [12, 12], [0, 16], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, [0, 0] ) )
    >>> print( w.ScaleFactor )
    1.0
    >>> print( w.ScaleOffset )
    0.0

    """
    def __init__( self, fetch ):
        if fetch[1] != len( fetch[2] ):
            raise RuntimeError( "Bad number of ActualPoints." )
        if fetch[1] != len( fetch[3] ):
            raise RuntimeError( "Bad number of FirstValidPoint." )
        if fetch[1] != len( fetch[4] ):
            raise RuntimeError( "Bad number of InitialXOffset." )
        if fetch[1] != len( fetch[5] ):
            raise RuntimeError( "Bad number of InitialXTimeSeconds." )
        if fetch[1] != len( fetch[6] ):
            raise RuntimeError( "Bad number of InitialXTimeFraction." )
        self.fetch = fetch
        self.SampleArray          = self.fetch[0]
        self.ActualRecords        = self.fetch[1]
        self.ActualPoints         = self.fetch[2]
        self.FirstValidPoint      = self.fetch[3]
        self.InitialXOffset       = self.fetch[4]
        self.InitialXTimeSeconds  = self.fetch[5]
        self.InitialXTimeFraction = self.fetch[6]
        self.XIncrement           = self.fetch[7]
        # Special case for FetchMultiRecordWaveformViReal64 that do not return scale parameters.
        try:
            self.ScaleFactor      = self.fetch[8]
            self.ScaleOffset      = self.fetch[9]
            self.Flags            = self.fetch[10]
        except (IndexError): 
            self.ScaleFactor      = 1.0
            self.ScaleOffset      = 0.0
            self.Flags            = self.fetch[8]


class _DDCSubWaveform:
    def __init__( self, mwfm, index, view ):
        if index<0 or index>=mwfm.ActualRecords:
            raise IndexError( "index out of bounds" )
        self.mwfm = mwfm
        self.index = index
        self._view = view

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
        return self._sample_view( index )

    def _sample_view( self, index ):
        first = self.mwfm.FirstValidPoint[self.index]
        actual = self.mwfm.ActualPoints[self.index]
        samples = self.mwfm.SampleArray[2*first:2*first+2*actual]
        real = samples[2*index]
        imag = samples[2*index+1]
        if self._view=='REAL':
            return real
        elif self._view=='IMAGINARY':
            return imag
        elif self._view=='TUPLE':
            return ( real, imag )
        elif self._view=='COMPLEX':
            return real + imag*1j
        elif self._view=='MAGNITUDE':
            return sqrt( real**2 + imag**2 )
        elif self._view=='PHASE':
            return arctan2( imag, real )
        else:
            raise RuntimeError( "Unknown DDCWaveform view type '%s'."%( self._view ) )

    @property
    def Samples( self ):
        first = self.mwfm.FirstValidPoint[self.index]
        actual = self.mwfm.ActualPoints[self.index]
        samples = self.mwfm.SampleArray
        if self._view=='REAL':
            return samples[2*first:2*first+2*actual:2]
        elif self._view=='IMAGINARY':
            return samples[2*first+1:2*first+2*actual+1:2]
        elif self._view=='COMPLEX':
            return samples[2*first:2*first+2*actual:2] + 1j*samples[2*first+1:2*first+2*actual+1:2]
        elif self._view=='MAGNITUDE':
            return fromfunction( lambda n: sqrt( samples[2*( first+n )+1]**2 + samples[2*( first+n )]**2 ), ( actual, ), dtype=int )
        elif self._view=='PHASE':
            return fromfunction( lambda n: arctan2( samples[2*( first+n )+1], samples[2*( first+n )]), ( actual, ), dtype=int )
        else:
            raise RuntimeError( "Unknown DDCWaveform view type '%s'."%( self._view ) )

    @property
    def view( self ):
        return self._view

    @view.setter
    def view( self, view ):
        if view not in ['REAL', 'IMAGINARY', 'MAGNITUDE', 'PHASE']:
            raise RuntimeError( "DDCWaveform view type must be REAL, IMAGINARY, MAGNITUDE, or PHASE" )
        self._view = view


class _DDCSubRecord:
    def __init__( self, mrec, index, view ):
        if index<0 or index>=len( mrec ):
            raise IndexError( "index out of bounds" )
        self.mrec = mrec
        self.index = index
        self.view = view

    def __len__( self ):
        return len( self.mrec.mwfms )

    def __getitem__( self, index ):
        return _DDCSubWaveform( self.mrec.mwfms[index], self.index, self.view )

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
    def SampleType( self ):
        return "Int32" if self.mrec.mwfms[0].SampleArray.dtype==int32 else "Int16" if self.mrec.mwfms[0].SampleArray.dtype==int16 else "Int8"


class DDCMultiRecord():
    """
    >>> samples = array( [ 12315,     -1,     97,     -1, -11877,      3,   -408,     -1, \
                           12283,     -2,     65,      0, -11957,      3,   -409,      0, \
                           12307,     -3,     89,     -1, -11887,      3,   -411,      1, \
                           12285,     -3,     79,     -1, -11957,      2,   -421,      1, \
                           12313,     -1,     39,      1, -11923,      1,   -418,      0, \
                           12289,     -3,     99,      1, -11793,      3,   -331,     -1, \
                           12287,     -3,     93,      0, -11816,      1,   -399,     -1, \
                           12293,     -3,     87,     -1, -11859,      1,   -392,      1 ], dtype=int16 )
    >>> mr = DDCMultiRecord( ( samples, 2, [12, 12], [0, 16], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, 2.0/32768, 0.0, 0 ) )
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
    12315
    >>> print( r0[0][1] )
    97
    >>> print( r0[0][12] )
    Traceback (most recent call last):
    ...
    IndexError: index 24 is out of bounds for axis 0 with size 24
    >>> print( r1[0][0] )
    12313
    >>> print( r1[0][1] )
    39
    >>> r0.InitialXOffset
    -7e-11
    >>> r1.InitialXOffset
    -3e-11
    >>> print( r0[0].Samples )
    [ 12315     97 -11877   -408  12283     65 -11957   -409  12307     89
     -11887   -411]
    >>> print( r1[0].Samples )
    [ 12313     39 -11923   -418  12289     99 -11793   -331  12287     93
     -11816   -399]

    """

    def __init__( self, fetch=None, checkXOffset=True, nbrAdcBits=None ):
        self.NbrAdcBits = nbrAdcBits
        self._view = 'REAL'
        self.checkXOffset = checkXOffset
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
        return _DDCSubRecord( self, index, self._view )

    @property
    def ActualRecords( self ):
        return self.mwfms[0].ActualRecords

    def append( self, fetch ):
        mwfm = _DDCMultiWaveform( fetch )
        if len( self.mwfms )>0 and self.mwfms[0].ActualRecords != mwfm.ActualRecords:
            raise RuntimeError( "ActualRecords do not match." )
        if len( self.mwfms )>0:
            for r in range( mwfm.ActualRecords ):
                if self.mwfms[0].ActualPoints[r] != mwfm.ActualPoints[r]:
                    raise RuntimeError( "ActualPoints do not match." )
                if self.checkXOffset:
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

    @property
    def SampleType( self ):
        return self.mwfms[0].SampleType

    @property
    def view( self ):
        return self._view

    @view.setter
    def view( self, view ):
        if view not in ['REAL', 'IMAGINARY', 'COMPLEX', 'MAGNITUDE', 'PHASE']:
            raise RuntimeError( "DDCWaveform view type must be REAL, IMAGINARY, COMPLEX, MAGNITUDE, or PHASE" )
        self._view = view



def ReadDDCRecords( f ):
    """ Read DDCRecord objects from a file

    >>> from io import StringIO
    >>> trace = '''$SampleType Int16
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
    >>> recs = ReadDDCRecords( f )
    >>> rec = next( recs )
    >>> print( len( rec ), rec.ActualPoints, rec.InitialXOffset, rec.InitialXTimeSeconds, rec.InitialXTimeFraction, rec.XIncrement )
    2 16 -7.93457e-11 0.0 0.002 6.25e-10
    >>> wfm = rec[0]
    >>> print( wfm.ActualPoints, wfm.InitialXOffset, wfm.InitialXTimeSeconds, wfm.InitialXTimeFraction, wfm.XIncrement, wfm.ScaleFactor, wfm.ScaleOffset )
    16 -7.93457e-11 0.0 0.002 6.25e-10 6.103515625e-05 0.0
    >>> print( wfm.Samples )
    [ -2243   8093  13533  10973   1869  -8403 -13571 -10755  -1427   8701
      13581  10429   1053  -9011 -13667 -10179]
    >>> wfm = rec[1]
    >>> print( wfm.ActualPoints, wfm.InitialXOffset, wfm.InitialXTimeSeconds, wfm.InitialXTimeFraction, wfm.XIncrement, wfm.ScaleFactor, wfm.ScaleOffset )
    16 -7.93457e-11 0.0 0.002 6.25e-10 3.0517578125e-05 0.0
    >>> print( wfm.Samples )
    [ -5486   5394  12962  12850   5074  -5742 -13118 -12734  -4670   6162
      13250  12482   4258  -6542 -13406 -12366]
    >>> wfm.view = "IMAGINARY"
    >>> print( wfm.ActualPoints, wfm.InitialXOffset, wfm.InitialXTimeSeconds, wfm.InitialXTimeFraction, wfm.XIncrement, wfm.ScaleFactor, wfm.ScaleOffset )
    16 -7.93457e-11 0.0 0.002 6.25e-10 3.0517578125e-05 0.0
    >>> print( wfm.Samples )
    [   -18   9902  13966   9598   -370 -10242 -14034  -9378    846  10542
      13918   8926  -1202 -10818 -13938  -8770]
    """
    for trc in ReadTrace( f ):
        record = DDCMultiRecord()
        record.SampleType = trc.SampleType
        for wfm in trc:
            record.append( ( wfm.Samples, 1, [trc.ActualPoints//2], [0], [trc.InitialXOffset], [trc.InitialXTimeSeconds], [trc.InitialXTimeFraction], trc.XIncrement, wfm.ScaleFactor, wfm.ScaleOffset, [0] ) )
        yield record[0]



if __name__ == "__main__":
    import doctest
    doctest.IGNORE_EXCEPTION_DETAIL = True
    doctest.testmod()

