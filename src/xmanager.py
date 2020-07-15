# class for reading and writing xmind files

import os
import shutil
import tempfile
import urllib.parse
import zipfile

from bs4 import BeautifulSoup
from consts import X_MEDIA_EXTENSIONS
from xnotemanager import ref_plus_question, ref_plus_answer, field_from_content, update_sort_id


def clean_ref_path(path):
    clean_path = path.replace('file://', '')
    clean_path = clean_path.replace('%20', ' ')
    clean_path = clean_path.split('/')
    clean_path[0] = clean_path[0] + '\\'
    clean_path = os.path.join(*clean_path)
    return clean_path


def get_ancestry(topic, descendants):
    if topic.parent.name == 'sheet':
        descendants.reverse()
        return descendants
    else:
        parent_topic = get_parent_topic(topic)
        descendants.append(parent_topic)
        return get_ancestry(topic=parent_topic, descendants=descendants)


def getNodeCrosslink(tag):
    """
    :param tag: tag to get the crosslink from
    :return: node id of the node the crosslink refers to
    """
    href = getNodeHyperlink(tag)
    if href and href.startswith('xmind:#'):
        return href[7:]
    else:
        return None


def getNodeHyperlink(tag):
    """
    :param tag: tag to get the hyperlink from
    :return: node's raw hyperlink string
    """
    try:
        return tag['xlink:href']
    except (KeyError, TypeError):
        return None


def getNodeImg(tag):
    """
    :param tag: Tag to get the image from
    :return: node's raw image string
    """
    try:
        return tag.find('xhtml:img', recursive=False)['xhtml:src']
    except (TypeError, AttributeError):
        return None


def getNodeTitle(tag):
    """
    :param tag: Tag to get the title from
    :return: node's title, empty string if it has none
    """
    try:
        return tag.find('title', recursive=False).text
    except AttributeError:
        return ''


def get_os_mod(file):
    os_mod = os.stat(file).st_mtime
    return os_mod


def get_parent_a_topics(q_topic, parent_q):
    parent_q_children = getChildnodes(parent_q)
    parent_topic = next(t for t in parent_q_children if
                        q_topic.text in t.text)
    if isEmptyNode(parent_topic):
        return [t for t in parent_q_children if not isEmptyNode(t)]
    else:
        return [parent_topic]


def get_parent_question_topic(tag):
    parent_relation_topic = get_parent_topic(get_parent_topic(tag))
    if is_anki_question(parent_relation_topic):
        return parent_relation_topic
    else:
        return get_parent_question_topic(parent_relation_topic)


def get_parent_topic(tag):
    return tag.parent.parent.parent


def get_topic_index(tag):
    return sum(1 for _ in tag.previous_siblings) + 1


def isQuestionNode(tag, level=0):
    # If the Tag is the root topic, return true if the length of the path is odd
    if tag.parent.name == 'sheet':
        return level % 2 == 1
    # Else add one to the path length and test again
    return isQuestionNode(tag.parent.parent.parent, level + 1)


def getChildnodes(tag):
    """
    :param tag: the tag to get the childnodes for
    :return: childnodes as tags, empty list if it doesn't have any
    """
    try:
        return tag.find('children', recursive=False).find(
            'topics', recursive=False)('topic', recursive=False)
    except AttributeError:
        return []


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
    if isEmptyNode(tag):
        return False
    children = getChildnodes(tag)
    if len(children) == 0:
        return False
    for child in children:
        if not isEmptyNode(child):
            return True
    return False


def is_crosslink(href):
    return href.startswith('xmind:#')


def is_crosslink_node(tag):
    href = getNodeHyperlink(tag)
    if not href or getNodeTitle(tag) or getNodeImg(tag) or not is_crosslink(
            href):
        return False
    return True


def isEmptyNode(tag):
    """
    :param tag: tag to check for
    :return: True if node does not contain any title, image or hyperlink
    """
    if getNodeTitle(tag):
        return False
    if getNodeImg(tag):
        return False
    if getNodeHyperlink(tag):
        return False
    return True


