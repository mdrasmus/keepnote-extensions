"""

    KeepNote
    Paste text and images into Keepnote page as they are copied into system clipboard

"""
from keepnote.timestamp import get_timestamp


#
#  KeepNote
#  Copyright (c) 2008-2011 Matt Rasmussen
#  Author: Matt Rasmussen <rasmus@mit.edu>
#  import_folder extension by: Will Rouesnel <electricitylikesme@hotmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.
#


# python imports
import codecs
import gettext
import locale
import mimetypes
import os
import sys
import time
import shutil
import urllib
import urlparse
import urllib2
import xml.dom
import thread # MAS
from xml.dom import minidom
from xml.sax.saxutils import escape


_ = gettext.gettext


# pygtk imports
import pygtk
pygtk.require('2.0')
from gtk import gdk
import gtk.glade
import gobject

# keepnote imports
import keepnote
from keepnote import unicode_gtk
from keepnote.notebook import NoteBookError, get_valid_unique_filename,\
    CONTENT_TYPE_PAGE, CONTENT_TYPE_DIR
# attach_file
from keepnote import notebook as notebooklib
from keepnote import tasklib, safefile 
from keepnote.gui import extension, FileChooserDialog
from keepnote.gui import dialog_wait
# imports needed to send clipboard directly to KN
from keepnote.gui.three_pane_viewer import ThreePaneViewer
from keepnote.gui.tabbed_viewer import TabbedViewer 


 
# pygtk imports
try:
    import pygtk
    pygtk.require('2.0')
    from gtk import gdk
    import gtk.glade
    import gobject
except ImportError:
    # do not fail on gtk import error,
    # extension should be usable for non-graphical uses
    pass



class Extension (extension.Extension):
    
    def __init__(self, app):
        """Initialize extension"""
        
        extension.Extension.__init__(self, app)
        self.app = app


    def get_depends(self):
        return [("keepnote", ">=", (0, 7, 1))]


    def on_add_ui(self, window):
        """Initialize extension for a particular window"""

        # add menu options
        self.add_action(
            window, "Activate Pasteboard", "_Pasteboard...",
            lambda w: self.on_activate_clipboard(window, window.get_notebook()),
            tooltip=_("Capture clipboard activity"),
            stock_id=gtk.STOCK_ADD)

        #lambda w: self.on_activate_clipboard(window, window.get_notebook(),debug)),
        
        self.add_ui(window,
            """
            <ui>
            <menubar name="main_menu_bar">
               <menu action="Edit">
                 <placeholder name="Viewer">
                     <menuitem action="Activate Pasteboard"/>
                 </placeholder>
               </menu>
            </menubar>
            
            <menubar name="popup_menus">
                <menu action="treeview_popup">
                    <menuitem action="Activate Pasteboard"/>
                </menu>
            
                <menu action="listview_popup">
                    <menuitem action="Activate Pasteboard"/>
                </menu>
            </menubar>
            </ui>
            """)


    def on_activate_clipboard(self, window, node):
        """Callback from gui verifying desire to start clipboard capture"""
        #debug.write("on_activate_ui/top\n")
        #= window.get_notebook()
        #if node is None :
        #  debug.write("node status sent OAC is None\n")
        #else :
        #  debug.write("node status sent OAC was NOT None\n")

        if Pannier.pannier :
            pkg = Pannier.pannier
            #debug.write("Using old package\n")
        else :
            pkg = Pannier(window, node, data="starting")
            Pannier.pannier = pkg
            #debug.write("just made package\n")

        #if notebook is None:
        # if pkg.data is None :
        #    debug.write("package data has disappeared!\n")
        # else :
        #    debug.write("I see package data " + pkg.data)

        if pkg.node is None:
            #debug.write("node status in pkg is None\n")
            return

        #debug.write("About to choose files??")

        #debug.write(result)
        
        if pkg.paste_activated:
            result = self.app.ask_yes_no("Deactivate pasteboard?", 
                                         "Pasteboard Activation", window)
            if result:
                pkg.paste_activated = False
            return
        else:
            result = self.app.ask_yes_no("Activate pasteboard?", 
                                         "Pasteboard Activation", window)
            if result:
                pkg.paste_activated = True
                self.activate_clipboard(pkg)
          
        #if result :
        # dialog = FileChooserDialog(
        #     "Activate Clipboard", window, 
        #     action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
        #     buttons=("Cancel", gtk.RESPONSE_CANCEL,
        #              "Activate Clipboard", gtk.RESPONSE_OK))        
        #response = dialog.run()
        #
        # if response == gtk.RESPONSE_OK : #and dialog.get_filename():
        #     #filename = unicode_gtk(dialog.get_filename())
        #     dialog.destroy()
        #
        #   self.activate_clipboard(pkg)
        # else:
        #     pass # DEBUG: May not need the else with yes/no dialog?
        #     #dialog.destroy()


    def activate_clipboard(self, pkg):

        #if notebook is None:
        #    return

        # Get the node we're going to write to
        if pkg.window is None:
            # Can't get a node, so we add to the base node
            node = pkg.node #notebook
            #debug.write("Couldn't see window")
        else:
            # Ask the window for the currently selected nodes
            #nodes = pkg.window.get_selected_nodes('focus')
            nodes = pkg.window.get_selected_nodes()
            # Use only the first
            node = nodes[0]
            #debug.write("Class is before : " + node.__class__.__name__ + "\n")
            pkg.node = node #node[0]
            #debug.write("Class is after : " + pkg.node.__class__.__name__ + "\n")
            #debug.write("Getting node from selected nodes\n")
            #debug.write("The data file is " + pkg.node.get_data_file() + "\n" )

        try:
            #activate_clipboard_capture(pkg)
            gobject.timeout_add(1000, clipboard_capture_thread,  pkg)
            #pkg.clipboard.request_text(clipboard_text_received,pkg)
            if pkg.window:
                pkg.window.set_status("Capture Activated")

            return True  
    
        except NoteBookError:
            #debug.write("Notebookerror\n")
            if pkg.window:
                pkg.window.set_status("")
                pkg.window.error("NBE/win error while activating clipboard capture (1).", 
                             e, sys.exc_info()[2])
            else:
                self.app.error("NBE/app error while activating clipboard capture (2).", 
                               e, sys.exc_info()[2])
            return False

        except Exception, e:
            #debug.write("unk error\n")
            if pkg.window:
                pkg.window.set_status("")
                pkg.window.error("unknown error", e, sys.exc_info()[2])
            else:
                self.app.error("unknown error", e, sys.exc_info()[2])
            return False


