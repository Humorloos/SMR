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

# def getOntologyBiologicalPsychology():
#     colPath = os.path.join(SUPPORT_PATH, 'collection.anki2')
#     col = Collection(colPath)
#     map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
#     xmindImporter = XmindImporter(col=col, file=map)
#     xmindImporter.deckId = '1'
#     xmindImporter.currentSheetImport = 'biological psychology'
#     xmindImporter.activeManager = xmindImporter.xManagers[0]
#     xid = '0pbme7b9sg9en8qqmmn9jj06od'
#     nodeTag = xmindImporter.activeManager.getTagById(xid)
#     concept = xmindImporter.onto.Root('biological psychology')
#     concept.Image = None
#     concept.Media = None
#     concept.Xid = xid
#     concept = [concept]
#     answerDict = {'nodeTag': nodeTag, 'isAnswer': True, 'aId': str(0),
#                   'crosslink': None, 'concepts': concept}
#     act = xmindImporter.getQuestions(parentAnswerDict=answerDict,
#                                 ref='biological psychology')
#     output = os.path.join(SUPPORT_PATH, 'ontology_biological_psychology.rdf')
#     xmindImporter.onto.save(file=output, format="rdfxml")
#     # TODO: figure out how to store the ontology properly, currently when
#      loading the ontology, properties and individuals cannot be accessed
#     return owlready2.get_ontology(output).load()


sheetImports = getSheetImports()
selectedSheets = getSelectedSheets()
sheetBiologicalPsychology = getSheetBiologicalPsychology()
# ontologyBiologicalPsychology = getOntologyBiologicalPsychology()
