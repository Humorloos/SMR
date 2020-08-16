# class for reading and writing xmind files

import os
import shutil
import tempfile
import urllib.parse
from typing import Dict, List, Optional, Any, Tuple, Union
from zipfile import ZipFile, ZIP_DEFLATED

from bs4 import BeautifulSoup, Tag

from smr.consts import X_MEDIA_EXTENSIONS
from smr.dto.nodecontentdto import NodeContentDto
from smr.dto.xmindfiledto import XmindFileDto


def clean_ref_path(path: str) -> str:
    """
    converts a path from the format that is provided in xmind files into the standard os format
    :param path: the path from the xmind file
    :return: the clean path in os format
    """
    path_elements: List[str] = path.replace('file://', '').replace('%20', ' ').split('/')
    path_elements[0] = path_elements[0] + '\\'
    clean_path: str = os.path.join(*path_elements)
    return clean_path


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


def get_child_nodes(tag: Tag) -> List[Tag]:
    """
    Gets all nodes directly following the node represented by the specified tag
    :param tag: the tag representing the node to get the child nodes for
    :return: the child nodes as a list of tags, an empty list if it doesn't have any
    """
    try:
        return tag.find('children', recursive=False).find(
            'topics', recursive=False).find_all('topic', recursive=False)
    except AttributeError:
        return []


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


def get_node_content(tag: Tag) -> NodeContentDto:
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
    href = get_node_hyperlink(tag)
    if href.endswith(X_MEDIA_EXTENSIONS):
        # for media that was referenced via hyperlink
        if href.startswith('file'):
            media = urllib.parse.unquote(href[7:])
        else:
            media = href[4:]
        node_content.media = media
    return node_content


class NodeNotFoundError(Exception):
    """
    Exception that occurs when a node is not found in the manager's node dict.
    """
    ERROR_MESSAGE = 'Node with id "{}" not found.'

    def __init__(self, node_id):
        self.node_id = node_id
        self.message = self.ERROR_MESSAGE.format(node_id)


