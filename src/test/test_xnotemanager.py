# class TestXNoteManager(TestCase):
#     def setUp(self):
#         col = Collection(os.path.join(SUPPORT_PATH, 'syncer',
#                                       'cols', 'no_changes', 'collection.anki2'))
#         self.note_manager = XNoteManager(col)
#
#
# class TestGetXmindFiles(TestXNoteManager):
#     def test_get_xmind_files(self):
#         act = self.note_manager.get_xmind_files()
#         self.fail()
#
#
# class TestGetLocal(TestXNoteManager):
#     def test_get_local(self):
#         manager = self.note_manager
#         file = EXAMPLE_MAP_PATH
#         act = manager.get_local(file=file)
#         self.fail()
#
#     def test_changes_general_psycholog(self):
#         col = Collection(os.path.join(SUPPORT_PATH, 'syncer',
#                                       'cols', 'changes', 'collection.anki2'))
#         manager = XNoteManager(col)
#         file = EXAMPLE_MAP_PATH
#         act = manager.get_local(file=file)
#         self.fail()
#
# class FieldFromClass(TestFieldTranslator):
#     def test_only_text(self):
#         translator = self.field_translator
#         content = 'MAO_is_not_a_neurotransmitter'
#         act = translator.field_from_class(content)
#         exp = 'MAO is not a neurotransmitter'
#         self.assertEqual(exp, act)
#
#     def test_only_image(self):
#         translator = self.field_translator
#         content = 'ximage_09r2e442o8lppjfeblf7il2rmd_extension_png'
#         act = translator.field_from_class(content)
#         exp = '<img src="09r2e442o8lppjfeblf7il2rmd.png">'
#         self.assertEqual(exp, act)
#
#     def test_only_media(self):
#         translator = self.field_translator
#         content = 'xmedia_3lv2k1fhghfb9ghfb8depnqvdt_extension_mp3'
#         act = translator.field_from_class(content)
#         exp = '[sound:3lv2k1fhghfb9ghfb8depnqvdt.mp3]'
#         self.assertEqual(exp, act)
#
#     def test_all_three(self):
#         translator = self.field_translator
#         content = 'MAO_is_not_a_neurotransmitter=:media:3lv2k1fhghfb9ghfb8depnqvdt.mp3:==:img:09r2e442o8lppjfeblf7il2rmd.png:='
#         act = translator.field_from_class(content)
#         exp = 'MAO is not a neurotransmitter[sound:3lv2k1fhghfb9ghfb8depnqvdt.mp3]<br><img src="09r2e442o8lppjfeblf7il2rmd.png">'
#         self.assertEqual(exp, act)
#
#     def test_parentheses(self):
#         translator = self.field_translator
#         class_name = 'biological_psychology_xlparenthesis_text_in_parenthses_xrparenthesis'
#         act = translator.field_from_class(class_name)
#         exp = 'biological psychology (text in parenthses)'
#         self.assertEqual(exp, act)
#
# class TestContentFromField(TestCase):
#     def test_content_from_field(self):
#         field = 'MAO is not a neurotransmitter[sound:3lv2k1fhghfb9ghfb8depnqvdt.mp3]<br><img src="09r2e442o8lppjfeblf7il2rmd.png">'
#         act = content_from_field(field)
#         self.fail()
#
#     def test_only_text(self):
#         field = 'former image'
#         act = content_from_field(field)
#         self.fail()
import pytest

from main.dto.nodecontentdto import NodeContentDTO
from main.xnotemanager import FieldTranslator, get_smr_note_reference_field, get_smr_note_sort_field, \
    sort_id_from_order_number, XNoteManager, image_from_field
import test.constants as cts


@pytest.fixture
def field_translator():
    yield FieldTranslator()


def test_class_from_content(field_translator):
    # given
    expected_class = 'biological_psychology'
    content = NodeContentDTO(title="biological psychology")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_only_image(field_translator):
    # given
    expected_class = 'ximage_09r2e442o8lppjfeblf7il2rmd_extension_png'
    content = NodeContentDTO(image="attachments/09r2e442o8lppjfeblf7il2rmd.png")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_only_media(field_translator):
    # given
    expected_class = 'xmedia_3lv2k1fhghfb9ghfb8depnqvdt_extension_mp3'
    content = NodeContentDTO(media="attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_parentheses(field_translator):
    # given
    expected_class = 'biological_psychology_xlparenthesis_text_in_parenthses_xrparenthesis'
    content = NodeContentDTO(title="biological psychology (text in parenthses)")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_get_smr_note_reference_field(smr_world_for_tests):
    # when
    reference_field = get_smr_note_reference_field(smr_world=smr_world_for_tests,
                                                   edge_id=cts.PRONOUNCIATION_EDGE_XMIND_ID)
    # then
    assert reference_field == 'biological psychology<li>investigates: information transfer and ' \
                              'processing</li><li>requires: neurotransmitters <img ' \
                              'src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic ' \
                              'amines</li><li> <img src="attachments09r2e442o8lppjfeblf7il2rmd.png">: Serotonin</li>'


def test_get_smr_note_reference_field_replace_media(smr_world_for_tests):
    # when
    reference_field = get_smr_note_reference_field(smr_world=smr_world_for_tests,
                                                   edge_id="7ipkhjdorhgcasdf12asd123ga")
    # then
    assert reference_field == 'biological psychology<li>investigates: perception</li><li>Pain</li><li>some media ' \
                              'edge title (media): answer to some media edge</li>'


def test_get_smr_note_sort_field(smr_world_for_tests):
    # when
    sort_field = get_smr_note_sort_field(smr_world=smr_world_for_tests,
                                         edge_id=cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID)
    # then
    assert sort_field == '|{|{{{|{'


def test_sort_id_from_order_number():
    # when
    sort_ids = [sort_id_from_order_number(i) for i in range(1, 21)]
    # then
    assert sort_ids == sorted(sort_ids)


@pytest.fixture
def note_manager(collection_4_migration):
    yield XNoteManager(collection_4_migration)


def test_image_from_field():
    # when
    image = image_from_field('MAO is not a neurotransmitter[sound:3lv2k1fhghfb9ghfb8depnqvdt.mp3]<br><img '
                             'src="09r2e442o8lppjfeblf7il2rmd.png">')
    # then
    assert image == '09r2e442o8lppjfeblf7il2rmd.png'


def test_image_from_field_no_image():
    # when
    image = image_from_field('no image')
    # then
    assert image is None
