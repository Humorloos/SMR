import json
import os
from typing import Optional, Dict, List

import main.consts as cts
from anki.utils import splitFields, intTime
from aqt import AnkiQt
from main.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from main.smrworld import SmrWorld
from main.xmindimport import XmindImporter
from main.xnotemanager import XNoteManager, FieldTranslator
from main.xontology import XOntology


class Collection2SmrWorldMigrator:
    """
    This class serves for migrating old anki collections into the smr world.
    """

    def __init__(self, mw: AnkiQt):
        mw.col.models.setCurrent(mw.col.models.byName(cts.X_MODEL_NAME))
        self._collection = mw.col
        self._note_manager: XNoteManager = XNoteManager(mw.col)
        self._smr_world: SmrWorld = mw.smr_world
        self._field_translator = FieldTranslator()
        self._current_onto: Optional[XOntology] = None
        self._mw = mw

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
                files[card['meta']['path']][card['meta']['questionId']]['cards'].append(card)
            except KeyError:
                try:
                    files[card['meta']['path']][card['meta']['questionId']] = {'cards': [card]}
                except KeyError:
                    files[card['meta']['path']] = {card['meta']['questionId']: {'cards': [card]}}
            finally:
                # add note fields from card to note dict
                files[card['meta']['path']][card['meta']['questionId']]['fields'] = card['fields']
                files[card['meta']['path']][card['meta']['questionId']]['meta'] = card['meta']
                files[card['meta']['path']][card['meta']['questionId']]['last_modified'] = card['last_modified']
                files[card['meta']['path']][card['meta']['questionId']]['note_id'] = card['note_id']
                # remove note fields from card dict
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
        self._mw.progress.start(immediate=True, label="Updating...")
        deck_names_and_ids = self._note_manager.col.decks.all_names_and_ids()
        # empty dynamic decks to avoid xmind files being scattered over multiple decks
        for deck_name_and_id in deck_names_and_ids:
            if self._collection.decks.isDyn(deck_name_and_id.id):
                self._collection.sched.emptyDyn(deck_name_and_id.id)
        for deck_name_and_id in deck_names_and_ids:
            self._migrate_deck_2_smr_world(deck_name_and_id.id)
        self._smr_world.save()
        self._collection.save()
        self._mw.reset(guiOnly=True)
        self._mw.progress.finish()

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
                     row in self._collection.db.execute("""SELECT DISTINCT 
        notes.id, flds, notes.mod, cards.id, cards.ord + 1, notes.tags
FROM cards
         INNER JOIN notes ON cards.nid = notes.id
WHERE did = ? and mid = ?""", smr_deck_id, self._note_manager.col.models.id_for_name(cts.X_MODEL_NAME))]
        files = self._get_deck_data(card_data)
        for file_path, notes in files.items():
            self._mw.progress.update(label="Registering file " + os.path.basename(file_path), maybeShow=False)
            self._mw.app.processEvents()
            importer = XmindImporter(col=self._collection, file=file_path, include_referenced_files=False)
            importer.initialize_import(user_inputs=DeckSelectionDialogUserInputsDTO(deck_id=smr_deck_id))
            notes_2_update = {n: importer.notes_2_import.pop(n) for n in list(importer.notes_2_import) if
                              n in notes}
            if notes_2_update:
                importer.tagModified = 'yes'
                importer.addUpdates(
                    rows=[[intTime(), self._collection.usn(), n.fieldsStr, n.tags[0], notes[k]['note_id'], n.fieldsStr]
                          for k, n in notes_2_update.items()])
                for edge_id in notes_2_update:
                    note_dict = notes[edge_id]
                    note_id = note_dict['note_id']
                    self._smr_world.add_smr_notes(note_id=note_id, edge_id=edge_id,
                                                  last_modified=notes[edge_id]['last_modified'])
                    for card in note_dict['cards']:
                        self._smr_world.update_smr_triples_card_ids(note_id=note_id, order_number=card[
                            'card_order_number'], card_id=card['card_id'])
            importer.import_notes_and_cards()
