#
# garden plugin 
#

import os, sys
from bauble.plugins import BaublePlugin, plugins, tables
from bauble.plugins.garden.accession import Accession, AccessionEditor, \
    AccessionInfoBox, acc_context_menu, acc_markup_func, SourceInfoBox
from bauble.plugins.garden.location import Location, LocationEditor,\
    LocationInfoBox, loc_context_menu, loc_markup_func
from bauble.plugins.garden.plant import Plant, PlantHistory, PlantEditor, \
    PlantInfoBox, plant_context_menu, plant_markup_func
#from reference import Reference, ReferenceEditor
from bauble.plugins.garden.source import Donation, Collection, \
    source_markup_func
from bauble.plugins.garden.donor import Donor, DonorEditor, DonorInfoBox, \
    donor_context_menu

# other ideas:
# - cultivation table
# - conservation table

class GardenPlugin(BaublePlugin):

    editors = [AccessionEditor, LocationEditor, PlantEditor, DonorEditor]

    tables = [Accession, Location, Plant, Donor, Donation, Collection,
              PlantHistory]
    
    @classmethod
    def init(cls):
        # add joins        
        
        #acc_join = MultipleJoin('Accession', joinMethodName="accessions", 
        #                        joinColumn='species_id')            
        #tables["Species"].sqlmeta.addJoin(acc_join)
        #table["Species"].mapping.add_property('accessions', relation('accession'))
        
        if "SearchViewPlugin" in plugins:
            from bauble.plugins.searchview.search import SearchMeta
            #from bauble.plugins.searchview.search import ResultsMeta
            from bauble.plugins.searchview.search import SearchView
            
            search_meta = SearchMeta("Accession", ["code"], "code")
            SearchView.register_search_meta("accession", search_meta)
            SearchView.register_search_meta("acc", search_meta)      
            SearchView.view_meta["Accession"].set(children="plants",                                                   
                                                  infobox=AccessionInfoBox,
                                                  context_menu=acc_context_menu,
                                                  markup_func=acc_markup_func)
            
            search_meta = SearchMeta("Location", ["site"], "site")
            SearchView.register_search_meta("location", search_meta)
            SearchView.register_search_meta("loc", search_meta)            
            SearchView.view_meta["Location"].set(children="plants",
                                                 infobox=LocationInfoBox,
                                                 context_menu=loc_context_menu,
                                                 markup_func=loc_markup_func)

            search_meta = SearchMeta('Plant', ["code"], "code")
            SearchView.register_search_meta('plant', search_meta)
            SearchView.view_meta["Plant"].set(infobox=PlantInfoBox,
                                              context_menu=plant_context_menu,
                                              markup_func=plant_markup_func)
            
            search_meta = SearchMeta('Donor', ['name'])
            SearchView.register_search_meta('donor', search_meta)
            SearchView.register_search_meta('don', search_meta)
            SearchView.view_meta["Donor"].set(children="donations", 
                                              infobox=DonorInfoBox,
                                              context_menu=donor_context_menu)

            SearchView.view_meta['Donation'].set(infobox=SourceInfoBox,
                                                 markup_func=source_markup_func)
            SearchView.view_meta['Collection'].set(infobox=SourceInfoBox,
                                                 markup_func=source_markup_func)

            # done here b/c the Species table is not part of this plugin
            SearchView.view_meta["Species"].child = "accessions"
    
    
    depends = ("PlantsPlugin","GeographyPlugin")

plugin = GardenPlugin