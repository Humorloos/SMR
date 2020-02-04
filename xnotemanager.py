import json

from anki.utils import splitFields, joinFields

from .utils import *
from .consts import X_FLDS, X_MEDIA_EXTENSIONS, X_IMG_EXTENSIONS, X_MAX_ANSWERS


def field_by_name(fields, name):
    return fields[get_index_by_field_name(name)]


def field_from_content(content):
    field = ''
    if content['content']:
        field += content['content']

    if content['media']['image']:
        if field != '':
            field += '<br>'
        field += '<img src="%s">' % re.sub('attachments/', '', content['media'][
            'image'])

    if content['media']['media']:
        if field != '':
            field += '<br>'
        field += '[sound:%s]' % re.sub('attachments/', '', content['media'][
            'media'])

    return field


def get_index_by_field_name(name):
    if name not in X_FLDS:
        raise NameError('Name not in X_FLDS, valid names are ' +
                        X_FLDS.keys())
    return list(X_FLDS.keys()).index(name)


def get_n_answers(note):
    answers = [field_by_name(note.fields, 'a' + str(i)) != '' for i in
               range(1, X_MAX_ANSWERS+1)]
    return sum(answers)


def img_from_field(field):
    try:
        return re.search('<img src=\"(.*\.(' + '|'.join(X_IMG_EXTENSIONS) +
                         '))\">', field).group(1)
    except AttributeError:
        return None


def index_from_sort_id(sort_id):
    return ord(sort_id) - 122


def media_from_field(field):
    try:
        return re.search('\[sound:(.*\.(' + '|'.join(X_MEDIA_EXTENSIONS) +
                         '))\]', field).group(1)
    except AttributeError:
        return None


def meta_from_fields(fields):
    return json.loads(field_by_name(fields, 'mt'))


def meta_from_flds(flds):
    return meta_from_fields(splitFields(flds))


def ref_minus_last(ref):
    return re.sub('<li>(?!.*<li>).*', '', ref)


def ref_plus_answer(field, followsBridge, ref, mult_subjects):
    # If the answerdict contains nothing (i.e. questions
    # following multiple answers), just close the reference
    if mult_subjects:
        ref = ref + '</li>'
    elif followsBridge:
        ref = ref + replaceSound(field) + '</li>'
    else:
        ref = ref + ': ' + replaceSound(field) + '</li>'
    return ref


def ref_plus_question(field, ref):
    # Update ref with content of this question but without sound
    refContent = replaceSound(field)
    nextRef = ref + '<li>' + refContent
    return nextRef


def replace_ref_answer(ref, answer_dict):
    old_answer = next(iter(answer_dict))
    return re.sub(': ' + old_answer + '</li>',
                  ': ' + answer_dict[old_answer] + '</li>', ref)


def replace_ref_question(ref, question_dict):
    old_question = next(iter(question_dict))
    return re.sub('<li>' + old_question + ':',
                  '<li>' + question_dict[old_question] + ':', ref)


def set_meta(note, meta):
    note.fields[get_index_by_field_name('mt')] = json.dumps(meta)


def sort_id_from_index(index):
    return chr(index + 122)


def title_from_field(field):
    return re.sub("(<br>)?(\[sound:.*\]|<img src=.*>)", "", field)


def update_sort_id(previousId, idToAppend):
    return previousId + sort_id_from_index(idToAppend)


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


class XNoteManager:
    def __init__(self, col):
        self.col = col
        self.model = xModelId(self.col)
        self.media_dir = re.sub(r"(?i)\.(anki2)$", ".media", self.col.path)

    def get_fields_from_qId(self, qId):
        return splitFields(self.col.db.first(
            "select flds from notes where flds like '%\"questionId\": \"" +
            qId + "\"%'")[0])

    def get_nid_from_q_id(self, qId):
        """
        Gets the nid of the note containing the questino with the given q_id
        :param qId: Xmind id of the question to get the note for
        :return: Id of the note containing this question
        """
        return self.col.db.first(
            "select id from notes where flds like '%\"questionId\": \"" +
            qId + "\"%'")[0]

    def get_note_from_q_id(self, q_id):
        """
        Gets the note that contains the question with the given q_id
        :param q_id: Xmind id of the question to get the note for
        :return: Note that contains the question with the given q_id
        """
        return self.col.getNote(self.get_nid_from_q_id(q_id))

    def get_xmind_files(self):
        return set(meta_from_flds(flds[0])['path'] for flds in
                   self.col.db.execute(
                       'select flds from notes where mid = %s' % self.model))

    def get_local(self, file):
        doc_notes = [{'id': r[1], 'ankiMod': r[2], 'flds': splitFields(r[0])}
                     for r in self.col.db.execute(
                'select flds, id, mod from notes where mid = %s' %
                self.model)
                     if meta_from_flds(r[0])['path'] == file]
        for n in doc_notes:
            n['meta'] = json.loads(field_by_name(n['flds'], 'mt'))
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
                    'content': field_by_name(question['flds'], 'qt'),
                    'answers': answers}
                for x, a in enumerate(self.get_answer_cards(question['id'])):
                    try:
                        a_id = question['meta']['answers'][x]['answerId']
                    # If this answer does not yet exist in meta, use the
                    # answer's card id as id instead
                    except IndexError:
                        a_id = a[1]
                    answers[a_id] = {'ankiMod': a[0],
                                     'content': field_by_name(
                                         question['flds'], 'a' + str(x + 1))}
        docMod = max([n['ankiMod'] for n in doc_notes])
        deck = self.col.db.first(
            'select did from cards where nid = %s' % doc_notes[0]['id'])[0]
        local = {'file': file,
                 'ankiMod': docMod,
                 'sheets': sheets,
                 'deck': deck}
        return local

    def get_answer_cards(self, nid):
        return self.col.db.all('select mod, id from cards where nid = %s' %
                               nid)

    def get_sheet_child_notes(self, note, answer):
        tag = ' ' + note.tags[0] + ' '
        sort_id = field_by_name(note.fields, 'id') + sort_id_from_index(
            answer)
        all_child_nids = self.col.db.list(
            'select id from notes where tags is ? and sfld '
            'like ? and length(sfld) > ?', tag, sort_id + '%', len(sort_id))
        return [self.col.getNote(n) for n in all_child_nids]

    def save_col(self):
        self.col.save()

    def set_ref(self, note, ref):
        note.fields[get_index_by_field_name('rf')] = ref
        flds = joinFields(note.fields)
        self.col.db.execute("""update notes set flds = ? where id = ?""",
                            (flds, note.id))

    def update_ref(self, question_dict, answer_dict, note):
        old_ref = field_by_name(note.fields, 'rf')
        new_ref = old_ref
        if question_dict:
            new_ref = replace_ref_question(
                ref=old_ref, question_dict=question_dict)
        if answer_dict:
            new_ref = replace_ref_answer(ref=new_ref, answer_dict=answer_dict)
        if new_ref == old_ref:
            print()
        self.set_ref(note=note, ref=new_ref)


class FieldTranslator:
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