def clipboard_capture_thread(pkg):
    if pkg.paste_activated:
        #if pkg.counter < 20 : # Debug to prevent runaway situation
        #pkg.clipboard.request_text(clipboard_text_received,pkg)
        gtk.gdk.threads_enter()
        insert_clipboard_page(pkg)
        gtk.gdk.threads_leave()
        return True
    else:
        return False

  
def insert_clipboard_page(pkg) :
    #debug.write("Inside of ICP\n")
    #if pkg.textview is None :
    #if pkg.editor is None :

    main_viewer = pkg.window.get_viewer() 
    #debug.write("ICP - I seem to have gotten viewer\n")
    #debug.write("main viewer class is: " + main_viewer.__class__.__name__ + "\n")
    textview = None
    if isinstance(main_viewer, TabbedViewer):
        viewer = main_viewer.get_current_viewer() 
        if isinstance(viewer, ThreePaneViewer):    
            try: 
                textview = viewer.editor._editor.get_textview() 
            except:
                pass
                #debug.write("Exception getting textview\n")
    if textview is None:
        return
    

    #debug.write("viewer class is: " + viewer.__class__.__name__ + "\n")
    try: 
        #textview.emit("paste-clipboard") # DEBUG
        
        #debug.write("Trying ...")
        if pkg.clipboard.wait_is_text_available():
            #debug.write(" text\n")
            last_text = pkg.clipboard.wait_for_text()

            
            if last_text and last_text != pkg.last_text:
                #debug.write("trying to get textview\n")
                #textview = viewer.editor._editor.get_textview() 
                #debug.write("got textview. Trying emit\n") 
                #textview.emit("paste-clipboard")
                textview.get_textbuffer().insert_at_cursor(last_text)
                #debug.write("Thinks its done emit\n")
                #pkg.clipboard.set_text("\n\n")
                #textview.emit("paste-clipboard")
                #pkg.clipboard.set_text(last_text)
                pkg.last_text = last_text
                #pkg.clipboard.clear()
                #pkg.clipboard.set_text("ZZZ")
        else:
            return
            #elif pkg.clipboard.wait_is_image_available() :
            #debug.write(" text\n")
            #textview = viewer.editor._editor.get_textview() 
            textview.emit("paste-clipboard")
            pkg.clipboard.set_text("\n\n")
            textview.emit("paste-clipboard")
            pkg.last_text = "\n\n"

    except:
        #debug.write("Some error trying to emit clipboard\n") 
        #raise
        keepnote.log_error()
        pass



#debug = open("c:/Program Files/KeepNote/extensions/capture_clipboard/debug.txt","w")
#debug.write("beginning log\n")
# (query-replace-regexp "^\s*debug" "#debug" nil nil)
class Pannier :
    """
    Pannier class
    I would have like to make this a singleton, but Python
    is too #!@$ clumsy to allow that.
    PARMS: window, node, data (string), debug (file name)
    MAS 2011-02-21
    """
    pannier = None # Calling program has to be smart enough to set this 
    #data = "orig"
    #stage = 0
    def __init__(self,window,node,data) :
        #debug.write("Inside init\n")
        #Pannier.stage += 1
        #Pannier.pannier = Pannier(window,node,data)
        #elif Pannier.stage == 1 :
        #debug.write("Inside stage 1\n")
        #Pannier.stage += 1
        #self.debug = open(debug,"w")
        self.window = window
        self.node = node
        #if self.node is None :
          #debug.write("Node passed seems to be none\n")
        #else :
          #debug.write("Node received seems to be NOT none\n")
        self.data = data
        #else :
        #debug.write("Somehow in final stage of pannier creation!\n")
        #self.debug = Pannier.pannier.debug
        #self.window = Pannier.pannier.window
        #self.node = Pannier.pannier.node
        #self.data = Pannier.pannier.data
        self.clipboard = gtk.clipboard_get("CLIPBOARD") #gtk.gdk.SELECTION_CLIPBOARD)
        self.clipboard.set_text("")
        self.counter = 0
        self.last_text = "" # Keeps track of last text pulled from clipboard
        self.paste_activated = False
        self.textview = None
        self.editor = None 

    def inc(self) :
        self.counter += 1
        return self.counter

