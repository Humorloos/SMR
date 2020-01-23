import json

from anki.utils import splitFields

from .utils import *


def meta_from_flds(flds):
    return json.loads(splitFields(flds)[-1])


class XNoteManager():
    def __init__(self, col):
        self.col = col
        self.model = xModelId(self.col)

    def get_xmind_files(self):
        return set(meta_from_flds(flds[0])['path'] for flds in
                   self.col.db.execute(
                       'select flds from notes where mid = %s' % self.model))

    def get_local(self, file):
        doc_notes = [{'id': r[1], 'ankiMod': r[2], 'meta': meta_from_flds(r[0])}
                     for r in self.col.db.execute(
                'select flds, id, mod from notes where mid = %s' % self.model)
                     if meta_from_flds(r[0])['path'] == file]
        sheet_ids = set(n['meta']['sheetId'] for n in doc_notes)
        sheet_notes = {i: [n for n in doc_notes if n['meta']['sheetId'] == i]
                       for i in sheet_ids}

        sheets = dict()
        for i in sheet_ids:
            questions = dict()
            sheets[i] = {'ankiMod': max([n['ankiMod'] for n in sheet_notes[
                i]]), 'questions': questions}
            for n in sheet_notes[i]:
                answers = dict()
                questions[n['meta']['questionId']] = {'ankiMod': n[
                    'ankiMod'], 'answers': answers}
                for x, a in enumerate(self.get_answer_cards(n['id'])):
                    answers[n['meta']['answers'][x]['answerId']] = {
                        'ankiMod': a}
        docMod = max([n['ankiMod'] for n in doc_notes])
        local = {'file': file, 'ankiMod': docMod, 'sheets': sheets}
        return local

    def get_answer_cards(self, nid):
        return self.col.db.list('select mod from cards where nid = %s' % nid)
