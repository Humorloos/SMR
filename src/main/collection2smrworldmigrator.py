import json
import os
from typing import Dict, List

import main.consts as cts
from anki import Collection
from anki.utils import splitFields, intTime
import aqt
from main.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from main.dto.smrnotedto import SmrNoteDto
from main.smrworld import SmrWorld
from main.xmindimport import XmindImporter
from main.xnotemanager import XNoteManager


class Collection2SmrWorldMigrator:
    """
    This class serves for migrating old anki collections into the smr world.
    """

    def __init__(self):
        aqt.mw.col.models.setCurrent(aqt.mw.col.models.byName(cts.X_MODEL_NAME))
        self.collection = aqt.mw.col
        self.note_manager: XNoteManager = XNoteManager(aqt.mw.col)
        self.smr_world: SmrWorld = aqt.mw.smr_world

    @property
    def collection(self) -> Collection:
        return self._collection

    @collection.setter
    def collection(self, value: Collection):
        self._collection = value

    @property
    def note_manager(self) -> XNoteManager:
        return self._note_manager

    @note_manager.setter
    def note_manager(self, value: XNoteManager):
        self._note_manager = value

    @property
    def smr_world(self) -> SmrWorld:
        return self._smr_world

    @smr_world.setter
    def smr_world(self, value: SmrWorld):
        self._smr_world = value

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
        aqt.mw.progress.start(immediate=True, label="Updating...")
        deck_names_and_ids = self.note_manager.col.decks.all_names_and_ids()
        # empty dynamic decks to avoid xmind files being scattered over multiple decks
        for deck_name_and_id in deck_names_and_ids:
            if self.collection.decks.isDyn(deck_name_and_id.id):
                self.collection.sched.emptyDyn(deck_name_and_id.id)
        for deck_name_and_id in deck_names_and_ids:
            self._migrate_deck_2_smr_world(deck_name_and_id.id)
        self.smr_world.save()
        self.collection.save()
        aqt.mw.reset(guiOnly=True)
        aqt.mw.progress.finish()

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
        card_data = [{'note_id': row[0], 'fields': splitFields(row[1]), 'last_modified': row[2],
                      'card_id': row[3], 'card_order_number': row[4], 'tags': row[5]
                      } for
                     row in self.collection.db.execute("""SELECT DISTINCT 
        notes.id, flds, notes.mod, cards.id, cards.ord + 1, notes.tags
FROM cards
         INNER JOIN notes ON cards.nid = notes.id
WHERE did = ? and mid = ?""", smr_deck_id, self.note_manager.col.models.id_for_name(cts.X_MODEL_NAME))]
        files = self._get_deck_data(card_data)
        for file_path, notes in files.items():
            aqt.mw.progress.update(label="Registering file " + os.path.basename(file_path), maybeShow=False)
            aqt.mw.app.processEvents()
            importer = XmindImporter(col=self.collection, file=file_path, include_referenced_files=False)
            importer.initialize_import(user_inputs=DeckSelectionDialogUserInputsDTO(deck_id=smr_deck_id))
            notes_2_update = {n: importer.notes_2_import.pop(n) for n in list(importer.notes_2_import) if
                              n in notes}
            if notes_2_update:
                importer.tagModified = 'yes'
                importer.addUpdates(
                    rows=[[intTime(), self._collection.usn(), n.fieldsStr, n.tags[0], notes[k]['note_id'], n.fieldsStr]
                          for k, n in notes_2_update.items()])
                smr_notes_2_add = []
                smr_cards_2_update = []
                for edge_id in notes_2_update:
                    note_dict = notes[edge_id]
                    note_id = note_dict['note_id']
                    smr_notes_2_add.append(SmrNoteDto(
                        note_id=note_dict['note_id'], edge_id=edge_id, last_modified=note_dict['last_modified']))
                    for card in note_dict['cards']:
                        smr_cards_2_update.append((note_id, card['card_order_number']))
                self.smr_world.add_smr_notes(smr_notes_2_add)
                self.smr_world.update_smr_triples_card_ids(data=smr_cards_2_update, collection=self.collection)
            importer.import_notes_and_cards()
