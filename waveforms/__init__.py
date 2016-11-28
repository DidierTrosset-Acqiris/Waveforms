#!/usr/bin/python3

from numpy import int16, int32, array, zeros, resize, fromfunction, sqrt, arctan2
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
    
    DDCMultiRecord is a specialized version of MultiRecord handling DDC data retreived
    using the DDCCore fetch functions. They should be used the same way as MuiltRecord.

    The waveform objects accessed through the Record and MultiRecord classes all provide the
    usual properties of IVI Digitizer waveforms: Samples, ActualPoints, InitialXOffset,
    InitialXTimeSeconds, InitialXTimeFraction, XIncrement, ScaleFactor, and ScaleOffset.
    
"""

if __name__ == "__main__":
    import doctest
    doctest.IGNORE_EXCEPTION_DETAIL = True
    import singlerecord
    doctest.testmod( singlerecord )
    import multirecord
    doctest.testmod( multirecord )
    import ddcrecord
    doctest.testmod( ddcrecord )
    import accumulatedrecord
    doctest.testmod( accumulatedrecord )

else:
    from .singlerecord import Record
    from .multirecord import MultiRecord
    from .ddcrecord import DDCMultiRecord
    from .accumulatedrecord import AccMultiRecord


