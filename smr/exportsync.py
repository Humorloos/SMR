import json
from zipfile import ZipFile, ZIP_DEFLATED

import aqt
from aqt.utils import tooltip

from anki.utils import split_fields

from .dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from .utils import *
from .xminder import XmindImporter


class MapSyncer:

    def __init__(self):
        self.notes2Sync = []
        self.srcDir = None
        self.tagList = None
        self.mediaDir = re.sub(r"(?i)\.(anki2)$", ".media", aqt.mw.col.path)
        self.manifest = None
        self.fileBin = None

    def syncMaps(self):
        aqt.mw.progress.start(immediate=True,
                              label='processing SMR changes...')
        aqt.mw.app.processEvents()
        self.getNotes2Sync()
        docs2Sync = set(map(lambda n: n['meta']['path'], self.notes2Sync))
        for doc2Sync in docs2Sync:
            self.syncDoc(doc2Sync)

        aqt.mw.col.tags.clear_unused_tags()
        aqt.mw.progress.finish()

    def getNotes2Sync(self):
        """gets all notes with fields that were changed after their last import"""
        xMid = xModelId(aqt.mw.col)
        xNotes = list(aqt.mw.col.db.execute(
            "select id, mod, flds from notes where mid = %s" % xMid))
        for xNote in xNotes:
            fields = split_fields(xNote[2])
            meta = json.loads(fields[23])
            # If the last time the note was edited was at least 10 Seconds after it was imported
            if xNote[1] > (meta['lastSync'] + 10):
                self.notes2Sync.append(
                    dict(meta=meta, fields=fields, nid=xNote[0]))

    def syncDoc(self, docPath):
        aqt.mw.progress.update(
            label="synchronizing %s" % os.path.basename(docPath),
            maybeShow=False)
        aqt.mw.app.processEvents()
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
            tooltip(msg=log, period=6000, parent=aqt.mw)
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
        if len(sheets2Sync) > 0:
            sheet = sheets2Sync[0]
            for note in notes4Doc:
                self.syncNote(note)
            self.update_zip(docPath, 'content.xml', str(soup))
            # Remove temp dir and its files
            shutil.rmtree(self.srcDir)
            # import sheets again
            importer = XmindImporter(col=aqt.mw.col, file=docPath)
            sheetImports = []
            print('importing sheet')
            tag4Sheet = next(taglist[0].strip() for taglist in aqt.mw.col.db.execute(
                "select tags from notes where flds like '%\"sheetId\": \"" +
                sheet['id'] + "\"%'"))
            sheetNid = next(nid_list[0] for nid_list in aqt.mw.col.db.execute(
                "select id from notes where flds like '%\"sheetId\": \"" +
                sheet['id'] + "\"%'"))
            did4Sheet = next(did_list[0] for did_list in aqt.mw.col.db.execute(
                "select did from cards where nid = %s" % sheetNid))
            user_inputs = DeckSelectionDialogUserInputsDTO(
                deck_id=did4Sheet,
                repair=False,
                deck_name=re.search(r'^([^:]*)::', tag4Sheet).group(1)
            )
            importer.importSheets(user_inputs=user_inputs)
            log = "\n".join(importer.log)
            tooltip(log)

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

    def update_zip(self, zipname, filename, data) -> None:
        """
        - replaces the content.xml file in the xmind file with the manager's content soup
        - replaces the manifest.xml with the manager's manifest soup
        - removes all files in the file_bin from the xmind file
        - adds all files in files_2_add to the xmind file
        code was adopted from
        https://stackoverflow.com/questions/25738523/how-to-update-one-file-inside-zip-file-using-python,
        """
        # generate a temp file
        temp_file_directory, temp_file_name = tempfile.mkstemp(dir=os.path.dirname(zipname))
        os.close(temp_file_directory)
        # create a temporary copy of the archive without filename
        with ZipFile(zipname, 'r') as zip_file_in:
            with ZipFile(temp_file_name, 'w') as zip_file_out:
                zip_file_out.comment = zip_file_in.comment  # preserve the comment
                for item in zip_file_in.infolist():
                    # keep all files that are not managed by the manager and that are not in the file bin
                    if item.filename not in [filename, 'META-INF/manifest.xml'] + self.fileBin:
                        zip_file_out.writestr(item, zip_file_in.read(item.filename))
        # Replace managed file with temporary file
        os.remove(zipname)
        os.rename(temp_file_name, zipname)
        # now add filename with its new data
        with ZipFile(zipname, mode='a', compression=ZIP_DEFLATED) as zip_file:
            zip_file.writestr('content.xml', data)
            for file in os.listdir(self.srcDir):
                zip_file.write(filename=file, arcname=os.path.join('attachments', file))
            zip_file.writestr(zinfo_or_arcname='META-INF/manifest.xml', data=str(self.manifest))
