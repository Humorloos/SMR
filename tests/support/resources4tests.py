# Script for generating the resources required for testing
import os
import shutil
from unittest.mock import MagicMock
from zipfile import ZipFile

from bs4 import BeautifulSoup

import aqt
import tests.constants as cts
from anki import Collection
from conftest import generate_new_file, generate_new_tree
from smr.consts import SMR_CONFIG
from smr.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from smr.template import add_x_model
from smr.xmindimport import XmindImporter
import smr.smrworld as smrworld
import smr.config as config


def main():
    # Get a copy of the original map files
    generate_new_file(src=cts.PATH_EXAMPLE_MAP_ORIGINAL, dst=cts.PATH_EXAMPLE_MAP_DEFAULT)
    generate_new_file(src=cts.PATH_MAP_GENERAL_PSYCHOLOGY_ORIGINAL, dst=cts.PATH_MAP_GENERAL_PSYCHOLOGY_DEFAULT)
    generate_new_file(src=cts.PATH_HYPERLINK_MEDIA_ORIGINAL, dst=cts.PATH_HYPERLINK_MEDIA_DEFAULT)
    # Get a copy of the default map files for temporary maps
    generate_new_file(src=cts.PATH_EXAMPLE_MAP_DEFAULT, dst=cts.PATH_EXAMPLE_MAP_TEMPORARY)
    generate_new_file(src=cts.PATH_MAP_GENERAL_PSYCHOLOGY_DEFAULT, dst=cts.PATH_MAP_GENERAL_PSYCHOLOGY_TEMPORARY)
    generate_new_file(src=cts.PATH_HYPERLINK_MEDIA_DEFAULT, dst=cts.PATH_HYPERLINK_MEDIA_TEMPORARY)
    generate_new_file(src=cts.PATH_NEW_MEDIA_ORIGINAL, dst=cts.PATH_NEW_MEDIA_TEMPORARY)
    # Get a copy of the new media file for the directory with changes
    generate_new_file(src=cts.PATH_NEW_MEDIA_ORIGINAL, dst=cts.PATH_NEW_MEDIA_CHANGED)
    # Extract to maps directory
    try:
        os.unlink(cts.PATH_CONTENT_EXAMPLE_MAP)
    except FileNotFoundError:
        pass
    open(cts.PATH_CONTENT_EXAMPLE_MAP, 'x')
    with open(cts.PATH_CONTENT_EXAMPLE_MAP, 'w') as content_file:
        content_file.write(BeautifulSoup(ZipFile(cts.PATH_EXAMPLE_MAP_DEFAULT, 'r').read(
            cts.NAME_CONTENT), features="html.parser").prettify())
    try:
        os.unlink(cts.PATH_CONTENT_GENERAL_PSYCHOLOGY)
    except FileNotFoundError:
        pass
    open(cts.PATH_CONTENT_GENERAL_PSYCHOLOGY, 'x')
    with open(cts.PATH_CONTENT_GENERAL_PSYCHOLOGY, 'w') as content_file:
        content_file.write(BeautifulSoup(ZipFile(cts.PATH_MAP_GENERAL_PSYCHOLOGY_DEFAULT, 'r').read(
            cts.NAME_CONTENT), features="html.parser").prettify())
    # Get an empty anki collection
    try:
        os.unlink(os.path.join(cts.TEMPORARY_EMPTY_COLLECTION_FUNCTION_PATH))
    except FileNotFoundError:
        pass
    try:
        shutil.rmtree(cts.TEMPORARY_EMPTY_COLLECTION_FUNCTION_MEDIA)
    except FileNotFoundError:
        pass
    collection = Collection(cts.TEMPORARY_EMPTY_COLLECTION_FUNCTION_PATH)
    add_x_model(collection)
    collection.set_config('smr', SMR_CONFIG)
    deck_id = collection.decks.id(cts.TEST_DECK_NAME)
    # Import the example map to the deck 'testdeck'
    aqt.mw = MagicMock()
    smr_world_path = os.path.join(cts.SMR_WORLD_DIRECTORY, cts.EMPTY_SMR_WORLD_NAME)
    try:
        os.unlink(smr_world_path)
    except FileNotFoundError:
        pass
    smrworld.SMR_WORLD_PATH = smr_world_path
    config.USER_PATH = cts.SMR_WORLD_DIRECTORY
    smr_world = smrworld.SmrWorld()
    smr_world.set_up()
    aqt.mw.smr_world = smr_world
    aqt.mw.return_value = aqt.mw
    importer = XmindImporter(col=collection, file=cts.PATH_EXAMPLE_MAP_TEMPORARY)
    importer.initialize_import(DeckSelectionDialogUserInputsDTO(deck_id=deck_id))
    importer.finish_import()
    # Import the map general psychology to the same deck
    importer = XmindImporter(col=collection, file=cts.PATH_MAP_GENERAL_PSYCHOLOGY_TEMPORARY)
    importer.initialize_import(DeckSelectionDialogUserInputsDTO(deck_id=deck_id))
    importer.finish_import()
    # Save smr world to smr world with example map
    importer.smr_world.close()
    shutil.copy(src=smr_world_path, dst=cts.ORIGINAL_SMR_WORLD_WITH_EXAMPLE_MAP_PATH)
    # save collection to collection with example map
    save_collection(collection, collection_path=cts.DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_PATH,
                    media_dir=cts.DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    # make changes to the collection
    # change fields
    collection.reopen()
    collection_changes = {
        " testdeck::example_general_psychology::general_psychology ": {
            "{": """\
general psychologynew questionemotionsperception{"""
        },
        " testdeck::example_map::biological_psychology ": {
            '|{{{{{{': """\
biological psychology<li>investigates: information transfer and processing</li><li>requires: neurotransmitters <img \
src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic amines</li>former imageSerotonin \
new|{{{{{{""",
            '|{{{{{{{{': """\
biological psychology<li>investigates: information transfer and processing</li><li>requires: neurotransmitters <img \
src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic amines</li><li> <img \
src="attachments09r2e442o8lppjfeblf7il2rmd.png">: Serotonin</li>affectsSleepformerly pain\
|{{{{{{{{""",
            '|{|': f"""\
biological psychology<li>investigates: information transfer and processing</li>modulated byenzymes<div><img \
src="{cts.NEW_IMAGE_NAME}"><br></div>|{{|""",  # double curly brace here because of format string
            '|{|{{{|': """\
biological psychology<li>investigates: information transfer and processing</li><li>modulated by: enzymes</li>\
<li>example: MAO</li>splits upSerotonindopamineadrenaline|{|{{{|""",
            '|{|{{{|{': """\
biological psychology<li>investigates: information transfer and processing</li><li>modulated by: enzymes</li>\
<li>example: MAO</li><li>splits up: Serotonin, dopamine, adrenaline, noradrenaline</li>are changed question\
biogenic amines|{|{{{|{""",
            '|{|{|{{': f"""\
biological psychology<li>investigates: information transfer and processing</li><li>modulated by: enzymes</li>\
<li>completely unrelated animation: (media)</li>means in englishvirtue [sound:{cts.NEW_MEDIA_NAME}]\
|{{|{{|{{{{"""  # double curly brace here because of format string
        },
        " testdeck::example_map::clinical_psychology ": {
            '{': """\
clinical psychologyinvestigatespsychological disorders alt{""",
            '{{{': """\
clinical psychology<li>investigates: psychological disorders</li>examplesnew disorderschizophrenia\
{{{""",
            '{{{{{': """
clinical psychology<li>investigates: psychological disorders</li><li>examples: anxiety disorders</li>example answer 1\
phobias{{{{{""",
            '{{{|{': """\
clinical psychology<li>investigates: psychological disorders</li><li>examples: schizophrenia</li>possible causes \
answer 2biochemical factors{{{|{"""
        }
    }
    change_collection(collection, collection_changes)
    new_media = [os.path.join(cts.TEST_COLLECTIONS_DIRECTORY, cts.NEW_IMAGE_NAME), cts.PATH_NEW_MEDIA_ORIGINAL]
    for media_path in new_media:
        collection.media.add_file(media_path)
    # save collection to collection with example map changes
    save_collection(collection, media_dir=cts.DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA,
                    collection_path=cts.DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    # generate collection with new answer
    generate_new_file(
        cts.DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_PATH, cts.DEFAULT_NEW_ANSWER_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    generate_new_tree(
        cts.DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_MEDIA, cts.DEFAULT_NEW_ANSWER_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    col = Collection(cts.DEFAULT_NEW_ANSWER_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    change = {
        " testdeck::example_map::biological_psychology ": {
            '|{|{{{|{': 'biological psychology<li>investigates: information transfer and '
                         'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits up: Serotonin, '
                         'dopamine, adrenaline, noradrenaline</li>arebiogenic '
                         'aminesadded answer|{|{{{|{'
        }
    }
    change_collection(collection=col, collection_changes=change)
    col.close()
    # generate collection with removed center node
    generate_new_file(
        cts.DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_PATH, cts.DEFAULT_REMOVED_CENTER_NODE_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    generate_new_tree(
        cts.DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_MEDIA,
        cts.DEFAULT_REMOVED_CENTER_NODE_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    col = Collection(cts.DEFAULT_REMOVED_CENTER_NODE_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    change = {
        " testdeck::example_map::biological_psychology ": {
            '|': 'biological psychologyinvestigatesinformation transfer and processing'
                 '|'
        }
    }
    change_collection(collection=col, collection_changes=change)
    col.close()


def change_collection(collection, collection_changes):
    data = [(fields, tag, sort_id) for tag, changes in collection_changes.items()
            for sort_id, fields in changes.items()]
    collection.db.executemany("UPDATE NOTES SET flds = ?, mod = mod + 1 WHERE tags = ? and sfld = ?", data)


def save_collection(collection, media_dir, collection_path):
    collection.close()
    generate_new_file(src=collection.path, dst=collection_path)
    generate_new_tree(src=collection.media._dir, dst=media_dir)


# Call the main function
if __name__ == "__main__":
    main()
