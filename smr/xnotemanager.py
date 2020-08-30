import re
from typing import List, Optional, Sequence

from bs4 import BeautifulSoup

import smr.consts as cts
from anki import Collection
from anki.backend_pb2 import NoteTypeNameID
from anki.models import ModelManager
from smr.dto.topiccontentdto import TopicContentDto
from smr.smrworld import SmrWorld
from smr.utils import get_smr_model_id

IMAGE_REGEX = r'<img src=\"(.*\.(' + '|'.join(cts.X_IMAGE_EXTENSIONS) + '))\">'
MEDIA_REGEX = r'\[sound:(.*\.(' + '|'.join(cts.X_MEDIA_EXTENSIONS) + r'))]'


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

    def remove_notes_by_sheet_id(self, sheet_id: str, smr_world: SmrWorld) -> None:
        """
        Removes all notes belonging to the specified sheet from the collection
        :param sheet_id: id of the sheet to remove the notes for
        :param smr_world: the smr world to get the note ids from
        """
        note_ids_in_sheet = smr_world.get_note_ids_from_sheet_id(sheet_id)
        self.col.remove_notes(note_ids_in_sheet)

    def save_col(self) -> None:
        """
        saves the collection
        """
        self.col.save()

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
