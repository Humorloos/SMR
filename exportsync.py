import json

import aqt.main as sync
from aqt.utils import tooltip

from anki.utils import splitFields

from .utils import *
from .xminder import XmindImporter


class MapSyncer:

    def __init__(self, mw):
        self.mw = mw
        self.notes2Sync = []
        self.srcDir = None
        self.tagList = None
        self.mediaDir = re.sub(r"(?i)\.(anki2)$", ".media", self.mw.col.path)
        self.manifest = None
        self.fileBin = None

    def syncMaps(self):
        self.mw.progress.start(immediate=True,
                               label='processing SMR changes...')
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
        self.mw.progress.update(
            label="synchronizing %s" % os.path.basename(docPath),
            maybeShow=False)
        self.mw.app.processEvents()
        # create temp dir
        self.srcDir = tempfile.mkdtemp()
        self.fileBin = []
        notes4Doc = list(filter(lambda n: n['meta']['path'] == docPath,
                                self.notes2Sync))
        try:
            xZip = zipfile.ZipFile(docPath, 'r')
        except FileNotFoundError:
            log = 'File "%s" not found, changes in "%s" not exported.' % (
                docPath, os.path.basename(docPath))
            tooltip(msg=log, period=6000, parent=self.mw)
            return
        content = xZip.read('content.xml')
        manifestContent = xZip.read("META-INF/manifest.xml")
        xZip.close()
        soup = BeautifulSoup(content, features='html.parser')
        self.manifest = BeautifulSoup(manifestContent, features='html.parser')
        self.tagList = soup('topic')
        sheets2Sync = set(map(lambda n: n['meta']['sheetId'], notes4Doc))
        sheets2Sync = list(
            map(lambda s: soup.find('sheet', {'id': s}), sheets2Sync))
        for note in notes4Doc:
            self.syncNote(note)
        self.updateZip(docPath, 'content.xml', str(soup))
        # Remove temp dir and its files
        shutil.rmtree(self.srcDir)
        # import sheets again
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
            sheetImport = dict(sheet=sheet, tag=tag4Sheet, deckId=did4Sheet,
                               repair=False)
            sheetImports.append(sheetImport)
        importer.importSheets(sheetImports)

    def syncNote(self, note):
        print('synchronizing note')
        questionTag = getTagById(tagList=self.tagList,
                                 tagId=note['meta']['questionId'])
        if not questionTag:
            return
        self.maybeReplaceTitle(noteContent=note['fields'][1], tag=questionTag)

        for aId, answer in enumerate(note['meta']['answers'], start=0):
            answerTag = getTagById(tagList=self.tagList,
                                   tagId=note['meta']['answers'][aId][
                                       'answerId'])
            self.maybeReplaceTitle(noteContent=note['fields'][aId + 2],
                                   tag=answerTag)

    def maybeReplaceTitle(self, noteContent, tag):
        tagContent = getNodeContent(tagList=self.tagList, tag=tag)[0]
        if noteContent != tagContent:
            self.setNodeContent(tag=tag, noteContent=noteContent)

    def setNodeContent(self, tag, noteContent):
        noteTitle = titleFromContent(noteContent)
        if noteTitle != getNodeTitle(tag):
            setNodeTitle(tag=tag, title=noteTitle)
        noteImg = imgFromContent(noteContent)
        nodeImg = getNodeImg(tag)
        if (noteImg and not nodeImg or noteImg and noteImg not in nodeImg) or \
                nodeImg and not noteImg:
            self.setNodeImg(tag=tag, noteImg=noteImg, nodeImg=nodeImg)

        print('')

    def setNodeImg(self, tag, noteImg, nodeImg):
        if not noteImg:
            # remove image node from Map, i do not know why decompose() has to be called twice but it only works this way
            imgTag = tag.find('xhtml:img')
            imgTag.decompose()
            fullPath = nodeImg[4:]
            self.fileBin.append(fullPath)
            self.manifest.find('file-entry',
                               attrs={"full-path": fullPath}).decompose()
            return
        # move image from note to the directory of images to add
        imgPath = os.path.join(self.mediaDir, noteImg)
        shutil.copy(src=imgPath, dst=self.srcDir)
        newFullPath = 'attachments/' + noteImg
        newMediaType = "image/" + os.path.splitext(noteImg)[1][1:]
        if not nodeImg:
            # create a new image tag and add it to the node Tag
            imgTag = self.manifest.new_tag(name='xhtml:img', align='bottom')
            fileEntry = self.manifest.new_tag(name='file-entry')
            imgTag['xhtml:src'] = 'xap:' + newFullPath
            fileEntry['full-path'] = newFullPath
            fileEntry['media-type'] = newMediaType
            self.manifest.find('manifest').append(fileEntry)
            tag.append(imgTag)

            print('added new image to map')
            return
        # change image
        fullPath = nodeImg[4:]
        self.fileBin.append(fullPath)
        fileEntry = self.manifest.find('file-entry',
                                       attrs={"full-path": fullPath})
        fileEntry['full-path'] = newFullPath
        fileEntry['media-type'] = newMediaType
        imgTag = tag.find('xhtml:img')
        imgTag['xhtml:src'] = 'xap:' + newFullPath

        # TODO: add code for changing images

    def updateZip(self, zipname, filename, data):
        """ taken from https://stackoverflow.com/questions/25738523/how-to-update-one-file-inside-zip-file-using-python, replaces one file in a zipfile"""
        # generate a temp file
        tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(zipname))
        os.close(tmpfd)

        # create a temp copy of the archive without filename
        with zipfile.ZipFile(zipname, 'r') as zin:
            with zipfile.ZipFile(tmpname, 'w') as zout:
                zout.comment = zin.comment  # preserve the comment
                for item in zin.infolist():
                    if item.filename not in [filename,
                                             'META-INF/manifest.xml'] + \
                            self.fileBin:
                        zout.writestr(item, zin.read(item.filename))

        # replace with the temp archive
        os.remove(zipname)
        os.rename(tmpname, zipname)

        # now add filename with its new data
        with zipfile.ZipFile(zipname, mode='a',
                             compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, data)
            for file in os.listdir(self.srcDir):
                zf.write(filename=os.path.join(self.srcDir, file),
                         arcname=os.path.join('attachments', file))
            zf.writestr(zinfo_or_arcname='META-INF/manifest.xml',
                        data=str(self.manifest))


# monkey patches


def syncOnSync(self):
    ############################################################################
    mapSyncer = MapSyncer(self)
    mapSyncer.syncMaps()
    ############################################################################
    self.unloadCollection(self._onSync)


sync.AnkiQt.onSync = syncOnSync
