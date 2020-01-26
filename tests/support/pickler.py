# creates support files for tests

import os
import pickle
import sys
import owlready2

from bs4 import BeautifulSoup
from PyQt5 import QtWidgets

from tests.shared import getEmptyCol
from anki import Collection

from XmindImport.consts import ADDON_PATH
from XmindImport.xmindimport import XmindImporter
from XmindImport.sheetselectors import MultiSheetSelector
from XmindImport.xmanager import XManager

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


def getSheetImports():
    col = getEmptyCol()
    map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
    xmindImporter = XmindImporter(col=col, file=map)
    sheetImports = xmindImporter.getRefManagers(xmindImporter.xManagers['root'])[1]
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
    selectedSheets = Dialog.getInputs()['sheetImports']
    pickle.dump(selectedSheets, open(
        os.path.join(SUPPORT_PATH, 'xmindImporter', 'selectedSheets.p'), 'wb'))
    return pickle.load(
        open(os.path.join(SUPPORT_PATH, 'xmindImporter', 'selectedSheets.p'),
             'rb'))


def getSheetBiologicalPsychology():
    col = getEmptyCol()
    map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
    xmindImporter = XmindImporter(col=col, file=map)
    xmindImporter.getRefManagers(xmindImporter.xManagers[0])
    sheets = xmindImporter.xManagers[0].sheets
    with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                           'sheet_biological_psychology.xml'), 'w') as file:
        file.write(str(sheets['biological psychology']))
    with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                           'sheet_biological_psychology.xml'), 'r') as file:
        return BeautifulSoup(file.read(), features='html.parser')


def getOntologyBiologicalPsychology():
    colPath = os.path.join(SUPPORT_PATH, 'collection.anki2')
    col = Collection(colPath)
    map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
    importer = XmindImporter(col=col, file=map)
    importer.deckId = '1'
    importer.currentSheetImport = 'biological psychology'
    importer.activeManager = importer.xManagers[0]
    importer.xManagers.append(
        XManager(os.path.join(
            ADDON_PATH, 'resources', 'example_general_psychology.xmind')))
    importer.importMap()
    importer.currentSheetImport = 'clinical psychology'
    importer.importMap()
    importer.activeManager = importer.xManagers[1]
    importer.currentSheetImport = 'general psychology'
    importer.importMap()
    output = os.path.join(SUPPORT_PATH, 'ontology_biological_psychology.rdf')
    importer.onto.save(file=output, format="rdfxml")
    return owlready2.get_ontology(output).load()


def getNoteData():
    colPath = os.path.join(SUPPORT_PATH, 'collection.anki2')
    col = Collection(colPath)
    map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
    importer = XmindImporter(col=col, file=map)
    importer.deckId = '1'
    importer.currentSheetImport = 'biological psychology'
    importer.activeManager = importer.xManagers[0]
    importer.xManagers.append(
        XManager(os.path.join(
            ADDON_PATH, 'resources', 'example_general_psychology.xmind')))
    importer.importMap()
    importer.currentSheetImport = 'clinical psychology'
    importer.importMap()
    importer.activeManager = importer.xManagers[1]
    importer.currentSheetImport = 'general psychology'
    importer.importMap()
    noteData = importer.onto.getNoteData([(328, 346, 325)])
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
