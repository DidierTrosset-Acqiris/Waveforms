#!/usr/bin/python3


from tkinter import *
from tkinter import ttk
from sys import stdout
import json


def Scale125():
    for power in range( 12 ):
        for mantissa in [1, 2, 5]:
            yield mantissa*( 10**power )


class EntryWithSpins( ttk.Frame ):

    def _DnValuePM( self ):
        self.textvariable.set( str( int( self.textvariable.get() )-1 ) )

    def _UpValuePM( self ):
        self.textvariable.set( str( int( self.textvariable.get() )+1 ) )

    def _DnValue125( self ):
        value = int( self.textvariable.get() )
        previousScale = 1
        for scale in Scale125():
            if scale<value:
                previousScale = scale
                continue
            self.textvariable.set( str( previousScale ) )
            return

    def _UpValue125( self ):
        value = int( self.textvariable.get() )
        for scale in Scale125():
            if scale>value:
                self.textvariable.set( str( scale ) )
                return

    def __init__( self, parent, textvariable, *args, **kwargs ):
        ttk.Frame.__init__( self, parent )
        self.textvariable = textvariable
        if "mode" in kwargs and kwargs["mode"]=="125":
            del kwargs["mode"]
            _DnValue = self._DnValue125
            _UpValue = self._UpValue125
        else:
            _DnValue = self._DnValuePM
            _UpValue = self._UpValuePM
        self.spdn = ttk.Button( self, text="-", width=1, command=_DnValue)
        self.text = ttk.Entry( self, justify="right", textvariable=textvariable, *args, **kwargs )
        self.spup = ttk.Button( self, text="+", width=1, command=_UpValue)
        self.spdn.pack( side="left", fill="y",    expand=False )
        self.text.pack( side="left", fill="both", expand=True  )
        self.spup.pack( side="left", fill="y",    expand=False )

        # expose some text methods as methods on this object
        self.insert = self.text.insert
        self.delete = self.text.delete
        self.get = self.text.get
        self.index = self.text.index


def Apply(*args):
    try:
        records = int( records_var.get() )
        samples = int( samples_var.get() )
        offset = int( offset_var.get() )
        fscale = int( fscale_var.get() )
        json.dump( { "records":records, "samples":samples, "vertical_offset":offset, "vertical_range":fscale }, fp=stdout )
        stdout.write( "\n" )
        stdout.flush()
    except ValueError:
        pass
    

root = Tk()
root.title("Module Control")

mainframe = ttk.Frame( root, padding="3 3 12 12" )
mainframe.grid( column=0, row=0, sticky=( N, W, E, S ) )
mainframe.columnconfigure( 0, weight=1 )
mainframe.rowconfigure( 0, weight=1 )

records_var = StringVar()
records_var.set( "1" )
records_var.trace( "w", Apply )
samples_var = StringVar()
samples_var.set( "100" )
samples_var.trace( "w", Apply )

records_entry = EntryWithSpins( mainframe, width=8, textvariable=records_var )
records_entry.grid( column=1, row=1, sticky=( W, E ) )

samples_entry = EntryWithSpins( mainframe, width=12, mode="125", textvariable=samples_var )
samples_entry.grid( column=1, row=2, sticky=( W, E ) )

ttk.Label( mainframe, text="Records" ).grid( column=0, row=1, sticky=W )
ttk.Label( mainframe, text="Samples" ).grid( column=0, row=2, sticky=E )

offset_var = StringVar()
offset_var.set( "0" )
offset_var.trace( "w", Apply )
fscale_var = StringVar()
fscale_var.set( "2" )
fscale_var.trace( "w", Apply )

offset_entry = EntryWithSpins( mainframe, width=8, textvariable=offset_var )
offset_entry.grid( column=3, row=1, sticky=( W, E ) )

fscale_entry = EntryWithSpins( mainframe, width=12, mode="125", textvariable=fscale_var )
fscale_entry.grid( column=3, row=2, sticky=( W, E ) )

ttk.Label( mainframe, text="Offset" ).grid( column=2, row=1, sticky=W )
ttk.Label( mainframe, text="Range " ).grid( column=2, row=2, sticky=E )

ttk.Button( mainframe, text="Apply", command=Apply ).grid( column=0, columnspan=4, row=3, sticky=E )

for child in mainframe.winfo_children():
    child.grid_configure( padx=5, pady=5 )

records_entry.focus()
root.bind('<Return>', Apply)

root.mainloop()

