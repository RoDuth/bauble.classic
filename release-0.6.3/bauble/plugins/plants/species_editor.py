#
# Species table definition
#
import os
import xml.sax.saxutils as sax
import gtk, gobject
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
import formencode.validators as validators
import bauble.utils as utils
import bauble.utils.sql as sql_utils
import bauble.paths as paths
from bauble.plugins import tables, editors
from bauble.editor import *
from bauble.utils.log import log, debug
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus, genus_table
from bauble.plugins.plants.species_model import Species, species_table, \
    SpeciesMeta, SpeciesSynonym, VernacularName, DefaultVernacularName#, SpeciesDistribution
from bauble.plugins.garden.accession import AccessionEditor

# TODO: would be nice, but not necessary, to edit existing vernacular names
# instead of having to add new ones

# TODO: what about author string and cultivar groups

# TODO: ensure None is getting set in the model instead of empty strings, 
# UPDATE: i think i corrected most of these but i still need to double check

# TODO: should only populate the distribution combo if the species meta is 
# expanded on start, and....
# expander = gtk.expander_new_with_mnemonic("_More Options")
# expander.connect("notify::expanded", expander_callback)

# take from accession.py
def delete_or_expunge(obj):
    session = object_session(obj)
    if session is None:
        return # no session, don't need to delete or expunge
#    debug('delete_or_expunge: %s' % obj)
    if obj in session.new:
#        debug('expunge obj: %s -- %s' % (obj, repr(obj)))
        session.expunge(obj)
        del obj
    else:
#        debug('delete obj: %s -- %s' % (obj, repr(obj)))        
        session.delete(obj)         
            

