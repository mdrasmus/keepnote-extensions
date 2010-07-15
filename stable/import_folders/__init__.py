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
    CONTENT_TYPE_DIR, attach_file
from keepnote import notebook as notebooklib
from keepnote import tasklib
from keepnote.gui import extension, FileChooserDialog

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
    
    version = (0, 2)
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
        return [("keepnote", ">=", (0, 6, 3))]


    def on_add_ui(self, window):
        """Initialize extension for a particular window"""
        
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


    def on_import_folder_tree(self, window, notebook):
        """Callback from gui for importing a folder tree"""
        
        # Ask the window for the currently selected nodes
        nodes = window.get_selected_nodes()
        if len(nodes) > 0:
            return
        node = nodes[0]


        dialog = FileChooserDialog(
            "Attach Folder", window, 
            action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=("Cancel", gtk.RESPONSE_CANCEL,
                     "Attach Folder", gtk.RESPONSE_OK))        
        response = dialog.run()

        if response == gtk.RESPONSE_OK and dialog.get_filename():
            filename = unicode_gtk(dialog.get_filename())
            dialog.destroy()

            self.import_folder_tree(notde, filename, window=window)
        else:
            dialog.destroy()


    def import_folder_tree(self, node, filename, window=None):
        try:
            import_folder(node, filename, task=None)

            if window:
                window.set_status("Folder imported.")
            return True
    
        except NoteBookError:
            if window:
                window.set_status("")
                window.error("Error while importing folder.", 
                             e, sys.exc_info()[2])
            else:
                self.app.error("Error while importing folder.", 
                               e, sys.exc_info()[2])
            return False

        except Exception, e:
            if window:
                window.set_status("")
                window.error("unknown error", e, sys.exc_info()[2])
            else:
                self.app.error("unknown error", e, sys.exc_info()[2])
            return False



def import_folder(node, filename, task=None):
    """
    Import a folder tree as a subfolder of the current item

    node     -- node to attach folder to
    filename -- filename of folder to import
    task     -- Task object to track progress
    """

    # TODO: Exceptions, intelligent error handling
    # For windows: 
    # Deep paths are handled by unicode "\\?\" extension to filename.


    if task is None:
        # create dummy task if needed
        task = tasklib.Task()
    

    # Determine number of files in advance so we can have a progress bar
    nfiles = 0
    for root, dirs, files in os.walk(filename):
        nfiles += len(files) # Add files found in current dir
        task.set_message(("text", "Found %i files..." % nfiles))


    # Make a node based on the root - so we have an origin to import to
    rootnode = node.new_child(CONTENT_TYPE_DIR, os.path.basename(filename))
    rootnode.set_attr("title", os.path.basename(filename))
    filename2node = {filename: rootnode}
    


    nfilescomplete = 0 # updates progress bar


    # Walk directory we're importing and create nodes
    for root, dirs, files in os.walk(filename):
        
        # create node for directory
        if root == filename:
            parent = rootnode
        else:
            parent2 = filename2node.get(os.path.dirname(root), None)
            if parent2 is None:
                continue
            
            parent = parent2.new_child(CONTENT_TYPE_DIR,
                                       os.path.basename(root))
            parent.set_attr("title", os.path.basename(root))
            filename2node[root] = parent

        
        # create nodes for files
        for fn in files:
            if keepnote.get_platform() is "windows":
                fn = "\\\\?\\" + os.path.join(root, fn)
            else:
                fn = os.path.join(root, fn)
            child = attach_file(fn, parent)
            
            nfilescomplete += 1
            task.set_message(("text", "Imported %i / %i files..." % 
                              (nfilescomplete, nfiles)))
            task.set_percent(float(nfilescomplete) / float(nfiles))

    task.finish()
                     
        
