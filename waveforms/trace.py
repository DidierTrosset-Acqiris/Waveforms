#!/usr/bin/python3

from sys import stderr
from numpy import int16, int32, array, zeros, resize
from __init__ import Record, MultiRecord


"""
This is how to use the Trace module. Of course, effective use will not
define the text of the file content, but read it from an actual file!

record = Record( AgMD2_FetchWaveformViInt16( Vi, ... ) )
OutputTrace( record, out=sys.stdout )

for rec in ReadTrace( sys.stdin ):
    # Do what you want with the record ...


"""


class TraceHandler:

    def __init__(self):
        self.keep_char = None 
        self.is_valid = False
        pass

    def SetKeepChar( self, ch ):
        self.keep_char = ch

    def GetKeepChar( self ):
        ch = self.keep_char
        self.keep_char = None
        return ch

    def trcBegin(self):
        self.Waves = None
        self._size = 0
        self._index = 0
        self.dtype = int16
        self.nbrRecords = 1 # In case there's only one
        self.InitialXOffset = 0.0

    def trcEnd(self, cont):
        if self._size==0 or not self.Waves or self._index==0:
            return
        for i in range( len( self.Waves ) ):
            self.Waves[i].resize( self._index )
        self.nbrRecords = len( self.Waves )
        self.nbrSamples = len( self.Waves[0] )
        self.ActualPoints = self.nbrSamples
        self.Samples = array( self.Waves, dtype=self.dtype, order="C" )
        self.is_valid = True

    def trcAttribute(self, strKey, strValue):
        if strKey=='MODEL':
            self.model = str(strValue)
        if strKey=='COUNTER':
            self.counter = int(strValue)
        if strKey=='FPGAIDS':
            self.fpgaids = map(str, strValue.split())
        if strKey=='#ADCS':
            self.nbrAdc = int(strValue)
        if strKey=='#CHANNELS':
            self.nbrRecords = int(strValue)
        if strKey=='FULLSCALE':
            self.fullscale = int(strValue)
            self.dtype = int32 if self.fullscale==4294967296 else int16
        if strKey=='CHANNELFSR':
            self.channelfsr = float(strValue)
        if strKey=='SAMPIVAL' or strKey=='XIncrement':
            self.XIncrement = float( strValue )
        if strKey=='TEMPERATURES':
            self.temperatures = list( map(int, strValue.split()) )
        if strKey=='HORPOS':
            self.InitialXOffset = list( map( float, strValue.split() ) )
            self.InitialXOffset = self.InitialXOffset[0]
        if strKey=='InitialXOffset':
            self.InitialXOffset = float( strValue )

    def trcSamples(self, strLine):
        if not self.Waves:
            self._size = 1024
            self.Waves = [ zeros( self._size, dtype=self.dtype ) for _ in range( self.nbrRecords ) ]
        if self._index>=self._size:
            self._size = self._size*2
            for i  in range( len( self.Waves ) ):
                self.Waves[i].resize( self._size )
            #self.Waves = [resize( wave, self._size ) for wave in self.Waves]
        try:
            values = strLine.split()
            for record, value in enumerate( values ):
                self.Waves[record][self._index] = int( value )
        except:
            stderr.write( "ERROR: '%s'\n"%( strLine ) )
            raise
        finally:
            self._index = self._index+1



def ParseTrace( input, handler ):
    EOF = True
    FS = chr(28)
    handler.trcBegin()
    isInSamples = False
    while True:
        if handler.keep_char:
            ch = handler.GetKeepChar()
        else:
            ch = input.read(1)

        if ch == "":
            EOF = True
            break
        if ch == "$" and isInSamples:
            handler.SetKeepChar( "$" )
            EOF = False
            break
        if ch == "\n":
            continue
        if ch == FS:
            continue
        line = ch + input.readline()
        line = line.strip()
        if line == "":
            EOF = True
            break
        if line[0] == "$":
            line = line[1:]
            key, value = line.split( None, maxsplit=1 )
            handler.trcAttribute( key, value )
        else:
            isInSamples = True
            handler.trcSamples( line )
    handler.trcEnd(cont = not EOF)
    return not EOF