class SpeciesEditorPresenter(GenericEditorPresenter):
    
    PROBLEM_INVALID_GENUS = 1
    
    widget_to_field_map = {'sp_genus_entry': 'genus',
                           'sp_species_entry': 'sp',
                           'sp_author_entry': 'sp_author',
                           'sp_infra_rank_combo': 'infrasp_rank',
                           'sp_hybrid_combo': 'sp_hybrid',
                           'sp_infra_entry': 'infrasp',
                           'sp_cvgroup_entry': 'cv_group',
                           'sp_infra_author_entry': 'infrasp_author',
                           'sp_idqual_combo': 'id_qual',
                           'sp_spqual_combo': 'sp_qual',
                           'sp_notes_textview': 'notes'}
    
    
    def __init__(self, model, view):                
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)
        
        #self.init_infrasp_rank_combo()
        self.init_combos()
        self.init_fullname_widgets()

        self.vern_presenter = VernacularNamePresenter(self.model, self.view, self.session)
        self.synonyms_presenter = SynonymsPresenter(self.model, self.view, self.session)
        self.meta_presenter = SpeciesMetaPresenter(self.model.model, self.view, self.session)        
        self.refresh_view()        
        
        #self.view.widgets.sp_infra_rank_combo.connect('changed', self.on_infra_rank_changed)
        # connect signals
        def gen_get_completions(text):           
            return self.session.query(Genus).select(genus_table.c.genus.like('%s%%' % text))
        def set_in_model(self, field, value):
            setattr(self.model, field, value)
        self.assign_completions_handler('sp_genus_entry', 'genus', 
                                        gen_get_completions, 
                                        set_func=set_in_model)
        self.assign_simple_handler('sp_species_entry', 'sp', StringOrNoneValidator())
        self.assign_simple_handler('sp_infra_rank_combo', 'infrasp_rank', StringOrNoneValidator())
        self.assign_simple_handler('sp_hybrid_combo', 'sp_hybrid', StringOrNoneValidator())
        self.assign_simple_handler('sp_infra_entry', 'infrasp', StringOrNoneValidator())
        self.assign_simple_handler('sp_cvgroup_entry', 'cv_group', UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_infra_author_entry', 'infrasp_author', UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_idqual_combo', 'id_qual', StringOrNoneValidator()) 
        self.assign_simple_handler('sp_spqual_combo', 'sp_qual', StringOrNoneValidator())
        self.assign_simple_handler('sp_author_entry', 'sp_author', UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_notes_textview', 'notes', UnicodeOrNoneValidator())
        
        self.init_change_notifier()
    
    
    def dirty(self):
#        debug('%s, %s, %s, %s' % (self.model.dirty, self.vern_presenter.dirty(),
#                                   self.synonyms_presenter.dirty(), self.meta_presenter.dirty()))
        return self.model.dirty or self.vern_presenter.dirty() or \
            self.synonyms_presenter.dirty() or self.meta_presenter.dirty()
    
    
    def refresh_sensitivity(self):
        '''
        set the sensitivity on the widgets that make up the species name 
        according to values in the model
        '''
        # TODO: there is a bug here that sometimes the ok/accept buttons don't
        # get set as sensitive after entering a genus name and species name,
        # it will work thought after Bauble has been restarted, it seems like
        # it happens after entering a second species name...UPDATE: something 
        # similar seems to be happening in the same Accession editor, maybe other
        # editors too
        sensitive = []
        notsensitive = []
        # TODO: make sure this is perfect
        # states_dict:
        # { field: [widget(s) whose sensitivity == fields is not None] }
        # - if widgets is a tuple then at least one of the items has to not be None
        # - this assumes that when field is not None, if field is none then
        # sensitive widgets are set to false
        states_dict = {'sp_hybrid_combo': [('genus', 'genus')],
                       'sp_species_entry': [('genus', 'genus')],
                       'sp_author_entry': ['sp'],
                       'sp_infra_rank_combo': ['sp'],
                       'sp_infra_entry': [('infrasp_rank', 'sp_hybrid'), 'sp'],
                       'sp_infra_author_entry': [('infrasp_rank', 'sp_hybrid'), 'infrasp', 'sp']}
        for widget, fields in states_dict.iteritems():
#            debug('%s: %s' % (widget, fields))
            none_status = []
            for field in fields:                
                if isinstance(field, tuple):
                    none_list = [f for f in field if self.model[f] is not None]                    
#                    debug(none_list)
                    if len(none_list) != 0:
                        none_status.append(none_list)
                elif getattr(self.model, field) is not None:
                    none_status.append(field)
            
#            debug(none_status)
#            debug(len(none_status))
#            debug(len(states_dict[widget]))
            if len(none_status) == len(states_dict[widget]):
                self.view.widgets[widget].set_sensitive(True)
            else:
                self.view.widgets[widget].set_sensitive(False)        
        
        # turn off the infraspecific rank combo if the hybrid value in the model
        # is not None, this has to be called before the conditional that
        # sets the sp_cvgroup_entry
        if self.model.sp_hybrid is not None:
            self.view.widgets.sp_infra_rank_combo.set_sensitive(False)
        
        # infraspecific rank has to be a cultivar for the cultivar group entry
        # to be sensitive
        if self.model.infrasp_rank == 'cv.' and self.view.widgets['sp_infra_rank_combo'].get_property('sensitive'):
            self.view.widgets.sp_cvgroup_entry.set_sensitive(True)
        else:
            self.view.widgets.sp_cvgroup_entry.set_sensitive(False)
            
        
    def on_field_changed(self, model, field):
        '''
        rests the sensitivity on the ok buttons and the name widgets when 
        values change in the model
        '''
#        debug('on_field_changed: %s' % field)
#        debug('on_field_changed: %s = %s' % (field, getattr(model, field)))
        sensitive = True
        if len(self.problems) != 0 \
           or len(self.vern_presenter.problems) != 0 \
           or len(self.synonyms_presenter.problems) != 0 \
           or len(self.meta_presenter.problems) != 0:
            sensitive = False        
        elif self.model.sp is None or self.model.genus is None:
            sensitive = False
        self.view.set_accept_buttons_sensitive(sensitive)
        self.refresh_sensitivity()
        
    
    def init_change_notifier(self):
        '''
        for each widget register a signal handler to be notified when the
        value in the widget changes, that way we can w things like sensitize
        the ok button
        '''
                
        for field in self.widget_to_field_map.values():         
            self.model.add_notifier(field, self.on_field_changed)
            
        for field in self.meta_presenter.widget_to_field_map.values():
            self.meta_presenter.model.add_notifier(field, self.on_field_changed)
        
         
    def init_combos(self):
        '''
        initialize the infraspecific rank combo, the species hybrid combo,
        the species idqualifier combo and the species qualifier combo    
        '''        
        combos = ['sp_infra_rank_combo', 'sp_hybrid_combo', 'sp_idqual_combo', 
                  'sp_spqual_combo']
        #combos = ['sp_idqual_combo', 'sp_spqual_combo']
        for combo_name in combos:
            combo = self.view.widgets[combo_name]
            combo.clear()
            r = gtk.CellRendererText()
            combo.pack_start(r, True)
            combo.add_attribute(r, 'text', 0)
            column = self.model.c[self.widget_to_field_map[combo_name]]            
            for enum in sorted(column.type.values):
                if enum == None:
                    combo.append_text('')
                else:
                    combo.append_text(enum)
    
    
    def init_fullname_widgets(self):
        '''
        initialized the signal handlers on the widgets that are relative to
        building the fullname string in the sp_fullname_label widget
        '''
        def on_insert(entry, *args):
            self.refresh_fullname_label()                
        def on_delete(entry, *args):
            self.refresh_fullname_label()
        for widget_name in ['sp_genus_entry', 'sp_species_entry', 'sp_author_entry',
                            'sp_infra_entry', 'sp_cvgroup_entry', 
                            'sp_infra_author_entry']:
            w = self.view.widgets[widget_name]
            w.connect_after('insert-text', on_insert)
            w.connect_after('delete-text', on_delete)

        def on_changed(*args):
            self.refresh_fullname_label()
        for widget_name in ['sp_infra_rank_combo', 'sp_hybrid_combo', 
                            'sp_idqual_combo', 'sp_spqual_combo']:
            w = self.view.widgets[widget_name]
            w.connect_after('changed', on_changed)
                    
        
    def refresh_fullname_label(self):
        '''
        resets the fullname label according to values in the model
        '''
        # TODO: i saw this not working once but then it started working again
        # when i restarted before i could debug it so somewhere there's a 
        # bug in hiding
#        debug('refresh_fullname_label')
        if len(self.problems) > 0:
#            debug('len(self.problems) > 0')
            s = '--'
        elif self.model.genus == None:
#            debug('self.model.genus == None')
            s = '--'
        else:
            # create an object that behaves like a Species and pass it to 
            # Species.str
            d = {}
            d.update(zip(self.model.c.keys(), 
                          [getattr(self.model, k) for k in self.model.c.keys()]))            
            
            class attr_dict(object):
                def __init__(self, d):
                    attr_dict.__setattr__(self, '__dict', d)                
                def __getattr__(self, item):
                    d = self.__getattribute__('__dict')
                    if item is '__dict':
                        return d
                    elif item in d:
                        return d[item]
                    else:
                        return getattr(d, item)
                def __setattr__(self, item, value):
                    if item is '__dict':                    
                        super(attr_dict, self).__setattr__(item , value)
                    d = self.__getattribute__('__dict')
                    d[item] = value                    
                def iteritems(self):
                    d = self.__getattribute__('__dict')
                    return d.iteritems()
                
            values = attr_dict(d)
            values.genus = self.model.genus
            for key, value in values.iteritems():
                if value is '':
                    values[key] = None                                        
            if values.sp_hybrid is not None:
                values.infrasp_rank = None
                values.cv_group = None
                values.sp_hybrid = values.sp_hybrid # so this is the last field on_field_changed is called on
            elif values.infrasp_rank is None:
                values.infrasp = None
                values.cv_group = None
                values.infrasp_author = None
            elif values.infrasp_rank != 'cv.':
                values.cv_group = None
            s = '%s  -  %s' % (Family.str(values.genus.family),
                               Species.str(values, authors=True, markup=True))
        self.view.widgets.sp_fullname_label.set_markup(s)
    
    
    def start(self):
        return self.view.start()
        
        
    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():                    
            if field is 'genus_id':
                value = self.model.genus
            else:
                value = getattr(self.model, field)
#            debug('%s, %s, %s' % (widget, field, value))            
#            self.view.set_widget_value(widget, value, 
#                                       default=self.defaults.get(field, None))             
            self.view.set_widget_value(widget, value)
        self.refresh_sensitivity()
        self.vern_presenter.refresh_view(self.model.default_vernacular_name)
        self.synonyms_presenter.refresh_view()
        self.meta_presenter.refresh_view()
            
    
    
class VernacularNamePresenter(GenericEditorPresenter):
    # TODO: change the background of the entries and desensitize the 
    # name/lang entries if the name conflicts with an existing vernacular
    # name for this species
    '''
    in the VernacularNamePresenter we don't really use self.model, we more
    rely on the model in the TreeView which are ModelDecorator objects wrapped
    around VernacularNames objects
    '''
    
    def __init__(self, species, view, session):
        '''
        @param model: a list of VernacularName objects
        @param view: 
        @param session:
        '''
        GenericEditorPresenter.__init__(self, species, view)
        self.session = session
        self.__dirty = False
        self.init_treeview(species.vernacular_names)
        self.view.widgets.sp_vern_add_button.connect('clicked', 
                                                  self.on_add_button_clicked)
        self.view.widgets.sp_vern_remove_button.connect('clicked', 
                                                  self.on_remove_button_clicked)
        lang_entry = self.view.widgets.vern_lang_entry
        lang_entry.connect('insert-text', self.on_entry_insert, 'vern_name_entry')
        lang_entry.connect('delete-text', self.on_entry_delete, 'vern_name_entry')
        
        name_entry = self.view.widgets.vern_name_entry
        name_entry.connect('insert-text', self.on_entry_insert, 'vern_lang_entry')
        name_entry.connect('delete-text', self.on_entry_delete, 'vern_lang_entry')        
        
    
    def dirty(self):        
        return self.__dirty
    
    
    def on_entry_insert(self, entry, new_text, new_text_length, position, 
                        other_widget_name):
        '''
        ensures that the two vernacular name entries both have text and sets 
        the sensitivity of the add button if so
        '''
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        sensitive = False
        if full_text != '' and self.view.widgets[other_widget_name].get_text() != '':
            sensitive = True
        self.view.widgets.sp_vern_add_button.set_sensitive(sensitive)
        
        
    def on_entry_delete(self, entry, start, end, other_widget_name):
        '''
        ensures that the two vernacular name entries both have text and sets 
        the sensitivity of the add button if so
        '''
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        sensitive = False
        if full_text != '' and self.view.widgets[other_widget_name].get_text() != '':
            sensitive = True
        self.view.widgets.sp_vern_add_button.set_sensitive(sensitive)
    
        
    def on_add_button_clicked(self, button, data=None):
        '''
        add the values in the entries to the model
        '''

        name = self.view.widgets.vern_name_entry.get_text()
        lang = self.view.widgets.vern_lang_entry.get_text()
        vn = VernacularName(name=name, language=lang)
        tree_model = self.treeview.get_model()
        self.model.vernacular_names.append(vn)
        it = tree_model.append([ModelDecorator(vn)]) # append to tree model
        if len(tree_model) == 1:
            default = DefaultVernacularName(vernacular_name=vn)
            self.model.default_vernacular_name = default
        self.view.widgets.sp_vern_add_button.set_sensitive(False)
        self.view.widgets.vern_name_entry.set_text('')
        self.view.widgets.vern_lang_entry.set_text('')
        self.view.set_accept_buttons_sensitive(True)
        self.__dirty = True
    
    
    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected vernacular name from the view
        '''        
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database        
        tree = self.view.widgets.vern_treeview
        path, col = tree.get_cursor()        
        tree_model = tree.get_model()        
        value = tree_model[tree_model.get_iter(path)][0]      

        msg = 'Are you sure you want to remove the vernacular name %s?' % utils.xml_safe(value.name)
        if not utils.yes_no_dialog(msg, parent=self.view.window):
            return
        
        tree_model.remove(tree_model.get_iter(path))            
        self.model.vernacular_names.remove(value.model)
        if self.model.default_vernacular_name is not None and value.model == self.model.default_vernacular_name.vernacular_name:
            delete_or_expunge(self.model.default_vernacular_name)
            self.model.default_vernacular_name = None 
            # if there is only one value in the tree then set it as the 
            # default vernacular name
            first = tree_model.get_iter_first()
            if first is not None:
                path = tree_model.get_path(tree_model.get_iter_first())                    
                default = DefaultVernacularName(vernacular_name=tree_model[first][0].model)                
                self.model.default_vernacular_name = default
        delete_or_expunge(value.model)        
        self.view.set_accept_buttons_sensitive(True)           
        self.__dirty = True 
        
        
    def on_default_toggled(self, cell, path, data=None):        
        '''
        default column callback
        '''
        # FIXME: there's a bug if you add a new vernacular, set it as the default,
        # set the default back to the previous default and then hit ok, you should
        # reliably get "duplicate key violates unique constraint "default_vn_index"
#        debug('on_default_toggled')        
        active = cell.get_property('active')
        if not active: # then it's becoming active ???
             tree_model = self.treeview.get_model()             
             it = tree_model.get_iter(path)             
             old_default = self.model.default_vernacular_name
#             debug('old_default: %s,%s(%s)' % (old_default.id,old_default,type(old_default)))
             self.model.default_vernacular_name = None
             delete_or_expunge(old_default)
#             if old_default.id is None:
#                 debug('not hasattr(id)')
                 #del old_default
#             debug('old default in session: %s' % (old_default in self.session))
             default = DefaultVernacularName(vernacular_name=tree_model[it][0].model)
             self.model.default_vernacular_name = default
        self.__dirty = True
        self.view.set_accept_buttons_sensitive(True)
        
    
    def init_treeview(self, model):
        '''
        initialized the list of vernacular names
        '''
        self.treeview = self.view.widgets.vern_treeview
                
        def _name_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', v.name)
            # just added so change the background color to indicate its new
#            if not v.isinstance:
            if v.id is None: # hasn't been committed
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Name', cell)
        col.set_cell_data_func(cell, _name_data_func)
        #col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        #col.set_min_width(150)
        col.set_fixed_width(150)
        col.set_min_width(50)
        col.set_resizable(True)
        self.treeview.append_column(col)
        
        def _lang_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', v.language)
            # just added so change the background color to indicate its new
            #if not v.isinstance:` 
            if v.id is None: # hasn't been committed
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Language', cell)
        col.set_cell_data_func(cell, _lang_data_func)
        #col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        col.set_resizable(True)
        #col.set_min_width(150)
        col.set_fixed_width(150)
        col.set_min_width(50)
        self.treeview.append_column(col)
        
        def _default_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            try:
                cell.set_property('active', v.model==self.model.default_vernacular_name.vernacular_name)
                return
            except AttributeError, e:
                pass
            cell.set_property('active', False)
            
        cell = gtk.CellRendererToggle()
        cell.connect('toggled', self.on_default_toggled)
        col = gtk.TreeViewColumn('Default', cell)
        col.set_cell_data_func(cell, _default_data_func)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        col.set_fixed_width(20)
        col.set_max_width(20)
        self.treeview.append_column(col)
        
        self.treeview.set_model(None)
        
        # TODO: why am i setting self.treeview.model and why does this work
        self.treeview.model = gtk.ListStore(object)
#        debug(self.model)
        #for vn in self.model:
        for vn in model:
            self.treeview.model.append([ModelDecorator(vn)])
        self.treeview.set_model(self.treeview.model)
        
        self.treeview.connect('cursor-changed', self.on_tree_cursor_changed)
        
    
    def on_tree_cursor_changed(self, tree, data=None):
        path, column = tree.get_cursor()
        self.view.widgets.sp_vern_remove_button.set_sensitive(True)
        
    
    def refresh_view(self, default_vernacular_name):        
        tree_model = self.treeview.get_model()
        #if len(self.model) > 0 and default_vernacular_name is None:
        vernacular_names = self.model.vernacular_names
        default_vernacular_name = self.model.default_vernacular_name
        if len(vernacular_names) > 0 and default_vernacular_name is None:
            msg = 'This species has vernacular names but none of them are '\
                  'selected as the default. The first vernacular name in the '\
                  'list has been automatically selected.'
            utils.message_dialog(msg)
            first = tree_model.get_iter_first()
            value = tree_model[first][0]
            path = tree_model.get_path(first)
            default = DefaultVernacularName(vernacular_name=value.model)
            self.model.default_vernacular_name = default
            self.view.set_accept_buttons_sensitive(True)
        elif default_vernacular_name is None:
            return
        
 
#
# TODO: you shouldn't be able to set a plant as a synonym of itself
#
class SynonymsPresenter(GenericEditorPresenter):
    
    PROBLEM_INVALID_SYNONYM = 1
    
    # TODO: if you add a species and then immediately remove then you get an
    # error, something about the synonym not being in the session
        
    def __init__(self, model, view, session):
        '''
        @param model: a Species instance
        @param view: see GenericEditorPresenter
        @param session: 
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = session
        self.init_treeview(model)
        
        # use completions_model as a dummy object for completions, we'll create
        # seperate SpeciesSynonym models on add
        completions_model = SpeciesSynonym()
        def sp_get_completions(text):           
            genus_ids = select([genus_table.c.id], genus_table.c.genus.like('%s%%' % text))
            sql = species_table.select(species_table.c.genus_id.in_(genus_ids))
            return self.session.query(Species).select(sql) 
        def set_in_model(self, field, value):
            # don't set anything in the model, just set self.selected
            sensitive = True
            if value is None:
                sensitive = False
            self.view.widgets.sp_syn_add_button.set_sensitive(sensitive)
            #completions_model.synonym = value
            self._added = value
#            self.selected = value

        self.assign_completions_handler('sp_syn_entry', 'synonym',
                                        sp_get_completions, 
                                        set_func=set_in_model,
                                        model=completions_model)
#        self.selected = None
        self._added = None
        self.view.widgets.sp_syn_add_button.connect('clicked', 
                                                    self.on_add_button_clicked)
        self.view.widgets.sp_syn_remove_button.connect('clicked', 
                                                    self.on_remove_button_clicked)
        self.__dirty = False
        
        
    def dirty(self):
        return self.model.dirty or self.__dirty
    
    
    def init_treeview(self, model):        
        '''
        initialize the gtk.TreeView
        '''
        self.treeview = self.view.widgets.sp_syn_treeview        
        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            #cell.set_property('text', str(v.synonym))
            cell.set_property('text', str(v))
            # just added so change the background color to indicate its new
            if v.id is None:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Synonym', cell)
        col.set_cell_data_func(cell, _syn_data_func)
        self.treeview.append_column(col)
        
        tree_model = gtk.ListStore(object)
        for syn in model.synonyms:
            tree_model.append([syn])
        self.treeview.set_model(tree_model)        
        self.treeview.connect('cursor-changed', self.on_tree_cursor_changed)
    
    
    def on_tree_cursor_changed(self, tree, data=None):
        '''
        '''
        path, column = tree.get_cursor()
        self.view.widgets.sp_syn_remove_button.set_sensitive(True)

    
    def refresh_view(self):
        '''
        doesn't do anything
        '''
        return
        
        
    def on_add_button_clicked(self, button, data=None):
        '''
        adds the synonym from the synonym entry to the list of synonyms for 
            this species
        '''        
        syn = SpeciesSynonym()
        syn.synonym = self._added        
        #self.session.save(syn)
        self.model.synonyms.append(syn)
        tree_model = self.treeview.get_model()
        tree_model.append([syn])
        self._added = None
        entry = self.view.widgets.sp_syn_entry
        # sid generated from GenericEditorPresenter.assign_completion_handler
        entry.handler_block(self._insert_sp_syn_entry_sid) 
        entry.set_text('')
        entry.set_position(-1)        
        entry.handler_unblock(self._insert_sp_syn_entry_sid)
        self.view.widgets.sp_syn_add_button.set_sensitive(False)
        self.view.widgets.sp_syn_add_button.set_sensitive(False)
        self.view.set_accept_buttons_sensitive(True)
        self.__dirty = True
        

    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected synonym from the list of synonyms for
        this species
        '''
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database        
        tree = self.view.widgets.sp_syn_treeview
        path, col = tree.get_cursor()
        tree_model = tree.get_model()
        value = tree_model[tree_model.get_iter(path)][0]      
#        debug('%s: %s' % (value, type(value)))
        s = Species.str(value.synonym, markup=True)
        msg = 'Are you sure you want to remove %s as a synonym to the ' \
              'current species?\n\n<i>Note: This will not remove the species '\
              '%s from the database.</i>' % (s, s)
        if utils.yes_no_dialog(msg, parent=self.view.window):            
            tree_model.remove(tree_model.get_iter(path))
            self.model.synonyms.remove(value)
#            delete_or_expunge(value)            
            self.view.set_accept_buttons_sensitive(True)
            self.__dirty = True
    
    
# TODO: there is no way to set the check buttons to None once they
# have been set and the inconsistent state doesn't convey None that
# well, the only other option I know of is to use Yes/No/None combos
# instead of checks
        

class SpeciesMetaPresenter(GenericEditorPresenter):    
    
    widget_to_field_map = {'sp_dist_combo': 'distribution',
                           'sp_humanpoison_check': 'poison_humans',
                           'sp_animalpoison_check': 'poison_animals',
                           'sp_food_check': 'food_plant'}
        
    def __init__(self, species, view, session):
        '''
        @param species: a Species object
        @param view: the view
        @param session: the session to save the model to, can be different than 
        that session the model is bound to
        '''        
        self.species = species
        meta = self.species.species_meta
        if meta is None:
            meta = SpeciesMeta()
        GenericEditorPresenter.__init__(self, ModelDecorator(meta), view)
        self.session = session
        self.init_distribution_combo()
        # we need to call refresh view here first before setting the signal
        # handlers b/c SpeciesEditorPresenter will call refresh_view after
        # these are assigned causing the the model to appear dirty
        self.refresh_view() 
        self.assign_simple_handler('sp_humanpoison_check', 'poison_humans')
        self.assign_simple_handler('sp_animalpoison_check', 'poison_animals')
        self.assign_simple_handler('sp_food_check', 'food_plant')                
        for field in self.widget_to_field_map.values():         
            self.model.add_notifier(field, self.on_field_changed)

    
    def dirty(self):
        return self.model.dirty

    
    def on_field_changed(self, model, field):
        if self.species.species_meta is None:
            self.species.species_meta = model

        
    def init_distribution_combo(self):        
#        def populate():  
#            combo = self.view.widgets.sp_dist_combo
#            combo.set_model(None)
#            model = gtk.TreeStore(object)
#            # TODO: how do we handled "Cultivated" since we no longer save
#            # the distribution as just a string
##            model.append(None, ["Cultivated"])
#            from bauble.plugins.geography.distribution import Continent, \
#                Region, BotanicalCountry, BasicUnit
#            for continent in self.session.query(Continent).select():
#                p1 = model.append(None, [continent])                
#                for region in self.session.query(Region).select_by(continent_id=continent.id):
#                    p2 = model.append(p1, [region])
#                    for country in self.session.query(BotanicalCountry).select_by(region_id=region.id):
#                        p3 = model.append(p2, [country])
#                        for unit in self.session.query(BasicUnit).select_by(botanical_country_id=country.id):
#                            if unit.name != country.name:
#                                model.append(p3, [unit])                    
#            combo.set_model(model)
#            combo.set_sensitive(True)
#            self.view.set_widget_value('sp_dist_combo', self.model.distribution)
#            self.assign_simple_handler('sp_dist_combo', 'distribution')       
        def populate():  
            combo = self.view.widgets.sp_dist_combo
            combo.set_model(None)
            model = gtk.TreeStore(object)
            model.append(None, [''])
            model.append(None, ['Cultivated'])            
            # TODO: i wonder if it would be faster to get all the data in one loop
            # and populate the model in another
            from bauble.plugins.geography.distribution import continent_table, \
                region_table, botanical_country_table, basic_unit_table                
            for continent_id, continent in select([continent_table.c.id, continent_table.c.continent]).execute():
                p1 = model.append(None, [continent])
                for region_id, region in select([region_table.c.id, region_table.c.region], region_table.c.continent_id==continent_id).execute():
                    p2 = model.append(p1, [region])
                    for country_id, country in select([botanical_country_table.c.id, botanical_country_table.c.name], botanical_country_table.c.region_id==region_id).execute():
                        p3 = model.append(p2, [country])
                        for unit, in select([basic_unit_table.c.name], and_(basic_unit_table.c.botanical_country_id==country_id, basic_unit_table.c.name!=country)).execute():
                            model.append(p3, [unit])
            combo.set_model(model)
            combo.set_sensitive(True)
            self.view.set_widget_value('sp_dist_combo', self.model.distribution)
            self.assign_simple_handler('sp_dist_combo', 'distribution', StringOrNoneValidator())
        gobject.idle_add(populate)
        
#    def init_distribution_combo(self):        
#        '''
#        '''
#        def _populate():
#            self.view.widgets.sp_dist_combo.set_model(None)
#            model = gtk.TreeStore(str)
#            model.append(None, ["Cultivated"])            
#            from bauble.plugins.geography.distribution import continent_table, \
#                region_table, botanical_country_table, basic_unit_table
#            region_select = select([region_table.c.id, region_table.c.region], 
#                                   region_table.c.continent_id==bindparam('continent_id')).compile()
#            country_select = select([botanical_country_table.c.id, botanical_country_table.c.name], 
#                                    botanical_country_table.c.region_id==bindparam('region_id')).compile()
#            unit_select = select([basic_unit_table.c.name, basic_unit_table.c.id], 
#                                 basic_unit_table.c.botanical_country_id==bindparam('country_id')).compile()                        
#            for continent_id, continent in select([continent_table.c.id, continent_table.c.continent]).execute():
#                p1 = model.append(None, [continent])
#                for region_id, region in region_select.execute(continent_id=continent_id):
#                    p2 = model.append(p1, [region])
#                    for country_id, country in country_select.execute(region_id=region_id):
#                        p3 = model.append(p2, [country])
#                        for unit, dummy in unit_select.execute(country_id=country_id):
#                            if unit != country:
#                                model.append(p3, [unit])
#            self.view.widgets.sp_dist_combo.set_model(model)
#            self.view.widgets.sp_dist_combo.set_sensitive(True)
#            self.view.set_widget_value('sp_dist_combo', self.model.distribution)
#            self.assign_simple_handler('sp_dist_combo', 'distribution')
#        gobject.idle_add(_populate)
    
        
        
    def refresh_view(self):
        '''
        '''
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            self.view.set_widget_value(widget, value)
            
    

class SpeciesEditorView(GenericEditorView):
    
    expanders_pref_map = {'sp_infra_expander': 'editor.species.infra.expanded', 
                          'sp_qual_expander': 'editor.species.qual.expanded',
                          'sp_meta_expander': 'editor.species.meta.expanded'}
    
    
    def __init__(self, parent=None):
        '''
        the constructor
        
        @param parent: the parent window
        '''
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'plants', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.species_dialog
        self.dialog.set_transient_for(parent)
        self.init_distribution_combo()
        self.attach_completion('sp_genus_entry', self.genus_completion_cell_data_func)
        self.attach_completion('sp_syn_entry', self.syn_cell_data_func)
        self.restore_state()
        self.connect_dialog_close(self.widgets.species_dialog)
        if sys.platform == 'win32':
            self.do_win32_fixes()
        
        
    def init_distribution_combo(self):
        def cell_data_func(column, renderer, model, iter, data=None):
            v = model[iter][0]
            renderer.set_property('text', '%s' % str(v))
        combo = self.widgets.sp_dist_combo
        combo.clear()        
        r = gtk.CellRendererText()
        combo.pack_start(r)
        combo.set_cell_data_func(r, cell_data_func)
        
        
    def _get_window(self):
        '''
        '''
        return self.widgets.species_dialog    
    window = property(_get_window)
    
    
    def set_accept_buttons_sensitive(self, sensitive):        
        '''
        set the sensitivity of all the accept/ok buttons for the editor dialog
        '''
        self.widgets.sp_ok_button.set_sensitive(sensitive)
        self.widgets.sp_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.sp_next_button.set_sensitive(sensitive)
        
        
    def _lower_completion_match_func(self, completion, key_string, iter, 
                                    data=None):
        '''
        the only thing this does different is it make the match case insensitve
        '''
        value = completion.get_model()[iter][0]
        return str(value).lower().startswith(key_string.lower())   
        
        
    def genus_completion_cell_data_func(self, column, renderer, model, iter, 
                                         data=None):
        '''
        '''
        v = model[iter][0]
        renderer.set_property('text', '%s (%s)' % \
                              (Genus.str(v), 
                               Family.str(v.family)))
        
        
    def syn_cell_data_func(self, column, renderer, model, iter, 
                                         data=None):
        '''
        '''
        v = model[iter][0]
        renderer.set_property('text', str(v))
        
        
    def do_win32_fixes(self):
        '''
        '''
        pass
        
        
    def save_state(self):        
        '''
        save the current state of the gui to the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            prefs[pref] = self.widgets[expander].get_expanded()
        
        
    def restore_state(self):
        '''
        restore the state of the gui from the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            expanded = prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)

            
    def start(self):
        '''
        starts the views, essentially calls run() on the main dialog
        '''
        return self.widgets.species_dialog.run()    
    


