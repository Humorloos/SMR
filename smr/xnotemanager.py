import json
import re
from typing import List, Optional, Sequence

from bs4 import BeautifulSoup

from anki import Collection
from anki.backend_pb2 import NoteTypeNameID
from anki.models import ModelManager
from anki.utils import splitFields, joinFields
import smr.consts as cts
from smr.dto.topiccontentdto import TopicContentDto
from smr.smrworld import SmrWorld, sort_id_from_order_number
from smr.utils import replace_embedded_media, get_smr_model_id

IMAGE_REGEX = r'<img src=\"(.*\.(' + '|'.join(cts.X_IMAGE_EXTENSIONS) + '))\">'
MEDIA_REGEX = r'\[sound:(.*\.(' + '|'.join(cts.X_MEDIA_EXTENSIONS) + r'))]'


def ref_minus_last(ref):
    return re.sub(r'<li>(?!.*<li>).*', '', ref)


def ref_plus_answer(field, followsBridge, ref, mult_subjects):
    # If the answerdict contains nothing (i.e. questions
    # following multiple answers), just close the reference
    if mult_subjects:
        ref = ref + '</li>'
    elif followsBridge:
        ref = ref + replace_embedded_media(field) + '</li>'
    else:
        ref = ref + ': ' + replace_embedded_media(field) + '</li>'
    return ref


def ref_plus_question(field, ref):
    # Update ref with content of this question but without sound
    refContent = replace_embedded_media(field)
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


def change_dict(old, new):
    return {'old': old, 'new': new}


def field_by_identifier(fields: List[str], identifier: str) -> str:
    """
    Given an anki fields list an an index identifier from the smr constants, gets the field that belongs to the
    identifier from the fields list
    :param fields: A list of smr note fields as returned by splitFields() applied to a fields string of an smr note
    :param identifier: The identifier from the SMR_FIELD_IDENTIFIERS list that identifies the desired field
    :return: the field's content as a string
    """
    return fields[cts.SMR_FIELD_IDENTIFIERS.index(identifier)]


def field_content_by_identifier(fields: List[str], identifier: str, smr_world: SmrWorld) -> TopicContentDto:
    """
    Given an anki fields list an an index identifier from the smr constants, gets the content of the field that
    belongs to the identifier from the fields list
    :param fields: A list of smr note fields as returned by splitFields() applied to a fields string of an smr note
    :param identifier: The identifier from the SMR_FIELD_IDENTIFIERS list that identifies the desired field
    :param smr_world: the smr world to get the xmind file uris from for images and media
    :return: the field's content as a string
    """
    return content_from_field(field=field_by_identifier(fields=fields, identifier=identifier), smr_world=smr_world)


def field_from_content(content: TopicContentDto, smr_world: SmrWorld) -> str:
    """
    Gets an anki field content representing the specified node content
    :param content: the node content to get the anki field for
    :param smr_world: the smr world to get the anki file names from for the files in the content dto
    :return: the anki field
    """
    field = content.title
    if content.image:
        if field != '':
            field += '<br>'
        field += f'<img src="{smr_world.get_anki_file_name_from_xmind_uri(content.image)}">'
    if content.media:
        if field != '':
            field += '<br>'
        field += f'[sound:{smr_world.get_anki_file_name_from_xmind_uri(content.media)}]'
    return field


def content_from_field(field: str, smr_world: SmrWorld) -> TopicContentDto:
    """
    Converts the string from an anki question or answer field to a node content dto
    :param field: an anki question or answer field
    :param smr_world: the smr world to get the xmind file uris from for images and media
    :return: a node content dto that represents the field's content
    """
    return TopicContentDto(image=image_from_field(field=field, smr_world=smr_world),
                           media=media_from_field(field=field, smr_world=smr_world),
                           title=title_from_field(field))


#
#
# def get_index_by_a_id(note, a_id):
#     a_metas = meta_from_fields(note.fields)['answers']
#     a_index = next(a_metas.index(d) for d in a_metas if d['answerId'] ==
#                    a_id) + 1
#     return get_field_index_by_field_name('a' + str(a_index))


def get_n_answers(note):
    answers = [field_by_identifier(note.fields, 'a' + str(i)) != '' for i in
               range(1, cts.X_MAX_ANSWERS + 1)]
    return sum(answers)


def title_from_field(field: str) -> str:
    """
    Extracts the title from an anki note field
    :param field: the anki note field to extract the title from
    :return: the title of the field
    """
    return BeautifulSoup(re.sub(IMAGE_REGEX + "|" + MEDIA_REGEX, "", field), "html.parser").text