def ReadTrace( f ):
    """
    This is how to use the Trace module. Of course, effective use will not
    define the text of the file content, but read it from an actual file!

    >>> from io import StringIO
    >>> trace = '''$#ADCS 1
    ... $#CHANNELS 2
    ... $SIGNED 1
    ... $FORMATTING DECIMAL
    ... $FULLSCALE 65536
    ... $MODEL M9703A
    ... $SERIALNO CH00085346
    ... $SAMPIVAL 6.25e-10
    ... $CHANNELFSR 1
    ... $HORPOS -7.93457e-11
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
    >>> for rec in ReadTrace( f ):
    ...    print( len( rec ) )
    ...    for w in rec:
    ...        print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    ...        print( w.Samples )
    2
    32 -7.93457e-11 0.0 0.0 6.25e-10 1.52587890625e-05 0.0
    [ -2243   3171   8093  11667  13533  13203  10973   6947   1869  -3485
      -8403 -11933 -13571 -13213 -10755  -6573  -1427   4019   8701  12067
      13581  12979  10429   6195   1053  -4333  -9011 -12349 -13667 -12941
     -10179  -5757]
    32 -7.93457e-11 0.0 0.0 6.25e-10 1.52587890625e-05 0.0
    [ -5486    -18   5394   9902  12962  13966  12850   9598   5074   -370
      -5742 -10242 -13118 -14034 -12734  -9378  -4670    846   6162  10542
      13250  13918  12482   8926   4258  -1202  -6542 -10818 -13406 -13938
     -12366  -8770]
    >>> trace = '''$#CHANNELS 2
    ... $SAMPIVAL 6.25e-10
    ... $HORPOS -7.93457e-11
    ... -2243 -5486  
    ... 3171  -18    
    ... 8093  5394   
    ... 11667 9902   
    ... 13533 12962  
    ... 13203 13966  
    ... 10973 12850  
    ... 6947  9598   
    ...
    ... $#CHANNELS 2
    ... $SAMPIVAL 6.25e-10
    ... $HORPOS -7.93457e-11
    ... 1869  5074   
    ... -3485 -370   
    ... -8403 -5742  
    ... -11933 -10242
    ... -13571 -13118
    ... -13213 -14034
    ... -10755 -12734
    ... -6573 -9378  
    ...
    ... $#CHANNELS 2
    ... $SAMPIVAL 6.25e-10
    ... $HORPOS -7.93457e-11
    ... -1427 -4670  
    ... 4019  846    
    ... 8701  6162   
    ... 12067 10542  
    ... 13581 13250  
    ... 12979 13918  
    ... 10429 12482  
    ... 6195  8926   
    ...
    ... $#CHANNELS 2
    ... $SAMPIVAL 6.25e-10
    ... $HORPOS -7.93457e-11
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
    >>> for rec in ReadTrace( f ):
    ...    print( len( rec ) )
    ...    for w in rec:
    ...        print( w.ActualPoints, w.InitialXOffset, w.InitialXTimeSeconds, w.InitialXTimeFraction, w.XIncrement, w.ScaleFactor, w.ScaleOffset )
    ...        print( w.Samples )
    2
    8 -7.93457e-11 0.0 0.0 6.25e-10 1.0 0.0
    [-2243  3171  8093 11667 13533 13203 10973  6947]
    8 -7.93457e-11 0.0 0.0 6.25e-10 1.0 0.0
    [-5486   -18  5394  9902 12962 13966 12850  9598]
    2
    8 -7.93457e-11 0.0 0.0 6.25e-10 1.0 0.0
    [  1869  -3485  -8403 -11933 -13571 -13213 -10755  -6573]
    8 -7.93457e-11 0.0 0.0 6.25e-10 1.0 0.0
    [  5074   -370  -5742 -10242 -13118 -14034 -12734  -9378]
    2
    8 -7.93457e-11 0.0 0.0 6.25e-10 1.0 0.0
    [-1427  4019  8701 12067 13581 12979 10429  6195]
    8 -7.93457e-11 0.0 0.0 6.25e-10 1.0 0.0
    [-4670   846  6162 10542 13250 13918 12482  8926]
    2
    8 -7.93457e-11 0.0 0.0 6.25e-10 1.0 0.0
    [  1053  -4333  -9011 -12349 -13667 -12941 -10179  -5757]
    8 -7.93457e-11 0.0 0.0 6.25e-10 1.0 0.0
    [  4258  -1202  -6542 -10818 -13406 -13938 -12366  -8770]
    """
    h = TraceHandler()
    keepon = True
    try:
        while keepon:
            keepon = ParseTrace( f, h )
            if h.is_valid:
                ActualPoints = h.ActualPoints
                InitialXOffset = h.InitialXOffset
                InitialXTimeSeconds = 0.0
                InitialXTimeFraction = 0.0
                XIncrement = h.XIncrement
                try:    ScaleFactor = h.channelfsr/h.fullscale
                except: ScaleFactor = 1.0
                ScaleOffset = 0.0
                r = Record()
                for w in h.Waves:
                    r.append( ( w, ActualPoints, 0, InitialXOffset, 0.0, 0.0, XIncrement, ScaleFactor, ScaleOffset ) )
                yield r
    except:
        raise



