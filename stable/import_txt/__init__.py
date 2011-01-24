"""

    KeepNote
    Import plain text files extension

"""

#
#  KeepNote
#  Copyright (c) 2008-2010 Matt Rasmussen
#  Author: Matt Rasmussen <rasmus@mit.edu>
#  import_folder extension by: Will Rouesnel <electricitylikesme@hotmail.com>
#                              Matt Rasmussen <rasmus@mit.edu>
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
import re
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
            ("Import Txt", None, _("Import _Txt..."),
             "", _("Import plain text files to the notebook"),
             lambda w: self.on_import_txt(window, window.get_notebook())),
            ])
        window.get_uimanager().insert_action_group(
            self._action_groups[window], 0)
        
        # TODO: Fix up the ordering on the affected menus.
        self._ui_id[window] = window.get_uimanager().add_ui_from_string(
            """
            <ui>
            <menubar name="main_menu_bar">
               <menu action="File">
                 <menu action="Import">
                     <menuitem action="Import Txt"/>
                 </menu>
               </menu>
            </menubar>
            </ui>
            """)

    def on_remove_ui(self, window):

        # remove option
        window.get_uimanager().remove_action_group(self._action_groups[window])
        del self._action_groups[window]
        
        window.get_uimanager().remove_ui(self._ui_id[window])
        del self._ui_id[window]



    def on_import_txt(self, window, notebook):
        """Callback from gui for importing a plain text file"""
        
        # Ask the window for the currently selected nodes
        nodes = window.get_selected_nodes()
        if len(nodes) == 0:
            return
        node = nodes[0]
        if isinstance(node, list):
            node = node[0] # remove for keepnote 0.6.4


        dialog = FileChooserDialog(
            "Import Plain Text", window, 
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=("Cancel", gtk.RESPONSE_CANCEL,
                     "Import", gtk.RESPONSE_OK))
        dialog.set_select_multiple(True)
        response = dialog.run()

        if response == gtk.RESPONSE_OK and dialog.get_filenames():
            filenames = map(unicode_gtk, dialog.get_filenames())
            dialog.destroy()

            self.import_plain_text(node, filenames, window=window)
        else:
            dialog.destroy()


    def import_plain_text(self, node, filenames, window=None):
        try:
            for filename in filenames:
                import_txt(node, filename, task=None)

            if window:
                window.set_status("Text files imported.")
            return True
    
        except NoteBookError:
            if window:
                window.set_status("")
                window.error("Error while importing plain text files.", 
                             e, sys.exc_info()[2])
            else:
                self.app.error("Error while importing plain text files.", 
                               e, sys.exc_info()[2])
            return False

        except Exception, e:
            if window:
                window.set_status("")
                window.error("unknown error", e, sys.exc_info()[2])
            else:
                self.app.error("unknown error", e, sys.exc_info()[2])
            return False



def import_txt(node, filename, index=None, task=None):
    """
    Import a text file into the notebook

    node     -- node to attach folder to
    filename -- filename of text file to import
    task     -- Task object to track progress
    """

    # TODO: handle spaces correctly

    if task is None:
        # create dummy task if needed
        task = tasklib.Task()
    

    child = node.new_child(notebooklib.CONTENT_TYPE_PAGE, 
                           os.path.basename(filename), index)
    child.set_attr("title", os.path.basename(filename)) # remove for 0.6.4

    lines = open(filename).readlines()
    
    out = safefile.open(child.get_data_file(), "w", codec="utf-8")
    out.write(u"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"><body>""")

    lines = [escape_whitespace(escape(line)) for line in lines]
    text = "".join(lines)

    # replace newlines
    text = text.replace(u"\n", u"<br/>")
    text = text.replace(u"\r", u"")

    out.write(text)
    out.write(u"</body></html>")

    out.close()
    task.finish()
                     

def escape_whitespace(line):
    """Escape white space for an HTML line"""

    line2 = []
    it = iter(line)

    # replace leading spaces
    for c in it:
        if c == " ":
            line2.append("&nbsp;")
        else:
            line2.append(c)
            break

    # replace multi-spaces
    for c in it:
        if c == " ":
            line2.append(" ")
            for c in it:
                if c == " ":
                    line2.append("&nbsp;")
                else:
                    line2.append(c)
                    break
        else:
            line2.append(c)

    return "".join(line2)
    


if __name__ == "__main__":
    
    text = ("  hello\n" 
            "there & hi a  word here    \n"
            "  ab  wer   123\n").split("\n")


    for line in text:
        line = escape(line)
        line = escape_whitespace(line)
        
        print line
