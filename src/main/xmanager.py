# class for reading and writing xmind files

import os
import shutil
import tempfile
import urllib.parse
from typing import Dict, List, Optional
from zipfile import ZipFile, ZIP_DEFLATED

from bs4 import BeautifulSoup, Tag
from main.consts import X_MEDIA_EXTENSIONS
from main.dto.nodecontentdto import NodeContentDTO
from main.xnotemanager import ref_plus_question, ref_plus_answer, field_from_content, update_sort_id


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


def get_os_mod(file):
    os_mod = os.stat(file).st_mtime
    return os_mod


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
            'topics', recursive=False)('topic', recursive=False)
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


def get_node_content(tag: Tag) -> NodeContentDTO:
    """
    Gets the content of the node represented by the specified Tag in a dictionary
    :param tag: the tag representing the node to get the content of
    :return: a NodeContentDTO containing the contents of the node
    """
    node_content = NodeContentDTO()
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


class XManager:
    def __init__(self, file):
        self._file: str = file
        self.xZip: ZipFile = ZipFile(file, 'r')
        self.soup: BeautifulSoup = BeautifulSoup(self.xZip.read('content.xml'), features='html.parser')
        self.manifest: BeautifulSoup = BeautifulSoup(self.xZip.read("META-INF/manifest.xml"), features='html.parser')
        self.srcDir: str = tempfile.mkdtemp()
        self._sheets: Dict[str, Dict] = None
        self._referenced_files = None
        self.fileBin = []
        self.did_introduce_changes = False
        self.tag_list = None

    def get_referenced_files(self):
        if not self._referenced_files:
            self._register_referenced_files()
        return self._referenced_files

    def get_sheets(self):
        if not self._sheets:
            self._register_sheets()
        return self._sheets

    def get_file(self):
        return self._file

    def get_sheet_id(self, sheet: str):
        """
        Gets the xmind sheet id for the specified sheet
        :param sheet: the name of the sheet to get the id for
        :return: the sheet's id
        """
        return self.get_sheets()[sheet]['tag']['id']

    def _register_sheets(self):
        self._sheets = dict()
        for sheet in self.soup('sheet'):
            sheet_title = sheet('title', recursive=False)[0].text
            self._sheets[sheet_title] = {'tag': sheet, 'nodes': sheet('topic')}

    def content_by_id(self, x_id):
        topic = self.get_tag_by_id(x_id)
        return get_node_content(topic)

    def get_answer_nodes(self, tag):
        return [{'src': n, 'crosslink': '' if not is_crosslink_node(n)
                else self.get_tag_by_id(getNodeCrosslink(n))} for n in
                get_child_nodes(tag) if not is_empty_node(n)]

    def read_attachment(self, attachment_uri: str) -> bytes:
        """
        extracts an attachment from the manager's file and saves it to the specified directory
        :param attachment_uri: uri of the attachment (of the form attachment/filename)
        :return: the attachment as binary data
        """
        with self.xZip.open(attachment_uri) as attachment:
            return attachment.read()

    def get_remote(self):
        remote_sheets = self.get_remote_sheets()

        for s in remote_sheets:
            remote_questions = self.get_remote_questions(s)
            remote_sheets[s]['questions'] = remote_questions

        remote = self.remote_file(remote_sheets)
        return remote

    def get_remote_questions(self, sheet_id):
        remote_questions = dict()
        for t in next(v for v in self.get_sheets().values() if
                      v['tag']['id'] == sheet_id)['nodes']:
            if is_anki_question(t):
                answers = dict()
                remote_questions[t['id']] = {'xMod': t['timestamp'],
                                             'index': get_topic_index(t),
                                             'answers': answers}
                for a in self.get_answer_nodes(self.get_tag_by_id(t['id'])):
                    answers[a['src']['id']] = {
                        'xMod': a['src']['timestamp'],
                        'index': get_topic_index(a['src']),
                        'crosslink': {}}
                    if a['crosslink']:
                        answers[a['src']['id']]['crosslink'] = {
                            'xMod': a['crosslink']['timestamp'],
                            'x_id': a['crosslink']['id']}
        return remote_questions

    def get_remote_sheets(self):
        content_keys = self.get_content_sheets()
        content_sheets = [self.get_sheets()[s] for s in content_keys]
        sheets = dict()
        for s in content_sheets:
            sheets[s['tag']['id']] = {'xMod': s['tag']['timestamp']}
        return sheets

    def get_tag_by_id(self, tag_id: str):
        """
        Gets the tag that
        :param tag_id: the id property of the tag
        :return: the tag containing the Id
        """
        return next(t for t in self.get_or_compute_tag_list() if t['id'] == tag_id)

    def remote_file(self, sheets=None):
        doc_mod = self.get_map_last_modified()
        os_mod = self.get_file_last_modified()
        remote = {'file': self._file, 'xMod': doc_mod, 'osMod': os_mod,
                  'sheets': sheets}
        return remote

    def get_file_last_modified(self):
        """
        Gets the timestamp of the last time the XManagers file was edited according to the file system
        :return: the timestamp (Real value)
        """
        return get_os_mod(self._file)

    def get_map_last_modified(self):
        """
        Gets the internally saved timestamp of the last time the file was modified
        :return: the timestamp (integer value)
        """
        return self.soup.find('xmap-content')['timestamp']

    def get_sheet_last_modified(self, sheet: str):
        """
        Gets the internally saved timestamp of the last time the sheet with the provided name was modified
        :param sheet: name of the sheet to get the timestamp for
        :return: the timestamp (integer)
        """
        return self.get_sheets()[sheet]['tag']['timestamp']

    def get_root_node(self, sheet: str):
        """
        Returns the root topic of the specified sheet
        :param sheet: the sheet to get the root topic for
        :return: the tag representing the root node
        """
        return self.get_sheets()[sheet]['tag'].topic

    def remove_node(self, a_id):
        tag = self.get_tag_by_id(a_id)
        if not get_child_nodes(tag):
            tag.decompose()
            self.tag_list.remove(tag)
            self.did_introduce_changes = True
        else:
            raise AttributeError('Topic has subtopics, can not remove.')

    def save_changes(self):
        self.xZip.close()
        if self.did_introduce_changes:
            self.updateZip()
        # Remove temp dir and its files
        shutil.rmtree(self.srcDir)

    def set_node_content(self, x_id, title, img, media_dir):
        tag = self.get_tag_by_id(x_id)
        if title != get_node_title(tag):
            self.setNodeTitle(tag=tag, title=title)

        # Remove crosslink if the tag has one
        if getNodeCrosslink(tag):
            del tag['xlink:href']

        nodeImg = get_node_image(tag)

        # If the note has an image and the tag not or the image is different
        # or the image was deleted, change it
        if (img and not nodeImg or img and img not in nodeImg) or \
                nodeImg and not img:
            self.set_node_img(tag=tag, noteImg=img, nodeImg=nodeImg,
                              media_dir=media_dir)
        self.did_introduce_changes = True

    def set_node_img(self, tag, noteImg, nodeImg, media_dir):
        if not noteImg:
            # remove image node from Map, i do not know why decompose() has
            # to be called twice but it only works this way
            imgTag = tag.find('xhtml:img')
            imgTag.decompose()
            fullPath = nodeImg[4:]
            self.fileBin.append(fullPath)
            self.manifest.find('file-entry',
                               attrs={"full-path": fullPath}).decompose()
            return
        # move image from note to the directory of images to add
        imgPath = os.path.join(media_dir, noteImg)
        shutil.copy(src=imgPath, dst=self.srcDir)
        newFullPath = 'attachments/' + noteImg
        newMediaType = "image/" + os.path.splitext(noteImg)[1][1:]
        if not nodeImg:
            # create a new image tag and add it to the node Tag
            imgTag = self.manifest.new_tag(name='xhtml:img', align='bottom')
            fileEntry = self.manifest.new_tag(name='file-entry')
            imgTag['xhtml:src'] = 'xap:' + newFullPath
            fileEntry['full-path'] = newFullPath
            fileEntry['media-type'] = newMediaType
            self.manifest.find('manifest').append(fileEntry)
            tag.append(imgTag)
            return
        # change image
        fullPath = nodeImg[4:]
        self.fileBin.append(fullPath)
        fileEntry = self.manifest.find('file-entry',
                                       attrs={"full-path": fullPath})
        fileEntry['full-path'] = newFullPath
        fileEntry['media-type'] = newMediaType
        imgTag = tag.find('xhtml:img')
        imgTag['xhtml:src'] = 'xap:' + newFullPath

    def setNodeTitle(self, tag, title):
        try:
            tag.find('title', recursive=False).string = title
        except AttributeError:
            title_tag = self.soup.new_tag(name='title')
            title_tag.string = title
            tag.append(title_tag)

    def updateZip(self):
        """ taken from https://stackoverflow.com/questions/25738523/how-to-update-one-file-inside-zip-file-using-python, replaces one file in a zipfile"""
        # generate a temp file
        tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(self._file))
        os.close(tmpfd)

        # create a temp copy of the archive without filename
        with ZipFile(self._file, 'r') as zin:
            with ZipFile(tmpname, 'w') as zout:
                zout.comment = zin.comment  # preserve the comment
                for item in zin.infolist():
                    if item.filename not in ['content.xml',
                                             'META-INF/manifest.xml'] + \
                            self.fileBin:
                        zout.writestr(item, zin.read(item.filename))

        # replace with the temp archive
        os.remove(self._file)
        os.rename(tmpname, self._file)

        # now add filename with its new data
        with ZipFile(self._file, mode='a',
                     compression=ZIP_DEFLATED) as zf:
            zf.writestr('content.xml', str(self.soup))
            for file in os.listdir(self.srcDir):
                zf.write(filename=os.path.join(self.srcDir, file),
                         arcname=os.path.join('attachments', file))
            zf.writestr(zinfo_or_arcname='META-INF/manifest.xml',
                        data=str(self.manifest))

    def get_content_sheets(self):
        return [k for k in self.get_sheets().keys() if k != 'ref']

    def get_or_compute_tag_list(self):
        """
        If the tag_list has not been computed yet computes it and returns it. The tag_list is a list of all tags
        contained in all sheets managed by this XManager
        :return: the tag_list
        """
        if not self.tag_list:
            # Nested list comprehension explained:
            # https://stackoverflow.com/questions/20639180/explanation-of-how-nested-list-comprehension-works
            self.tag_list = [t for s in self.get_sheets().values() for t in s['nodes']]
        return self.tag_list

    def ref_and_sort_id(self, q_topic):
        ancestry = get_ancestry(topic=q_topic, descendants=[])
        ref = get_node_title(ancestry.pop(0))
        sort_id = ''
        mult_subjects = False
        follows_bridge = False
        for i, ancestor in enumerate(ancestry):
            field = field_from_content(get_node_content(ancestor))
            sort_id = update_sort_id(sort_id, get_topic_index(ancestor))
            if i % 2:
                ref = ref_plus_answer(field=field, followsBridge=follows_bridge,
                                      ref=ref, mult_subjects=mult_subjects)
                follows_bridge = False
                mult_subjects = is_empty_node(ancestor)
            else:
                ref = ref_plus_question(field=field, ref=ref)
                if not is_anki_question(ancestor):
                    follows_bridge = True
        return ref, sort_id

    def _register_referenced_files(self):
        """
        Finds the names of files to which the XManager has references to. Files are referenced in a sheet titled "ref"
        """
        self._referenced_files = []
        for sheet in self.get_sheets().values():
            # Get reference sheets
            if sheet['tag']('title', recursive=False)[0].text == 'ref':
                ref_tags = get_child_nodes(sheet['tag'].topic)
                ref_paths = (get_node_hyperlink(t) for t in ref_tags)
                self._referenced_files = [clean_ref_path(p) for p in ref_paths if p is not None]