class SpeciesEditor(GenericModelViewPresenterEditor):
    
    label = 'Species'
    mnemonic_label = '_Species'
    
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
    
    def __init__(self, model=None, parent=None):
        '''
        @param model: a species instance or None
        @param parent: the parent window or None
        '''        
        if model is None:
            model = Species()
            
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        self.parent = parent
        self._committed = []
        

    def handle_response(self, response):
        '''
        @return: return a list if we want to tell start() to close the editor, 
        the list should either be empty or the list of committed values, return 
        None if we want to keep editing
        '''
        # TODO: need to do a __cleanup_model before the commit to do things
        # like remove the insfraspecific information that's attached to the 
        # model if the infraspecific rank is None
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:                
                exc = traceback.format_exc()
                msg = 'Error committing changes.\n\n%s' % utils.xml_safe(e.orig)
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except Exception, e:
                msg = 'Unknown error when committing changes. See the details '\
                      'for more information.\n\n%s' % utils.xml_safe(e)
                debug(traceback.format_exc())
                #warning(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) or not self.presenter.dirty():        
            return True
        else:
            return False
        
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = SpeciesEditor(Species(genus=self.model.genus), self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            e = AccessionEditor(Accession(species=self.model, parent=self.parent))
            more_committed = e.start()
                    
        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)
        
        return True


    def commit_changes(self):
        if self.model.sp_hybrid is None and self.model.infrasp_rank is None:
            self.model.infrasp = None
            self.model.infrasp_author = None
            self.model.cv_group = None
        super(SpeciesEditor, self).commit_changes()
        
        
    def start(self):
        if self.session.query(Genus).count() == 0:        
            msg = 'You must first add or import at least one genus into the '\
                  'database before you can add species.'
            utils.message_dialog(msg)
            return
        self.view = SpeciesEditorView(parent=self.parent)
        self.presenter = SpeciesEditorPresenter(self.model, self.view)
        
        # add quick response keys
        dialog = self.view.dialog        
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return', gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_OK_AND_ADD, 'k', gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n', gtk.gdk.CONTROL_MASK)        
        
        # set default focus
        if self.model.genus is None:
            self.view.widgets.sp_genus_entry.grab_focus()
        else:
            self.view.widgets.sp_species_entry.grab_focus()
        
        exc_msg = "Could not commit changes.\n"
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
        self.session.close() # cleanup session
        return self._committed

    
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander
except ImportError:
    pass