def image_from_field(field: str, smr_world: SmrWorld) -> Optional[str]:
    """
    Extracts an image filename from an anki note field and returns the xmind uri that is linked to that anki file name.
    If no xmind uri was found, returns the anki filename instead
    :param field: the content of the anki note field to extract the image from
    :param smr_world: the smr_world to get the xmind file uri from
    :return: the xmind file uri
    - None if the field does not contain an image
    - The anki file name if the file was not yet registered in the relation
    """
    try:
        anki_file_name = re.search(IMAGE_REGEX, field).group(1)
    except AttributeError:
        return None
    xmind_uri = smr_world.get_xmind_uri_from_anki_file_name(anki_file_name)
    if not xmind_uri:
        return anki_file_name
    else:
        return xmind_uri


def media_from_field(field: str, smr_world: SmrWorld) -> Optional[str]:
    """
    Extracts a media filename from an anki note field and returns the xmind uri that is linked to that anki file name
    :param field: the content of the anki note field to extract the media from
    :param smr_world: the smr_world to get the xmind file uri from
    :return: the xmind file uri, None if the field does not contain any media
    """
    try:
        anki_file_name = re.search(MEDIA_REGEX, field).group(1)
    except AttributeError:
        return None
    return smr_world.get_xmind_uri_from_anki_file_name(anki_file_name)


def meta_from_fields(fields):
    return json.loads(field_by_identifier(fields, 'mt'))


def meta_from_flds(flds):
    return meta_from_fields(splitFields(flds))


def update_sort_id(previousId, idToAppend):
    return previousId + sort_id_from_order_number(idToAppend)


def local_answer_dict(anki_mod, answers, field, a_id):
    answers[a_id] = {'ankiMod': anki_mod,
                     'content': field}


class XNoteManager:
    def __init__(self, col: Collection):
        self.col = col
        self.model = None
        self.media_directory = None

    @property
    def col(self) -> Collection:
        return self._col

    @col.setter
    def col(self, value: Collection):
        self._col = value

    @property
    def media_directory(self) -> str:
        if not self._media_directory:
            self.media_directory = re.sub(r"(?i)\.(anki2)$", ".media", self.col.path)
        return self._media_directory

    @media_directory.setter
    def media_directory(self, value: str):
        self._media_directory = value

    @property
    def model(self) -> ModelManager:
        if not self._model:
            self.model = get_smr_model_id(self.col.models)
        return self._model

    @model.setter
    def model(self, value: ModelManager):
        self._model = value

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
            n['meta'] = json.loads(field_by_identifier(n['flds'], 'mt'))
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
                    'content': field_by_identifier(question['flds'], 'qt'),
                    'answers': answers}
                for x, a in enumerate(self.get_answer_cards(question['id'])):
                    field = field_by_identifier(question['flds'], 'a' + str(x + 1))
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
        sort_id = field_by_identifier(note.fields, 'id') + sort_id_from_order_number(a_index)
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

    def remove_notes_by_sheet_id(self, sheet_id: str, smr_world: SmrWorld) -> None:
        """
        Removes all notes belonging to the specified sheet from the collection
        :param sheet_id: id of the sheet to remove the notes for
        :param smr_world: the smr world to get the note ids from
        """
        note_ids_in_sheet = smr_world.get_note_ids_from_sheet_id(sheet_id)
        self.col.remove_notes(note_ids_in_sheet)

    def save_col(self):
        self.col.save()

    def save_note(self, note):
        flds = joinFields(note.fields)
        self.col.db.execute("""update notes set flds = ? where id = ?""",
                            flds, note.id)

    def set_meta(self, note, meta):
        note.fields[get_field_index_by_field_name('mt')] = json.dumps(meta)
        self.save_note(note)

    def set_ref(self, note, ref):
        note.fields[get_field_index_by_field_name('rf')] = ref
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
                old_ref = field_by_identifier(sheet_child_note.fields, 'rf')
                new_ref = old_ref
                if question_dict:
                    new_ref = replace_ref_question(
                        ref=old_ref, question_dict=question_dict)
                if answer_dict:
                    new_ref = replace_ref_answer(ref=new_ref,
                                                 answer_dict=answer_dict)
                self.set_ref(note=sheet_child_note, ref=new_ref)

    def get_actual_deck_names_and_ids(self) -> Sequence[NoteTypeNameID]:
        """
        Empties dynamic decks and returns the names and ids of all actual decks in the collection
        :return: Names and ids of all actual decks in the collection that are not dynamic decks
        """
        deck_names_and_ids = self.col.decks.all_names_and_ids()
        # Empty dynamic decks to avoid xmind files being scattered over multiple decks
        for deck_name_and_id in deck_names_and_ids:
            if self.col.decks.isDyn(deck_name_and_id.id):
                self.col.sched.emptyDyn(deck_name_and_id.id)
        return deck_names_and_ids

    def rearrange_answers(self, note, index_dict):
        # TODO: complete this
        meta = meta_from_fields(note.fields)
        for index in index_dict:
            print()
        print()

