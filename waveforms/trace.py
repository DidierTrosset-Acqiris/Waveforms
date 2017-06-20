#!/usr/bin/python3

from sys import stderr
from numpy import int8, int16, int32, float64, array, zeros, resize
from waveforms.singlerecord import Record


"""
This is how to use the Trace module. Of course, effective use will not
define the text of the file content, but read it from an actual file!

record = Record( AgMD2_FetchWaveformViInt16( Vi, ... ) )
OutputTrace( record, file=sys.stdout )

for rec in ReadTrace( sys.stdin ):
    # Do what you want with the record ...


"""

class Trace:
    """ Abstract Trace class used to hold coherent series of values.
    """
    class Wave:
        def __init__( self ):
            self.Samples = None

        def __len__( self ):
            return len( self.Samples )

        def __getitem__( self, index ):
            return self.Samples[index]

        def __iter__( self ):
            return iter( self.Samples )

    def __init__( self ):
        self.Waves = []

    def __len__( self ):
        return len( self.Waves )

    def __getitem__( self, index ):
        return self.Waves[index]

    def __iter__( self ):
        return iter( self.Waves )


def SampleType( dataType ):
    if dataType==int32:
        return "Int32"
    elif dataType==int16:
        return "Int16"
    elif dataType==int8:
        return "Int8"
    elif dataType==float64:
        return "Real64"
    else:
        raise RuntimeError( "ERROR: Unknown sample type "+str( dataType )+"." )

def DataType( sampleType ):
    if sampleType=="Int32":
        return int32
    elif sampleType=="Int16":
        return int16
    elif sampleType=="Int8":
        return int8
    elif sampleType=="Real64":
        return float64
    else:
        raise RuntimeError( "ERROR: Unknown sample type "+str( SampleType )+"." )

def FullScale( sampleType ):
    if sampleType=="Int32":
        return 2**32
    elif sampleType=="Int16":
        return 2**16
    elif sampleType=="Int8":
        return 2**8
    elif sampleType=="Real64":
        return 1.0
    else:
        raise RuntimeError( "ERROR: Unknown sample type "+str( SampleType )+"." )

