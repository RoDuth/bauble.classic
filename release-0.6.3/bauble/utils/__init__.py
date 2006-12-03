    #
# utils module
#

import imp, os, sys, re
import bauble
import gtk, gtk.glade
from bauble.utils.log import debug
import xml
from sqlalchemy import *

# TODO: this util module might need to be split up if it gets much larger
# we could have a utils.gtk and utils.sql
#

#def search_tree_model(model, data, func=lambda row, data: row[0] == data):
#    '''
#    return the first occurence of data found in model
#    
#    @param model: the tree model to search
#    @param data: what we are searching for
#    @param func: the function to use to compare each row in the model, the 
#        default is C{lambda row, data: row[0] == data}
#    '''
#    result = None
#    for row in model:
#        if func(row, data):
#            return row
#        result = search_tree_model(row.iterchildren(), data, func)    
#    return result



def find_dependent_tables(table, metadata=None):
    from sqlalchemy import default_metadata
    import sqlalchemy.sql_util as sql_util
    if metadata is None:
        metadata = default_metadata
    result = []
#    debug('find_dependent_tables(%s)' % table.name)
    def _impl(t2):
        for name, t in metadata.tables.iteritems():  
            for c in t.c:
                try:
                    if c.foreign_key.column.table == t2:
                        if t not in result and t is not table:
                            result.append(t)
#                            print 'finding dependencies for %s' % t.name
                            _impl(t)
                except AttributeError, e:
                    pass
    _impl(table)
    collection = sql_util.TableCollection()
    for r in result:
        collection.add(r)        
    sorted = collection.sort(False)
    return [s for s in sorted if s is not table]


class GladeWidgets(dict):
    '''
    dictionary and attribute access for widgets
    '''

    def __init__(self, glade_xml):
        '''
        @params glade_xml: a gtk.glade.XML object
        '''
        if isinstance(glade_xml, str):
            self.glade_xml = gtk.glade.XML(glade_xml)
        else:
            self.glade_xml = glade_xml
    
    def __getitem__(self, name):
        '''
        @param name:
        '''
        # TODO: raise a key error if there is no widget
        return self.glade_xml.get_widget(name)

    def __getattr__(self, name):
        '''
        @param name:
        '''
        return self.glade_xml.get_widget(name)
    
    
    def remove_parent(self, widget):
        if isinstance(widget, str):
            w = self[widget]
        else:
            w = widget
        parent = w.get_parent()
        if parent is not None:
            parent.remove(w)
            
            
    def signal_autoconnect(self, handlers):
        self.glade_xml.signal_autoconnect(handlers)
        

def tree_model_has(tree, value):
    return len(search_tree_model(tree, value)) > 0
    
    
def search_tree_model(parent, data, func=lambda row, data: row[0] == data):
    '''
    return a list of tree iters to all occurences of data in model
    '''
    results = []
    for row in parent:
        search_tree_model(row.iterchildren(), data, func)
        if func(row, data):
#            debug('row %s: %s' % (row, row[0]))
            try:
                results.extend(row.iter)
            except:
                results = [row.iter]
#    debug(results)
    return results


def combo_set_active_text(combo, value):
    '''
    does the same thing as set_combo_from_value but this looks more like a 
    GTK+ method
    '''
    set_combo_from_value(combo, value)


def set_combo_from_value(combo, value, cmp=lambda row, value: row[0] == value):
    '''
    find value in combo model and set it as active, else raise ValueError
    cmp(row, value) is the a function to use for comparison
        
    NOTE: if more than one value is found in the combo then the first one
    in the list is set
    '''
    model = combo.get_model()    
    matches = search_tree_model(model, value, cmp)
    if len(matches) == 0:
        raise ValueError('set_combo_from_value() - could not find value in '\
                         'combo: %s' % value)
    combo.set_active_iter(matches[0])

    
def combo_get_value_iter(combo, value, cmp=lambda row, value: row[0] == value):
    '''
    @param combo: the combo where we should search
    @param value: the value to search for
    @param cmp: the method to use to compare rows in the combo model and value, 
        the default is C{lambda row, value: row[0] == value}
    @return: the gtk.TreeIter that points to value
    
    NOTE: if more than one value is found in the combo then the first one
    in the list is returned
    '''
    model = combo.get_model()
    matches = search_tree_model(model, value, cmp)
    if len(matches) == 0:        
        return None
    return matches[0]


