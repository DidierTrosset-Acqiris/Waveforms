Waveforms: Digitizer recordings processing library
==================================================

Waveforms is a Python module enabling digitizer's waveforms analysis,
filtering, serializing and imaging. Its high-level API is designed to enable
complex processing on multiple records, multiple channels digitizer data,
either live or recorded.

Use cases
=========

* Storing waveforms recorded from multiple digitizer channels.
* Calculating whole recording or sliding sine fits on waveforms.
* Calculating and plotting channel-to-channel skews.
* Reading previously stored recordings to apply new filters.

Goals
=====

Storing an entire frequency sweep in a single file
--------------------------------------------------

for frequency in [list of frequencies]:
    # Set generator to frequency
    InitiateAcquisition( vi )
    WaitForAcquisitionComplete( vi, 2000 )
    record = SingleRecord( SineFreq=frequency )
    for channel in [list of channels]:
        record.append( FetchWaveformInt16( vi, channel, ... ) )
    WriteTrace( record )

Ther resulting file will contain as many records as have been recorded, one
for every frequency. Each record containing as many channels as fetched.

Displaying waveforms
--------------------

display = WaveformDisplay()
InitiateAcquisition( vi )
WaitForAcquisitionComplete( vi, 2000 )
record = SingleRecord()
for channel in [list of channels]:
    record.append( FetchWaveformInt16( vi, channel ) )
display.show( record )

Fetch multiple channels at a glance
-----------------------------------

record = FetchSingleRecord( vi, ["Channel1", "Channel2"], 1000 )
records = FetchMultiRecords( vi, ["Channel1", "Channel2"], 0, 100, 1000 )
records = FetchDDCRecords( vi, ["DDCCore1", "DDCCore2"], 0, 100, 1000 )
records = FetchAccumulatedRecords( vi, ["DDCCore1", "DDCCore2"], 0, 1, 1000 )

The trace file format
=====================

A trace file is a text file that contains waveforms, or more generally arrays
of successive values. A trace file starts by a number of lines starting with
a dollar sign '$' describing attributes of the values. Then, every line
contains the same number of numeric fields representing the values. An empty
line denotes the end of a waveform. A new waveform can start on the next line.

Waveform traces
---------------

Waveform traces represent the numeric values returned by a digitizer. The
attributes in the header show the standard IVI-C fields of a waveform. Then,
each line of values contains the sample values of the choosen channels.