class TraceHandler:

    def __init__( self ):
        self.keep_line = None 
        self.is_valid = False
        self.trace = None
        pass

    def SetKeepLine( self, line ):
        self.keep_line = line

    def GetKeepLine( self ):
        line = self.keep_line
        self.keep_line = None
        return line

    def trcBegin(self):
        self.Waves = None
        self._size = 0
        self._index = 0
        self._chans = 0
        self.stype = int
        self.dtype = int16
        self.FullScale = 65536

    def trcEnd(self, cont):
        if self._size==0 or not self.Waves or self._index==0:
            return
        while len( self.trace.Waves )<len( self.Waves ):
            self.trace.Waves.append( Trace.Wave() )
        for i in range( len( self.Waves ) ):
            self.Waves[i].resize( self._index )
            self.trace.Waves[i].Samples = self.Waves[i]
        self.trace.ActualChannels = len( self.trace.Waves )
        self.trace.ActualPoints = len( self.trace.Waves[0].Samples )
        self.is_valid = True

    def trcAttribute(self, strKey, strValue):
        if strKey=='TraceType':
            self.trace.TraceType = strValue
        elif strKey=='SampleType':
            self.sampleType = strValue
            self.trace.SampleType = strValue
        elif strKey=='FULLSCALE':
            self.sampleType = "Int8" if strValue=="256" else "Int16" if strValue=="65536" else "Int32"
            self.trace.SampleType = self.sampleType
        elif strKey=='Model':
            self.trace.Model = strValue
        elif strKey=='SINEFREQ' or strKey=='SineFreq':
            self.trace.SineFreq = float( strValue )
        elif strKey=='Counter':
            self.trace.counter = int( strValue )
        elif strKey=='#ADCS':
            pass
        elif strKey=='#CHANNELS' or strKey=='ActualChannels':
            self.trace.ActualChannels = int(strValue)
        elif strKey=='FullScale':
            self.trace.FullScale = float(strValue) if float(strValue)!=int(strValue) else int(strValue)
        elif strKey=='NbrAdcBits':
            self.trace.NbrAdcBits = int(strValue)
        elif strKey=='SAMPIVAL' or strKey=='XIncrement':
            self.trace.XIncrement = float( strValue )
        elif strKey=='ActualAverages':
            self.trace.ActualAverages = int( strValue )
        elif strKey=='HORPOS':
            self.trace.InitialXOffset = float( strValue )
        elif strKey=='InitialXOffset':
            self.trace.InitialXOffset = float( strValue )
        elif strKey=='InitialTimeSeconds':
            self.trace.InitialXTimeSeconds = float( strValue )
        elif strKey=='InitialTimeFraction':
            self.trace.InitialXTimeFraction = float( strValue )
        else:
            try:
                setattr( self.trace, strKey, strValue )
            except:
                print( "ERROR:", "Cannot process attribute", strKey, "value", strValue, file=stderr )

    def trcWaveAttribute(self, index, strKey, strValue):
        assert index>=0
        while len( self.trace.Waves )<=index:
            self.trace.Waves.append( Trace.Wave() )
        if strKey=='ScaleFactor':
            self.trace.Waves[index].ScaleFactor = float( strValue )
        elif strKey=='ScaleOffset':
            self.trace.Waves[index].ScaleOffset = float( strValue )
        else:
            try:
                setattr( self.trace.Waves[index], strKey, strValue )
            except:
                print( "ERROR:", "Cannot process attribute", strKey, "index", index, "value", strValue, file=stderr )

    def _initWaves( self, sampleType, nbrChannels ):
        assert self.Waves is None
        self._dtype = DataType( sampleType )
        self._stype = float if self.dtype==float64 else int
        self._size = 1024
        self._index = 0
        self._chans = nbrChannels
        self.Waves = [ zeros( self._size, dtype=self._dtype ) for _ in range( self._chans ) ]

    def _resizeWaves( self ):
        assert self.Waves is not None
        assert self._stype is not None
        assert self._dtype is not None
        self._size = self._size*2
        for i in range( len( self.Waves ) ):
            self.Waves[i].resize( self._size )

    def trcSamples(self, strLine):
        values = strLine.split()
        if not self.Waves:
            self._initWaves( self.sampleType, len( values ) )
        if self._index>=self._size:
            self._resizeWaves()
        try:
            for record, value in enumerate( values ):
                self.Waves[record][self._index] = self._stype( value )
        except:
            print( "ERROR:", "Cannot understand samples", strLine, file=stderr )
            raise
        finally:
            self._index = self._index+1



def ParseTrace( input, handler ):
    EOF = True
    FS = chr(28)
    handler.trace = Trace()
    handler.trcBegin()

    isInSamples = False
    while True:
        # Get the next line
        if handler.keep_line:
            line = handler.GetKeepLine()
        else:
            line = input.readline()

        # Handles EOF
        if line=="":
            EOF = True
            break

        # Handles end of record with start of new one
        if line[0]=="$" and isInSamples:
            handler.SetKeepLine( line )
            EOF = False
            break

        # Handles empty lines
        line = line.strip()
        if line=="" or line[0]==FS:
            continue

        # Interpret the line
        if line[0]=="$" and line[1]=="$":
            line = line[2:]
            key, index, value = line.split( None, maxsplit=2 )
            handler.trcWaveAttribute( int( index ), key, value )
        elif line[0]=="$":
            line = line[1:]
            key, value = line.split( None, maxsplit=1 )
            handler.trcAttribute( key, value )
        else:
            isInSamples = True
            handler.trcSamples( line )
            
    handler.trcEnd(cont = not EOF)
    return handler.trace, not EOF




