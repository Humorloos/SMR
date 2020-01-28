import json

from anki.utils import splitFields

from .utils import *
from .consts import X_FLDS, X_MEDIA_EXTENSIONS, X_IMG_EXTENSIONS


def img_from_field(field):
    try:
        return re.search('<img src=\"(.*\.(' + '|'.join(X_IMG_EXTENSIONS) +
                         '))\">', field).group(1)
    except AttributeError:
        return None


def media_from_field(field):
    try:
        return re.search('\[sound:(.*\.(' + '|'.join(X_MEDIA_EXTENSIONS) +
                         '))\]', field).group(1)
    except AttributeError:
        return None


def meta_from_flds(flds):
    return json.loads(splitFields(flds)[-1])


def title_from_field(field):
    return re.sub("(<br>)?(\[sound:.*\]|<img src=.*>)", "", field)


def content_from_field(field):
    image = img_from_field(field)
    if image:
        image = 'attachments/' + image
    media = media_from_field(field)
    if media:
        media = 'attachments/' + media
    return {'content': title_from_field(field),
            'media': {
                'image': image,
                'media': media
            }}


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


class FieldTranslator():
    def __init__(self):
        self.field_re_dict = {
            'ximage_': '<img src="',
            'xmedia_': '[sound:',
        }
        self.field_regex = re.compile("(%s)" % "|".join(
            self.field_re_dict.keys()))

    def field_from_class(self, class_name):
        class_name = re.sub('(.)(ximage_)', '\\1<br>\\2', class_name)
        class_name = self.field_regex.sub(
            lambda mo: self.field_re_dict[mo.string[mo.start():mo.end()]],
            class_name)
        class_name = re.sub('(_extension_)(' + '|'.join(X_IMG_EXTENSIONS) + ')',
                            '.\\2">', class_name)
        class_name = re.sub('(_extension_)(' + '|'.join(X_MEDIA_EXTENSIONS) +
                            ')', '.\\2]', class_name)
        class_name = class_name.replace("_", " ")
        return class_name