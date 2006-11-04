#
# ABCD import/exporter
#

import os,csv
import gtk.gdk
import lxml.etree as etree
from lxml.etree import Element, SubElement, ElementTree
import bauble.paths as paths
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.utils import xml_safe
from bauble.plugins import BaublePlugin, BaubleTool, plugins
from bauble.plugins.abcd.abcd import DataSets, ABCDElement, ElementFactory
from bauble.plugins.plants.species_model import Species

#import bauble.plugins.abcd.abcd

# NOTE: see biocase provider software for reading and writing ABCD data
# files, already downloaded software to desktop

# TODO: should have a command line argument to create labels without starting 
# the full bauble interface, after creating the labels it should automatically 
# open the whatever ever view is associated with pdf files
# e.g bauble -labels "select string"
# bauble -labels "block=4"
# bauble -label "acc=1997"
#
# TODO: create label make in the tools that show a dialog with an entry
# the entry is for a search string that then returns a list of all the labels
# that'll be made with checkboxess next to them to de/select the ones you 
# don't want to print, could also have a check box to select species or 
# accessions so we can print labels for plants that don't have accessions, 
# though this could be a problem b/c abcd data expects 'unitid' fields but 
# we could have a special case just for generating labels
# 

def validate(root):
    '''
    validate root against ABCD 2.06 schema
    @param root: root of an XML tree to validate against
    @type root: an lxml.etree.Element
    @returns: True or False depending if root validate correctly
    '''
    schema_file = os.path.join(paths.lib_dir(), 'plugins',
            'abcd','abcd_2.06.xsd')
    xmlschema_doc = etree.parse(schema_file)
    abcd_schema = etree.XMLSchema(xmlschema_doc)
    return abcd_schema.validate(root)


def plants_to_abcd(plants, authors=True):
    '''
    @param plants: a list of bauble.plugins.garden.Plant object to convert
    to valid ABCD XML
    @returns: a valid ABCD ElementTree
    '''
    datasets = DataSets()
    ds = ElementFactory(datasets, 'DataSet')
    tech_contacts = ElementFactory(ds, 'TechnicalContacts')
    tech_contact = ElementFactory(tech_contacts, 'TechnicalContact')
    ElementFactory(tech_contact, 'Name', text='Brett')
    ElementFactory(tech_contact, 'Email', text='brett@belizebotanic.org')
    cont_contacts = ElementFactory(ds, 'ContentContacts')
    cont_contact = ElementFactory(cont_contacts, 'ContentContact')
    ElementFactory(cont_contact, 'Name', text='Brett')
    ElementFactory(cont_contact, 'Email', text='brett@belizebotanic.org')
    metadata = ElementFactory(ds, 'Metadata', )
    description = ElementFactory(metadata, 'Description')
    representation = ElementFactory(description, 'Representation', attrib={'language': 'en'})
    revision = ElementFactory(metadata, 'RevisionData')
    ElementFactory(revision, 'DateModified', text='2001-03-01T00:00:00')
    title = ElementFactory(representation, 'Title', text='TheTitle')
    units = ElementFactory(ds, 'Units')
    # add standard data that's not part of the units, e.g. metadata
    # TODO: what is required???
    # - TechnicalContacts, 
    
    # build the ABCD unit    
    for plant in plants:
        unit = ElementFactory(units, 'Unit')
        # TODO: get SourceInstitutionID from the prefs/metadata
        ElementFactory(unit, 'SourceInstitutionID', text='BBG')
        
        # TODO: get id divider from prefs/metadata
        divider = '.'
        # TODO: don't really understand the SourceID element
        ElementFactory(unit, 'SourceID', text='Bauble')
