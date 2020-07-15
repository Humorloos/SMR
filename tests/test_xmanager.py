import bs4


# class TestGetNodeContent(TestXManager):
#     def test_getNodeContent(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = self.xManager.getNodeContent(tag=tag)
#         self.assertEqual(act['content'], 'biological psychology')
#         self.assertEqual(act['media']['image'], None)
#         self.assertEqual(act['media']['media'], None)
#
#     def test_crosslink_answer(self):
#         manager = self.xManager
#         tag = manager.getTagById('3nb97928e68dcu5512pft7gkcg')
#         act = manager.getNodeContent(tag=tag)
#         self.fail()
#
#
# class TestGetNodeTitle(TestXManager):
#     def test_getNodeTitle(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = get_node_title(tag)
#         self.assertEqual(act, 'biological psychology')
#
#
# class TestGetNodeImg(TestXManager):
#     def test_no_image(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = getNodeImg(tag)
#         self.assertEqual(act, None)
#
#
# class TestGetNodeHyperlink(TestXManager):
#     def test_no_hyperlink(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = getNodeHyperlink(tag)
#         self.assertEqual(act, None)
#
#
# class TestGetTagById(TestXManager):
#     def test_get_tag_by_id(self):
#         x_id = '4r6avbt0pbuam4fg07jod0ubec'
#         act = self.xManager.getTagById(x_id)
#         self.fail()
#
#
# class TestIsEmptyNode(TestXManager):
#     def test_not_empty(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = isEmptyNode(tag)
#         self.assertEqual(act, False)
#
#
# class TestGetRemote(TestXManager):
#     def test_get_remote(self):
#         manager = self.xManager
#         act = manager.get_remote()
#         self.fail()
#
#
# class TestGetAnswerNodes(TestXManager):
#     def test_crosslink_answers(self):
#         manager = self.xManager
#         tag = manager.getTagById('4lrqok8ac9hec8u2c2ul4mpo4k')
#         act = manager.get_answer_nodes(tag)
#         self.fail()
#
#     def test_no_answers(self):
#         manager = self.xManager
#         tag = manager.getTagById('4s27e1mvsb5jqoiuaqmnlo8m71')
#         act = manager.get_answer_nodes(tag)
#         self.fail()
#
#
# class TestIsCrosslinkNode(TestXManager):
#     def test_media_node(self):
#         manager = self.xManager
#         tag = manager.getTagById('1s7h0rvsclrnvs8qq9u71acml5')
#         act = manager.is_crosslink_node(tag)
#         self.assertFalse(act)
#


def test_xmanager(x_manager):
    # given
    expected_sheets = ['biological psychology', 'clinical psychology', 'ref']
    expected_referenced_file = ['C:\\Users\\lloos\\OneDrive - bwedu\\Projects\\AnkiAddon\\anki-addon-dev\\addons21'
                                '\\XmindImport\\resources\\example_general_psychology.xmind']
    # when
    cut = x_manager
    # then
    assert list(cut.get_sheets().keys()) == expected_sheets
    assert cut.get_referenced_files() == expected_referenced_file


def test_get_root_topic(x_manager):
    # given
    cut = x_manager
    # when
    root_topic = cut.get_root_node(sheet="biological psychology")
    # then
    assert isinstance(root_topic, bs4.element.Tag)