class XManager:
    def __init__(self, file):
        self.file = file
        self.xZip = zipfile.ZipFile(file, 'r')
        self.soup = BeautifulSoup(self.xZip.read('content.xml'), features='html.parser')
        self.manifest = BeautifulSoup(self.xZip.read("META-INF/manifest.xml"), features='html.parser')
        self.srcDir = tempfile.mkdtemp()
        self.sheets = dict()
        self._register_sheets()
        self.referenced_files = []
        self._register_referenced_files()
        self.fileBin = []
        self.did_introduce_changes = False
        self.tag_list = None

    def get_referenced_files(self):
        return self.referenced_files

    def get_sheets(self):
        return self.sheets

    def _register_sheets(self):
        for sheet in self.soup('sheet'):
            sheet_title = sheet('title', recursive=False)[0].text
            self.sheets[sheet_title] = {'tag': sheet, 'nodes': sheet('topic')}

    def content_by_id(self, x_id):
        topic = self.getTagById(x_id)
        return self.getNodeContent(topic)

    def get_answer_nodes(self, tag):
        return [{'src': n, 'crosslink': '' if not is_crosslink_node(n)
                else self.getTagById(getNodeCrosslink(n))} for n in
                getChildnodes(tag) if not isEmptyNode(n)]

    def getAttachment(self, identifier, directory):
        # extract attachment to anki media directory
        self.xZip.extract(identifier, directory)
        # get image from subdirectory attachments in mediaDir
        return os.path.join(directory, identifier)

    def getNodeContent(self, tag):
        """
        :param tag: the tag to get the content for
        :return: dictionary containing the content of the node as a string,
            an optional url to an image and a media file
        """
        content = ''
        media = dict(image=None, media=None)
        href = getNodeHyperlink(tag)
        title = getNodeTitle(tag)

        if title:
            content += title

        # if necessary add image
        attachment = getNodeImg(tag=tag)
        if attachment:
            media['image'] = attachment[4:]

        # If the node contains a link to another node, add the text of that
        # node.
        if href and is_crosslink(href):
            crosslinkTag = self.getTagById(tagId=href[7:])
            crosslinkTitle = getNodeTitle(crosslinkTag)
            if not content:
                content = crosslinkTitle

        # if necessary add sound
        if href and href.endswith(X_MEDIA_EXTENSIONS):
            if href.startswith('file'):
                mediaPath = urllib.parse.unquote(href[7:])
                media['media'] = mediaPath
            else:
                mediaPath = href[4:]
                media['media'] = mediaPath
        return {'content': content, 'media': media}

    def get_remote(self):
        remote_sheets = self.get_remote_sheets()

        for s in remote_sheets:
            remote_questions = self.get_remote_questions(s)
            remote_sheets[s]['questions'] = remote_questions

        remote = self.remote_file(remote_sheets)
        return remote

    def get_remote_questions(self, sheet_id):
        remote_questions = dict()
        for t in next(v for v in self.sheets.values() if
                      v['tag']['id'] == sheet_id)['nodes']:
            if is_anki_question(t):
                answers = dict()
                remote_questions[t['id']] = {'xMod': t['timestamp'],
                                             'index': get_topic_index(t),
                                             'answers': answers}
                for a in self.get_answer_nodes(self.getTagById(t['id'])):
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
        content_sheets = [self.sheets[s] for s in content_keys]
        sheets = dict()
        for s in content_sheets:
            sheets[s['tag']['id']] = {'xMod': s['tag']['timestamp']}
        return sheets

    def getTagById(self, tagId):
        """
        :param tagId: the id property of the tag
        :return: the tag containing the Id
        """
        try:
            return next(t for t in self.get_tag_list() if t['id'] == tagId)
        except StopIteration:
            # TODO: Warn if the node is not found
            return None

    def remote_file(self, sheets=None):
        doc_mod = self.get_map_last_modified()
        os_mod = self.get_file_last_modified()
        remote = {'file': self.file, 'xMod': doc_mod, 'osMod': os_mod,
                  'sheets': sheets}
        return remote

    def get_file_last_modified(self):
        return get_os_mod(self.file)

    def get_map_last_modified(self):
        return self.soup.find('xmap-content')['timestamp']

    def remove_node(self, a_id):
        tag = self.getTagById(a_id)
        if not getChildnodes(tag):
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
        tag = self.getTagById(x_id)
        if title != getNodeTitle(tag):
            self.setNodeTitle(tag=tag, title=title)

        # Remove crosslink if the tag has one
        if getNodeCrosslink(tag):
            del tag['xlink:href']

        nodeImg = getNodeImg(tag)

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
        tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(self.file))
        os.close(tmpfd)

        # create a temp copy of the archive without filename
        with zipfile.ZipFile(self.file, 'r') as zin:
            with zipfile.ZipFile(tmpname, 'w') as zout:
                zout.comment = zin.comment  # preserve the comment
                for item in zin.infolist():
                    if item.filename not in ['content.xml',
                                             'META-INF/manifest.xml'] + \
                            self.fileBin:
                        zout.writestr(item, zin.read(item.filename))

        # replace with the temp archive
        os.remove(self.file)
        os.rename(tmpname, self.file)

        # now add filename with its new data
        with zipfile.ZipFile(self.file, mode='a',
                             compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('content.xml', str(self.soup))
            for file in os.listdir(self.srcDir):
                zf.write(filename=os.path.join(self.srcDir, file),
                         arcname=os.path.join('attachments', file))
            zf.writestr(zinfo_or_arcname='META-INF/manifest.xml',
                        data=str(self.manifest))

    def get_content_sheets(self):
        return [k for k in self.sheets.keys() if k != 'ref']

    def get_tag_list(self):
        if not self.tag_list:
            self.tag_list = [t for s in self.sheets for
                             t in self.sheets[s]['nodes']]
        # Nested list comprehension explained:
        # https://stackoverflow.com/questions/20639180/explanation-of-how-nested-list-comprehension-works
        return self.tag_list

    def ref_and_sort_id(self, q_topic):
        ancestry = get_ancestry(topic=q_topic, descendants=[])
        ref = getNodeTitle(ancestry.pop(0))
        sort_id = ''
        mult_subjects = False
        follows_bridge = False
        for i, ancestor in enumerate(ancestry):
            field = field_from_content(self.getNodeContent(ancestor))
            sort_id = update_sort_id(sort_id, get_topic_index(ancestor))
            if i % 2:
                ref = ref_plus_answer(field=field, followsBridge=follows_bridge,
                                      ref=ref, mult_subjects=mult_subjects)
                follows_bridge = False
                mult_subjects = isEmptyNode(ancestor)
            else:
                ref = ref_plus_question(field=field, ref=ref)
                if not is_anki_question(ancestor):
                    follows_bridge = True
        return ref, sort_id

    def _register_referenced_files(self):
        """
        Finds the names of files to which the XManager has references to. Files are referenced in a sheet titled "ref"
        """
        for sheet in self.sheets.values():
            # Get reference sheets
            if sheet['tag']('title', recursive=False)[0].text == 'ref':
                ref_tags = getChildnodes(sheet['tag'].topic)
                ref_paths = (getNodeHyperlink(t) for t in ref_tags)
                self.referenced_files = [clean_ref_path(p) for p in ref_paths if p is not None]
