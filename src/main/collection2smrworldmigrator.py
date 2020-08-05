import json
from typing import Optional, Dict, List, Tuple

from anki import Collection
from anki.utils import splitFields
from main.smrworld import SmrWorld
from main.xmanager import XManager, get_node_content, get_parent_node
from main.xmindimport import XmindImporter
from main.xnotemanager import XNoteManager, order_number_from_sort_id_character, FieldTranslator
from main.xontology import XOntology, connect_concepts
import main.consts as cts


class Collection2SmrWorldMigrator:
    """
    This class serves for migrating old anki collections into the smr world.
    """

    def __init__(self, col: Collection, smr_world: SmrWorld):
        col.models.setCurrent(col.models.byName(cts.X_MODEL_NAME))
        self._note_manager: XNoteManager = XNoteManager(col)
        self._smr_world: SmrWorld = smr_world
        self._field_translator = FieldTranslator()
        self._current_onto: Optional[XOntology] = None

    @staticmethod
    def _get_deck_data(smr_cards_in_deck: List[Dict]) -> Dict:
        """
        Builds a hierarchical dictionary structure from the relevant data for migration of one deck into the smr world
        :param smr_cards_in_deck: list of Dictionaries returned by the anki collection for the
        :return: A dictionary of dictionaries containing cards in notes in sheets in files
        """
        files = {}
        for card in smr_cards_in_deck:
            card['meta'] = json.loads(card['fields'][23])
            try:
                # add card to note's card list
                files[card['meta']['path']][card['meta']['sheetId']][card['note_id']]['cards'].append(card)
            except KeyError:
                try:
                    # if no note yet, add note and card to sheet's note dict
                    files[card['meta']['path']][card['meta']['sheetId']][card['note_id']] = {'cards': [card]}
                except KeyError:
                    try:
                        # if no sheet yet, add sheet, note, and card to file's sheet dict
                        files[card['meta']['path']][card['meta']['sheetId']] = {card['note_id']: {'cards': [card]}}
                    except KeyError:
                        # if no file yet, add file, sheet, note, and card to file dict
                        files[card['meta']['path']] = {card['meta']['sheetId']: {card['note_id']: {'cards': [card]}}}
                finally:
                    # if note was new for sheet, add note fields from card to note dict
                    files[card['meta']['path']][card['meta']['sheetId']][card['note_id']][
                        'fields'] = card['fields']
                    files[card['meta']['path']][card['meta']['sheetId']][card['note_id']][
                        'meta'] = card['meta']
                    files[card['meta']['path']][card['meta']['sheetId']][card['note_id']][
                        'last_modified'] = card['last_modified']
            finally:
                # in all cases remove note fields from card dict
                del card['fields']
                del card['note_id']
                del card['last_modified']
                del card['meta']
                del card['tags']
        return files

    def migrate_collection_2_smr_world(self) -> None:
        """
        Finds all decks with anki notes and migrates each deck into the smr world
        """
        deck_names_and_ids = self._note_manager.col.decks.all_names_and_ids()
        for deck_name_and_id in deck_names_and_ids:
            self._migrate_deck_2_smr_world(deck_name_and_id.id)
        self._smr_world.save()
        self._note_manager.save_col()

    def _migrate_deck_2_smr_world(self, smr_deck_id: int) -> None:
        """
        - creates an ontology for the specified deck id and links it to the deck in the smr world
        - finds all files in the deck with the specified id
        - migrates all files into the smr world
        - migrates all sheets in each file into the smr world with their root node
        - migrates all notes, with their edges in each sheet into the smr world
        - finally, migrates all cards with their nodes for each note to the smr world
        :param smr_deck_id: the id of the deck to migrate
        """
        self._current_onto = XOntology(smr_deck_id, self._smr_world)
        card_data = [{'note_id': row[0], 'fields': splitFields(row[1]), 'last_modified': row[2],
                                          'card_id': row[3], 'card_order_number': row[4], 'tags': row[5]
                                          } for
                                         row in self._note_manager.col.db.execute("""SELECT DISTINCT 
        notes.id, flds, notes.mod, cards.id, cards.ord + 1, notes.tags
FROM cards
         INNER JOIN notes ON cards.nid = notes.id
WHERE did = ? and mid = ?""", smr_deck_id, self._note_manager.col.models.id_for_name(cts.X_MODEL_NAME))]
        files = self._get_deck_data(card_data)
        for file_path, sheets in files.items():
            importer = XmindImporter(col=self._note_manager.col, file=file_path)
            # add file to smr world
            x_manager = XManager(file_path)
            self._smr_world.add_xmind_file(x_manager=x_manager, deck_id=self._current_onto.get_deck_id())
            for sheet_id, notes in sheets.items():
                sheet_name = next(sheet_name for sheet_name, sheet_content in x_manager.get_sheets().items() if
                                  sheet_content['tag']['id'] == sheet_id)
                # add sheets to smr world
                self._smr_world.add_xmind_sheet(x_manager=x_manager, sheet_name=sheet_name)
                # change tags to hierarchical tags
                new_tag = x_manager.acquire_anki_tag(
                    deck_name=self._note_manager.col.db.first("select name from decks where id = ?", smr_deck_id)[0],
                    sheet_name=sheet_name)
                self._note_manager.col.db.executemany("update notes set tags = ? where id = ?",
                                                      [(new_tag, note_id) for note_id in notes.keys()])
                # sort notes by sort field
                notes = {k: v for k, v in sorted(notes.items(), key=lambda item: item[1]['fields'][22])}
                # add root concept to ontology
                parent_nodes = [get_parent_node(
                    x_manager.get_tag_by_id(list(notes.values())[0]['meta']['questionId']))]
                root_content = get_node_content(parent_nodes[0])
                parent_concepts = [self._current_onto.concept_from_node_content(
                    node_content=root_content, node_is_root=True)]
                # add root concept media to smr world
                self._smr_world.add_image_and_media_to_collection_and_self(
                    content=root_content, collection=self._note_manager.col, x_manager=x_manager)
                # add root concept to smr world
                self._smr_world.add_xmind_node(
                    node=parent_nodes[0], node_content=root_content, ontology_storid=parent_concepts[0].storid,
                    sheet_id=sheet_id, order_number=1)
                for note_id, note in notes.items():
                    # add relationship to ontology
                    edge = x_manager.get_tag_by_id(note['meta']['questionId'])
                    edge_content = get_node_content(edge)
                    relationship_class_name = self._field_translator.class_from_content(edge_content)
                    relationship_property = self._current_onto.add_relation(relationship_class_name)
                    # add edge image and media to the anki collection
                    self._smr_world.add_image_and_media_to_collection_and_self(
                        content=edge_content, collection=self._note_manager.col, x_manager=x_manager)
                    # add edge to smr world
                    self._smr_world.add_xmind_edge(
                        edge=edge, edge_content=edge_content, sheet_id=sheet_id,
                        order_number=order_number_from_sort_id_character(note['fields'][22][-1]),
                        ontology_storid=relationship_property.storid)
                    # add answer concepts to ontology
                    child_nodes = [x_manager.get_tag_by_id(a['answerId']) for a in note['meta']['answers']]
                    child_node_contents = [get_node_content(n) for n in child_nodes]
                    child_concepts = [self._current_onto.concept_from_node_content(node_content=c, node_is_root=False)
                                      for c in child_node_contents]
                    for child_node, child_node_content, child_concept, card in zip(
                            child_nodes, child_node_contents, child_concepts, note['cards']):
                        # add node image and media to smr world and collection
                        self._smr_world.add_image_and_media_to_collection_and_self(
                            content=child_node_content, collection=self._note_manager.col, x_manager=x_manager)
                        # add nodes to smr world
                        self._smr_world.add_xmind_node(
                            node=child_node, node_content=child_node_content, ontology_storid=child_concept.storid,
                            sheet_id=sheet_id, order_number=card['card_order_number'])
                        for pc, pn in zip(parent_concepts, parent_nodes):
                            # connect parent and child in ontology
                            connect_concepts(child_thing=child_concept, parent_thing=pc,
                                             relationship_class_name=relationship_class_name)
                            # add triples to smr world
                            self._smr_world.add_smr_triple(parent_node_id=pn['id'], edge_id=edge['id'],
                                                           child_node_id=child_node['id'], card_id=card['card_id'])
                    # add note to smr world
                    self._smr_world.add_smr_note(note_id=note_id, edge_id=edge['id'],
                                                 last_modified=note['last_modified'])
