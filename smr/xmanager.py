# class for reading and writing xmind files

import os
import tempfile
import urllib.parse
from typing import Dict, List, Optional, Tuple, Union
from zipfile import ZipFile, ZIP_DEFLATED

from bs4 import BeautifulSoup, Tag

from smr.consts import X_MEDIA_EXTENSIONS
from smr.dto.nodecontentdto import NodeContentDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindmediatoankifilesdto import XmindMediaToAnkiFilesDto
from smr.smrworld import SmrWorld
from smr.xmindsheet import XmindSheet, get_child_nodes


def get_ancestry(topic, descendants):
    if topic.parent.name == 'sheet':
        descendants.reverse()
        return descendants
    else:
        parent_topic = get_parent_node(topic)
        descendants.append(parent_topic)
        return get_ancestry(topic=parent_topic, descendants=descendants)


def get_node_hyperlink(node: Tag) -> str:
    """
    Gets the hyperlink of an xmind node
    :param node: the tag representing th node to get the hyperlink from
    :return: node's raw hyperlink string, empty string if it has none
    """
    try:
        return node['xlink:href']
    except KeyError:
        return ''


def get_node_image(node: Tag) -> Optional[str]:
    """
    Gets the image uri of an xmind node
    :param node: the tag representing the node to get the image from
    :return: node's raw image uri, None if it has none
    """
    image_attribute = node.find('xhtml:img', recursive=False)
    if image_attribute:
        return image_attribute['xhtml:src']
    else:
        return None


def get_node_title(node: Tag) -> str:
    """
    Gets the title of an xmind node
    :param node: Tag representing the node to get the title from
    :return: node's title, empty string if it has none
    """
    try:
        return node.find('title', recursive=False).text
    except AttributeError:
        return ''


def get_parent_a_topics(q_topic, parent_q):
    parent_q_children = get_child_nodes(parent_q)
    parent_topic = next(t for t in parent_q_children if
                        q_topic.text in t.text)
    if is_empty_node(parent_topic):
        return [t for t in parent_q_children if not is_empty_node(t)]
    else:
        return [parent_topic]


def get_parent_question_topic(tag):
    parent_relation_topic = get_parent_node(get_parent_node(tag))
    if is_anki_question(parent_relation_topic):
        return parent_relation_topic
    else:
        return get_parent_question_topic(parent_relation_topic)


def get_parent_node(tag: Tag) -> Tag:
    """
    gets the tag representing the parent node of the node represented by the specified tag
    :param tag: the tag representing the node to get the parent node for
    :return: the tag representing the parent node
    """
    return tag.parent.parent.parent


def get_topic_index(tag):
    return sum(1 for _ in tag.previous_siblings) + 1


def isQuestionNode(tag, level=0):
    # If the Tag is the root topic, return true if the length of the path is odd
    if tag.parent.name == 'sheet':
        return level % 2 == 1
    # Else add one to the path length and test again
    return isQuestionNode(tag.parent.parent.parent, level + 1)


def get_non_empty_sibling_nodes(tag: Tag) -> List[Tag]:
    """
    gets all nodes that are siblings of the node represented by the specified tag and not empty
    :param tag: the tag representing the node to get the sibling nodes for
    :return: the sibling nodes as a list of tags
    """
    return [node for node in get_child_nodes(get_parent_node(tag)) if not is_empty_node(node)]


def is_anki_question(tag):
    """
    Returns true if the tag would be represented as a question in anki,
    that is, it is a relation, not empty and has at least one answer that is
    not an empty topic
    :param tag: The tag to check whether it is an anki question tag
    :return: True if the tag is an anki question, false if it is not
    """
    if not isQuestionNode(tag):
        return False
    if is_empty_node(tag):
        return False
    children = get_child_nodes(tag)
    if len(children) == 0:
        return False
    for child in children:
        if not is_empty_node(child):
            return True
    return False