else:
    from bauble.plugins.garden.accession import Accession, accession_table
    from bauble.plugins.garden.plant import Plant, plant_table
    
#    
# Species infobox for SearchView
#
    class VernacularExpander(InfoExpander):
        '''
        the constructor
        '''
        def __init__(self, widgets):
            InfoExpander.__init__(self, "Vernacular Names", widgets)
            vernacular_box = self.widgets.sp_vernacular_box
            self.widgets.remove_parent(vernacular_box)
            self.vbox.pack_start(vernacular_box)
            
            
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get thevalues from
            '''
            if len(row.vernacular_names) == 0:
                self.set_sensitive(False)
                self.set_expanded(False)
            else:                
                names = []
                for vn in row.vernacular_names:
                    #if vn == row.default_vernacular_name:
                    if row.default_vernacular_name is not None and vn == row.default_vernacular_name.vernacular_name:
                        names.insert(0, '%s - %s (default)' % \
                                     (vn.name, vn.language))
                    else:
                        names.append('%s - %s' % \
                                     (vn.name, vn.language))
                self.set_widget_value('sp_vernacular_data', '\n'.join(names))
                self.set_sensitive(True)
                # TODO: get expanded state from prefs
                self.set_expanded(True) 
        
        
            
    class SynonymsExpander(InfoExpander):
        
        def __init__(self, widgets):
            InfoExpander.__init__(self, "Synonyms", widgets)
            synonyms_box = self.widgets.sp_synonyms_box
            self.widgets.remove_parent(synonyms_box)
            self.vbox.pack_start(synonyms_box)
            
            
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get thevalues from
            '''
            #debug(row.synonyms)
            if len(row.synonyms) == 0:
                self.set_sensitive(False)
                self.set_expanded(False)
            else:
                synonyms = []
                for syn in row.synonyms:
                    s = Species.str(syn.synonym, markup=True, authors=True)
                    synonyms.append(s)
                self.widgets.sp_synonyms_data.set_markup('\n'.join(synonyms))
                self.set_sensitive(True)
                # TODO: get expanded state from prefs
                self.set_expanded(True)
        
        
        
    class NotesExpander(InfoExpander):
        
        def __init__(self, widgets):
            InfoExpander.__init__(self, "Notes", widgets)
            notes_box = self.widgets.sp_notes_box
            self.widgets.remove_parent(notes_box)
            self.vbox.pack_start(notes_box)
            
                        
        def update(self, row):
            if row.notes is None:
                self.set_expanded(False)
                self.set_sensitive(False)
            else:
                self.set_expanded(True)
                self.set_sensitive(True)
                self.set_widget_value('sp_notes_data', row.notes)
            
    
    class GeneralSpeciesExpander(InfoExpander):
        '''
        expander to present general information about a species
        '''
    
        def __init__(self, widgets):
            '''
            the constructor
            '''
            InfoExpander.__init__(self, "General", widgets)
            general_box = self.widgets.sp_general_box
            self.widgets.remove_parent(general_box)
            self.vbox.pack_start(general_box)
            
            # make the check buttons read only
            def on_enter(button, *args):
                button.emit_stop_by_name("enter-notify-event")
                return True
            self.widgets.sp_food_check.connect('enter-notify-event', on_enter)
            self.widgets.sp_phumans_check.connect('enter-notify-event', on_enter)
            self.widgets.sp_panimals_check.connect('enter-notify-event', on_enter)

        
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get the values from
            '''
            self.set_widget_value('sp_name_data', row.markup(True))
            
            if row.id_qual is not None:
                self.widgets.sp_idqual_label.set_sensitive(True)
                self.widgets.sp_idqual_data.set_sensitive(True) 
                self.set_widget_value('sp_idqual_data', row.id_qual)
            else:
                self.widgets.sp_idqual_label.set_sensitive(False)
                self.widgets.sp_idqual_data.set_sensitive(False)
            
            if row.species_meta is not None:
                meta = row.species_meta
                # set the sensitivity of the widgets before setting them
                def set_meta(widget, value):                
                    if value is None:
                        self.widgets[widget].set_sensitive(False)
                    else:
                        self.widgets[widget].set_sensitive(True)
                    self.set_widget_value(widget, value)
                set_meta('sp_dist_data', meta.distribution)
                set_meta('sp_food_check', meta.food_plant)
                set_meta('sp_phumans_check', meta.poison_humans)
                set_meta('sp_panimals_check', meta.poison_animals)
            else:
                for w in ('sp_dist_data', 'sp_food_check', 'sp_phumans_check', 'sp_panimals_check'):
                    self.set_widget_value(w, None)
                    self.widgets[w].set_sensitive(False)
                
                        
            nacc = sql_utils.count(accession_table, accession_table.c.species_id==row.id)
            self.set_widget_value('sp_nacc_data', nacc)
            
            acc_ids = select([accession_table.c.id], accession_table.c.species_id==row.id)
            nplants_str = str(sql_utils.count(plant_table, plant_table.c.accession_id.in_(acc_ids)))
            if nplants_str != '0':                
                nacc_with_plants = sql_utils.count_distinct_whereclause(plant_table.c.accession_id, plant_table.c.accession_id.in_(acc_ids))
                nplants_str = '%s in %s accessions' % (nplants_str, nacc_with_plants)
            self.set_widget_value('sp_nplants_data', nplants_str)
    
    
    
    class SpeciesInfoBox(InfoBox):
        '''
        - general info, fullname, common name, num of accessions and clones
        - poisonous to humans
        - poisonous to animals
        - food plant
        - origin/distribution
        '''
        
        # others to consider: reference, images, redlist status
        
        def __init__(self):
            ''' 
            the constructor
            '''
            InfoBox.__init__(self)
            glade_file = os.path.join(paths.lib_dir(), 'plugins', 'plants', 
                                      'infoboxes.glade')            
            self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
            self.general = GeneralSpeciesExpander(self.widgets)
            self.add_expander(self.general)
            self.vernacular = VernacularExpander(self.widgets)
            self.add_expander(self.vernacular)
            self.synonyms = SynonymsExpander(self.widgets)
            self.add_expander(self.synonyms)
            self.notes = NotesExpander(self.widgets)
            self.add_expander(self.notes)
            
            #self.ref = ReferenceExpander()
            #self.ref.set_expanded(True)
            #self.add_expander(self.ref)
            
            #img = ImagesExpander()
            #img.set_expanded(True)
            #self.add_expander(img)
            
            
        def update(self, row):
            '''
            update the expanders in this infobox
            
            @param row: the row to get the values from
            '''
            self.general.update(row)
            self.vernacular.update(row)
            self.synonyms.update(row)
            self.notes.update(row)
            #self.ref.update(row.references)
            #self.ref.value = row.references
            #ref = self.get_expander("References")
            #ref.set_values(row.references)
    
    
    # it's easier just to put this here instead of playing around with imports
    class VernacularNameInfoBox(SpeciesInfoBox):
        def update(self, row):
            super(VernacularNameInfoBox, self).update(row.species)
        