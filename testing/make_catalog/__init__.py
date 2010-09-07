"""

    KeepNote
    Generate Catalog of Files

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
    name = "Make File Catalog"
    author = "Mark Saliers <throaway@yahoo.com> after Will Rouesnel"
    description = "Imports a folder tree, listing file names (maybe as links) notebook"


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
            ("Make Catalog", gtk.STOCK_ADD, "_Make Catalog...",
             "", _("Make a catalog of files"),
             lambda w: self.on_make_catalog(window,
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
                     <menuitem action="Make Catalog"/>
                 </placeholder>
               </menu>
            </menubar>
            
            <menubar name="popup_menus">
                <menu action="treeview_popup">
                    <menuitem action="Make Catalog"/>
                </menu>
            
                <menu action="listview_popup">
                    <menuitem action="Make Catalog"/>
                </menu>
            </menubar>
            </ui>
            """)


    def on_make_catalog(self, window, notebook, widget="focus"):
        """Callback from gui for making a catalog tree"""
        
        if notebook is None:
            return

        dialog = FileChooserDialog(
            "Make Catalog", window, 
            action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=("Cancel", gtk.RESPONSE_CANCEL,
                     "Make Catalog", gtk.RESPONSE_OK))        
        response = dialog.run()

        if response == gtk.RESPONSE_OK and dialog.get_filename():
            filename = unicode_gtk(dialog.get_filename())
            dialog.destroy()

            self.make_catalog(notebook, filename, 
                                    window=window, widget=widget)
        else:
            dialog.destroy()


    def make_catalog(self, notebook, filename, 
                           window=None, widget="focus"):
        if notebook is None:
            return

        # Get the node we're going to attach to
        if window is None:
            # Can't get a node, so we add to the base node
            node = notebook
        else:
            # Ask the window for the currently selected nodes
            nodes, widget = window.get_selected_nodes()
            # Use only the first
            node = nodes[0]

        try:
            generate_catalog_folders(node, filename, task=None)

            if window:
                window.set_status("Catalog Made")
            return True
    
        except NoteBookError:
            if window:
                window.set_status("")
                window.error("Error while making catalog.", 
                             e, sys.exc_info()[2])
            else:
                self.app.error("Error while making catalog.", 
                               e, sys.exc_info()[2])
            return False

        except Exception, e:
            if window:
                window.set_status("")
                window.error("unknown error", e, sys.exc_info()[2])
            else:
                self.app.error("unknown error", e, sys.exc_info()[2])
            return False


def generate_catalog_folders(node, filename, task=None):
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
    rootnode = node.new_child(CONTENT_TYPE_PAGE, os.path.basename(filename))
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
                keepnote.log_message("parent node not found '%s'.\n" % root)
                continue
            
            parent = parent2.new_child(CONTENT_TYPE_PAGE,
                                       os.path.basename(root))
            parent.set_attr("title", os.path.basename(root))
            filename2node[root] = parent

        
        # create nodes for files
        fileList = "" ;
        for shortName in files:
            #if keepnote.get_platform() is "windows":
            #    fn = "\\\\?\\" + os.path.join(root, fn)
            #else:
            #    fn = os.path.join(root, fn)

            #child = attach_file(fn, parent)
            fn = os.path.join(root,shortName)
            fileSize = os.stat(fn).st_size
            #fileTime = time.asctime(time.localtime(os.stat(fn).st_mtime))
            ft = time.localtime(os.stat(fn).st_mtime)
            fileLine = '<a href="%s">%s</a> %s %02d-%02d-%02d %02d:%02d:%02d ' % (fn,shortName,formatFileSize(fileSize),ft.tm_year,ft.tm_mon,ft.tm_mday,ft.tm_hour,ft.tm_min,ft.tm_sec)

            fileList += fileLine + "\n"  # Will be converted to <br> when page inserted
            nfilescomplete += 1
            task.set_message(("text", "Imported %i / %i files..." % 
                              (nfilescomplete, nfiles)))
            task.set_percent(float(nfilescomplete) / float(nfiles))

        make_catalog_page(parent,fileList,task)

    task.finish()
                     


def make_catalog_page(child,text,task) :
        #node, filename, index=None, task=None):
    """
    Insert a listing of files into current page

    child     -- write into this node
    text -- formatted listing of files or content to insert into page
    task     -- Task object to track progress

    filename -- filename of text file to import
    """

    # TODO: handle spaces correctly

    if task is None:
        # create dummy task if needed
        task = tasklib.Task()
    

    #child = node.new_child(notebooklib.CONTENT_TYPE_PAGE, os.path.basename(filename), index)
    #child.set_attr("title", os.path.basename(filename)) # remove for 0.6.4

    #text = open(filename).read()
    
    out = safefile.open(child.get_data_file(), "w", codec="utf-8")
    out.write(u"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"><body>""")

    #text = escape(text)
    text = text.replace(u"\n", u"<br/>")
    text = text.replace(u"\r", u"")

    out.write(text)
    out.write(u"</body></html>")

    out.close()
    task.finish()      


def formatFileSize(fileSize) :
    locale.setlocale(locale.LC_ALL, "")
    sizes = (3,2,1,0)
    sufs = ('gb','mb','kb','b')
    for bracket in sizes :
        #print "%d %d %d" % (bracket,fileSize,pow(1024,bracket) )
        if fileSize > pow(1024,bracket) or bracket==0 :
            return locale.format('%d', fileSize // pow(1024,bracket), True) + sufs[3-bracket]