class XManager:
    FILE_NOT_FOUND_MESSAGE = 'Xmind file "{}" not found.'
    MANAGED_FILES_NAMES = ['content.xml', 'META-INF/manifest.xml']

    def __init__(self, file: Union[str, XmindFileDto]):
        self.file = file
        self.file_last_modified = None
        self.map_last_modified = None
        self.zip_file = None
        self.soup = None
        self.manifest = None
        self.sheets = None
        self.content_sheets = None
        self.referenced_files = None
        self.referenced_x_managers = []
        self.notes_2_add = []
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
    def zip_file(self) -> ZipFile:
        if not self._zip_file:
            try:
                self.zip_file: ZipFile = ZipFile(self.file, 'r')
            except FileNotFoundError:
                raise FileNotFoundError(self.FILE_NOT_FOUND_MESSAGE.format(self.file))
        return self._zip_file

    @zip_file.setter
    def zip_file(self, value: ZipFile):
        self._zip_file = value

    @property
    def soup(self) -> BeautifulSoup:
        if not self._soup:
            self.soup = BeautifulSoup(self.zip_file.read('content.xml'), features='html.parser')
        return self._soup

    @soup.setter
    def soup(self, value: BeautifulSoup):
        self._soup = value

    @property
    def manifest(self) -> BeautifulSoup:
        if not self._manifest:
            self.manifest = BeautifulSoup(self.zip_file.read("META-INF/manifest.xml"), features='html.parser')
        return self._manifest

    @manifest.setter
    def manifest(self, value: BeautifulSoup):
        self._manifest = value

    @property
    def sheets(self) -> Dict[str, Dict[str, Union[Tag, List[Tag]]]]:
        if not self._sheets:
            sheets = {}
            for sheet in self.soup('sheet'):
                sheets[sheet('title', recursive=False)[0].text] = {'tag': sheet, 'nodes': sheet('topic')}
            self.sheets = sheets
        return self._sheets

    @sheets.setter
    def sheets(self, value: Dict[str, Dict[str, Union[Tag, List[Tag]]]]):
        self._sheets = value

    @property
    def referenced_x_managers(self) -> List['XManager']:
        if not self._referenced_x_managers:
            self.referenced_x_managers = self._get_referenced_x_managers()
        return self._referenced_x_managers

    @referenced_x_managers.setter
    def referenced_x_managers(self, value: List['XManager']):
        self._referenced_x_managers = value

    def _get_referenced_x_managers(self) -> List['XManager']:
        ref_managers = [XManager(f) for f in self.referenced_files]
        for manager in ref_managers:
            ref_managers.extend(XManager._get_referenced_x_managers(manager))
        return ref_managers

    @property
    def referenced_files(self) -> List[str]:
        if not self._referenced_files:
            referenced_files = []
            for sheet in self.sheets.values():
                # Get reference sheets
                if sheet['tag']('title', recursive=False)[0].text == 'ref':
                    ref_tags = get_child_nodes(sheet['tag'].topic)
                    ref_paths = (get_node_hyperlink(t) for t in ref_tags)
                    referenced_files.extend(clean_ref_path(p) for p in ref_paths if p is not None)
            self.referenced_files = referenced_files
        return self._referenced_files

    @referenced_files.setter
    def referenced_files(self, value: List[str]):
        self._referenced_files = value

    @property
    def file_bin(self) -> List[str]:
        return self. _file_bin

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
    def content_sheets(self) -> List[str]:
        if not self._content_sheets:
            self.content_sheets = [sheet_name for sheet_name in self.sheets.keys() if sheet_name != 'ref']
        return self._content_sheets

    @content_sheets.setter
    def content_sheets(self, value: List[str]):
        self._content_sheets = value

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
    def notes_2_add(self) -> List[bytes]:
        return self._notes_2_add

    @notes_2_add.setter
    def notes_2_add(self, value: List[bytes]):
        self._notes_2_add = value

    @property
    def did_introduce_changes(self) -> bool:
        return self._did_introduce_changes

    @did_introduce_changes.setter
    def did_introduce_changes(self, value: bool):
        self._did_introduce_changes = value

    def get_sheet_id(self, sheet: str):
        """
        Gets the xmind sheet id for the specified sheet
        :param sheet: the name of the sheet to get the id for
        :return: the sheet's id
        """
        return self.sheets[sheet]['tag']['id']

    def read_attachment(self, attachment_uri: str) -> bytes:
        """
        extracts an attachment from the manager's file and saves it to the specified directory
        :param attachment_uri: uri of the attachment (of the form attachment/filename)
        :return: the attachment as binary data
        """
        with self.zip_file.open(attachment_uri) as attachment:
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

    def content_by_id(self, x_id):
        topic = self.get_tag_by_id(x_id)
        return get_node_content(topic)

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

    def get_remote_sheets(self):
        content_keys = self.get_content_sheets()
        content_sheets = [self.sheets[s] for s in content_keys]
        sheets = dict()
        for s in content_sheets:
            sheets[s['tag']['id']] = {'xMod': s['tag']['timestamp']}
        return sheets

    def get_sheet_last_modified(self, sheet: str) -> int:
        """
        Gets the internally saved timestamp of the last time the sheet with the provided name was modified
        :param sheet: name of the sheet to get the timestamp for
        :return: the timestamp (integer)
        """
        return int(self.sheets[sheet]['tag']['timestamp'])

    def get_root_node(self, sheet: str):
        """
        Returns the root topic of the specified sheet
        :param sheet: the sheet to get the root topic for
        :return: the tag representing the root node
        """
        return self.sheets[sheet]['tag'].topic

    def remove_node(self, a_id):
        tag = self.get_tag_by_id(a_id)
        if not get_child_nodes(tag):
            tag.decompose()
            del self.node_dict[a_id]
            self.did_introduce_changes = True
        else:
            raise AttributeError('Topic has subtopics, can not remove.')

    def save_changes(self):
        self.zip_file.close()
        if self.did_introduce_changes:
            self._update_zip()

    def set_node_content(self, node_id: str, content: NodeContentDto, media_directory: str):
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
            self.set_node_img(tag=tag, note_image=content.image, node_image=node_image, media_dir=media_directory)
        self.did_introduce_changes = True

    def set_node_img(self, tag: Tag, note_image: Optional[str], node_image: Optional[str], media_directory: str):
        # only remove the image if no note_image was specified
        if not note_image:
            image_tag = tag.find('xhtml:img')
            image_tag.decompose()
            full_image_path = node_image[4:]
            self.manifest.find('file-entry', attrs={"full-path": full_image_path}).decompose()
            self.file_bin.append(full_image_path)
            self.did_introduce_changes = True
            return
        # move image from note to the directory of images to add
        image_path = os.path.join(media_directory, note_image)
        with open(image_path) as image:
            self.files_2_add.append(image)
        xmind_uri = 'attachments/' + note_image
        newMediaType = "image/" + os.path.splitext(note_image)[1][1:]
        if not node_image:
            # create a new image tag and add it to the node Tag
            image_tag = self.manifest.new_tag(name='xhtml:img', align='bottom')
            fileEntry = self.manifest.new_tag(name='file-entry')
            image_tag['xhtml:src'] = 'xap:' + xmind_uri
            fileEntry['full-path'] = xmind_uri
            fileEntry['media-type'] = newMediaType
            self.manifest.find('manifest').append(fileEntry)
            tag.append(image_tag)
            return
        # change image
        full_image_path = node_image[4:]
        self.file_bin.append(full_image_path)
        fileEntry = self.manifest.find('file-entry',
                                       attrs={"full-path": full_image_path})
        fileEntry['full-path'] = xmind_uri
        fileEntry['media-type'] = newMediaType
        image_tag = tag.find('xhtml:img')
        image_tag['xhtml:src'] = 'xap:' + xmind_uri

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

    def _update_zip(self):
        """
        - replaces the content.xml file in the xmind file with the manager's content soup
        - replaces the manifest.xml with the manager's manifest soup
        - removes all files in the file_bin from the xmind file
        - adds all files in files_to_add to the xmind file
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
            for file in os.listdir(self.files_to_add):
                zip_file.write(filename=os.path.join(self.srcDir, file), arcname=os.path.join('attachments', file))
            zip_file.writestr(zinfo_or_arcname='META-INF/manifest.xml', data=str(self.manifest))
