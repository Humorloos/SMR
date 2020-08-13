# creates support files for tests

import os
import pickle
import sys
import owlready2

from bs4 import BeautifulSoup
from PyQt5 import QtWidgets

from tests.shared import getEmptyCol
from pylib.anki import Collection

from consts import ADDON_PATH
from xmindimport import XmindImporter
from smr import XManager, register_referenced_x_managers

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


def getSheetImports():
    col = getEmptyCol()
    map = EXAMPLE_MAP_PATH
    xmindImporter = XmindImporter(col=col, file=map)
    sheetImports = register_referenced_x_managers(xmindImporter._x_managers['root'])[1]
    pickle.dump(sheetImports, open(
        os.path.join(SUPPORT_PATH, 'sheetSelectors', 'sheetImports.p'), 'wb'))
    return pickle.load(
        open(os.path.join(SUPPORT_PATH, 'sheetSelectors', 'sheetImports.p'),
             'rb'))


def getSelectedSheets():
    app = QtWidgets.QApplication(sys.argv)
    sheetImports = pickle.load(
        open(os.path.join(SUPPORT_PATH, 'sheetselectors', 'sheetImports.p'),
             "rb"))
    Dialog = MultiSheetSelector(sheetImports)
    Dialog.show()
    app.exec_()
    selectedSheets = Dialog.get_inputs()['sheetImports']
    pickle.dump(selectedSheets, open(
        os.path.join(SUPPORT_PATH, 'xmindImporter', 'selectedSheets.p'), 'wb'))
    return pickle.load(
        open(os.path.join(SUPPORT_PATH, 'xmindImporter', 'selectedSheets.p'),
             'rb'))


def getSheetBiologicalPsychology():
    col = getEmptyCol()
    map = EXAMPLE_MAP_PATH
    xmindImporter = XmindImporter(col=col, file=map)
    register_referenced_x_managers(xmindImporter._x_managers[0])
    sheets = xmindImporter._x_managers[0].sheets
    with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                           'sheet_biological_psychology.xml'), 'w') as file:
        file.write(str(sheets['biological psychology']))
    with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                           'sheet_biological_psychology.xml'), 'r') as file:
        return BeautifulSoup(file.read(), features='html.parser')


def getOntologyBiologicalPsychology():
    colPath = os.path.join(SUPPORT_PATH, 'collection.anki2')
    col = Collection(colPath)
    map = EXAMPLE_MAP_PATH
    importer = XmindImporter(col=col, file=map)
    importer._deck_id = '1'
    importer._current_sheet_import = 'biological psychology'
    importer._active_manager = importer._x_managers[0]
    importer._x_managers.append(
        XManager(os.path.join(
            ADDON_PATH, 'resources', 'example_general_psychology.xmind')))
    importer.import_map()
    importer._current_sheet_import = 'clinical psychology'
    importer.import_map()
    importer._active_manager = importer._x_managers[1]
    importer._current_sheet_import = 'general psychology'
    importer.import_map()
    output = os.path.join(SUPPORT_PATH, 'ontology_biological_psychology.rdf')
    importer.__onto.save(file=output, format="rdfxml")
    return owlready2.get_ontology(output).load()


def getNoteData():
    colPath = os.path.join(SUPPORT_PATH, 'collection.anki2')
    col = Collection(colPath)
    map = EXAMPLE_MAP_PATH
    importer = XmindImporter(col=col, file=map)
    importer._deck_id = '1'
    importer._current_sheet_import = 'biological psychology'
    importer._active_manager = importer._x_managers[0]
    importer._x_managers.append(
        XManager(os.path.join(
            ADDON_PATH, 'resources', 'example_general_psychology.xmind')))
    importer.import_map()
    importer._current_sheet_import = 'clinical psychology'
    importer.import_map()
    importer._active_manager = importer._x_managers[1]
    importer._current_sheet_import = 'general psychology'
    importer.import_map()
    noteData = importer.__onto.getNoteData([(328, 346, 325)])
    pickle.dump(noteData, open(
        os.path.join(SUPPORT_PATH, 'xmindImporter', 'noteData.p'), 'wb'))
    return pickle.load(
        open(os.path.join(SUPPORT_PATH, 'xmindImporter', 'noteData.p'),
             'rb'))

sheetImports = getSheetImports()
selectedSheets = getSelectedSheets()
sheetBiologicalPsychology = getSheetBiologicalPsychology()
ontologyBiologicalPsychology = getOntologyBiologicalPsychology()
noteData = getNoteData()

# onto_sqlite3 = getOntologyBiologicalPsychology()
# onto_sqlite3.world.set_backend(filename=os.path.join(SUPPORT_PATH,
#                                               'test_onto.sqlite3'))
# onto_sqlite3.world.save()