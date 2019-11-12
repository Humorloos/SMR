import json

import aqt.main as sync

from anki.utils import splitFields

from .utils import *
from .xminder import XmindImporter


class MapSyncer:

    def __init__(self, mw):
        self.mw = mw
        self.notes2Sync = []
        self.tagList = None

    def syncMaps(self):
        self.mw.progress.start(immediate=True, label='processing SMR changes...')
        self.mw.app.processEvents()
        self.getNotes2Sync()
        docs2Sync = set(map(lambda n: n['meta']['path'], self.notes2Sync))
        for doc2Sync in docs2Sync:
            self.syncDoc(doc2Sync)
        self.mw.progress.finish()

    def getNotes2Sync(self):
        """gets all notes with fields that were changed after their last import"""
        xMid = xModelId(self.mw.col)
        xNotes = list(self.mw.col.db.execute(
            "select id, mod, flds from notes where mid = %s" % xMid))
        for xNote in xNotes:
            fields = splitFields(xNote[2])
            meta = json.loads(fields[23])
            # If the last time the note was edited was at least 10 Seconds after it was imported
            if xNote[1] > (meta['lastSync'] + 10):
                self.notes2Sync.append(
                    dict(meta=meta, fields=fields, nid=xNote[0]))

    def syncDoc(self, docPath):
        self.mw.progress.update(label="synchronizing %s" % os.path.basename(docPath), maybeShow=False)
        self.mw.app.processEvents()
        notes4Doc = list(filter(lambda n: n['meta']['path'] == docPath,
                                self.notes2Sync))
        xZip = zipfile.ZipFile(docPath, 'r')
        content = xZip.read('content.xml')
        xZip.close()
        soup = BeautifulSoup(content, features='html.parser')
        self.tagList = soup('topic')
        sheets2Sync = set(map(lambda n: n['meta']['sheetId'], notes4Doc))
        sheets2Sync = list(
            map(lambda s: soup.find('sheet', {'id': s}), sheets2Sync))
        for note in notes4Doc:
            self.syncNote(note)
        updateZip(docPath, 'content.xml', str(soup))
        importer = XmindImporter(col=self.mw.col, file=docPath)
        sheetImports = []
        for sheet in sheets2Sync:
            print('importing sheet')
            tag4Sheet = sum(set(self.mw.col.db.execute(
                "select tags from notes where flds like '%\"sheetId\": \"" +
                sheet['id'] + "\"%'")), ())[0]
            sheetNid = sum(set(self.mw.col.db.execute(
                "select id from notes where flds like '%\"sheetId\": \"" +
                sheet['id'] + "\"%'")), ())[0]
            did4Sheet = sum(set(self.mw.col.db.execute(
                "select did from cards where nid = %s" % sheetNid)), ())[0]
            sheetImport = dict(sheet=sheet, tag=tag4Sheet, deckId=did4Sheet, repair=False)
            sheetImports.append(sheetImport)
        importer.importSheets(sheetImports)


    def syncNote(self, note):
        print('synchronizing note')
        questionTag = getTagById(tagList=self.tagList,
                                 tagId=note['meta']['questionId'])
        maybeReplaceTitle(noteContent=note['fields'][1], tag=questionTag)

        for aId, answer in enumerate(note['meta']['answers'], start=0):
            answerTag = getTagById(tagList=self.tagList,
                                   tagId=note['meta']['answers'][aId][
                                       'answerId'])
            maybeReplaceTitle(noteContent=note['fields'][aId + 2],
                              tag=answerTag)


# monkey patches


def syncOnSync(self):
    ############################################################################
    mapSyncer = MapSyncer(self)
    mapSyncer.syncMaps()
    ############################################################################
    self.unloadCollection(self._onSync)


sync.AnkiQt.onSync = syncOnSync
