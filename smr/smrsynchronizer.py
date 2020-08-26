from itertools import zip_longest
from typing import List, Dict

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
from smr.xnotemanager import field_by_identifier, XNoteManager, field_from_content, meta_from_fields, \
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
        self.edge_ids_of_notes_2_update = []
        self.xmind_nodes_2_update = []
        self.xmind_nodes_2_remove = []
        self.changed_smr_notes = {}
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
    def edge_ids_of_notes_2_update(self) -> List[str]:
        return self._edge_ids_of_notes_2_update

    @edge_ids_of_notes_2_update.setter
    def edge_ids_of_notes_2_update(self, value: List[str]):
        self._edge_ids_of_notes_2_update = value

    @property
    def changed_smr_notes(self) -> Dict[str, SmrNoteDto]:
        return self._changed_smr_notes

    @changed_smr_notes.setter
    def changed_smr_notes(self, value: Dict[str, SmrNoteDto]):
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
    def importer(self):
        return self._importer

    @importer.setter
    def importer(self, value):
        self._importer = value

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
                remote_change = False
                if xmind_file.file_last_modified != self.x_manager.file_last_modified:
                    xmind_file.file_last_modified = self.x_manager.file_last_modified
                    if xmind_file.map_last_modified != self.x_manager.map_last_modified:
                        remote_change = True
                        xmind_file.map_last_modified = self.x_manager.map_last_modified
                    self.xmind_files_2_update.append(xmind_file)
                local_change = xmind_file.file_path in self.changed_smr_notes
                if not local_change and not remote_change:
                    continue
                elif local_change and not remote_change:
                    self._process_local_changes(xmind_file)
                elif not local_change and remote_change:
                    self._process_remote_changes(file=xmind_file, deck_id=smr_deck.deck_id)
                else:
                    self.process_local_and_remote_changes()
                self.x_manager.save_changes()
        # process changes in smr world
        self.smr_world.add_or_replace_xmind_files(self.xmind_files_2_update)
        # TODO: remove xmind sheets
        print('remove xmind sheets')
        self.smr_world.add_or_replace_xmind_edges(self.xmind_edges_2_update)
        self.smr_world.add_or_replace_xmind_nodes(self.xmind_nodes_2_update)
        self.smr_world.remove_xmind_nodes(self.xmind_nodes_2_remove)
        smr_notes_2_update = self.smr_world.get_updated_child_smr_notes(list(self.edge_ids_of_notes_2_update))
        self.smr_world.add_or_replace_smr_notes(list(smr_notes_2_update.values()))
        # update smr notes affected by changes
        changed_notes = self.smr_world.generate_notes(self.col, list(smr_notes_2_update))
        importer = XmindImporter(col=self.col, file='')
        importer.tagModified = 'yes'
        importer.addUpdates(rows=[
            [smr_notes_2_update[edge_id].last_modified, self.col.usn(), foreign_note.fieldsStr,
             foreign_note.tags[0], smr_notes_2_update[edge_id].note_id, foreign_note.fieldsStr] for
            edge_id, foreign_note in changed_notes.items()])
        # generate cards + update field cache
        self.col.after_note_updates(nids=[n.note_id for n in smr_notes_2_update.values()], mark_modified=False)
        self.note_manager.save_col()
        aqt.mw.progress.finish()

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

    def add_remote_as(self, q_content, q_id, remote, status, import_dict):
        not_in_status = [a for a in remote['answers'] if a not in status[
            'answers']]
        for a_id in not_in_status:
            a_tag = self.map_manager.get_node_by_id(a_id)
            import_dict = self.add_remote_a(
                import_dict=import_dict,
                q_content=q_content,
                q_id=q_id, remote=remote, status=status, a_tag=a_tag)
        return import_dict

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
        xmind_node.ontology_storid = self.onto.rename_node(
            xmind_node=xmind_node, xmind_edge=xmind_edge, parent_node_ids=parent_node_ids, children=children).storid

    # def change_remote_as(self, status, remote, q_id, level, import_dict):
    #     for a_id in {**status, **remote}:
    #         if not status[a_id]['xMod'] == remote[a_id]['xMod']:
    #             if not import_dict['note']:
    #                 note = self.note_manager.get_note_from_q_id(q_id)
    #
    #             # Change answer in note
    #             a_content = self.map_manager.get_node_content_by_id(a_id)
    #             a_field = field_from_content(a_content)
    #             old_field = import_dict['note'].fields[get_index_by_a_id(
    #                 note=import_dict['note'], a_id=a_id)]
    #             if not a_field == old_field:
    #                 import_dict['note'].fields[
    #                     get_field_index_by_field_name('a' + str(
    #                         remote[a_id]['index']))] = a_field
    #                 old_content = content_from_field(old_field)
    #                 self.maybe_add_media(content=a_content,
    #                                      old_content=old_content,
    #                                      importer=import_dict['importer'])
    #
    #                 # Change answer in ontology
    #                 self.onto.rename_node(q_id=q_id, a_id=a_id,
    #                                       a_field=a_field)
    #
    #                 # Change answer content in status and xmod
    #                 status[a_id]['content'] = a_field
    #
    #                 # Add change to ref_change_list
    #                 import_dict['ref_changes'][a_id] = change_dict(
    #                     old=old_field, new=a_field)
    #             status[a_id]['xMod'] = remote[a_id]['xMod']
    #
    #             # If index has changed:
    #         if not status[a_id]['index'] == remote[a_id]['index']:
    #
    #             # Change index in note
    #             if not import_dict['note']:
    #                 import_dict['note'] = \
    #                     self.note_manager.get_note_from_q_id(q_id)
    #             a_field = import_dict['note'].fields[get_index_by_a_id(
    #                 note=import_dict['note'], a_id=a_id)]
    #             a_content = content_from_field(a_field)
    #             a_class = self.translator.class_from_content(a_content)
    #             import_dict['index_dict'][remote[a_id]['index']] = a_field
    #
    #             # Change index in ontology
    #             self.onto.set_trpl_a_index(a_id=a_id, q_id=q_id,
    #                                        a_index=remote[a_id]['index'])
    #
    #             # Change index in status
    #             status[a_id]['index'] = remote[a_id]['index']
    #
    #             # Add change to sort_id_changes
    #             new_sort_id = sort_id_from_order_number(remote[a_id]['index'])
    #             if not level:
    #                 q_topic = self.map_manager.get_node_by_id(q_id)
    #                 level = len(self.map_manager.ref_and_sort_id(q_topic)[1])
    #             import_dict['sort_id_changes'][a_id] = change_dict(
    #                 old=level, new=new_sort_id)
    #
    #     # Assign answer fields with new indices to note fields
    #     if import_dict['index_dict']:
    #         self.note_manager.rearrange_answers(
    #             note=import_dict['note'], index_dict=import_dict['index_dict'])
    #
    #     return import_dict

    # def process_note(self, q_id, status, remote, import_dict):
    #     q_content = None
    #     level = None
    #     if not status['xMod'] == remote['xMod']:
    #         note = self.note_manager.get_note_from_q_id(q_id)
    #         q_content = self.map_manager.get_node_content_by_id(q_id)
    #         new_q_field = field_from_content(q_content)
    #         q_index = get_field_index_by_field_name('qt')
    #
    #         # Add change to changes dict
    #         import_dict['ref_changes']['question'] = change_dict(
    #             old=note.fields[q_index], new=new_q_field)
    #
    #         # Change question field to new question
    #         note.fields[q_index] = new_q_field
    #
    #         # Change question in ontology
    #         self.onto.change_relationship_class_name(x_id=q_id, new_question_content=new_q_field)
    #
    #         # Adjust question in status
    #         status['xMod'] = remote['xMod']
    #
    #     # Adjust index if it has changed
    #     if not status['index'] == remote['index']:
    #         q_topic = self.map_manager.get_node_by_id(q_id)
    #         level = len(self.map_manager.ref_and_sort_id(q_topic)[1])
    #         new_sort_id = sort_id_from_order_number(remote['index'])
    #
    #         # Add change to changes dict
    #         import_dict['sort_id_changes']['question'] = change_dict(
    #             old=level, new=new_sort_id)
    #
    #         # Adjust index in status
    #         status['index'] = remote['index']
    #
    #     # Add new answers if there are any
    #     # TODO: check whether answers meta is adjusted correctly
    #     import_dict = self.add_remote_as(
    #         q_content=q_content, q_id=q_id, remote=remote,
    #         status=status, import_dict=import_dict)
    #
    #     # Remove old answers if there are any
    #     # TODO: check whether answers meta is adjusted correctly
    #     import_dict = self.remove_remote_as(
    #         status=status['answers'], remote=remote['answers'], q_id=q_id,
    #         import_dict=import_dict)
    #
    #     # Change answers that have changed content
    #     import_dict = self.change_remote_as(
    #         status=status['answers'], remote=remote['answers'], q_id=q_id,
    #         level=level, import_dict=import_dict)

    # Change answer in note fields
    # Change answer in ontology
    # Change answer in status

    # Adjust answer index for answers that have changed position
    # Adjust ref of all following notes and set new fields
    # if note:
    #     if ref_changes:
    #         self.note_manager.update_ref(note=note, changes=ref_changes)
    #     if sort_id_changes:
    #         self.note_manager.update_sort_id(note=note,
    #                                          changes=sort_id_changes)
    #     # self.note_manager.set_fields(...)
    # if importer:
    #     importer.finish_import()
    # print('change note in anki and status and put changes in change_list')

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
        self.x_manager.set_edge_content(edge_id=xmind_edge.node_id, content=xmind_edge.content,
                                        media_directory=self.note_manager.media_directory, smr_world=self.smr_world)
        # Change question in ontology
        xmind_edge.ontology_storid = self.onto.change_relationship_class_name(
            parent_node_ids=parent_node_ids, child_node_ids=child_node_ids,
            new_question_content=xmind_edge.content, edge_id=xmind_edge.node_id).storid

    def maybe_add_media(self, content, importer, old_content=None):
        a_media = content['media']
        if old_content:
            old_media = old_content['media']
        else:
            old_media = a_media
        if a_media['image'] or a_media['media']:
            if not importer:
                importer = XmindImporter(col=self.note_manager.col,
                                         file=self.map_manager.file)
            if a_media['image'] and not a_media['image'] == old_media['image']:
                importer.images.append(a_media['image'])
            if a_media['media'] and not a_media['media'] == old_media['media']:
                importer.media.append(a_media['media'])
        return importer

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
        # Remove node from ontology
        self.onto.remove_node(xmind_node=xmind_node, xmind_edge=xmind_edge,
                              parent_node_ids=parent_node_ids, children={})
        # Add node to nodes to remove
        self.xmind_nodes_2_remove.append(xmind_node.node_id)

    def process_change_list(self):
        for sheet in self.change_list:
            changed_notes = [self.note_manager.get_note_from_q_id(q_id) for
                             q_id in self.change_list[sheet]]
            for note in changed_notes:
                meta = meta_from_fields(note.fields)
                changes = self.change_list[sheet][meta['questionId']]
                self.note_manager.update_ref(note=note, changes=changes,
                                             meta=meta)

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
                # change question if necessary
                question_content_local = field_content_by_identifier(
                    fields=fields, identifier='qt', smr_world=self.smr_world)
                if question_content_local != note_data['edge'].content:
                    note_data['edge'].content = question_content_local
                    self._change_remote_question(
                        xmind_edge=note_data['edge'], parent_node_ids=note_data['parents'],
                        child_node_ids=[a['node'].node_id for a in note_data['answers'].values()])
                    # Add edge to edges to be updated
                    self.xmind_edges_2_update.append(note_data['edge'])
                    anki_note_was_changed = True
                sorted_answers = sorted(note_data['answers'].items(), key=lambda item: item[0])
                # change answers if necessary
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
                            self._change_remote_node(xmind_edge=note_data['edge'],
                                                     parent_node_ids=note_data['parents'],
                                                     xmind_node=answer_data['node'], children=answer_data['children'])
                            self.xmind_nodes_2_update.append(answer_data['node'])
                            anki_note_was_changed = True
                        # do nothing if answer has not changed
                        else:
                            continue
                if anki_note_was_changed:
                    self.edge_ids_of_notes_2_update.append(note_data['note'].edge_id)

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
                self._process_remote_questions(sheet_id)

    def _process_remote_questions(self, sheet_id):
        nodes_status = self.smr_world.get_xmind_nodes_in_sheet(sheet_id)
        nodes_remote = self.x_manager.sheets[sheet_id].nodes
        for node_id in set(list(nodes_status) + list(nodes_remote)):
            if node_id not in nodes_status:
                print('')
            elif node_id not in nodes_remote:
                print('remove node')
            elif nodes_status[node_id].last_modified != nodes_remote[node_id]['last_modified']:
                print('change node')
        print('do the same for edges')
        #
        #
        # # Remove questions that were removed in map
        # not_in_remote = [q for q in status if q not in remote]
        # self.remove_questions(q_ids=not_in_remote, status=status)
        #
        # # Add questions that were added in map
        # not_in_status = [q for q in remote if q not in status]
        # tags_to_add = [self.map_manager.get_node_by_id(q) for q in not_in_status]
        # if tags_to_add:
        #     tags_and_parent_qs = [{'tag': t,
        #                            'parent_q': get_parent_question_topic(t)} for
        #                           t in tags_to_add]
        #
        #     # Get all questions whose parent question is already in status,
        #     # since they are the starting points for the imports
        #     seed_dicts = [d for d in tags_and_parent_qs if
        #                   d['parent_q']['id'] in status]
        #     importer = XmindImporter(col=self.note_manager.col,
        #                              file=self.map_manager.file,
        #                              status_manager=self.status_manager)
        #     for seed_dict in seed_dicts:
        #         parent_as = get_parent_a_topics(
        #             q_topic=seed_dict['tag'], parent_q=seed_dict['parent_q'])
        #
        #         # If the parent answer of this new question is not yet in
        #         # status, add the answer before importing from the question
        #         for a in parent_as:
        #             if a['id'] not in \
        #                     status[seed_dict['parent_q']['id']]['answers']:
        #                 if not note:
        #                     note = self.note_manager.get_note_from_q_id(
        #                         seed_dict['parent_q']['id'])
        #                 q_content = self.map_manager.get_topic_content(
        #                     seed_dict['parent_q'])
        #                 import_dict = {
        #                     'meta': meta_from_fields(note.fields),
        #                     'note': note,
        #                     'importer': importer,
        #                     'index_dict': {},
        #                     'ref_changes': {},
        #                     'sort_id_changes': {}}
        #                 import_dicts[seed_dict['parent_q'][
        #                     'id']] = self.add_remote_a(
        #                     q_content=q_content,
        #                     q_id=seed_dict['parent_q']['id'],
        #                     remote=remote[seed_dict['parent_q']['id']],
        #                     status=status[seed_dict['parent_q']['id']],
        #                     a_tag=a, import_dict=import_dict)['index_dict']
        #                 self.note_manager.save_note(note)
        #         importer.partial_import(
        #             seed_topic=seed_dict['tag'], sheet_id=sheet_id,
        #             deck_id=deck_id, parent_q=seed_dict['parent_q'],
        #             parent_as=parent_as, onto=self.onto)
        #     importer.finish_import()
        #
        #     # Add questions to status
        #     importer_status = next(
        #         f for f in importer.status_manager.status if
        #         f['file'] == self.map_manager.file)['sheets'][sheet_id][
        #         'questions']
        #     for q_id in importer_status:
        #         if q_id not in status:
        #             status[q_id] = importer_status[q_id]
        #
        # for question in {**status, **remote}:
        #     if question in import_dicts:
        #         import_dict = import_dicts[question]
        #     else:
        #         import_dict = {'note': note,
        #                        'meta': meta,
        #                        'importer': importer,
        #                        'index_dict': {},
        #                        'ref_changes': {},
        #                        'sort_id_changes': {}}
        #     self.process_note(q_id=question, status=status[question],
        #                       remote=remote[question],
        #                       import_dict=import_dict)
        # print()

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
        Removes all notes belonging to a sheet from the collection and the ontology and adds the sheet to the list of
        sheets to remove.
        :param sheet_id: xmind sheet id of the sheet to remove
        """
        self.note_manager.remove_notes_by_sheet_id(sheet_id, self.smr_world)
        self.onto.remove_sheet(sheet_id, self.smr_world.get_root_node_id(sheet_id))
        self.xmind_sheets_2_remove.append(sheet_id)

    def process_local_and_remote_changes(self):
        pass