def set_widget_value(glade_xml, widget_name, value, markup=True, default=None):
    '''
    @param glade_xml: the glade_file to get the widget from
    @param widget_name: the name of the widget
    @param value: the value to put in the widget
    @param markup: whether or not
    @param default: the default value to put in the widget if the value is None    
    
    NOTE: any values passed in for widgets that expect a string will call
    the values __str__ method    
    '''

    w = glade_xml.get_widget(widget_name)
    if value is None:  # set the value from the default
        if isinstance(w,(gtk.Label, gtk.TextView, gtk.Entry)) and default is None:
            value = ''
        else:
            value = default
        
    if isinstance(w, gtk.Label):
        #w.set_text(str(value))
        # FIXME: some of the enum values that have <not set> as a values
        # will give errors here, but we can't escape the string because
        # if someone does pass something that needs to be marked up
        # then it won't display as intended, maybe BaubleTable.markup()
        # should be responsible for returning a properly escaped values
        # or we should just catch the error(is there an error) and call
        # set_text if set_markup fails
        if markup: 
            w.set_markup(str(value))
        else:
            w.set_text(str(value))
    elif isinstance(w, gtk.TextView):
        w.get_buffer().set_text(str(value))
    elif isinstance(w, gtk.Entry):
        w.set_text(str(value))
    elif isinstance(w, gtk.ComboBox): # TODO: what about comboentry
        # TODO: what if None is in the model
        i = combo_get_value_iter(w, value)
        if i is not None:
            w.set_active_iter(i)
        elif w.get_model() is not None:
            w.set_active(-1)
#        if value is None:
#            if w.get_model() is not None:
#                w.set_active(-1)
#        else:
#            set_combo_from_value(w, value)	
    elif isinstance(w, (gtk.ToggleButton, gtk.CheckButton, gtk.RadioButton)): 
        if value is True:     
            w.set_inconsistent(False)
            w.set_active(True)
        elif value is False: # how come i have to unset inconsistent for False?
            w.set_inconsistent(False)
            w.set_active(False)
        else:
            w.set_inconsistent(True)            
    else:
        raise TypeError('don\'t know how to handle the widget type %s with '\
		                'name %s' % (type(w), widget_name))

# TODO: if i escape the messages that come in then my own markup doesn't 
# work, what really needs to be done is make sure that any exception that
# are going to be passed to one of these dialogs should be escaped before 
# coming through

def create_message_dialog(msg, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK, parent=None):
    '''
    '''
    if parent is None:
        try: # this might get called before bauble has started
            parent = bauble.app.gui.window
        except:
            parent = None    
    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          parent=parent, type=type, buttons=buttons)
    d.set_markup(msg)
    d.show_all()
    return d


def message_dialog(msg, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK, parent=None):
    '''
    '''
    d = create_message_dialog(msg, type, buttons, parent)
    r = d.run()
    d.destroy()
    return r

    
def create_yes_no_dialog(msg, parent=None):
    '''
    '''
    if parent is None:
        try: # this might get called before bauble has started
            parent = bauble.app.gui.window
        except:
            parent = None    
    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          parent=parent, type=gtk.MESSAGE_QUESTION,
                          buttons = gtk.BUTTONS_YES_NO)            
    d.set_markup(msg)
    d.show_all()
    return d
    
    
# TODO: it would be nice to implement a yes_or_no method that asks from the 
# console if there is no gui. is it possible to know if we have a terminal
# to write to?
def yes_no_dialog(msg, parent=None):
    '''
    '''
    d = create_yes_no_dialog(msg, parent)
    r = d.run()
    d.destroy()  
    return r == gtk.RESPONSE_YES

#
# TODO: give the button the default focus instead of the expander
#
def create_message_details_dialog(msg, details, type=gtk.MESSAGE_INFO, 
                                  buttons=gtk.BUTTONS_OK, parent=None):
    '''
    '''
    if parent is None:
        try: # this might get called before bauble has started
            parent = bauble.app.gui.window    
        except:    
            parent = None
    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                         parent=parent,type=type, buttons=buttons)
    d.set_markup(msg)
    expand = gtk.Expander("Details")    
    text_view = gtk.TextView()
    text_view.set_editable(False)
    text_view.set_wrap_mode(gtk.WRAP_WORD)
    tb = gtk.TextBuffer()
    tb.set_text(details)
    text_view.set_buffer(tb)
    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    sw.add(text_view)    
    expand.add(sw)
    d.vbox.pack_start(expand)
    ok_button = d.action_area.get_children()[0]
    d.set_focus(ok_button)
    d.show_all()
    return d
    
    
def message_details_dialog(msg, details, type=gtk.MESSAGE_INFO, 
                           buttons=gtk.BUTTONS_OK):
    '''
    '''
    d = create_message_details_dialog(msg, details, type, buttons)
    r = d.run()
    d.destroy()
    return r


def xml_safe(ustr, encoding='utf-8'):    
    '''
    return a unicode string encoded to @param encoding that is safe for xml
    output
    '''
    #return xml.sax.saxutils.escape(ustr).encode(encoding)
    # TODO: encodings.string_escape to escape string as well
    return xml.sax.saxutils.escape(unicode(ustr)).encode(encoding)


def startfile(filename):
    '''
    @param filename: the name of the file to execute
    
    opens a file with it's associated application, should work on win32 and
    linux/gnome for now
    '''
    if sys.platform == 'win32':
        try:
            os.startfile(filename)
        except WindowsError, e: # probably no file association
            msg = "Could not open pdf file.\n\n%s" % xml_safe(e)
            message_dialog(msg)        
    elif sys.platform == 'linux2':
        # FIXME: need to determine if gnome or kde
        os.system("gnome-open " + filename)
    else:
        raise Exception("bauble.utils.startfile(): can't open file:" + filename)
   
   