# Script for generating the resources required for testing
import os
import shutil
from unittest.mock import MagicMock

import aqt
import tests.constants as cts
from anki import Collection
from conftest import generate_new_file, generate_new_tree
from smr.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from smr.template import add_x_model
from smr.xmindimport import XmindImporter
import smr.smrworld as smrworld
import smr.config as config


def main():
    # Get a copy of the original map files
    generate_new_file(src=cts.ORIGINAL_EXAMPLE_MAP_PATH, dst=cts.DEFAULT_EXAMPLE_MAP_PATH)
    generate_new_file(src=cts.ORIGINAL_GENERAL_PSYCHOLOGY_MAP_PATH, dst=cts.DEFAULT_GENERAL_PSYCHOLOGY_MAP_PATH)
    generate_new_file(src=cts.ORIGINAL_HYPERLINK_MEDIA_PATH, dst=cts.DEFAULT_HYPERLINK_MEDIA_PATH)
    generate_new_file(src=cts.DEFAULT_EXAMPLE_MAP_PATH, dst=cts.TEMPORARY_EXAMPLE_MAP_PATH)
    generate_new_file(src=cts.DEFAULT_GENERAL_PSYCHOLOGY_MAP_PATH, dst=cts.TEMPORARY_GENERAL_PSYCHOLOGY_MAP_PATH)
    generate_new_file(src=cts.DEFAULT_HYPERLINK_MEDIA_PATH, dst=cts.TEMPORARY_HYPERLINK_MEDIA_PATH)
    # Get an empty anki collection
    try:
        os.unlink(os.path.join(cts.EMPTY_COLLECTION_FUNCTION_PATH))
    except FileNotFoundError:
        pass
    try:
        shutil.rmtree(cts.EMPTY_COLLECTION_FUNCTION_MEDIA)
    except FileNotFoundError:
        pass
    collection = Collection(cts.EMPTY_COLLECTION_FUNCTION_PATH)
    add_x_model(collection)
    deck_id = collection.decks.id('testdeck')
    # Import the example map to the deck 'testdeck'
    aqt.mw = MagicMock()
    smr_world_path = os.path.join(cts.SMR_WORLD_PATH, cts.EMPTY_SMR_WORLD_NAME)
    try:
        os.unlink(smr_world_path)
    except FileNotFoundError:
        pass
    smrworld.SMR_WORLD_PATH = smr_world_path
    config.USER_PATH = cts.SMR_WORLD_PATH
    smr_world = smrworld.SmrWorld()
    smr_world.set_up()
    aqt.mw.smr_world = smr_world
    aqt.mw.return_value = aqt.mw
    importer = XmindImporter(col=collection, file=cts.TEMPORARY_EXAMPLE_MAP_PATH)
    importer.initialize_import(DeckSelectionDialogUserInputsDTO(deck_id=deck_id))
    importer.finish_import()
    # Save smr world to smr world with example map
    importer.smr_world.close()
    shutil.copy(src=smr_world_path, dst=cts.ORIGINAL_SMR_WORLD_WITH_EXAMPLE_MAP_PATH)
    # save collection to collection with example map
    save_collection(collection, collection_path=cts.ORIGINAL_COLLECTION_WITH_EXAMPLE_MAP_PATH,
                    media_dir=cts.ORIGINAL_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    # make changes to the collection
    # change fields
    collection.reopen()
    collection_changes = {
        " testdeck::example_general_psychology::general_psychology ": {
            "{": "general psychologynew questionemotionsperception{"
        },
        " testdeck::example_map::biological_psychology ": {
            '|{{{{{{': 'biological psychology<li>investigates: information transfer and processing</li><li>requires: '
                       'neurotransmitters <img src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: '
                       'biogenic amines</li>former imageSerotonin new|{{{{{{',
            '|{{{{{{{{': 'biological psychology<li>investigates: information transfer and '
                         'processing</li><li>requires: neurotransmitters <img '
                         'src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic amines</li><li> '
                         '<img src="attachments09r2e442o8lppjfeblf7il2rmd.png">: '
                         'Serotonin</li>affectsSleepformerly pain|{{{{{{{{',
            '|{|': 'biological psychology<li>investigates: information transfer and processing</li>modulated '
                   'byenzymes&nbsp;<img src="paste-cbf726a37a2fa4c403412f84fd921145335bd0b0.jpg'
                   '">|{|',
            '|{|{{{|': 'biological psychology<li>investigates: information transfer and processing</li><li>modulated '
                       'by: enzymes</li><li>example: MAO</li>splits '
                       'upSerotonindopamineadrenaline|{|{{{|',
            '|{|{{{|{': 'biological psychology<li>investigates: information transfer and '
                         'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits up: Serotonin, '
                         'dopamine, adrenaline, noradrenaline</li>are changed questionbiogenic '
                         'amines|{|{{{|{'
        },
        " testdeck::example_map::clinical_psychology ": {
            '{': 'clinical psychologyinvestigatespsychological disorders alt{',
            '{{{': 'clinical psychology<li>investigates: psychological disorders</li>examplesnew '
                   'disorderschizophrenia{{{',
            '{{{{{': 'clinical psychology<li>investigates: psychological disorders</li><li>examples: anxiety '
                     'disorders</li>example answer 1phobias{{{{{',
            '{{{|{': 'clinical psychology<li>investigates: psychological disorders</li><li>examples: '
                     'schizophrenia</li>possible causes answer 2biochemical factors{{{|{'
        }
    }
    data = [(fields, tag, sort_id) for tag, changes in collection_changes.items()
            for sort_id, fields in changes.items()]
    collection.db.executemany("UPDATE NOTES SET flds = ?, mod = mod + 1 WHERE tags = ? and sfld = ?", data)
    collection.media.add_file(os.path.join(cts.TEST_COLLECTIONS_PATH, cts.NEW_IMAGE_NAME))
    # save collection to collection with example map changes
    save_collection(collection, media_dir=cts.ORIGINAL_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA,
                    collection_path=cts.ORIGINAL_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_PATH)


def save_collection(collection, media_dir, collection_path):
    collection.close()
    generate_new_file(src=collection.path, dst=collection_path)
    generate_new_tree(src=collection.media._dir, dst=media_dir)


# Call the main function
if __name__ == "__main__":
    main()
