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
        doc_notes = [{'id': r[1], 'ankiMod': r[2], 'flds': splitFields(r[0])}
                     for r in self.col.db.execute(
                'select flds, id, mod from notes where mid = %s' % self.model)
                     if meta_from_flds(r[0])['path'] == file]
        for n in doc_notes:
            n['meta'] = json.loads(self.get_field_by_name(n['flds'], 'mt'))
        sheet_ids = set(n['meta']['sheetId'] for n in doc_notes)
        sheet_notes = {i: {n['meta']['questionId']: n for n in doc_notes if
                           n['meta']['sheetId'] == i} for i in sheet_ids}

        sheets = dict()
        for i in sheet_ids:
            questions = dict()
            sheet_note = sheet_notes[i]
            sheets[i] = {'ankiMod': max(
                [sheet_note[n]['ankiMod'] for n in sheet_note]),
                'questions': questions}
            for n in sheet_note:
                answers = dict()
                question = sheet_note[n]
                questions[question['meta']['questionId']] = {
                    'ankiMod': question['ankiMod'],
                    'content': self.get_field_by_name(question['flds'], 'qt'),
                    'answers': answers}
                for x, a in enumerate(self.get_answer_cards(question['id'])):
                    try:
                        a_id = question['meta']['answers'][x]['answerId']
                    except IndexError:
                        a_id = a[1]
                    answers[a_id] = {'ankiMod': a[0],
                                     'content': self.get_field_by_name(
                                         question['flds'], 'a' + str(x+1))}
        docMod = max([n['ankiMod'] for n in doc_notes])
        local = {'file': file, 'ankiMod': docMod, 'sheets': sheets}
        return local

    def get_answer_cards(self, nid):
        return self.col.db.all('select mod, id from cards where nid = %s' %
                                nid)