def is_crosslink(href):
    return href.startswith('xmind:#')


def is_crosslink_node(tag):
    href = get_node_hyperlink(tag)
    if not href or get_node_title(tag) or get_node_image(tag) or not is_crosslink(
            href):
        return False
    return True


def is_empty_node(tag: Tag):
    """
    Checks whether the node represented by the specified tag does not contain any title, image or media
    :param tag: tag to check for
    :return: True if node does not contain any title, image or hyperlink
    """
    if get_node_title(tag):
        return False
    if get_node_image(tag):
        return False
    if get_node_hyperlink(tag):
        return False
    return True


class NodeNotFoundError(Exception):
    """
    Exception that occurs when a node is not found in the manager's node dict.
    """
    ERROR_MESSAGE = 'Node with id "{}" not found.'

    def __init__(self, node_id):
        self.node_id = node_id
        self.message = self.ERROR_MESSAGE.format(node_id)


class XManager:
    MANAGED_FILES_NAMES = ['content.xml', 'META-INF/manifest.xml']

    def __init__(self, file: Union[str, XmindFileDto]):
        self.file = file
        self.file_last_modified = None
        self.map_last_modified = None
        self.soup = None
        self.manifest = None
        self.sheets = None
        self.content_sheets = None
        self.files_2_add = {}
        self.file_bin = []
        self.did_introduce_changes = False
        self.node_dict = None

    @property
    def file(self) -> str:
        return self._file

    @file.setter
    def file(self, value: Union[str, XmindFileDto]):
        if type(value) == XmindFileDto:
            self._file = os.path.join(value.directory, value.file_name + '.xmind')
        else:
            self._file = value

    @property
    def soup(self) -> BeautifulSoup:
        if not self._soup:
            with ZipFile(self.file, 'r') as zip_file:
                self.soup = BeautifulSoup(zip_file.read('content.xml'), features='html.parser')
        return self._soup

    @soup.setter
    def soup(self, value: BeautifulSoup):
        self._soup = value

    @property
    def manifest(self) -> BeautifulSoup:
        if not self._manifest:
            with ZipFile(self.file, 'r') as zip_file:
                self.manifest = BeautifulSoup(zip_file.read("META-INF/manifest.xml"), features='html.parser')
        return self._manifest

    @manifest.setter
    def manifest(self, value: BeautifulSoup):
        self._manifest = value

    @property
    def sheets(self) -> Dict[str, XmindSheet]:
        if not self._sheets:
            sheets = {}
            for sheet in self.soup('sheet'):
                sheets[sheet['id']] = XmindSheet(sheet)
            self.sheets = sheets
        return self._sheets

    @sheets.setter
    def sheets(self, value: Dict[str, XmindSheet]):
        self._sheets = value

    @property
    def file_bin(self) -> List[str]:
        return self._file_bin

    @file_bin.setter
    def file_bin(self, value: List[str]):
        self._file_bin = value

    @property
    def node_dict(self) -> Dict[str, Tag]:
        if not self._node_dict:
            # Nested list comprehension explained:
            # https://stackoverflow.com/questions/20639180/explanation-of-how-nested-list-comprehension-works
            self.node_dict = {t['id']: t for s in self.sheets.values() for t in s['nodes']}
        return self._node_dict

    @node_dict.setter
    def node_dict(self, value: Dict[str, Tag]):
        self._node_dict = value

    @property
    def file_last_modified(self) -> float:
        if not self._file_last_modified:
            self.file_last_modified = os.stat(self.file).st_mtime
        return self._file_last_modified

    @file_last_modified.setter
    def file_last_modified(self, value: float):
        self._file_last_modified = value

    @property
    def map_last_modified(self) -> int:
        if not self._map_last_modified:
            self.map_last_modified = int(self.soup.find('xmap-content')['timestamp'])
        return self._map_last_modified

    @map_last_modified.setter
    def map_last_modified(self, value: int):
        self._map_last_modified = value

    @property
    def files_2_add(self) -> Dict[str, bytes]:
        return self._files_2_add

    @files_2_add.setter
    def files_2_add(self, value: Dict[str, bytes]):
        self._files_2_add = value

    @property
    def did_introduce_changes(self) -> bool:
        return self._did_introduce_changes

    @did_introduce_changes.setter
    def did_introduce_changes(self, value: bool):
        self._did_introduce_changes = value

    def get_hyperlink_uri(self, node: Tag) -> Optional[str]:
        """
        converts a path from the format that is provided in xmind files into the standard os format
        :param node: the node to get the uri from
        :return: the clean path in os format, a relative identifier if the hyperlink is embedded, and None if the
        node has no hyperlink
        """
        href = get_node_hyperlink(node)
        if not href:
            return
        # for media that was referenced via hyperlink, return an absolute path
        if href.startswith('file'):
            if href[5:7] == "//":
                uri = os.path.normpath(urllib.parse.unquote(href[7:]))
            else:
                uri = os.path.join(os.path.split(self.file)[0], urllib.parse.unquote(href[5:]))
        # for embedded media, return the relative path
        else:
            uri = href[4:]
        return uri

    def get_node_content(self, tag: Tag) -> NodeContentDto:
        """
        Gets the content of the node represented by the specified Tag in a dictionary
        :param tag: the tag representing the node to get the content of
        :return: a NodeContentDTO containing the contents of the node
        """
        node_content = NodeContentDto()
        node_content.title = get_node_title(tag)

        # if necessary add image
        node_image = get_node_image(node=tag)
        if node_image:
            node_content.image = node_image[4:]

        # if necessary add sound
        hyperlink_uri = self.get_hyperlink_uri(tag)
        if hyperlink_uri and hyperlink_uri.endswith(X_MEDIA_EXTENSIONS):
            node_content.media = hyperlink_uri
        return node_content

    def get_node_content_by_id(self, node_id: str) -> NodeContentDto:
        """
        gets a node's content from its node id
        :param node_id: xmind node id of the node to get the content from
        :return: the node content in a node content dto
        """
        node = self.get_tag_by_id(node_id)
        return self.get_node_content(node)

    def get_sheet_name(self, sheet_id: str) -> str:
        """
        Gets the title of the sheet with the specified xmind sheet id
        :param sheet_id: xmind id of the sheet to get the name of
        :return: the name of the sheet
        """
        return self.sheets[sheet_id]['tag']('title', recursive=False)[0].text

    def get_sheet_last_modified(self, sheet_id: str) -> int:
        """
        Gets the internally saved timestamp of the last time the sheet with the provided name was modified
        :param sheet_id: xmind sheet id of the sheet to get the timestamp for
        :return: the timestamp (integer)
        """
        return int(self.sheets[sheet_id]['tag']['timestamp'])

    def read_attachment(self, attachment_uri: str) -> bytes:
        """
        extracts an attachment from the manager's file and saves it to the specified directory
        :param attachment_uri: uri of the attachment (of the form attachment/filename)
        :return: the attachment as binary data
        """
        with ZipFile(self.file, 'r') as zip_file:
            with zip_file.open(attachment_uri) as attachment:
                return attachment.read()

    def get_tag_by_id(self, tag_id: str):
        """
        Gets the tag that
        :param tag_id: the id property of the tag
        :return: the tag containing the Id
        """
        try:
            return self.node_dict[tag_id]
        except KeyError as exception_info:
            raise NodeNotFoundError(exception_info.args[0])

    def get_directory_and_file_name(self) -> Tuple[str, str]:
        """
        Gets the directory and the file name from the manager's own path
        :return: The directory and the file without extension as strings
        """
        directory, file_name = os.path.split(self.file)
        file_name = os.path.splitext(file_name)[0]
        return directory, file_name

    def get_remote(self):
        remote_sheets = self.get_remote_sheets()

        for s in remote_sheets:
            remote_questions = self.get_remote_questions(s)
            remote_sheets[s]['questions'] = remote_questions

        remote = self.remote_file(remote_sheets)
        return remote

    # def get_remote_questions(self, sheet_id):
    #     remote_questions = dict()
    #     for t in next(v for v in self.sheets.values() if
    #                   v['tag']['id'] == sheet_id)['nodes']:
    #         if is_anki_question(t):
    #             answers = dict()
    #             remote_questions[t['id']] = {'xMod': t['timestamp'],
    #                                          'index': get_topic_index(t),
    #                                          'answers': answers}
    #             for a in self.get_answer_nodes(self.get_tag_by_id(t['id'])):
    #                 answers[a['src']['id']] = {
    #                     'xMod': a['src']['timestamp'],
    #                     'index': get_topic_index(a['src']),
    #                     'crosslink': {}}
    #                 if a['crosslink']:
    #                     answers[a['src']['id']]['crosslink'] = {
    #                         'xMod': a['crosslink']['timestamp'],
    #                         'x_id': a['crosslink']['id']}
    #     return remote_questions

    # def get_remote_sheets(self):
    #     content_keys = self.get_content_sheets()
    #     content_sheets = [self.sheets[s] for s in content_keys]
    #     sheets = dict()
    #     for s in content_sheets:
    #         sheets[s['tag']['id']] = {'xMod': s['tag']['timestamp']}
    #     return sheets

    def remove_node(self, node_id: str):
        """
        Removes the node with the specified xmind id from the map
        :param node_id: the xmind node id of the node to remove
        """
        tag = self.get_tag_by_id(node_id)
        if not get_child_nodes(tag):
            tag.decompose()
            del self.node_dict[node_id]
            self.did_introduce_changes = True
        else:
            raise AttributeError('Topic has subtopics, can not remove.')

    def save_changes(self) -> None:
        """
        Closes the map and saves changes if they were made
        """
        if self.did_introduce_changes:
            assert self.manifest and self.soup
            self._update_zip()

    def set_node_content(self, node_id: str, content: NodeContentDto, media_directory: str,
                         smr_world: SmrWorld) -> None:
        """
        Sets an xmind node's title and image to the ones specified in the content dto
        :param node_id: the node's xmind_id
        :param content: the node's content
        :param media_directory: the anki's collection.media directory to get images from
        :param smr_world: the smr world to register newly added and removed images
        """
        tag = self.get_tag_by_id(node_id)
        if content.title != get_node_title(tag):
            self.set_node_title(tag=tag, title=content.title)
        # change the image if
        # - the note has an image and the node not
        # - the images of note and tag are different or
        # - the image was removed
        node_image = get_node_image(tag)
        if (content.image and not node_image or content.image and content.image != node_image) or \
                node_image and not content.image:
            self.set_node_image(tag=tag, note_image=content.image, node_image=node_image,
                                media_directory=media_directory, smr_world=smr_world)

    def set_node_image(self, tag: Tag, note_image: Optional[str], node_image: Optional[str], media_directory: str,
                       smr_world: SmrWorld) -> None:
        """
        Sets the image of an xmind node.
        - If no note image is specified, removes the image from the specified node
        - If no node image is specified, adds the note image to the specified node
        - If both note and node image are specified, changes the node's image to the note's image
        :param tag: the tag representing the node for which to set the image
        :param note_image: an xmind uri acquired from the note's field that specifies the image to set or None if you
        want to remove the image
        :param node_image: the current image of the node that is to be removed, with 'xap:' prefix, None if you only
        want to add an image
        :param media_directory: anki's collection.media directory where all media files are saved
        :param smr_world: the in which to save a new entry for new files or from which to delete removed images
        :return:
        """
        self.did_introduce_changes = True
        # only remove the image from the map if no note_image was specified
        if not note_image:
            tag.find('xhtml:img', recursive=False).decompose()
            xmind_uri = node_image[4:]
            self.manifest.find('file-entry', attrs={"full-path": xmind_uri}).decompose()
            self.file_bin.append(xmind_uri)
            smr_world.remove_xmind_media_to_anki_file(xmind_uri=xmind_uri)
            return
        # Add image to list of images to add
        with open(os.path.join(media_directory, note_image), "rb") as image:
            self.files_2_add[note_image] = image.read()
        new_media_type = "image/" + os.path.splitext(note_image)[1][1:]
        # Only create a new image tag and add it to the node Tag if the node does not have an image yet
        if not node_image:
            image_tag = self.manifest.new_tag(name='xhtml:img', align='bottom')
            file_entry = self.manifest.new_tag(name='file-entry')
            image_tag['xhtml:src'] = 'xap:' + note_image
            file_entry['full-path'] = note_image
            file_entry['media-type'] = new_media_type
            self.manifest.find('manifest').append(file_entry)
            tag.append(image_tag)
            smr_world.add_xmind_media_to_anki_files([XmindMediaToAnkiFilesDto(*2 * [note_image])])
            return
        # Change the image if the node already has an image
        xmind_uri = node_image[4:]
        file_entry = self.manifest.find('file-entry', attrs={"full-path": xmind_uri})
        self.file_bin.append(xmind_uri)
        file_entry['full-path'] = note_image
        file_entry['media-type'] = new_media_type
        tag.find('xhtml:img', recursive=False)['xhtml:src'] = 'xap:' + note_image
        smr_world.remove_xmind_media_to_anki_file(xmind_uri=xmind_uri)
        smr_world.add_xmind_media_to_anki_files([XmindMediaToAnkiFilesDto(*2 * [note_image])])

    def set_node_title(self, tag: Tag, title: str):
        """
        Sets the title of an xmind node
        :param tag: the tag representing the node to set the title for
        :param title: the title to set for the node
        """
        try:
            tag.find('title', recursive=False).string = title
        except AttributeError:
            title_tag = self.soup.new_tag(name='title')
            title_tag.string = title
            tag.append(title_tag)
        self.did_introduce_changes = True

    def _update_zip(self) -> None:
        """
        - replaces the content.xml file in the xmind file with the manager's content soup
        - replaces the manifest.xml with the manager's manifest soup
        - removes all files in the file_bin from the xmind file
        - adds all files in files_2_add to the xmind file
        code was adopted from
        https://stackoverflow.com/questions/25738523/how-to-update-one-file-inside-zip-file-using-python,
        """
        # generate a temp file
        temp_file_directory, temp_file_name = tempfile.mkstemp(dir=os.path.dirname(self.file))
        os.close(temp_file_directory)
        # create a temporary copy of the archive without filename
        with ZipFile(self.file, 'r') as zip_file_in:
            with ZipFile(temp_file_name, 'w') as zip_file_out:
                zip_file_out.comment = zip_file_in.comment  # preserve the comment
                for item in zip_file_in.infolist():
                    # keep all files that are not managed by the manager and that are not in the file bin
                    if item.filename not in self.MANAGED_FILES_NAMES + self.file_bin:
                        zip_file_out.writestr(item, zip_file_in.read(item.filename))
        # Replace managed file with temporary file
        os.remove(self.file)
        os.rename(temp_file_name, self.file)
        # now add filename with its new data
        with ZipFile(self.file, mode='a', compression=ZIP_DEFLATED) as zip_file:
            zip_file.writestr('content.xml', str(self.soup))
            for file_uri, file in self.files_2_add.items():
                zip_file.writestr(zinfo_or_arcname=file_uri, data=file)
            zip_file.writestr(zinfo_or_arcname='META-INF/manifest.xml', data=str(self.manifest))
