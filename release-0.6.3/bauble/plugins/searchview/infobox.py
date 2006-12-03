#
# infobox.py
#

import sys, os
import gtk
import bauble.utils as utils
import bauble.paths as paths
from bauble.utils.log import debug
from bauble.plugins import tables


# TODO: reset expander data on expand, the problem is that we don't keep the 
# row around that was used to update the infoexpander, if we don't do this then 
# we can't update unless the search view updates us, this means that the search
# view would have to register on_expanded on each info expander in the infobox

# what to display if the value in the database is None
DEFAULT_VALUE='--'

class InfoExpander(gtk.Expander):
    """
    an abstract class that is really just a generic expander with a vbox
    
    to extend this you just have to implement the update() method
    """
    # TODO: we should be able to make this alot more generic
    # and get information from sources other than table columns
    def __init__(self, label, widgets=None):
        '''
        the constructor

        @param label: the name of this info expander, this is displayed on the 
        expander's expander
        @param glade_xml: a gtk.glade.XML instace where can find the expanders 
        widgets
        '''
        gtk.Expander.__init__(self, label)
        self.vbox = gtk.VBox(False)
        self.vbox.set_border_width(5)
        self.add(self.vbox)
        self.set_expanded(True)
        self.widgets = widgets
        
              
    def set_widget_value(self, widget_name, value, markup=True, default=None):
        '''
        a shorthand for L{utils.set_widget_value}
        TODO: how do i link the docs to reference utils.set_widget_value
        '''
        utils.set_widget_value(self.widgets.glade_xml, widget_name, value, markup, 
                               default)
        
        
    def update(self, value):
        '''
        should be implement
        '''
        raise NotImplementedError("InfoExpander.update(): not implemented")

   
# should we have a specific expander for those that use glade
class GladeInfoExpander(gtk.Expander):
    pass
    
    
class InfoBox(gtk.ScrolledWindow):
    """
    a VBox with a bunch of InfoExpanders
    """
    
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.vbox = gtk.VBox()
        self.vbox.set_spacing(10)
        viewport = gtk.Viewport()
        viewport.add(self.vbox)
        self.add(viewport)
        
        self.expanders = {}
    
    
    def add_expander(self, expander):
        '''
        add an expander to the list of exanders in this infobox
        
        @type expander: InfoExpander
        @param expander: the expander to add to this infobox
        '''
        self.vbox.pack_start(expander, False, False)
        self.expanders[expander.get_property("label")] = expander
        
        sep = gtk.HSeparator()
        self.vbox.pack_start(sep, False, False)
    
    
    def get_expander(self, label):
        '''
        returns an expander by the expander's label name
        
        @param label: the name of the expander to return
        @returns: returns an expander by the expander's label name
        '''
        #if self.expanders.has_key(label): 
        if label in self.expanders:
            return self.expanders[label]
        else: return None
    
    
    def remove_expander(self, label):
        '''
        remove expander from the infobox by the expander's label bel
        
        @param label: the name of th expander to remove
        @return: return the expander that was removed from the infobox
        '''
        #if self.expanders.has_key(label): 
        if label in self.expanders:
            return self.vbox.remove(self.expanders[label])
    
    
    def update(self, row):
        '''
        updates the infobox with values from row
        
        @param row: the SQLObject instance to use to update this infobox,
        this is passed to each of the infoexpanders in turn
        '''
        # TODO: should we just iter over the expanders and update them all
        raise NotImplementedError


# TODO: references expander should also show references to any
# foreign key defined in the table, e.g. if a species is being
# display it should also show the references associated with
# the family and genera

# TODO: it would be uber-cool to look up book references on amazon, 
# is there a python api for amazon or should it just defer to the browser
#class ReferencesExpander(TableExpander):
#    def __init__(self, label="References", columns={'label': 'Label',
#                                                    'reference': 'References'}):
#        TableExpander.__init__(self, label, columns)

#class ImagesExpander(InfoExpander):
#    def __init(self, label="Images"):#, columns={'label': 'Label',
#                                    #          'uri': 'URI'}):
#        InfoExpander.__init__(self, label)
#                                                            
#    def create_gui(self):
#        pass
#        
#    def update(self, values):
#        pass
#        
#        
#class ReferencesExpander(InfoExpander):
#    def __init__(self):
#        InfoExpander.__init__(self, 'References', None)
#                
#    def update(self, values):
#        if type(values) is not list:
#            raise ValueError('ReferencesExpander.update(): expected a list')
#            
#        for v in values:
#            print v.reference

        