def _test_ReadTrace( f ):
    """
    This is how to use the Trace module. Of course, effective use will not
    define the text of the file content, but read it from an actual file!

    >>> from io import StringIO
    >>> trace = '''$TraceType Digitizer
    ... $ActualChannels 2
    ... $SampleType Int16
    ... $FullScale 65536
    ... $Model M9703B
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93457e-11
    ... $InitialXTimeSeconds 0.0
    ... $InitialXTimeFraction 0.002
    ... $$ScaleFactor 0 1.52587890625e-05
    ... $$ScaleOffset 0 0.0
    ... $$ScaleFactor 1 1.52587890625e-05
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
    >>> for trc in ReadTrace( f ):
    ...    print( len( trc.Waves ) )
    ...    print( trc.ActualChannels, trc.ActualPoints, trc.InitialXOffset, trc.InitialXTimeSeconds, trc.InitialXTimeFraction, trc.XIncrement )
    ...    for wfm in trc:
    ...        print( wfm.ScaleFactor, wfm.ScaleOffset )
    ...        print( wfm.Samples )
    2
    2 32 -7.93457e-11 0.0 0.002 6.25e-10
    1.52587890625e-05 0.0
    [ -2243   3171   8093  11667  13533  13203  10973   6947   1869  -3485
      -8403 -11933 -13571 -13213 -10755  -6573  -1427   4019   8701  12067
      13581  12979  10429   6195   1053  -4333  -9011 -12349 -13667 -12941
     -10179  -5757]
    1.52587890625e-05 0.0
    [ -5486    -18   5394   9902  12962  13966  12850   9598   5074   -370
      -5742 -10242 -13118 -14034 -12734  -9378  -4670    846   6162  10542
      13250  13918  12482   8926   4258  -1202  -6542 -10818 -13406 -13938
     -12366  -8770]
    >>> trace = '''$TraceType Digitizer
    ... $ActualChannels 2
    ... $SampleType Int16
    ... $FullScale 65536
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93456e-11
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
    ... $ActualChannels 2
    ... $SampleType Int16
    ... $FullScale 65536
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93457e-11
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
    ... $ActualChannels 2
    ... $SampleType Int16
    ... $FullScale 65536
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93458e-11
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
    ... $ActualChannels 2
    ... $SampleType Int16
    ... $FullScale 65536
    ... $XIncrement 6.25e-10
    ... $InitialXOffset -7.93459e-11
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
    >>> for trc in ReadTrace( f ):
    ...    print( len( trc.Waves ) )
    ...    print( trc.ActualChannels, trc.ActualPoints, trc.InitialXOffset, trc.XIncrement )
    ...    for wfm in trc:
    ...        print( wfm.Samples )
    2
    2 8 -7.93456e-11 6.25e-10
    [-2243  3171  8093 11667 13533 13203 10973  6947]
    [-5486   -18  5394  9902 12962 13966 12850  9598]
    2
    2 8 -7.93457e-11 6.25e-10
    [  1869  -3485  -8403 -11933 -13571 -13213 -10755  -6573]
    [  5074   -370  -5742 -10242 -13118 -14034 -12734  -9378]
    2
    2 8 -7.93458e-11 6.25e-10
    [-1427  4019  8701 12067 13581 12979 10429  6195]
    [-4670   846  6162 10542 13250 13918 12482  8926]
    2
    2 8 -7.93459e-11 6.25e-10
    [  1053  -4333  -9011 -12349 -13667 -12941 -10179  -5757]
    [  4258  -1202  -6542 -10818 -13406 -13938 -12366  -8770]
    """


def ReadTrace( f ):
    """ Read a trace from a file """
    keepon = True
    handler = TraceHandler()
    while keepon:
        trace, keepon = ParseTrace( f, handler )
        if not handler.is_valid:
            continue
        yield trace



