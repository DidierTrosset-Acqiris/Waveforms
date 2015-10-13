#!/usr/bin/python3


from tkinter import *
from tkinter import ttk
from sys import stdout
import json


class EntryWithSpins( ttk.Frame ):

    def _DnValue( self ):
        self.textvariable.set( str( int( self.textvariable.get() )-1 ) )

    def _UpValue( self ):
        self.textvariable.set( str( int( self.textvariable.get() )+1 ) )

    def __init__( self, parent, textvariable, *args, **kwargs ):
        ttk.Frame.__init__( self, parent )
        self.textvariable = textvariable
        self.text = ttk.Entry( self, textvariable=textvariable, *args, **kwargs )
        self.spup = ttk.Button( self, text="up", command=self._UpValue)
        self.spdn = ttk.Button( self, text="dn", command=self._DnValue)
        self.spup.pack(side="right", fill="y")
        self.spdn.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        # expose some text methods as methods on this object
        self.insert = self.text.insert
        self.delete = self.text.delete
        self.get = self.text.get
        self.index = self.text.index

def Apply(*args):
    try:
        records = int( records_var.get() )
        samples = int( samples_var.get() )
        json.dump( { "records":records, "samples":samples }, fp=stdout )
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
samples_var = StringVar()
samples_var.set( "200" )

records_entry = ttk.Entry( mainframe, width=7, textvariable=records_var )
records_entry.grid( column=2, row=1, sticky=( W, E ) )

samples_entry = EntryWithSpins( mainframe, width=7, textvariable=samples_var )
samples_entry.grid( column=2, row=2, sticky=( W, E ) )

ttk.Button( mainframe, text="Apply", command=Apply ).grid( column=3, row=3, sticky=W )

ttk.Label( mainframe, text="Records" ).grid( column=1, row=1, sticky=W )
ttk.Label( mainframe, text="Samples" ).grid( column=1, row=2, sticky=E )

for child in mainframe.winfo_children():
    child.grid_configure( padx=5, pady=5 )

records_entry.focus()
root.bind('<Return>', Apply)

root.mainloop()

