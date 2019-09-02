from anki.importing.noteimp import NoteImporter


class XmindImporter(NoteImporter):
    needMapper = False

    def run(self):
        self.log = ['Xmind Datei wurde importiert.']