#        debug(xml_safe('%s%s%s' % (plant.accession.code, divider, plant.code)))
        unit_id = ElementFactory(unit, 'UnitID',
                                 text = xml_safe('%s%s%s' % (plant.accession.code, 
                                                             divider, plant.code)))
        # TODO: metadata -- <DateLastEdited>2001-03-01T00:00:00</DateLastEdited>
        identifications = ElementFactory(unit, 'Identifications')
        
        # scientific name identification
        identification = ElementFactory(identifications, 'Identification')
        result = ElementFactory(identification, 'Result')
        taxon_identified = ElementFactory(result, 'TaxonIdentified')
        higher_taxa = ElementFactory(taxon_identified, 'HigherTaxa')
        higher_taxon = ElementFactory(higher_taxa, 'HigherTaxon')
        higher_taxon_name = ElementFactory(higher_taxon, 'HigherTaxonName', 
                                           #text=xml_safe(plant.accession.species.genus.family))
                                           text=xml_safe(unicode(plant.accession.species.genus.family)))
        higher_taxon_rank = ElementFactory(higher_taxon, 'HigherTaxonRank', 
                                           text='familia')
        scientific_name = ElementFactory(taxon_identified, 'ScientificName')
        ElementFactory(scientific_name, 'FullScientificNameString', 
                       text=Species.str(plant.accession.species, authors=authors, markup=False))
        name_atomised = ElementFactory(scientific_name, 'NameAtomised')
        botanical = ElementFactory(name_atomised, 'Botanical')
        ElementFactory(botanical, 'GenusOrMonomial', text=xml_safe(plant.accession.species.genus))
        ElementFactory(botanical, 'FirstEpithet', text=xml_safe(plant.accession.species.sp))
        # TODO: handle more complex names
        ElementFactory(botanical, 'AuthorTeam', text=(xml_safe(plant.accession.species.sp_author)))
        
        # vernacular name identification
        # only include the default vernacular name, not all the vernacular names
        vernacular_name = plant.accession.species.default_vernacular_name
#        debug(vernacular_name)
        if vernacular_name is not None:
            identification = ElementFactory(identifications, 'Identification')
            result = ElementFactory(identification, 'Result')
            taxon_identified = ElementFactory(result, 'TaxonIdentified')
            ElementFactory(taxon_identified, 'InformalNameString', text=(xml_safe(vernacular_name)))
            #ElementFactory(taxon_identified, 'InformalNameString', text=(xml_safe(vernacular_name)),
            #               attrib={'language': vernacular_name.language})
        
        # TODO: handle verifiers/identifiers
        # TODO: RecordBasis
        # TODO: Gathering, make our collection records fit Gatherings
        # TODO: see BotanicalGardenUnit
            
    try:    
        assert validate(datasets), 'ABCD data not valid'
    except AssertionError, e:
        utils.message_dialog('ABCD data not valid')
        #utils.message_details_dialog('ABCD data not valid', etree.tostring(datasets))
        debug(etree.tostring(datasets))
        raise
        
    return ElementTree(datasets)


class ABCDImporter:

    def start(self, filenames=None):
        pass
        
    def run(self, filenames):
        pass
        
    
class ABCDExporter:
    
    def start(self, filename=None, plants=None):
        if filename == None: # no filename, ask the user
            d = gtk.FileChooserDialog("Choose a file to export to...", None,
                                      gtk.FILE_CHOOSER_ACTION_SAVE,
                                      (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                       gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            response = d.run()
            filename = d.get_filename()
            d.destroy()
            if response != gtk.RESPONSE_ACCEPT or filename == None:
                return
        self.run(filename, plants)
        
    
    def run(self, filename, plants=None):
        if filename == None:
            raise ValueError("filename can not be None")            
            
        # TODO: check if filename already exists give a message to the user
        
        # if plants is None then export all plants, this could be huge 
        # TODO: do something about this, like list the number of plants
        # to be returned and make sure this is what the user wants
        if plants == None:
            plants = plugins.tables["Plant"].select()
        data = plants_to_abcd(plants)
        # TODO: this needs to be changed to support the lxml XMLWriter
        raise NotImplementedError
        
        #f = open(filename, "w")
        #f.write(data)
        #f.close()
        
        
class ABCDImportTool(BaubleTool):
    category = "Import"
    label = "ABCD"

    @classmethod
    def start(cls):
        ABCDImporter().start()
    
    
class ABCDExportTool(BaubleTool):
    category = "Export"
    label = "ABCD"
    
    @classmethod
    def start(cls):
        ABCDExporter().start()
    

class ABCDImexPlugin(BaublePlugin):
    #tools = [ABCDImportTool, ABCDExportTool]
    tools = [ABCDExportTool]
    depends = ["PlantsPlugin"]
plugin = ABCDImexPlugin
            
            
__all__ = [DataSets, ABCDElement, ElementFactory, ABCDExporter, ABCDExportTool, plants_to_abcd]