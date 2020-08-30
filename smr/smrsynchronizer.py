from itertools import zip_longest
from typing import List, Dict, Set, Union, NamedTuple

import aqt as aqt
import smr.consts as cts
from anki import Collection
from anki.utils import splitFields
from smr.dto.smrnotedto import SmrNoteDto
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.fieldtranslator import FieldTranslator
from smr.smrworld import SmrWorld
from smr.xmanager import XManager
from smr.xmindimport import XmindImporter
from smr.xmindtopic import XmindEdge
from smr.xnotemanager import field_by_identifier, XNoteManager, field_from_content, \
    content_from_field, field_content_by_identifier
from smr.xontology import XOntology


# Algorithm for synchronization was adopted from
# https://unterwaditzer.net/2016/sync-algorithm.html
class SmrSynchronizer:
    """
    Class for synchronizing changes in the anki collection and source xmind files
    """

    def __init__(self):
        self.col = aqt.mw.col
        self.note_manager = XNoteManager(col=aqt.mw.col)
        self.smr_world = aqt.mw.smr_world
        self.x_manager = None
        self.importer = None
        self.current_sheet_sync = None
        self.warnings = []
        self.translator = FieldTranslator()
        self.xmind_files_2_update = []
        self.xmind_sheets_2_remove = []
        self.xmind_edges_2_update = []
        self.xmind_nodes_2_update = []
        self.xmind_nodes_2_remove = []
        self.log = []
        self.onto = None

    @property
    def col(self) -> Collection:
        return self._col

    @col.setter
    def col(self, value: Collection):
        self._col = value

    @property
    def note_manager(self) -> XNoteManager:
        return self._note_manager

    @note_manager.setter
    def note_manager(self, value: XNoteManager):
        self._note_manager = value

    @property
    def smr_world(self) -> SmrWorld:
        return self._smr_world

    @smr_world.setter
    def smr_world(self, value: SmrWorld):
        self._smr_world = value

    @property
    def xmind_files_2_update(self) -> List[XmindFileDto]:
        return self._xmind_files_2_update

    @xmind_files_2_update.setter
    def xmind_files_2_update(self, value: List[XmindFileDto]):
        self._xmind_files_2_update = value

    @property
    def xmind_edges_2_update(self) -> List[XmindTopicDto]:
        return self._xmind_edges_2_update

    @xmind_edges_2_update.setter
    def xmind_edges_2_update(self, value: List[XmindTopicDto]):
        self._xmind_edges_2_update = value

    @property
    def edge_ids_of_anki_notes_2_update(self) -> Set[str]:
        try:
            return self._edge_ids_of_anki_notes_2_update
        except AttributeError:
            self._edge_ids_of_anki_notes_2_update = set()
            return self._edge_ids_of_anki_notes_2_update

    @edge_ids_of_anki_notes_2_update.setter
    def edge_ids_of_anki_notes_2_update(self, value: Set[str]):
        self._edge_ids_of_anki_notes_2_update = value

    @property
    def changed_smr_notes(self) -> 'ChangedSmrNotes':
        try:
            return self._changed_smr_notes
        except AttributeError:
            self._changed_smr_notes = {}
            return self._changed_smr_notes

    @changed_smr_notes.setter
    def changed_smr_notes(self, value: 'ChangedSmrNotes'):
        self._changed_smr_notes = value

    @property
    def x_manager(self) -> XManager:
        return self._x_manager

    @x_manager.setter
    def x_manager(self, value: XManager):
        self._x_manager = value

    @property
    def onto(self) -> XOntology:
        return self._onto

    @onto.setter
    def onto(self, value: XOntology):
        self._onto = value

    @property
    def log(self) -> List[str]:
        return self._log

    @log.setter
    def log(self, value: List[str]):
        self._log = value

    @property
    def xmind_nodes_2_remove(self) -> List[str]:
        return self._xmind_nodes_2_remove

    @xmind_nodes_2_remove.setter
    def xmind_nodes_2_remove(self, value: List[str]):
        self._xmind_nodes_2_remove = value

    @property
    def xmind_sheets_2_remove(self) -> List[str]:
        return self._xmind_sheets_2_remove

    @xmind_sheets_2_remove.setter
    def xmind_sheets_2_remove(self, value: List[str]):
        self._xmind_sheets_2_remove = value

    @property
    def xmind_nodes_2_update(self) -> List[XmindTopicDto]:
        return self._xmind_nodes_2_update

    @xmind_nodes_2_update.setter
    def xmind_nodes_2_update(self, value: List[XmindTopicDto]):
        self._xmind_nodes_2_update = value

    @property
    def smr_notes_2_update(self) -> List[SmrNoteDto]:
        try:
            return self._smr_notes_2_update
        except AttributeError:
            self._smr_notes_2_update = []
            return self._smr_notes_2_update

    @smr_notes_2_update.setter
    def smr_notes_2_update(self, value: List[SmrNoteDto]):
        self._smr_notes_2_update = value

    @property
    def importer(self) -> XmindImporter:
        return self._importer

    @importer.setter
    def importer(self, value: XmindImporter):
        self._importer = value

    @property
    def xmind_edges_2_remove(self) -> Set[str]:
        try:
            return self._xmind_edges_2_remove
        except AttributeError:
            self._xmind_edges_2_remove = set()
            return self._xmind_edges_2_remove

    @xmind_edges_2_remove.setter
    def xmind_edges_2_remove(self, value: Set[str]):
        self._xmind_edges_2_remove = value

    @property
    def relations_2_change(self) -> List[Dict[str, Union[List[str], XmindTopicDto]]]:
        try:
            return self._relations_2_change
        except AttributeError:
            self._relations_2_change = []
            return self._relations_2_change

    @relations_2_change.setter
    def relations_2_change(self, value: List[Dict[str, Union[List[str], XmindTopicDto]]]):
        self._relations_2_change = value

    @property
    def concepts_2_remove(self) -> List[Dict[str, Union[List[str], str]]]:
        try:
            return self._concepts_2_remove
        except AttributeError:
            self._concepts_2_remove = []
            return self._concepts_2_remove

    @concepts_2_remove.setter
    def concepts_2_remove(self, value: List[Dict[str, Union[List[str], XmindTopicDto, Dict[str, List[str]]]]]):
        self._concepts_2_remove = value

    @property
    def concepts_2_rename(self) -> List[Dict[str, Union[List[str], XmindTopicDto, Dict[str, List[str]]]]]:
        try:
            return self._concepts_2_rename
        except AttributeError:
            self._concepts_2_rename = []
            return self._concepts_2_rename

    @concepts_2_rename.setter
    def concepts_2_rename(self, value: List[Dict[str, Union[List[str], XmindTopicDto, Dict[str, List[str]]]]]):
        self._concepts_2_rename = value

    @property
    def anki_notes_2_update(self) -> Dict[str, SmrNoteDto]:
        try:
            return self._anki_notes_2_update
        except AttributeError:
            self._anki_notes_2_update = {}
            return self._anki_notes_2_update

    @anki_notes_2_update.setter
    def anki_notes_2_update(self, value: Dict[str, SmrNoteDto]):
        self._anki_notes_2_update = value

    @property
    def anki_sheets_2_remove(self) -> List[str]:
        try:
            return self._anki_sheets_2_remove
        except AttributeError:
            self._anki_sheets_2_remove = []
            return self._anki_sheets_2_remove

    @anki_sheets_2_remove.setter
    def anki_sheets_2_remove(self, value: List[str]):
        self._anki_sheets_2_remove = value

    @property
    def onto_sheets_2_remove(self) -> Dict[str, str]:
        try:
            return self._onto_sheets_2_remove
        except AttributeError:
            self._onto_sheets_2_remove = {}
            return self._onto_sheets_2_remove

    @onto_sheets_2_remove.setter
    def onto_sheets_2_remove(self, value: Dict[str, str]):
        self._onto_sheets_2_remove = value

    @property
    def anki_notes_2_remove(self) -> Set[int]:
        try:
            return self._anki_notes_2_remove
        except AttributeError:
            self._anki_notes_2_remove = set()
            return self._anki_notes_2_remove

    @anki_notes_2_remove.setter
    def anki_notes_2_remove(self, value: Set[int]):
        self._anki_notes_2_remove = value

    @property
    def is_running(self) -> bool:
        try:
            return self._is_running
        except AttributeError:
            self._is_running = True
            return self._is_running

    @is_running.setter
    def is_running(self, value: bool):
        self._is_running = value

    def synchronize(self):
        """
        Checks whether there were changes in notes or xmind files since the last synchronization and triggers the
        respective synchronization methods in case there were changes
        """
        aqt.mw.progress.start(immediate=True, label="Synchronizing SMR changes...")
        smr_decks = self.smr_world.get_ontology_lives_in_deck()
        xmind_files_in_decks = self.smr_world.get_xmind_files_in_decks()
        self.changed_smr_notes = self.smr_world.get_changed_smr_notes(self.col)
        for smr_deck in smr_decks:
            files_in_deck = xmind_files_in_decks[smr_deck.deck_id]
            self.onto = XOntology(smr_deck.deck_id, self.smr_world)
            for xmind_file in files_in_deck:
                self.x_manager = XManager(xmind_file)
                # look for local and remote changes in the file
                remote_change = False
                if xmind_file.file_last_modified != self.x_manager.file_last_modified:
                    xmind_file.file_last_modified = self.x_manager.file_last_modified
                    if xmind_file.map_last_modified != self.x_manager.map_last_modified:
                        remote_change = True
                        xmind_file.map_last_modified = self.x_manager.map_last_modified
                    self.xmind_files_2_update.append(xmind_file)
                local_change = xmind_file.file_path in self.changed_smr_notes
                # use the appropriate strategy for getting updates
                if not local_change and not remote_change:
                    continue
                elif local_change and not remote_change:
                    self._process_local_changes(xmind_file)
                elif not local_change and remote_change:
                    self._process_remote_changes(file=xmind_file, deck_id=smr_deck.deck_id)
                    self.importer.finish_import()
                else:
                    self.process_local_and_remote_changes()
                # apply updates to the all mediums
                self.x_manager.save_changes()
                self._synchronize_ontology()
                self._synchronize_smr_world()
                self._synchronize_anki_collection()
        aqt.mw.progress.finish()

    def _synchronize_anki_collection(self):
        # update anki notes affected by changes
        changed_notes = self.smr_world.generate_notes(self.col, list(self.anki_notes_2_update))
        importer = XmindImporter(col=self.col, file='')
        importer.tagModified = 'yes'
        importer.addUpdates(rows=[
            [self.anki_notes_2_update[edge_id].last_modified, self.col.usn(), foreign_note.fieldsStr,
             foreign_note.tags[0], self.anki_notes_2_update[edge_id].note_id, foreign_note.fieldsStr] for
            edge_id, foreign_note in changed_notes.items()])
        # generate cards + update field cache
        self.col.after_note_updates(nids=[n.note_id for n in self.anki_notes_2_update.values()], mark_modified=False)
        self.anki_notes_2_update = {}
        # remove notes with note_ids from list of anki notes to remove
        self.col.remove_notes(list(self.anki_notes_2_remove))
        self.anki_notes_2_remove = set()
        # bulk remove notes for removed sheets
        for sheet_id in self.anki_sheets_2_remove:
            self.note_manager.remove_notes_by_sheet_id(sheet_id, self.smr_world)
        self.note_manager.save_col()
        self.anki_sheets_2_remove = []

    def _synchronize_smr_world(self):
        """
        makes all necessary changes to the smr world
        """
        # updates
        self.smr_world.add_or_replace_xmind_files(self.xmind_files_2_update)
        self.xmind_files_2_update = []
        self.smr_world.add_or_replace_xmind_edges(self.xmind_edges_2_update)
        self.xmind_edges_2_update = []
        self.smr_world.add_or_replace_xmind_nodes(self.xmind_nodes_2_update)
        self.xmind_nodes_2_update = []
        # get notes that have to be updated because they follow notes with updated fields
        self.anki_notes_2_update = self.smr_world.get_updated_child_smr_notes(
            list(self.edge_ids_of_anki_notes_2_update))
        # update smr notes where only last modified has to be adjusted and those where anki notes' fields need to be
        # adjusted
        self.smr_world.add_or_replace_smr_notes(self.smr_notes_2_update + list(self.anki_notes_2_update.values()))
        self.smr_notes_2_update = []
        self._edge_ids_of_anki_notes_2_update = set()
        # removals
        self.smr_world.remove_xmind_nodes(self.xmind_nodes_2_remove)
        self.xmind_nodes_2_remove = []
        self.smr_world.remove_xmind_edges(self.xmind_edges_2_remove)
        self.xmind_edges_2_remove = []
        self.smr_world.remove_xmind_sheets(sheet_ids=self.xmind_sheets_2_remove)
        self.xmind_sheets_2_remove = []

    def _synchronize_ontology(self):
        """
        Makes all necessary changes to the ontology that are not covered by XmindImport
        """
        # First perform updates to avoid conflicts with removed entities
        # Rename nodes in ontology
        for concept in self.concepts_2_rename:
            self.onto.rename_node(parent_node_ids=concept['parent_node_ids'], xmind_edge=concept['xmind_edge'],
                                  xmind_node=concept['xmind_node'], children=concept['children'])
        self.concepts_2_rename = []
        # Change relation names in ontology
        for relation in self.relations_2_change:
            self.onto.change_relationship_class_name(
                parent_node_ids=relation['parent_node_ids'], child_node_ids=relation['child_node_ids'],
                xmind_edge=relation['xmind_edge'])
        self.relations_2_change = []

        # Remove nodes from ontology
        for concept in self.concepts_2_remove:
            self.onto.remove_node(parent_node_ids=concept['parent_node_ids'], parent_edge_id=concept['edge_id'],
                                  node_id=concept['node_id'], children={})
        self.concepts_2_remove = []
        # Remove nodes from ontology by sheets
        for sheet_id, root_node_id in self.onto_sheets_2_remove.items():
            self.onto.remove_sheet(sheet_id=sheet_id, root_node_id=root_node_id)

    # TODO: Implement this, do not forget here that we need to add smr triples in this case
    def _add_answer(self, answer_content: TopicContentDto, xmind_edge: XmindTopicDto):
        print('add answer to map')
        print('add answer to ontology')
        self.log.append(f"""\
Invalid added answer: Cannot add answer "{field_from_content(content=answer_content, smr_world=self.smr_world)}" to \
question "{field_from_content(content=xmind_edge.content, smr_world=self.smr_world)}" (reference: \
{self.smr_world.get_smr_note_reference_fields([xmind_edge.node_id])[xmind_edge.node_id]}). Adding answers via \
anki is not yet supported, instead, add the answer in your xmind map and synchronize. I removed the answer from the \
note.""")

    # def add_remote_a(self, q_content, q_id, remote, status, a_tag, import_dict):
    #     a_content = self.map_manager.get_topic_content(a_tag)
    #     a_field = field_from_content(a_content)
    #
    #     # Add answer to note fields
    #     a_index = get_topic_index(a_tag)
    #     if not import_dict['note']:
    #         import_dict['note'] = self.note_manager.get_note_from_q_id(q_id)
    #     if not import_dict['meta']:
    #         import_dict['meta'] = meta_from_fields(import_dict['note'].fields)
    #     import_dict['index_dict'][a_index] = {
    #         'a_id': a_tag['id'], 'field': a_field}
    #     import_dict['importer'] = self.maybe_add_media(
    #         a_content, import_dict['importer'])
    #
    #     # Add answer to ontology
    #     if not q_content:
    #         q_content = content_from_field(field_by_identifier(
    #             import_dict['note'].fields, 'qt'))
    #     q_class = self.translator.class_from_content(q_content)
    #     rel_dict = get_rel_dict(
    #         aIndex=a_index,
    #         image=q_content['media']['image'],
    #         media=q_content['media']['media'],
    #         x_id=q_id,
    #         ref=field_by_identifier(import_dict['note'].fields, 'rf'),
    #         sortId=field_by_identifier(import_dict['note'].fields, 'id'),
    #         doc=self.map_manager.file,
    #         sheet=import_dict['meta']['sheetId'],
    #         tag=import_dict['note'].tags[0]
    #     )
    #     a_concept = self.onto.add_node(
    #         a_id=a_tag['id'], answer_field=a_field, rel_dict=rel_dict,
    #         question_class=q_class)
    #
    #     # Add answer to status
    #     # a_cards = self.note_manager.get_answer_cards(note.id)
    #     # local_a_dict = local_answer_dict(anki_mod = a_card[])
    #     status['answers'][a_tag['id']] = remote['answers'][a_tag['id']]
    #     return import_dict

    # def add_remote_as(self, q_content, q_id, remote, status, import_dict):
    #    not_in_status = [a for a in remote['answers'] if a not in status[
    #        'answers']]
    #    for a_id in not_in_status:
    #        a_tag = self.map_manager.get_node_by_id(a_id)
    #        import_dict = self.add_remote_a(
    #            import_dict=import_dict,
    #            q_content=q_content,
    #            q_id=q_id, remote=remote, status=status, a_tag=a_tag)
    #    return import_dict

    def _change_remote_node(self, xmind_edge: XmindTopicDto, parent_node_ids: List[str], xmind_node: XmindTopicDto,
                            children: Dict[str, List[str]]) -> None:
        """
        Changes a node's content in the xmind map and in the ontology
        :param xmind_edge: the xmind edge preceding the node to change
        :param parent_node_ids: list of node ids of parent nodes of the preceding edge
        :param xmind_node: xmind node dto of the node to change
        :param children: dictionary where keys are edge_ids of edges following the node to change and values are
        lists of xmind node ids belonging to the edge's child nodes
        """
        # Change answer in map
        self.x_manager.set_node_content(node_id=xmind_node.node_id, content=xmind_node.content,
                                        media_directory=self.note_manager.media_directory, smr_world=self.smr_world)
        # Change answer in Ontology
        self.concepts_2_rename.append({'xmind_node': xmind_node, 'xmind_edge': xmind_edge,
                                       'parent_node_ids': parent_node_ids, 'children': children})

    def _change_remote_question(self, xmind_edge: XmindTopicDto, parent_node_ids: List[str],
                                child_node_ids: List[str]):
        """
        - Changes the content of the xmind edge that belongs to the specified note data to the local question content
        - Changes the relationship class name in the ontology according to the new content
        :param xmind_edge: xmind node dto of the edge representing the question to be changed. The content must
        already be updated to the new value.
        :param parent_node_ids: list of xmind node ids of the parent nodes of the edge to change
        :param child_node_ids: list of xmind node ids of the child nodes of the edge to change
        """
        # Change edge in map
        self.x_manager.set_edge_content(edge=xmind_edge, media_directory=self.note_manager.media_directory,
                                        smr_world=self.smr_world)
        # Add node ids and edge to relations to change
        self.relations_2_change.append({
            'parent_node_ids': parent_node_ids, 'xmind_edge': xmind_edge, 'child_node_ids': child_node_ids})

    # def maybe_add_media(self, content, importer, old_content=None):
    #    a_media = content['media']
    #    if old_content:
    #        old_media = old_content['media']
    #    else:
    #        old_media = a_media
    #    if a_media['image'] or a_media['media']:
    #        if not importer:
    #            importer = XmindImporter(col=self.note_manager.col,
    #                                     file=self.map_manager.file)
    #        if a_media['image'] and not a_media['image'] == old_media['image']:
    #            importer.images.append(a_media['image'])
    #        if a_media['media'] and not a_media['media'] == old_media['media']:
    #            importer.media.append(a_media['media'])
    #    return importer

    def _try_to_remove_answer(self, xmind_edge: XmindTopicDto, xmind_node: XmindTopicDto,
                              parent_node_ids: List[str]):
        """
        checks whether an answer is a leave node and if it is, removes it from the xmind map and the ontology
        :param xmind_edge: xmind node dto of the edge preceding the node to delete
        :param xmind_node: xmind node dto of the node to delete
        :param parent_node_ids: List of node ids of the parents of the node to delete
        """
        # Remove node from map
        try:
            self.x_manager.remove_node(node_id=xmind_node.node_id)
        except AttributeError:
            self.log.append(f"""\
Invalid answer removal: Cannot remove answer "{field_from_content(xmind_node.content, self.smr_world)}" to question \
"{field_from_content(xmind_edge.content, self.smr_world)}" (reference: \
{self.smr_world.get_smr_note_reference_fields([xmind_edge.node_id])[xmind_edge.node_id]}), because more questions \
follow this answer in the xmind map. I restored the answer. If you want to remove the answer, do it in the concept \
map and then synchronize.""")
        # Add node to concepts to remove
        self.concepts_2_remove.append({'node_id': xmind_node.node_id, 'edge_id': xmind_edge.node_id,
                                       'parent_node_ids': parent_node_ids})
        # Add node to nodes to remove
        self.xmind_nodes_2_remove.append(xmind_node.node_id)

    # def process_change_list(self):
    #    for sheet in self.change_list:
    #        changed_notes = [self.note_manager.get_note_from_q_id(q_id) for
    #                         q_id in self.change_list[sheet]]
    #        for note in changed_notes:
    #            meta = meta_from_fields(note.fields)
    #            changes = self.change_list[sheet][meta['questionId']]
    #            self.note_manager.update_ref(note=note, changes=changes,
    #                                         meta=meta)

    def _process_local_changes(self, file: XmindFileDto):
        """
        if for each sheet in the specified file, changes questions and answers where necessary and adds changed
        entities to the respective lists
        :param file: xmind file for which to work through the changes
        """
        for sheet_data in self.changed_smr_notes[file.file_path].values():
            for note_id, note_data in sheet_data.items():
                anki_note_was_changed = False
                fields = splitFields(note_data['note_fields'])
                # get data for changing question if necessary
                question_content_local = field_content_by_identifier(
                    fields=fields, identifier='qt', smr_world=self.smr_world)
                if question_content_local != note_data['edge'].content:
                    note_data['edge'].content = question_content_local
                    self._change_remote_question(
                        xmind_edge=note_data['edge'], parent_node_ids=note_data['parents'],
                        child_node_ids=[a['node'].node_id for a in note_data['answers'].values()])
                    self.xmind_edges_2_update.append(note_data['edge'])
                    anki_note_was_changed = True
                # get data for changing answers if necessary
                sorted_answers = sorted(note_data['answers'].items(), key=lambda item: item[0])
                local_answer_fields = [field_by_identifier(fields=fields, identifier='a' + str(i))
                                       for i in range(1, cts.X_MAX_ANSWERS + 1)]
                for local_answer_field, answer_id, answer_data in zip_longest(
                        local_answer_fields, (a[0] for a in sorted_answers), (a[1] for a in sorted_answers)):
                    # stop if no more answers left
                    if not local_answer_field and not answer_id:
                        break
                    # try to remove answer from remote if not present in anki anymore
                    elif not local_answer_field:
                        self._try_to_remove_answer(xmind_edge=note_data['edge'], xmind_node=answer_data['node'],
                                                   parent_node_ids=note_data['parents'])
                    else:
                        local_answer_content = content_from_field(field=local_answer_field, smr_world=self.smr_world)
                        # TODO: add answer to remote if added in anki (not implemented yet)
                        if not answer_id:
                            self._add_answer(answer_content=local_answer_content, xmind_edge=note_data['edge'])
                            anki_note_was_changed = True
                        # change answer if content was changed
                        elif local_answer_content != answer_data['node'].content:
                            answer_data['node'].content = local_answer_content
                            self._change_remote_node(
                                xmind_edge=note_data['edge'], parent_node_ids=note_data['parents'],
                                xmind_node=answer_data['node'], children=answer_data['children'])
                            self.xmind_nodes_2_update.append(answer_data['node'])
                            anki_note_was_changed = True
                        # do nothing if answer has not changed
                        else:
                            continue
                if anki_note_was_changed:
                    self.edge_ids_of_anki_notes_2_update.add(note_data['note'].edge_id)
                else:
                    self.smr_notes_2_update.append(note_data['note'])

    def _process_remote_changes(self, file: XmindFileDto, deck_id: int):
        sheets_status = self.smr_world.get_xmind_sheets_in_file(file_directory=file.directory, file_name=file.file_name)
        sheet_ids_remote = list(self.x_manager.sheets)
        self.importer = XmindImporter(col=self.col, file=file.file_path)
        for sheet_id in set(list(sheets_status) + sheet_ids_remote):
            if sheet_id not in sheets_status:
                self.importer.import_sheet(sheet_id=sheet_id, deck_id=deck_id)
                self.importer.finish_import()
            elif sheet_id not in sheet_ids_remote:
                self._remove_sheet(sheet_id)
            elif sheets_status[sheet_id].last_modified != self.x_manager.sheets[sheet_id].last_modified:
                self._register_remote_sheet_changes(sheet_id)

    def _register_remote_sheet_changes(self, sheet_id):
        edges_remote = self.x_manager.sheets[sheet_id].edges
        edges_status = self.smr_world.get_xmind_edges_in_sheet(sheet_id)
        for edge_id in set(list(edges_status) + list(edges_remote)):
            if edge_id not in edges_status:
                # the importer takes care of everything necessary concerning pure imports
                self.importer.read_edge(edges_remote[edge_id])
            elif edge_id not in edges_remote:
                self._register_remote_edge_removal(edge_data=edges_status[edge_id])
            elif edges_status[edge_id].last_modified != edges_remote[edge_id].last_modified:
                edges_remote[edge_id].last_modified = edges_status[edge_id].last_modified
                self._register_remote_edge_update(remote_edge=edges_remote[edge_id])
        nodes_status = self.smr_world.get_xmind_nodes_in_sheet(sheet_id)
        nodes_remote = self.x_manager.sheets[sheet_id].nodes
        for node_id in set(list(nodes_status) + list(nodes_remote)):
            if node_id not in nodes_status:
                node_remote = nodes_remote[node_id]
                # if the node does not belong to a newly imported edge, do not import it via importer but add
                if node_remote.parent_edge.id not in self.importer.edge_ids_2_make_notes_of:
                    self.edge_ids_of_anki_notes_2_update.add(node_remote.parent_edge.id)
                self.importer.read_node_if_concept(node_remote)
            elif node_id not in nodes_remote:
                node_status = nodes_status[node_id]
                self._register_remote_node_removal(node_status)
            elif nodes_status[node_id].last_modified != nodes_remote[node_id].last_modified:
                print('change node')

    def _register_remote_node_removal(self, node_status):
        # register node for removal from ontology
        self.concepts_2_remove.append(
            {'node_id': node_status['xmind_node'].node_id,
             'parent_edge_id': node_status['parent_edge_id'],
             'parent_node_ids': node_status['parent_node_ids']})
        # register node for removal from smr world
        self.xmind_nodes_2_remove.append(node_status['xmind_node'].node_id)
        # add parent edge to edges of anki notes to update
        if node_status['note_id'] not in self.anki_notes_2_remove:
            self.edge_ids_of_anki_notes_2_update.add(node_status['parent_edge_id'])

    def _register_remote_edge_removal(self, edge_data: NamedTuple):
        """
        registers data for removing data belonging to an xmind edge from all required data structures
        :param edge_data: A named tuple containing the note id belonging to the edge in the last slot and all the data
        from the xmind edges relation in the first slots
        """
        # we do not remove relations from the ontology explicitly since that is already part of removing nodes
        # add edge to smr world xmind edges to remove
        self.xmind_edges_2_remove.add(edge_data.node_id)
        # add edge to notes to remove if it belongs to a note
        note_id = edge_data.pop(-1)
        if note_id is not None:
            self.anki_notes_2_remove.add(note_id)

    def _register_remote_edge_update(self, remote_edge: XmindEdge):
        """
        registers data for updating data belonging to an xmind edge in all required data structures
        :param remote_edge: Xmind edge with the data for the updates from an xmind file
        """
        # update ontology relation
        xmind_edge = remote_edge.dto
        self.relations_2_change.append({
            'parent_node_ids': [node.id for node in remote_edge.parent_nodes],
            'xmind_edge': xmind_edge,
            'child_node_ids': [node.id for node in remote_edge.child_nodes]})
        # add edge id to edge ids of notes 2 update
        self.xmind_edges_2_update.append(xmind_edge)
        # add edge id to list of edge ids of anki notes to update
        self.edge_ids_of_anki_notes_2_update.add(remote_edge.id)

    def remove_questions(self, q_ids, status):
        self.note_manager.remove_notes_by_q_ids(q_ids)
        self.onto.remove_questions(q_ids)
        for q_id in q_ids:
            del status[q_id]

    # def remove_remote_as(self, status, remote, q_id, import_dict):
    #     not_in_remote = [a for a in status if a not in remote]
    #     for a_id in not_in_remote:
    #
    #         # Remove answer from note fields
    #         if not import_dict['note']:
    #             import_dict['note'] = self.note_manager.get_note_from_q_id(q_id)
    #         import_dict['note'].fields[get_field_index_by_field_name(
    #             'a' + str(status[a_id]['index']))] = ''
    #
    #         # Remove answer from ontology
    #         self.onto.remove_node(q_id=q_id, a_id=a_id)
    #
    #         # Remove answer from status
    #         del status[a_id]
    #     return import_dict

    def _remove_sheet(self, sheet_id: str) -> None:
        """
        adds the needed data for removing the sheet with the specified id to the respective data structures
        :param sheet_id: xmind sheet id of the sheet to remove
        """
        self.anki_sheets_2_remove.append(sheet_id)
        self.onto_sheets_2_remove[sheet_id] = self.smr_world.get_root_node_id(sheet_id)
        self.xmind_sheets_2_remove.append(sheet_id)

    def process_local_and_remote_changes(self):
        pass
