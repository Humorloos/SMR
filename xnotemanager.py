import json
import re

from consts import X_FLDS, X_MEDIA_EXTENSIONS, X_IMG_EXTENSIONS, X_MAX_ANSWERS
from utils import replaceSound, xModelId

from anki.utils import splitFields, joinFields


def change_dict(old, new):
    return {'old': old, 'new': new}


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


def get_index_by_a_id(note, a_id):
    a_metas = meta_from_fields(note.fields)['answers']
    a_index = next(a_metas.index(d) for d in a_metas if d['answerId'] ==
                   a_id) + 1
    return get_index_by_field_name('a' + str(a_index))


def get_n_answers(note):
    answers = [field_by_name(note.fields, 'a' + str(i)) != '' for i in
               range(1, X_MAX_ANSWERS + 1)]
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


def local_answer_dict(anki_mod, answers, field, a_id):
    answers[a_id] = {'ankiMod': anki_mod,
                     'content': field}


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
        :param qId: Xmind id of the question to get the nid for
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
        return list(set(
            meta_from_flds(flds[0])['path'] for flds in self.col.db.execute(
                'select flds from notes where mid = %s' % self.model)))

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
                    field = field_by_name(question['flds'], 'a' + str(x + 1))
                    try:
                        a_id = question['meta']['answers'][x]['answerId']

                    # If this answer does not yet exist in meta, use the
                    # answer's card id as id instead
                    except IndexError:
                        a_id = a[1]
                    local_answer_dict(
                        anki_mod=a[0], answers=answers, field=field, a_id=a_id)
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

    def get_sheet_child_notes(self, note, a_index):
        """
        Returns all notes for a given note that are children of that note,
        that is, their sort_id contains the sort_id of the given note +
        answer and they belong to the same sheet
        :param note: The note to get the child_notes for
        :param a_index: The index of the answer in the note that is parent to
        the child note (1 is first answer)
        :return: All notes that are children of the given note
        """
        tag = ' ' + note.tags[0] + ' '
        sort_id = field_by_name(note.fields, 'id') + sort_id_from_index(a_index)
        all_child_nids = self.col.db.list(
            'select id from notes where tags is ? and sfld '
            'like ? and length(sfld) > ?', tag, sort_id + '%', len(sort_id))
        return [self.col.getNote(n) for n in all_child_nids]

    def get_sheet_nids(self, sheet_id):
        """
        Gets the nids of the notes belonging to the sheet with the given id
        :param sheet_id: Xmind id of the sheet to get the nids for
        :return: Ids of the notes belonging to this sheet
        """
        return self.col.db.list(
            "select id from notes where flds like '%\"sheetId\": \"" +
            sheet_id + "\"%'")

    def get_sheet_notes(self, sheet_id):
        """
        Gets all notes belonging to the sheet with the given id
        :param sheet_id: Xmind id of the sheet to get the notes for
        :return: All notes that belong to the sheet with the given id
        """
        return [self.col.getNote(n) for n in self.get_sheet_nids(sheet_id)]

    def remove_notes_by_q_ids(self, q_ids):
        nids_2_remove = [self.get_nid_from_q_id(q) for q in q_ids]
        self.col.remNotes(nids_2_remove)

    def remove_sheet(self, sheet):
        # Remove notes from this sheet from collection
        sheet_nids = self.get_sheet_nids(sheet)
        tag = self.col.getNote(sheet_nids[0]).tags[0]
        self.col.remNotes(sheet_nids)

        # Remove tag
        del self.col.tags.tags[tag]

    def save_col(self):
        self.col.save()

    def save_note(self, note):
        flds = joinFields(note.fields)
        self.col.db.execute("""update notes set flds = ? where id = ?""",
                            flds, note.id)

    def set_meta(self, note, meta):
        note.fields[get_index_by_field_name('mt')] = json.dumps(meta)
        self.save_note(note)

    def set_ref(self, note, ref):
        note.fields[get_index_by_field_name('rf')] = ref
        self.save_note(note)

    def update_ref(self, note, changes, meta=None):
        """
        Changes the ref of all notes that are children of the given note
        according to changes made to the note's question or answers.
        :param meta: Optional: Content of the note's meta field, if not
        provided it will be generated by this method
        :param note: The note in which changes were made to questions and/or
        answers
        :param changes: Dictionary with optional keys 'question' or xmind
        answer ids containing dictionaries with keys 'old' and 'new', example:
        {'question': {'old': 'investigates', 'new': 'new question'}}
        """
        if not meta:
            meta = meta_from_fields(note.fields)
        question_dict = {}
        if 'question' in changes:
            question_dict[changes['question']['old']] = changes[
                'question']['new']
        for i in range(1, get_n_answers(note) + 1):
            sheet_child_notes = self.get_sheet_child_notes(note=note, a_index=i)
            a_id = meta['answers'][i - 1]['answerId']
            answer_dict = {}
            if a_id in changes:
                answer_dict[changes[a_id]['old']] = changes[a_id]['new']
            for sheet_child_note in sheet_child_notes:
                old_ref = field_by_name(sheet_child_note.fields, 'rf')
                new_ref = old_ref
                if question_dict:
                    new_ref = replace_ref_question(
                        ref=old_ref, question_dict=question_dict)
                if answer_dict:
                    new_ref = replace_ref_answer(ref=new_ref, answer_dict=answer_dict)
                self.set_ref(note=sheet_child_note, ref=new_ref)


class FieldTranslator:
    def __init__(self):
        self.field_re_dict = {
            'ximage_': '<img src="',
            'xmedia_': '[sound:',
            'xlparenthesis_': '(',
            '_xrparenthesis': ')'
        }
        self.field_regex = re.compile("(%s)" % "|".join(
            self.field_re_dict.keys()))
        self.inverse_dict = {re.escape(self.field_re_dict[k]): k for k in
                             self.field_re_dict}
        self.inverse_regex = re.compile("(%s)" % "|".join(
            self.inverse_dict.keys()))

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

    def class_from_content(self, content):
        classified = content['content'].replace(" ", "_")
        if content['media']['image']:
            classified += "ximage_" + re.sub(
                'attachments/', '', content['media']['image'])
            classified = re.sub('(\\.)(' + '|'.join(X_IMG_EXTENSIONS) + ')',
                                '_extension_\\2', classified)
        if content['media']['media']:
            classified += "xmedia_" + re.sub(
                'attachments/', '', content['media']['media'])
            classified = re.sub('(\\.)(' + '|'.join(X_MEDIA_EXTENSIONS) + ')',
                                '_extension_\\2', classified)
        classified = self.inverse_regex.sub(lambda mo: self.inverse_dict[
            re.escape(mo.string[mo.start():mo.end()])], classified)
        return classified
