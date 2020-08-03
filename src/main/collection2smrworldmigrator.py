from anki import Collection
from main.smrworld import SmrWorld
from main.xnotemanager import XNoteManager
from main.xontology import XOntology


class Collection2SmrWorldMigrator:
    """
    This class serves for migrating old anki collections into the smr world.
    """
    def __init__(self, col: Collection, smr_world: SmrWorld):
        self.note_manager = XNoteManager(col)
        self.smr_world = smr_world

    def migrate_collection_2_smr_world(self):
        """
        Finds all decks with anki notes and migrates each deck into the smr world
        """
        smr_deck_ids = self.note_manager.get_smr_deck_ids()
        for smr_deck_id in smr_deck_ids:
            self.migrate_deck_2_smr_world(smr_deck_id)

    def migrate_deck_2_smr_world(self, smr_deck_id):
        """
        - creates an ontology for the specified deck id and links it to the deck in the smr world
        - finds all notes in the deck with the specified id
        - migrates all notes into the smr world
        :param smr_deck_id: the id of the deck to migrate
        """
        ontology = XOntology(smr_deck_id, self.smr_world)
        # add ontology to smr world
        self.smr_world.add_ontology_lives_in_deck(ontology_base_iri=ontology.base_iri, deck_id=smr_deck_id)




# add file to smr world
# add sheets to smr world
# add edges to smr world
# add nodes to smr world
# add triples to smr world
# add notes to smr world
# add cards to smr world
# add media to smr world
# add concepts to ontology
# change tags to new tags

