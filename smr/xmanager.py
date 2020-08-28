# class for reading and writing xmind files

import os
import tempfile
from typing import Dict, List, Optional, Tuple, Union
from zipfile import ZipFile, ZIP_DEFLATED

from bs4 import BeautifulSoup

from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindmediatoankifilesdto import XmindMediaToAnkiFilesDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.smrworld import SmrWorld
from smr.xmindsheet import XmindSheet
from smr.xmindtopic import XmindNode, XmindEdge


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
        self.edge_dict = None

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
                sheets[sheet['id']] = XmindSheet(sheet, self.file)
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
    def node_dict(self) -> Dict[str, XmindNode]:
        if not self._node_dict:
            node_dict = {}
            for sheet in self.sheets.values():
                node_dict.update(sheet.nodes)
            self.node_dict = node_dict
        return self._node_dict

    @node_dict.setter
    def node_dict(self, value: Dict[str, XmindNode]):
        self._node_dict = value

    @property
    def edge_dict(self) -> Dict[str, XmindEdge]:
        if not self._edge_dict:
            edge_dict = {}
            for sheet in self.sheets.values():
                edge_dict.update(sheet.edges)
            self.edge_dict = edge_dict
        return self._edge_dict

    @edge_dict.setter
    def edge_dict(self, value: Dict[str, XmindEdge]):
        self._edge_dict = value

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

    def get_node_content_by_id(self, node_id: str) -> TopicContentDto:
        """
        gets a node's content from its node id
        :param node_id: xmind node id of the node to get the content from
        :return: the node content in a node content dto
        """
        node = self.get_node_by_id(node_id)
        return node.content

    def read_attachment(self, attachment_uri: str) -> bytes:
        """
        extracts an attachment from the manager's file and saves it to the specified directory
        :param attachment_uri: uri of the attachment (of the form attachment/filename)
        :return: the attachment as binary data
        """
        with ZipFile(self.file, 'r') as zip_file:
            with zip_file.open(attachment_uri) as attachment:
                return attachment.read()

    def get_node_by_id(self, node_id: str) -> XmindNode:
        """
        Gets the node with the specified xmind id
        :param node_id: the node's xmind id
        :return: the tag containing the Id
        """
        try:
            return self.node_dict[node_id]
        except KeyError as exception_info:
            raise NodeNotFoundError(exception_info.args[0])

    def get_edge_by_id(self, edge_id: str) -> XmindEdge:
        """
        Gets the edge with the specified xmind id
        :param edge_id: the edge's xmind id
        :return: the tag representing the edge with the specified id
        """
        try:
            return self.edge_dict[edge_id]
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

    def remove_node(self, node_id: str):
        """
        Removes the node with the specified xmind id from the map
        :param node_id: the xmind node id of the node to remove
        """
        node = self.get_node_by_id(node_id)
        if not node.child_edges:
            node.decompose()
        else:
            raise AttributeError('Topic has subtopics, can not remove.')
        del self.node_dict[node_id]
        del self.sheets[node.sheet_id].nodes[node_id]
        self.did_introduce_changes = True

    def save_changes(self) -> None:
        """
        Closes the map and saves changes if they were made
        """
        if self.did_introduce_changes:
            assert self.manifest and self.soup
            self._update_zip()

    def set_node_content(self, node_id: str, content: TopicContentDto, media_directory: str,
                         smr_world: SmrWorld) -> None:
        """
        Sets an xmind node's title and image to the ones specified in the content dto
        :param node_id: the node's xmind_id
        :param content: the node's content
        :param media_directory: the anki's collection.media directory to get images from
        :param smr_world: the smr world to register newly added and removed images
        """
        node = self.get_node_by_id(node_id)
        self._set_topic_content(topic=node, content=content, media_directory=media_directory, smr_world=smr_world)

    def set_edge_content(self, edge: XmindTopicDto, media_directory: str, smr_world: SmrWorld) -> None:
        """
        Sets an xmind edge's title and image to the ones specified in the content dto
        :param edge: xmind topic dto of the edge of which to set the content
        :param media_directory: the anki's collection.media directory to get images from
        :param smr_world: the smr world to register newly added and removed images
        """
        edge = self.get_edge_by_id(edge.node_id)
        self._set_topic_content(topic=edge, content=edge.content, media_directory=media_directory, smr_world=smr_world)

    def _set_topic_content(self, topic: Union[XmindEdge, XmindNode], content: TopicContentDto, media_directory: str,
                           smr_world: SmrWorld) -> None:
        """
        Sets an xmind topic's title and image to the ones specified in the content dto
        :param topic: the topic to set the content for
        :param content: the topic's content
        :param media_directory: anki's collection.media directory to get images from
        :param smr_world: the smr world to register newly added and removed images
        """
        topic.content = content
        if content.title != topic.title:
            topic.title = content.title
            self.did_introduce_changes = True
        # change the image if
        # - the note has an image and the node not
        # - the images of note and tag are different or
        # - the image was removed
        if (content.image and not topic.image or content.image and content.image != topic.image) or \
                topic.image and not content.image:
            self.set_topic_image(topic=topic, image_name=content.image,
                                 media_directory=media_directory, smr_world=smr_world)

    def set_topic_image(self, topic: Union[XmindNode, XmindEdge], image_name: Optional[str],
                        media_directory: str, smr_world: SmrWorld) -> None:
        """
        Sets the image of an xmind node.
        - If no note image is specified, removes the image from the specified node
        - If no node image is specified, adds the note image to the specified node
        - If both note and node image are specified, changes the node's image to the note's image
        :param topic: the tag representing the topic for which to set the image
        :param image_name: an xmind uri acquired from the note's field that specifies the image to set or None if you
        want to remove the image
        :param media_directory: anki's collection.media directory where all media files are saved
        :param smr_world: the in which to save a new entry for new files or from which to delete removed images
        :return:
        """
        self.did_introduce_changes = True
        # only remove the image from the map if no note_image was specified
        if not image_name:
            self.manifest.find('file-entry', attrs={"full-path": topic.image}).decompose()
            self.file_bin.append(topic.image)
            smr_world.remove_xmind_media_to_anki_file(xmind_uri=topic.image)
            del topic.image
            return
        # Add image to list of images to add
        with open(os.path.join(media_directory, image_name), "rb") as image:
            self.files_2_add[image_name] = image.read()
        new_media_type = "image/" + os.path.splitext(image_name)[1][1:]
        # Only create a new image tag and add it to the node Tag if the node does not have an image yet
        if topic.image is None:
            topic.image = image_name
            file_entry = self.manifest.new_tag(name='file-entry')
            file_entry['full-path'] = image_name
            file_entry['media-type'] = new_media_type
            self.manifest.find('manifest').append(file_entry)
            smr_world.add_xmind_media_to_anki_files([XmindMediaToAnkiFilesDto(*2 * [image_name])])
            return
        # Change the image if the node already has an image
        file_entry = self.manifest.find('file-entry', attrs={"full-path": topic.image})
        file_entry['full-path'] = image_name
        file_entry['media-type'] = new_media_type
        self.file_bin.append(topic.image)
        smr_world.remove_xmind_media_to_anki_file(xmind_uri=topic.image)
        smr_world.add_xmind_media_to_anki_files([XmindMediaToAnkiFilesDto(*2 * [image_name])])
        topic.image = image_name

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
