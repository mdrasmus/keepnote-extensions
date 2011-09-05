"""

    KeepNote
    Create node/s from selected text
    (originally import_txt)

"""

#
# KeepNote
# Copyright (c) 2008-2011 Matt Rasmussen
# Author: Matt Rasmussen <rasmus@mit.edu>
# text2nodes extension by: Derek O'Connell <doconnel@gmail.com>
#   (originally import_txt)
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
from keepnote.notebook import NoteBookError, get_valid_unique_filename,CONTENT_TYPE_DIR, attach_file
from keepnote import notebook as notebooklib
from keepnote import tasklib, safefile
from keepnote.gui import extension, FileChooserDialog

#from keepnote import log_error

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
        
        self._widget_focus = {}
        self._set_focus_id = {}
        
        extension.Extension.__init__(self, app)
        
        #self.enabled.add(self.on_enabled)


    def get_depends(self):
        return [("keepnote", ">=", (0, 7, 1))]


    def on_add_ui(self, window):
        """Initialize extension for a particular window"""
        
        # Preferably a context menu option in app's textview but
        # for now just any regular menu...

        # add menu options
        self.add_action(
            window, "Text2Nodes", _("Text2Nodes"),
            lambda w: self.on_text2nodes(window),
            tooltip=_("Create Node/s from highlighted text"))
        
        # TODO: Fix up the ordering on the affected menus.
        self.add_ui(window,
            """
            <ui>
            <menubar name="main_menu_bar">
               <menu action="Tools">
                 <menuitem action="Text2Nodes"/>
               </menu>
            </menubar>
            </ui>
            """)

        # list to focus events from the window
        self._set_focus_id[window] = window.connect("set-focus", self._on_focus)


    def on_remove_ui(self, window):
        
        extension.Extension.on_remove_ui(self, window)
        
        # disconnect window callbacks
        window.disconnect(self._set_focus_id[window])
        del self._set_focus_id[window]


    def _on_focus(self, window, widget):
        """Callback for focus change in window"""
        self._widget_focus[window] = widget


    def on_text2nodes(self, window):
        """Callback from gui for text2nodes"""
        
        # Assert focus is textview
        # Assert textview has selected text
        # Get current node
        # For each line of selected text create child page

        #nb = window.get_notebook()

        widget = self._widget_focus.get(window, None)
        if not isinstance(widget, gtk.TextView):
            keepnote.log_error("T2N: focus")
            return

        # For testing simply duplicate at end of page
        
        #eop = buf.get_end_iter()
        #buf.insert(eop, '\n>>>PAGE END\n')
        #return

        buf = widget.get_buffer()
        bounds = buf.get_selection_bounds()
        if not bounds:
            return

        txt = unicode_gtk(buf.get_text(bounds[0], bounds[1]))

        # Ask the window for the currently selected nodes
        nodes = window.get_selected_nodes()
        if len(nodes) == 0:
            return
        node = nodes[0]

        task = tasklib.Task()
        
        # For testing simply duplicate at end of page
        for title in txt.splitlines():
            title = title.strip()
            if title != '':
                #eop = buf.get_end_iter()
                #buf.insert(eop, '\n>>>\n'+txt)
                self.make_page(node, title, '')

        task.finish()


    def make_page(self, parent_node, title, text):
        """
        """

        child = parent_node.new_child(notebooklib.CONTENT_TYPE_PAGE, title, None)
        #child.set_attr("title", l) # remove for 0.6.4


        # TODO: handle spaces correctly


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


        #except NoteBookError:
        #    if window:
        #        window.set_status("")
        #        window.error("Error while importing plain text files.", 
        #                     e, sys.exc_info()[2])
        #    else:
        #        self.app.error("Error while importing plain text files.", 
        #                       e, sys.exc_info()[2])
        #    return False



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
    print 'text2nodes'

