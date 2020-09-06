from __future__ import annotations

from itertools import zip_longest
from typing import List, Dict, Set, Union, Tuple

import aqt as aqt
import smr.consts as cts
from anki import Collection
from anki.utils import splitFields
from owlready2 import ThingClass
from smr.cachedproperty import cached_property
from smr.dto.smrnotedto import SmrNoteDto
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindmediatoankifilesdto import XmindMediaToAnkiFilesDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.fieldtranslator import relation_class_from_content
from smr.smrworld import SmrWorld
from smr.xmanager import XManager
from smr.xmindimport import XmindImporter
from smr.xmindtopic import XmindEdge, XmindNode
from smr.xnotemanager import get_field_by_identifier, XNoteManager, field_from_content, \
    content_from_field, get_field_content_by_identifier
from smr.xontology import XOntology


# Algorithm for synchronization was adopted from
# https://unterwaditzer.net/2016/sync-algorithm.html
class SmrSynchronizer:
    """
    Class for synchronizing changes in the anki collection and source xmind files
    """

    def __init__(self):
        self.x_manager = None
        self.importer = None
        self.onto = None
        self.smr_world = aqt.mw.smr_world
        self.note_manager = XNoteManager(col=aqt.mw.col)
        self.col = aqt.mw.col
        self.must_remove_anki_tags = False

    @property
    def x_manager(self) -> XManager:
        return self._x_manager

    @x_manager.setter
    def x_manager(self, value: XManager):
        self._x_manager = value

    @property
    def importer(self) -> XmindImporter:
        return self._importer

    @importer.setter
    def importer(self, value: XmindImporter):
        self._importer = value

    @property
    def onto(self) -> XOntology:
        return self._onto

    @onto.setter
    def onto(self, value: XOntology):
        self._onto = value

    @property
    def smr_world(self) -> SmrWorld:
        return self._smr_world

    @smr_world.setter
    def smr_world(self, value: SmrWorld):
        self._smr_world = value

    @property
    def note_manager(self) -> XNoteManager:
        return self._note_manager

    @note_manager.setter
    def note_manager(self, value: XNoteManager):
        self._note_manager = value

    @property
    def col(self) -> Collection:
        return self._col

    @col.setter
    def col(self, value: Collection):
        self._col = value

    @cached_property
    def log(self) -> List[str]:
        return []

    @cached_property
    def changed_smr_notes(self) -> Dict[str, Dict[str, Dict[int, Dict[str, Union[
        SmrNoteDto, XmindTopicDto, str, Dict[int, Dict[str, Union[XmindTopicDto, Dict[str, Set[str]]]]], Set[str]]]]]]:
        return self.smr_world.get_changed_smr_notes(self.col)

    @cached_property
    def relations_2_move(self) -> List[Dict[str, Union[str, List[str]]]]:
        return []

    @cached_property
    def concepts_2_move(self) -> List[Dict[str, Union[str, List[str], Set[str]]]]:
        return []

    @cached_property
    def concepts_2_rename(self) -> Dict[str, Dict[str, Union[List[str], XmindTopicDto, Dict[str, List[str]]]]]:
        return {}

    @cached_property
    def relations_2_rename(self) -> List[Dict[str, Union[List[str], XmindTopicDto]]]:
        return []

    @cached_property
    def concepts_2_remove(self) -> List[Dict[str, Union[List[str], str, ThingClass]]]:
        return []

    @cached_property
    def onto_sheets_2_remove(self) -> Dict[str, str]:
        return {}

    @cached_property
    def xmind_files_2_update(self) -> List[XmindFileDto]:
        return []

    @cached_property
    def xmind_uris_2_anki_files_2_update(self) -> List[XmindMediaToAnkiFilesDto]:
        return []

    @cached_property
    def xmind_nodes_2_update(self) -> Dict[str, XmindTopicDto]:
        return {}

    @cached_property
    def xmind_edges_2_update(self) -> Dict[str, XmindTopicDto]:
        return {}

    @cached_property
    def smr_notes_2_update(self) -> List[SmrNoteDto]:
        return []

    @cached_property
    def smr_triple_edges_2_move(self) -> Dict[str, List[Tuple[str, str]]]:
        return {'new_data': [], 'old_data': []}

    @cached_property
    def smr_triple_nodes_2_move(self) -> Dict[str, List[Tuple[str, str]]]:
        return {'new_data': [], 'old_data': []}

    @cached_property
    def xmind_nodes_2_remove(self) -> List[str]:
        return []

    @cached_property
    def xmind_edges_2_remove(self) -> Set[str]:
        return set()

    @cached_property
    def xmind_uris_2_remove(self) -> Set[str]:
        return set()

    @cached_property
    def xmind_sheets_2_remove(self) -> List[str]:
        return []

    @cached_property
    def edge_ids_of_anki_notes_2_update(self) -> Set[str]:
        return set()

    @cached_property
    def anki_notes_2_update(self) -> Dict[str, SmrNoteDto]:
        return self.smr_world.get_updated_child_smr_notes(list(self.edge_ids_of_anki_notes_2_update))

    @cached_property
    def anki_notes_2_remove(self) -> Set[int]:
        return set()

    def synchronize(self):
        """
        Checks whether there were changes in notes or xmind files since the last synchronization and triggers the
        respective synchronization methods in case there were changes
        """
        aqt.mw.progress.start(immediate=True, label="Synchronizing SMR changes...")
        smr_decks = self.smr_world.get_ontology_lives_in_deck()
        xmind_files_in_decks = self.smr_world.get_xmind_files_in_decks()
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
                if local_change:
                    self.importer = XmindImporter(col=self.col, file=xmind_file.file_path, onto=self.onto)
                    if remote_change:
                        self.process_local_and_remote_changes()
                    else:
                        self._process_local_changes(xmind_file)
                        self.x_manager.save_changes()
                else:
                    if remote_change:
                        self.importer = XmindImporter(col=self.col, file=xmind_file.file_path, onto=self.onto)
                        self._process_remote_file_changes(xmind_file)
                        self.importer.finish_import()
                    else:
                        continue
                # apply updates to the all systems
                self._synchronize_ontology()
                self._synchronize_smr_world()
                self._synchronize_anki_collection()
        aqt.mw.progress.finish()

    def _synchronize_anki_collection(self):
        # update anki notes affected by changes
        changed_notes = self.smr_world.generate_notes(self.col, list(self.anki_notes_2_update))
        self.importer.tagModified = 'yes'
        self.importer.addUpdates(rows=[
            [self.anki_notes_2_update[edge_id].last_modified, self.col.usn(), foreign_note.fieldsStr,
             foreign_note.tags[0], self.anki_notes_2_update[edge_id].note_id, foreign_note.fieldsStr] for
            edge_id, foreign_note in changed_notes.items()])
        # generate cards + update field cache
        self.col.after_note_updates(nids=[n.note_id for n in self.anki_notes_2_update.values()], mark_modified=False)
        del self.anki_notes_2_update
        # remove notes with note_ids from list of anki notes to remove
        self.col.remove_notes(list(self.anki_notes_2_remove))
        del self.anki_notes_2_remove
        # remove empty cards
        self.col.remove_cards_and_orphaned_notes([
            c for n in self.col.backend.get_empty_cards().notes for c in n.card_ids])
        # bulk remove notes for removed sheets
        if self.must_remove_anki_tags:
            self.must_remove_anki_tags = False
            self.note_manager.clear_unused_tags()
        self.note_manager.save_col()

    def _synchronize_smr_world(self):
        """
        makes all necessary changes to the smr world
        """
        # updates
        self.smr_world.add_or_replace_xmind_files(self.xmind_files_2_update)
        del self.xmind_files_2_update
        self.smr_world.add_or_replace_xmind_edges(list(self.xmind_edges_2_update.values()))
        del self.xmind_edges_2_update
        # move edges
        self.smr_world.move_smr_triple_edges(new_data=self.smr_triple_edges_2_move['new_data'],
                                             old_data=self.smr_triple_edges_2_move['old_data'])
        del self.smr_triple_edges_2_move
        # move nodes
        self.smr_world.move_smr_triple_nodes(new_data=self.smr_triple_nodes_2_move['new_data'],
                                             old_data=self.smr_triple_nodes_2_move['old_data'])
        del self.smr_triple_nodes_2_move
        # removals
        self.smr_world.remove_xmind_nodes(self.xmind_nodes_2_remove)
        del self.xmind_nodes_2_remove
        self.smr_world.remove_xmind_edges(self.xmind_edges_2_remove)
        del self.xmind_edges_2_remove
        self.smr_world.remove_xmind_media_2_anki_files(self.xmind_uris_2_remove)
        del self.xmind_uris_2_remove
        self.smr_world.remove_xmind_sheets(sheet_ids=self.xmind_sheets_2_remove)
        del self.xmind_sheets_2_remove
        # update smr notes where only last modified has to be adjusted and those where anki notes' fields need to be
        # adjusted. Do so after removals to avoid finding anki notes that were already deleted
        self.smr_world.add_or_replace_smr_notes(self.smr_notes_2_update + list(self.anki_notes_2_update.values()))
        del self.smr_notes_2_update
        self.smr_world.save()

    def _synchronize_ontology(self):
        """
        Makes all necessary changes to the ontology that are not covered by XmindImport
        """
        # First move entities to avoid conflicts when trying to rename moved entities
        # Move edges first to avoid nodes that were moved from moved edges to be reattached to the edges
        for relation in self.relations_2_move:
            self.onto.move_edge(old_parent_node_ids=relation['old_parent_node_ids'],
                                new_parent_node_ids=relation['new_parent_node_ids'],
                                edge_id=relation['edge_id'],
                                child_node_ids=relation['child_node_ids'])
        del self.relations_2_move
        # Move nodes
        for concept in self.concepts_2_move:
            self.onto.move_node(old_parent_node_ids=concept['old_parent_node_ids'],
                                new_parent_node_ids=concept['new_parent_node_ids'],
                                old_parent_edge_id=concept['old_parent_edge_id'],
                                new_parent_edge_id=concept['new_parent_edge_id'],
                                node_id=concept['node_id'])
        del self.concepts_2_move
        # Add smr world media and node updates before renaming to overwrite nodes that are updated without renaming
        # and avoid foreign key constraint violations
        self.smr_world.add_xmind_media_to_anki_files(list(self.xmind_uris_2_anki_files_2_update))
        del self.xmind_uris_2_anki_files_2_update
        self.smr_world.add_or_replace_xmind_nodes(list(self.xmind_nodes_2_update.values()))
        del self.xmind_nodes_2_update
        # Rename nodes in ontology and assign new storids to respective nodes
        for concept in self.concepts_2_rename.values():
            self.onto.rename_node(parent_node_ids=concept['parent_node_ids'], xmind_edge=concept['xmind_edge'],
                                  xmind_node=concept['xmind_node'], children=concept['children'])
        del self.concepts_2_rename
        # Change relation names in ontology and assign new storids to respective edges
        for relation in self.relations_2_rename:
            edge_2_rename = relation['xmind_edge']
            relation_class_name = relation_class_from_content(edge_2_rename.content)
            self.xmind_edges_2_update[edge_2_rename.node_id].storid = self.onto.add_relation(relation_class_name)
            self.onto.rename_relation(
                parent_node_ids=relation['parent_node_ids'], relation_class_name=relation_class_name,
                child_node_ids=relation['child_node_ids'], edge_id=edge_2_rename.node_id)
        del self.relations_2_rename
        # Remove nodes from ontology
        for concept in self.concepts_2_remove:
            self.onto.disconnect_node(parent_node_ids=concept['parent_node_ids'], parent_edge_id=concept[
                'parent_edge_id'], concept=concept['concept'], children={})
        for concept in self.concepts_2_remove:
            self.onto.destroy_node(concept=concept['concept'], node_id=concept['node_id'])
        del self.concepts_2_remove
        # Remove nodes from ontology by sheets
        for sheet_id, root_node_id in self.onto_sheets_2_remove.items():
            self.onto.remove_sheet(sheet_id=sheet_id, root_node_id=root_node_id)
        del self.onto_sheets_2_remove

    def _add_answer(self, answer_content: TopicContentDto, xmind_edge: XmindTopicDto):
        print('add answer to map')
        print('add answer to ontology')
        self.log.append(f"""\
Invalid added answer: Cannot add answer "{field_from_content(content=answer_content, smr_world=self.smr_world)}" to \
question "{field_from_content(content=xmind_edge.content, smr_world=self.smr_world)}" (reference: \
{self.smr_world.get_smr_note_reference_fields([xmind_edge.node_id])[xmind_edge.node_id]}). Adding answers via \
anki is not yet supported, instead, add the answer in your xmind map and synchronize. I removed the answer from the \
note.""")

    def _change_remote_node(self, xmind_edge: XmindTopicDto, parent_node_ids: Set[str], xmind_node: XmindTopicDto,
                            children: Dict[str, List[str]]) -> None:
        """
        Changes a node's content in the xmind map and in the ontology
        :param xmind_edge: the xmind edge preceding the node to change
        :param parent_node_ids: list of node ids of parent nodes of the preceding edge
        :param xmind_node: xmind node dto of the node to change
        :param children: dictionary where keys are edge_ids of edges following the node to change and values are
        lists of xmind node ids belonging to the edge's child nodes
        """
        self.x_manager.set_node_content(node_id=xmind_node.node_id, content=xmind_node.content,
                                        media_directory=self.note_manager.media_directory)
        # Change answer in Ontology
        self.concepts_2_rename[xmind_node.node_id] = {'xmind_node': xmind_node, 'xmind_edge': xmind_edge,
                                                      'parent_node_ids': parent_node_ids, 'children': children}

    def _change_remote_question(self, xmind_edge: XmindTopicDto, parent_node_ids: Set[str],
                                child_node_ids: List[str]):
        """
        - Changes the content of the xmind edge that belongs to the specified note data to the local question content
        - Changes the relationship class name in the ontology according to the new content
        :param xmind_edge: xmind node dto of the edge representing the question to be changed. The content must
        already be updated to the new value.
        :param parent_node_ids: list of xmind node ids of the parent nodes of the edge to change
        :param child_node_ids: list of xmind node ids of the child nodes of the edge to change
        """
        self.x_manager.set_edge_content(edge_id=xmind_edge.node_id, content=xmind_edge.content,
                                        media_directory=self.note_manager.media_directory)
        # Add node ids and edge to relations to change
        self.relations_2_rename.append({
            'parent_node_ids': parent_node_ids, 'xmind_edge': xmind_edge, 'child_node_ids': child_node_ids})

    def _try_to_remove_answer(self, xmind_edge: XmindTopicDto, xmind_node: XmindTopicDto,
                              parent_node_ids: Set[str]):
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
        self.concepts_2_remove.append({'node_id': xmind_node.node_id, 'parent_edge_id': xmind_edge.node_id,
                                       'parent_node_ids': parent_node_ids,
                                       'concept': self.onto.get_concept_from_node_id(xmind_node.node_id)})
        # Add node to nodes to remove
        self.xmind_nodes_2_remove.append(xmind_node.node_id)

    def _process_local_changes(self, file: XmindFileDto):
        """
        if for each sheet in the specified file, changes questions and answers where necessary and adds changed
        entities to the respective lists
        :param file: xmind file for which to work through the changes
        """
        for sheet_data_status in self.changed_smr_notes[file.file_path].values():
            for note_id, note_data_status in sheet_data_status.items():
                anki_note_was_changed = False
                fields = splitFields(note_data_status['note_fields'])
                # get data for changing question if necessary
                question_content_local = get_field_content_by_identifier(
                    fields=fields, identifier='qt', smr_world=self.smr_world)
                if question_content_local != note_data_status['edge'].content:
                    # register changes in files for smr world
                    content_status = note_data_status['edge'].content
                    self._register_local_topic_media_changes(
                        content_status=content_status, content_local=question_content_local, media_is_image=True)
                    self._register_local_topic_media_changes(
                        content_status=content_status, content_local=question_content_local, media_is_image=False)
                    content_status.title = question_content_local.title
                    note_data_status['edge'].content = content_status
                    # change question in  map
                    self._change_remote_question(
                        xmind_edge=note_data_status['edge'], parent_node_ids=note_data_status['parents'],
                        child_node_ids=[a['node'].node_id for a in note_data_status['answers'].values()])
                    self.xmind_edges_2_update[note_data_status['edge'].node_id] = note_data_status['edge']
                    anki_note_was_changed = True
                # get data for changing answers if necessary
                sorted_answers_status = sorted(note_data_status['answers'].items(), key=lambda item: item[0])
                local_answer_fields = [get_field_by_identifier(fields=fields, identifier='a' + str(i))
                                       for i in range(1, cts.X_MAX_ANSWERS + 1)]
                for local_answer_field, answer_id, answer_data_status in zip_longest(
                        local_answer_fields, (a[0] for a in sorted_answers_status),
                        (a[1] for a in sorted_answers_status)):
                    # stop if no more answers left
                    if not local_answer_field:
                        if not answer_id:
                            break
                        # try to remove answer from remote if not present in anki anymore
                        else:
                            self._try_to_remove_answer(xmind_edge=note_data_status['edge'],
                                                       xmind_node=answer_data_status['node'],
                                                       parent_node_ids=note_data_status['parents'])
                            anki_note_was_changed = True
                    else:
                        answer_content_local = content_from_field(field=local_answer_field, smr_world=self.smr_world)
                        if not answer_id:
                            self._add_answer(answer_content=answer_content_local, xmind_edge=note_data_status['edge'])
                            anki_note_was_changed = True
                        # change answer if content was changed
                        elif answer_content_local != answer_data_status['node'].content:
                            content_status = answer_data_status['node'].content
                            self._register_local_topic_media_changes(
                                content_status=content_status, content_local=answer_content_local, media_is_image=True)
                            self._register_local_topic_media_changes(
                                content_status=content_status, content_local=answer_content_local,
                                media_is_image=False)
                            content_status.title = answer_content_local.title
                            answer_data_status['node'].content = content_status
                            self._change_remote_node(
                                xmind_edge=note_data_status['edge'], parent_node_ids=note_data_status['parents'],
                                xmind_node=answer_data_status['node'], children=answer_data_status['children'])
                            anki_note_was_changed = True
                        # do nothing if answer has not changed
                        else:
                            continue
                if anki_note_was_changed:
                    self.edge_ids_of_anki_notes_2_update.add(note_data_status['note'].edge_id)
                else:
                    self.smr_notes_2_update.append(note_data_status['note'])

    def _register_local_topic_media_changes(self, content_status, content_local, media_is_image: bool):
        """
        - checks whether image or media in the provided content dtos have been modified
        - if the checked media is of type image:
          - adds the image to the lists for anki file name entries to add/remove from the smr world
          - changes the smr world content to the one of the collection
        - if the checked media is of type media, adds a warning to the log
        :param content_status: the topic's content as it is registered in the smr world
        :param content_local: the topic's content from the anki collection
        :param media_is_image: whether to execute the method for the image in the content or the media
        """
        if media_is_image:
            def update_action(syncer):
                syncer.xmind_uris_2_anki_files_2_update.append(XmindMediaToAnkiFilesDto(*2 * [content_local.image]))
                content_status.image = content_local.image

            def delete_action(syncer):
                syncer.xmind_uris_2_remove.add(content_status.image)
                content_status.image = None

            media_status = content_status.image
            media_local = content_local.image
        else:
            media_status = content_status.media
            media_local = content_local.media

            def update_action(syncer):
                syncer.log.append(f"""\
Invalid added media: Cannot add media "{media_local}". Adding media via anki is not yet supported, instead, add the 
file in your xmind map and synchronize. I removed the file from the note.""")

            def delete_action(syncer):
                syncer.log.append(f"""\
Invalid removed media: Cannot remove media "{media_local}". Removing media via anki is not yet supported, instead, 
remove the file from your xmind map and synchronize. I added the file to the note again.
""")

        if media_status is None:
            if media_local is None:
                pass
            else:
                update_action(self)
        else:
            if media_local is None:
                delete_action(self)
            else:
                if media_status != media_local:
                    update_action(self)
                    delete_action(self)
                else:
                    pass

    def _process_remote_file_changes(self, file: XmindFileDto):
        """
        for each sheet in the specified file, checks whether it was removed, added, or changed and calls the correct
        method for each case
        :param file: the file to process
        """
        sheets_status = self.smr_world.get_xmind_sheets_in_file(file_directory=file.directory, file_name=file.file_name)
        sheet_ids_remote = list(self.x_manager.sheets)
        for sheet_id in set(list(sheets_status) + sheet_ids_remote):
            if sheet_id not in sheets_status:
                self.importer.import_sheet(sheet_id=sheet_id)
            elif sheet_id not in sheet_ids_remote:
                self._remove_sheet(sheet_id)
            elif sheets_status[sheet_id].last_modified != self.x_manager.sheets[sheet_id].last_modified:
                self._register_remote_sheet_changes(sheet_id)

    def _remove_sheet(self, sheet_id: str) -> None:
        """
        adds the needed data for removing the sheet with the specified id to the respective data structures
        :param sheet_id: xmind sheet id of the sheet to remove
        """
        self.anki_notes_2_remove.update(self.smr_world.get_note_ids_from_sheet_id(sheet_id))
        self.must_remove_anki_tags = True
        self.onto_sheets_2_remove[sheet_id] = self.smr_world.get_root_node_id(sheet_id)
        self.xmind_sheets_2_remove.append(sheet_id)

    def _register_remote_sheet_changes(self, sheet_id):
        """
        - for each edge in the sheet with the specified id checks whether it was removed, added or changed and takes
        the corresponding actions
        - for each node in the sheet does the same as for each edge
        :param sheet_id: xmind id of the sheet to process
        """
        # edges
        edges_remote = self.x_manager.sheets[sheet_id].edges
        edges_status = self.smr_world.get_xmind_edges_in_sheet(sheet_id)
        for edge_id in set(list(edges_status) + list(edges_remote)):
            if edge_id in edges_remote:
                edge_remote = edges_remote[edge_id]
                if edge_id in edges_status:
                    edge_data_status = edges_status[edge_id]
                    # do not register changes in sibling edges if the edge was not moved
                    if not self._register_remote_edge_changes(edge_remote=edge_remote,
                                                              edge_data_status=edge_data_status):
                        continue
                else:
                    # the importer takes care of everything necessary concerning pure imports
                    self.importer.read_edge(edge_remote)
                # register existing sibling edges for sort id updates if their order number has changed
                for sibling_edge in edge_remote.sibling_edges:
                    if sibling_edge.id in edges_status and not sibling_edge.order_number < edge_remote.order_number:
                        self.edge_ids_of_anki_notes_2_update.add(sibling_edge.id)
                        if sibling_edge.id not in self.xmind_edges_2_update:
                            sibling_edge.dto.storid = edges_status[sibling_edge.id]['xmind_edge'].storid
                            self.xmind_edges_2_update[sibling_edge.id] = sibling_edge.dto
            else:
                edge_data_status = edges_status[edge_id]
                self._register_remote_edge_removal(edge_data=edge_data_status)
                # register existing sibling edges for sort id updates if their order number has changed
                for sibling_edge_id in edge_data_status['sibling_edge_ids']:
                    sibling_edge = edges_status[sibling_edge_id]['xmind_edge']
                    if sibling_edge_id in edges_remote and \
                            not sibling_edge.order_number < edge_data_status['xmind_edge'].order_number:
                        self.edge_ids_of_anki_notes_2_update.add(sibling_edge_id)
                        if sibling_edge_id not in self.xmind_edges_2_update:
                            remote_sibling_edge = edges_remote[sibling_edge_id]
                            remote_sibling_edge.dto.storid = sibling_edge.storid
                            self.xmind_edges_2_update[sibling_edge_id] = remote_sibling_edge.dto
        # nodes
        nodes_status = self.smr_world.get_xmind_nodes_in_sheet(sheet_id)
        nodes_remote = self.x_manager.sheets[sheet_id].nodes
        for node_id in set(list(nodes_status) + list(nodes_remote)):
            if node_id in nodes_remote:
                node_remote = nodes_remote[node_id]
                if node_id in nodes_status:
                    node_data_status = nodes_status[node_id]
                    if not self._register_remote_node_changes(node_data_status=node_data_status,
                                                              node_remote=node_remote):
                        continue
                else:
                    # if the node does not belong to a newly imported edge, also register its parent node for updating
                    if node_remote.parent_edge.id not in self.importer.edge_ids_2_make_notes_of:
                        self.edge_ids_of_anki_notes_2_update.add(node_remote.parent_edge.id)
                    self.importer.read_node_if_concept(node_remote)
                # register child edges of sibling nodes for sort id updates if their order number has changed
                for sibling_node in node_remote.non_empty_sibling_nodes:
                    if sibling_node.order_number < node_remote.order_number and \
                            sibling_node.id in nodes_status:
                        self.edge_ids_of_anki_notes_2_update.update({e.id for e in sibling_node.child_edges})
                        if sibling_node.id not in self.xmind_nodes_2_update:
                            sibling_node.dto.storid = nodes_status[sibling_node.id]['xmind_node'].storid
                            self.xmind_nodes_2_update[sibling_node.id] = sibling_node.dto
            else:
                node_data_status = nodes_status[node_id]
                self._register_remote_node_removal(node_data_status)
                # register existing child edges of sibling nodes for sort id updates if their order number has changed
                for sibling_node_id in node_data_status['sibling_node_ids']:
                    sibling_node = nodes_status[sibling_node_id]['xmind_node']
                    if sibling_node_id in nodes_remote and \
                            not sibling_node.order_number < node_data_status['xmind_node'].order_number:
                        remote_sibling_node = nodes_remote[sibling_node_id]
                        self.edge_ids_of_anki_notes_2_update.update(
                            {e.id for e in remote_sibling_node.child_edges})
                        if sibling_node_id not in self.xmind_nodes_2_update:
                            remote_sibling_node.dto.storid = sibling_node.storid
                            self.xmind_nodes_2_update[sibling_node_id] = remote_sibling_node.dto

    def _register_remote_edge_removal(self, edge_data: Dict[str, Union[XmindTopicDto, int, List[str]]]) -> None:
        """
        registers data for removing data belonging to an xmind edge from all required data structures
        :param edge_data: Dictionary containing a topic dto representing the edge to remove from the smr world,
        and the note id
        """
        # we do not remove relations from the ontology explicitly since that is already part of removing nodes
        # add edge to smr world xmind edges to remove
        self.xmind_edges_2_remove.add(edge_data['xmind_edge'].node_id)
        # add edge to notes to remove if it belongs to a note
        note_id = edge_data['note_id']
        if note_id is not None:
            self.anki_notes_2_remove.add(note_id)

    def _register_remote_edge_changes(self, edge_remote: XmindEdge,
                                      edge_data_status: Dict[str, Union[XmindTopicDto, int, Set[str]]]) -> bool:
        """
        - registers data for updating data belonging to an xmind edge in all required data structures
        - checks whether the edge was moved and returns the result of the check
        :param edge_remote: Xmind Edge as extracted from the xmind file
        :param edge_data_status: Dictionary containing all necessary data from the smr world
        :return: Whether the edge was moved
        """
        index_was_changed = False
        edge_was_changed = False
        # register edge for moving in ontology and smr_world if necessary
        remote_parent_node_ids = set(pn.id for pn in edge_remote.parent_nodes)
        edge_status = edge_data_status['xmind_edge']
        if remote_parent_node_ids != edge_data_status['parent_node_ids']:
            self.relations_2_move.append({
                'old_parent_node_ids': edge_data_status['parent_node_ids'],
                'new_parent_node_ids': remote_parent_node_ids,
                'edge_id': edge_remote.id,
                'child_node_ids': edge_data_status['child_node_ids']})
            for parent_node_id in remote_parent_node_ids:
                self.smr_triple_edges_2_move['new_data'].append((parent_node_id, edge_remote.id))
            for parent_node_id in edge_data_status['parent_node_ids']:
                self.smr_triple_edges_2_move['old_data'].append((parent_node_id, edge_remote.id))
            index_was_changed = True
            edge_was_changed = True
        elif edge_remote.order_number != edge_status.order_number:
            index_was_changed = True
            edge_was_changed = True
        # register edge for renaming in ontology if necessary
        remote_edge_dto = edge_remote.dto
        content_status = edge_status.content
        content_remote = edge_remote.content
        if content_status != content_remote:
            # if the node was empty before, generate a new note for it
            if content_status.is_empty():
                self.importer.read_edge(edge_remote)
            # if the node is empty now, remove the note later
            elif content_remote.is_empty():
                self.anki_notes_2_remove.add(edge_data_status['note_id'])
            # update ontology relation
            self.relations_2_rename.append({
                'parent_node_ids': [node.id for node in edge_remote.parent_nodes],
                'xmind_edge': remote_edge_dto,
                'child_node_ids': [node.id for node in edge_remote.non_empty_child_nodes]})
            # update media if necessary
            self._register_remote_topic_media_changes(content_remote=content_remote, content_status=content_status)
            edge_was_changed = True
        if edge_was_changed:
            # add edge id to edge ids of notes 2 update
            remote_edge_dto.storid = edge_status.storid
            self.xmind_edges_2_update[remote_edge_dto.node_id] = remote_edge_dto
            # add edge id to list of edge ids of anki notes to update
            self.edge_ids_of_anki_notes_2_update.add(edge_remote.id)
        return index_was_changed

    def _register_remote_node_removal(self, node_status: Dict[str, Union[XmindTopicDto, str, List[str]]]) -> None:
        """
        registers the data for removing a node from ontology, smr world, and collection
        :param node_status: dictionary with the xmind node as an xmind topic dto, the node's parent edge's xmind id
        and a list of the node's grandparent node's xmind ids
        """
        # register node for removal from ontology
        self.concepts_2_remove.append(
            {'node_id': node_status['xmind_node'].node_id,
             'parent_edge_id': node_status['parent_edge_id'],
             'parent_node_ids': node_status['parent_node_ids'],
             'concept': self.onto.get_concept_from_node_id(node_status['xmind_node'].node_id)})
        # register node for removal from smr world
        self.xmind_nodes_2_remove.append(node_status['xmind_node'].node_id)
        # add parent edge to edges of anki notes to update
        if node_status['note_id'] not in self.anki_notes_2_remove:
            self.edge_ids_of_anki_notes_2_update.add(node_status['parent_edge_id'])

    def _register_remote_node_changes(self, node_data_status: Dict[str, Union[XmindTopicDto, str, List[str]]],
                                      node_remote: XmindNode) -> bool:
        """
        - If the specified node was moved in the map, registers the necessary data for adjusting ontology,
        smr world anki collection to the move
        - If the content of the specified node was changed, registers the necessary data for changing the related
        data in the ontology, smr world and anki collection
        - checks whether the index of the node was changed and returns the result of the check
        :param node_data_status: Dictionary of the topic content dto representing the changed node in the smr world,
        the node's parent edge's xmind id and the node's grandparent nodes' xmind ids
        :param node_remote: The xmind node taken from the current version of the xmind file
        :return: whether the index of the node was changed
        """
        index_was_changed = False
        node_was_changed = False
        # move node if necessary
        remote_parent_edge = node_remote.parent_edge
        if remote_parent_edge is not None and remote_parent_edge.id != node_data_status['parent_edge_id']:
            self.concepts_2_move.append({
                'old_parent_node_ids': node_data_status['parent_node_ids'],
                'new_parent_node_ids': [n.id for n in node_remote.parent_edge.parent_nodes],
                'old_parent_edge_id': node_data_status['parent_edge_id'],
                'new_parent_edge_id': node_remote.parent_edge.id,
                'node_id': node_remote.id})
            self.smr_triple_nodes_2_move['new_data'].append((node_remote.id, node_remote.parent_edge.id))
            self.smr_triple_nodes_2_move['old_data'].append((node_data_status['parent_edge_id'], node_remote.id))
            self.edge_ids_of_anki_notes_2_update.add(node_data_status['parent_edge_id'])
            self.edge_ids_of_anki_notes_2_update.add(remote_parent_edge.id)
            index_was_changed = True
            node_was_changed = True
        elif node_data_status['xmind_node'].order_number != node_remote.order_number:
            self.edge_ids_of_anki_notes_2_update.add(node_data_status['parent_edge_id'])
            index_was_changed = True
            node_was_changed = True
        if node_was_changed:
            node_remote.dto.storid = node_data_status['xmind_node'].storid
            # add node to changes in smr world
            self.xmind_nodes_2_update[node_remote.id] = node_remote.dto
        # change node content if necessary
        content_remote = node_remote.content
        content_status = node_data_status['xmind_node'].content
        if content_remote != content_status:
            # add node to changes in ontology
            parent_node_ids = [n.id for n in
                               remote_parent_edge.parent_nodes] if remote_parent_edge is not None else []
            parent_edge_dto = remote_parent_edge.dto if remote_parent_edge is not None else None
            self.concepts_2_rename[node_remote.id] = {
                'xmind_node': node_remote.dto, 'xmind_edge': parent_edge_dto,
                'parent_node_ids': parent_node_ids, 'children': {ce.id: [
                    cn.id for cn in ce.non_empty_child_nodes] for ce in node_remote.child_edges}}
            # update image if necessary
            self._register_remote_topic_media_changes(content_remote, content_status)
            # add parent edge to edge ids of anki notes to update
            if remote_parent_edge is not None:
                self.edge_ids_of_anki_notes_2_update.add(remote_parent_edge.id)
            else:
                self.edge_ids_of_anki_notes_2_update.update(ce.id for ce in node_remote.child_edges)
        return index_was_changed

    def _register_remote_topic_media_changes(self, content_remote: TopicContentDto,
                                             content_status: TopicContentDto) -> None:
        """
        Checks whether an image or media file was added, removed or modified in the topic with the given content and
        adds it to the list of uris to add / remove if necessary
        :param content_remote: Topic content dto with the content of the topic in the xmind file
        :param content_status: Topic content dto with the content of the topic from the smr world
        """
        for media_remote, media_status in zip(*[(c.image, c.media) for c in (content_remote, content_status)]):
            if media_remote is not None:
                if media_status is not None:
                    if media_remote != media_status:
                        self.xmind_uris_2_remove.add(media_status)
                        self.importer.media_uris_2_add.append(media_remote)
                else:
                    self.importer.media_uris_2_add.append(media_remote)
            else:
                if media_status is not None:
                    self.xmind_uris_2_remove.add(media_status)

    def process_local_and_remote_changes(self):
        pass