def OutputTrace( records, out ):
    """ Write the given Record or MultiRecord to the given out file object.

    >>> from io import StringIO
    >>> samples = array( [ -2243,   3171,   8093,  11667,  13533,  13203,  10973,   6947, \
                            1869,  -3485,  -8403, -11933, -13571, -13213, -10755,  -6573, \
                           -1427,   4019,   8701,  12067,  13581,  12979,  10429,   6195, \
                            1053,  -4333,  -9011, -12349, -13667, -12941, -10179,  -5757], dtype=int16 )
    >>> r = Record( ( samples, 30, 0, -7e-11, 0.0, 2e-3, 6.25e-10, 2.0/32768, 0.0 ) )
    >>> r.append(   ( samples, 30, 2, -7e-11, 0.0, 2e-3, 6.25e-10, 2.0/32768, 0.0 ) )
    >>> o = StringIO()
    >>> OutputTrace( r, out=o )
    >>> print( o.getvalue() )
    $#CHANNELS 2
    $SIGNED 1
    $FORMATTING DECIMAL
    $FULLSCALE 65536
    $MODEL U5303A
    $SAMPIVAL 6.25e-10
    $HORPOS -7e-11
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
    >>> mr = MultiRecord( ( samples, 32, 2, [12, 12], [0, 16], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, 2.0/32768, 0.0 ) )
    >>> mr.append(        ( samples, 32, 2, [12, 12], [1, 17], [-7e-11, -3e-11], [0.0, 0.0], [2e-3, 3e-3], 6.25e-10, 2.0/32768, 0.0 ) )
    >>> o = StringIO()
    >>> OutputTrace( mr, out=o )
    >>> print( o.getvalue() )
    $#CHANNELS 2
    $SIGNED 1
    $FORMATTING DECIMAL
    $FULLSCALE 65536
    $MODEL U5303A
    $SAMPIVAL 6.25e-10
    $HORPOS -7e-11
    -2243 3171
    3171 8093
    8093 11667
    11667 13533
    13533 13203
    13203 10973
    10973 6947
    6947 1869
    1869 -3485
    -3485 -8403
    -8403 -11933
    -11933 -13571
    <BLANKLINE>
    $#CHANNELS 2
    $SIGNED 1
    $FORMATTING DECIMAL
    $FULLSCALE 65536
    $MODEL U5303A
    $SAMPIVAL 6.25e-10
    $HORPOS -3e-11
    -1427 4019
    4019 8701
    8701 12067
    12067 13581
    13581 12979
    12979 10429
    10429 6195
    6195 1053
    1053 -4333
    -4333 -9011
    -9011 -12349
    -12349 -13667
    <BLANKLINE>
    <BLANKLINE>
    >>> o.close()
    """

    if isinstance( records, Record ):
        records = [records]
    for rec in records:
        #out.write( "$#ADCS %d\n" % adcs )
        out.write( "$#CHANNELS %d\n" % len( rec ) )
        out.write( "$SIGNED %d\n" % 1 )
        out.write( "$FORMATTING DECIMAL\n" )
        out.write( "$FULLSCALE %d\n" % 65536 )
        out.write( "$MODEL %s\n" % "U5303A" )
        out.write( "$SAMPIVAL %g\n" % rec.XIncrement )
        #out.write( "$CHANNELFSR -1\n" )
        out.write( "$HORPOS %g\n" % rec.InitialXOffset )

        for samples in zip( *rec ):
            out.write( " ".join( map( str, samples ) )+"\n" )
    
        out.write( "\n" )

    out.flush()




if __name__ == "__main__":
    import doctest
    doctest.testmod()