def _test_OutputTrace( records, file ):
    """ Test the OutputTrace function

    >>> from io import StringIO
    >>> samples = array( [ -2243,   3171,   8093,  11667,  13533,  13203,  10973,   6947, \
                            1869,  -3485,  -8403, -11933, -13571, -13213, -10755,  -6573, \
                           -1427,   4019,   8701,  12067,  13581,  12979,  10429,   6195, \
                            1053,  -4333,  -9011, -12349, -13667, -12941, -10179,  -5757], dtype=int16 )
    >>> r = Record( ( samples, 30, 0, -7e-11, 0.0, 2e-3, 6.25e-10, 2.0/32768, 0.0 ) )
    >>> r.append(   ( samples, 30, 2, -7e-11, 0.0, 2e-3, 6.25e-10, 1.0/32768, 0.0 ) )
    >>> o = StringIO()
    >>> OutputTrace( r, file=o, Model="U5303A" )
    >>> print( o.getvalue() )
    $TraceType Digitizer
    $SampleType Int16
    $FullScale 65536
    $ActualChannels 2
    $Model U5303A
    $XIncrement 6.25e-10
    $InitialXOffset -7e-11
    $InitialXTimeSeconds 0.0
    $InitialXTimeFraction 0.002
    $$ScaleFactor 0 6.103515625e-05
    $$ScaleOffset 0 0.0
    $$ScaleFactor 1 3.0517578125e-05
    $$ScaleOffset 1 0.0
    -2243 8093
    3171 11667
    8093 13533
    11667 13203
    13533 10973
    13203 6947
    10973 1869
    6947 -3485
    1869 -8403
    -3485 -11933
    -8403 -13571
    -11933 -13213
    -13571 -10755
    -13213 -6573
    -10755 -1427
    -6573 4019
    -1427 8701
    4019 12067
    8701 13581
    12067 12979
    13581 10429
    12979 6195
    10429 1053
    6195 -4333
    1053 -9011
    -4333 -12349
    -9011 -13667
    -12349 -12941
    -13667 -10179
    -12941 -5757
    <BLANKLINE>
    <BLANKLINE>
    >>> o.close()
    >>> o = StringIO()
    >>> OutputTrace( r, file=o, Model="U5303A", NbrSamples=8 )
    >>> print( o.getvalue() )
    $TraceType Digitizer
    $SampleType Int16
    $FullScale 65536
    $ActualChannels 2
    $Model U5303A
    $XIncrement 6.25e-10
    $InitialXOffset -7e-11
    $InitialXTimeSeconds 0.0
    $InitialXTimeFraction 0.002
    $$ScaleFactor 0 6.103515625e-05
    $$ScaleOffset 0 0.0
    $$ScaleFactor 1 3.0517578125e-05
    $$ScaleOffset 1 0.0
    -2243 8093
    3171 11667
    8093 13533
    11667 13203
    13533 10973
    13203 6947
    10973 1869
    6947 -3485
    <BLANKLINE>
    <BLANKLINE>
    >>> o.close()
    """


def OutputTraces( traces, file, Model=None, NbrSamples=None ):
    for trace in traces:
        OutputTrace( trace, file=file, Model=Model, NbrSamples=NbrSamples )


def OutputTrace( trace, file, Model=None, NbrSamples=None ):
    """ Write the given Trace to the given file object.
    """
    sampleType = getattr( trace, 'SampleType', SampleType( trace[0].Samples.dtype ) )
    print( "$TraceType", trace.TraceType, file=file )
    print( "$SampleType", sampleType, file=file )
    if hasattr( trace, 'NbrAdcBits' ) and trace.NbrAdcBits: print( "$NbrAdcBits", trace.NbrAdcBits, file=file )
    if hasattr( trace, 'FullScale' ) and trace.FullScale: print( "$FullScale", trace.FullScale, file=file )
    print( "$ActualChannels", len( trace ), file=file )
    if Model: print( "$Model", Model, file=file )
    print( "$XIncrement", trace.XIncrement, file=file )
    print( "$InitialXOffset", trace.InitialXOffset, file=file )
    print( "$InitialXTimeSeconds", trace.InitialXTimeSeconds, file=file )
    print( "$InitialXTimeFraction", trace.InitialXTimeFraction, file=file )
    for index, wave in enumerate( trace ):
        print( "$$ScaleFactor", index, wave.ScaleFactor, file=file )
        print( "$$ScaleOffset", index, wave.ScaleOffset, file=file )
    try: print( "$ActualAverages", trace.ActualAverages, file=file )
    except: pass

    for index, samples in enumerate( zip( *trace ) ):
        if NbrSamples and index>=NbrSamples:
            break
        file.write( " ".join( map( str, samples ) )+"\n" )

    file.write( "\n" )

    file.flush()





if __name__ == "__main__":
    import doctest
    doctest.testmod()

