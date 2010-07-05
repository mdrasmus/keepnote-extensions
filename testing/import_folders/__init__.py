"""

    KeepNote
    Import folder structure extension

"""
from keepnote.timestamp import get_timestamp

#
#  KeepNote
#  Copyright (c) 2008-2009 Matt Rasmussen
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
import mimetypes
import os
import sys
import time
import shutil
import urllib
import urlparse
import urllib2
import xml.dom
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
    CONTENT_TYPE_DIR, NODE_META_FILE, NoteBookNodeMetaData
from keepnote import notebook as notebooklib
from keepnote import tasklib
from keepnote.gui import extension

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
    
    version = (0, 1)
    name = "Import Folder Tree"
    author = "Will Rouesnel <electricitylikesme@hotmail.com>"
    description = "Imports a folder tree as nodes in a notebook"


    def __init__(self, app):
        """Initialize extension"""
        
        extension.Extension.__init__(self, app)
        self.app = app

        self._ui_id = {}
        self._action_groups = {}


    def get_depends(self):
        return [("keepnote", ">=", (0, 6, 1))]


    def on_add_ui(self, window):
        """Initialize extension for a particular window"""

        # TODO: ACTION GROUP MUST BE PER WINDOW
        # add menu options
        self._action_groups[window] = gtk.ActionGroup("MainWindow")
        self._action_groups[window].add_actions([
            ("Import Folder", gtk.STOCK_ADD, "_Attach Folder...",
             "", _("Attach a folder and its contents to the notebook"),
             lambda w: self.on_import_folder_tree(window,
                                               window.get_notebook())),
            ])
        window.get_uimanager().insert_action_group(
            self._action_groups[window], 0)
        
        # TODO: Fix up the ordering on the affected menus.
        self._ui_id[window] = window.get_uimanager().add_ui_from_string(
            """
            <ui>
            <menubar name="main_menu_bar">
               <menu action="Edit">
                 <placeholder name="Viewer">
                     <menuitem action="Import Folder"/>
                 </placeholder>
               </menu>
            </menubar>
            
            <menubar name="popup_menus">
                <menu action="treeview_popup">
                    <menuitem action="Import Folder"/>
                </menu>
            
                <menu action="listview_popup">
                    <menuitem action="Import Folder"/>
                </menu>
            </menubar>
            </ui>
            """)


    def on_import_folder_tree(self, window, notebook, widget="focus"):
        """Callback from gui for importing a folder tree"""
        
        if notebook is None:
            return

        dialog = gtk.FileChooserDialog("Attach Folder", window, 
            action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=("Cancel", gtk.RESPONSE_CANCEL,
                     "Attach Folder", gtk.RESPONSE_OK))
        
        response = dialog.run()

        if response == gtk.RESPONSE_OK and dialog.get_filename():
            filename = unicode_gtk(dialog.get_filename())
            
            dialog.destroy()

            self.import_folder_tree(notebook, filename, window=window, widget=widget)
        else:
            dialog.destroy()


    def import_folder_tree(self, notebook, filename, window=None, widget="focus"):
        if notebook is None:
            return

        if window:
            import_folder(notebook, filename, window, task=None, widget=widget)

            # check exceptions
            try:
                window.set_status("Folder imported.")
                return True

            except NoteBookError:
                window.set_status("")
                window.error("Error while importing folder.")
                return False

            except Exception:
                window.set_status("")
                window.error("unknown error")
                return False

        else:
            import_folder(notebook, filename, window=window, task=None, widget=widget)

def import_folder(notebook, filename, window=None, task=None, widget="focus"):
    """Import a folder tree as a subfolder of the current item

       filename -- filename of folder to import
    """

    if task is None:
        # create dummy task if needed
        task = tasklib.Task()
    
    # Determine number of files in advance so we can have a progress bar
    nfiles = 0
    for root, dirs, files in os.walk(filename):
        nfiles += len(files) # Add files found in current dir
        task.set_message(("text", "Found %i files..." % nfiles))
    
    # Get the node we're going to attach to
    node = None
    if window is None:
        # Can't get a node, so we add to the base node
        node = notebook.get_node_by_id(notebook.get_universal_root_id())
    else:
        # Ask the window for the currently selected nodes
        nodes, widget = window.get_selected_nodes(widget)
        # Use only the first
        node = nodes[0]
    
    # Make sure initial child is none
    child = None
    nfilescomplete = 0 # updates progress bar
    
    # Make a node based on the root - so we have an origin to import to
    new_filename = os.path.basename(filename)
    path = notebooklib.get_valid_unique_filename(node.get_path(), new_filename)    
    child = notebook.new_node(CONTENT_TYPE_DIR,
                              path,
                              node,
                              {"title": new_filename})
    child.create()
    node.add_child(child)
    child.save(True)
    
    node = child
    rootnode = node
    
    # TODO: Exceptions, intelligent error handling, deep paths
    # DONE? Deep paths are handled by unicode "\\?\" extension to filename. Does this break in Linux?
    # Walk directory we're importing and create nodes
    for root, dirs, files in os.walk(filename):
        # Get the relative path of the directory
        #new_filename = os.path.relpath(root, filename)
        new_filename = root[len(filename)+1:]
        
        # Don't do anything if we're root, otherwise make the node directories
        if len(new_filename) is not 0:
            path = notebooklib.get_unique_filename(rootnode.get_path(), new_filename)
            
            # Parent node will be in the root of path directory, read it off the disk
            ParentNodeMeta = NoteBookNodeMetaData() # Initialize a meta-data object
            tail, head = os.path.split(path)
            ParentNodeMeta.read( os.path.join(tail, NODE_META_FILE), notebook.notebook_attrs )
            
            node = notebook.get_node_by_id(ParentNodeMeta.attr.get("nodeid"))        
            
            # Make a node directory
            child = notebook.new_node(CONTENT_TYPE_DIR,
                                      path,
                                      node,
                                      {"title": os.path.basename(new_filename)})
            child.create()
            node.add_child(child)
            child.save(True)
        
        for file in files:
            # Get relative path of the file
            #new_filename = os.path.relpath(os.path.join(root, file), filename)
            new_filename = os.path.join(root, file)[len(filename)+1:]
            
            path = notebooklib.get_unique_filename(rootnode.get_path(), new_filename)
            
            content_type = mimetypes.guess_type(os.path.join(root, file))[0]
            if content_type is None:
                content_type = "application/octet-stream"
            
            # Parent node will be 1 dir down, read it off the disk
            ParentNodeMeta = NoteBookNodeMetaData() # Initialize a meta-data object
            tail, head = os.path.split(path)
            ParentNodeMeta.read( os.path.join(tail, NODE_META_FILE), notebook.notebook_attrs )
            
            node = notebook.get_node_by_id(ParentNodeMeta.attr.get("nodeid"))  
            
            # Make a node directory
            child = notebook.new_node(
                    content_type, 
                    path,
                    node,
                    {"payload_filename": new_filename,
                     "title": os.path.basename(new_filename)})
            child.create()
            node.add_child(child)
            if keepnote.get_platform() is "windows":
                child.set_payload( "\\\\?\\" + os.path.join(root, file) )
            else:
                child.set_payload(os.path.join(root, file))
            child.save(True)
            
            #Commented out coz we don't use them anyway currently
            #task.set_message(("text", "Imported %i // %i files..." % nfilescomplete % nfiles))
            #task.set_percent(float(nfilescomplete) / float(nfiles))

    if task:
        task.finish()
                     
        