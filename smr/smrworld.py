import os
from collections import namedtuple
from typing import List, TextIO, Tuple, Dict, Any, Union, Optional, Set

from anki import Collection
from anki.importing.noteimp import ForeignNote, ForeignCard
from anki.utils import joinFields, intTime
from owlready2.namespace import World
from smr.consts import ADDON_PATH, USER_PATH, X_MAX_ANSWERS
from smr.dto.ontologylivesindeckdto import OntologyLivesInDeckDto
from smr.dto.smrnotedto import SmrNoteDto
from smr.dto.smrtripledto import SmrTripleDto
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindmediatoankifilesdto import XmindMediaToAnkiFilesDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.dto.xmindsheetdto import XmindSheetDto
from smr.fieldtranslator import FieldTranslator
from smr.utils import replace_embedded_media

FILE_NAME = 'smrworld.sqlite3'
SQL_FILE_NAME = 'smrworld.sql'
ANKI_COLLECTION_DB_NAME = "anki_collection"
SMR_WORLD_PATH = os.path.join(USER_PATH, FILE_NAME)
ANNOTATED_PROPERTY_STORID = 85

Node2Remove: Dict[str, Union[XmindTopicDto, List[str]]]


def get_node_2_remove(record) -> 'Node2Remove':
    return {'parent_node_ids': [record.parent_node_id],
            'xmind_edge': XmindTopicDto(node_id=record.edge_id, title=record.title,
                                        image=record.image, link=record.link),
            'xmind_node': XmindTopicDto(node_id=record.node_id)}


def get_xmind_content_selection_clause(relation_name: str) -> str:
    """
    builds an sql select clause that returns title, image, and media in the correct format to be displayed in anki
    fields
    :param relation_name: the name of the relation in the smr world to get the content from
    :return: the select clause
    """
    return f"""
        ifnull({relation_name}.title, '') ||
            case
                when {relation_name}.image is null then ''
                else case
                         when {relation_name}.title = '' or {relation_name}.title is null then ''
                         else '<br>' end ||
                     '<img src="' ||
                     (SELECT anki_file_name FROM xmind_media_to_anki_files WHERE xmind_uri = {relation_name}.image) ||
                     '">'
                end ||
            case
                when {relation_name}.link is null then ''
                else case
                         when ({relation_name}.title = '' or {relation_name}.title is null) 
                         and {relation_name}.image is null then ''
                         else '<br>' end ||
                     '[sound:' ||
                     (SELECT anki_file_name FROM xmind_media_to_anki_files WHERE xmind_uri = {relation_name}.link) ||
                     ']'
                end"""


def get_sort_id_recursive_cte_clause(where_clause: str):
    """
    Gets an sqlite cte clause that can be used to get the sort id of the edges specified by the where clause
    :param where_clause: sql clause for where selection in the cte clause (e.g. "e.sheet_id = 'my sheet id'" or
    "e.edge_id in ('id1', 'id2')"
    :return: the recursive cte clause
    """
    return f"""-- noinspection SqlResolveForFile
WITH ancestor AS (
    SELECT t1.parent_node_id, t1.edge_id AS root_id, 0 AS level, n.order_number as node, e.order_number as edge
    FROM smr_triples t1
             JOIN xmind_edges e ON t1.edge_id = e.edge_id
             JOIN xmind_nodes n ON t1.parent_node_id = n.node_id
    WHERE {where_clause}
    UNION ALL
    SELECT t.parent_node_id, a.root_id, a.level + 1, n.order_number, e.order_number
    FROM smr_triples t
             JOIN ancestor a ON a.parent_node_id = t.child_node_id
             JOIN xmind_edges e ON t.edge_id = e.edge_id
             JOIN xmind_nodes n ON t.parent_node_id = n.node_id),
     ancestry as (SELECT distinct * from ancestor),
     aggregated as (
         select root_id, level, case when count(DISTINCT node) > 1 then max(node) + 1 else max(node) end as node, edge
         from ancestry
         group by root_id, level),
     rows as (
         select a1.level, a1.root_id, a1.edge || ifnull(a2.node, '') as row
         from aggregated a1 left outer join aggregated a2 on a1.root_id = a2.root_id and a1.level = a2.level + 1
         order by a1.root_id, a1.level desc
     )"""


class SmrWorld(World):
    """
    Class for managing all the data required by SMR. The smr world is an sqlite database containing the ontologies
    generated by owlready2 and all information needed by the SMR Addon to synchronize xmind files with the anki
    collection and manage the retrieval order.
    """
    CHILD_NAME = 'smrchild'
    PARENT_NAME = 'smrparent'

    def __init__(self):
        self.parent_storid = None
        self.parent_relation_name = None
        self.child_relation_name = None
        self.field_translator = None
        super().__init__()
        self.set_backend(filename=SMR_WORLD_PATH)
        self.graph.execute('PRAGMA foreign_keys = ON')
        self.save()

    @property
    def parent_storid(self) -> int:
        if not self._parent_storid:
            self.parent_storid = self.graph.execute(f"""
SELECT storid
FROM resources
WHERE iri LIKE '%{self.parent_relation_name}'""").fetchone()[0]
        return self._parent_storid

    @parent_storid.setter
    def parent_storid(self, value: int):
        self._parent_storid = value

    @property
    def parent_relation_name(self) -> str:
        if self._parent_relation_name is None:
            self.parent_relation_name = self.field_translator.relation_class_from_content(
                TopicContentDto(title=self.PARENT_NAME))
        return self._parent_relation_name

    @parent_relation_name.setter
    def parent_relation_name(self, value: str):
        self._parent_relation_name = value

    @property
    def child_relation_name(self) -> str:
        if self._child_relation_name is None:
            self.child_relation_name = self.field_translator.relation_class_from_content(
                TopicContentDto(title=self.CHILD_NAME))
        return self._child_relation_name

    @child_relation_name.setter
    def child_relation_name(self, value: str):
        self._child_relation_name = value

    @property
    def field_translator(self) -> FieldTranslator:
        if not self._field_translator:
            self.field_translator = FieldTranslator()
        return self._field_translator

    @field_translator.setter
    def field_translator(self, value: FieldTranslator):
        self._field_translator = value

    def set_up(self) -> None:
        """
        Sets up SMR's database architecture. Use this method once to set up the database for the first time.
        """
        sql_file: TextIO = open(os.path.join(ADDON_PATH, SQL_FILE_NAME), 'r')
        sql_code: List[str] = sql_file.read().split(';')
        sql_file.close()
        for statement in sql_code:
            self.graph.execute(statement)
        self.save()

    def add_ontology_lives_in_deck(self, ontology_base_iri: str, deck_id: int) -> None:
        """
        Registers a deck for an imported ontology
        :param ontology_base_iri: base_iri of the imported ontology
        :param deck_id: the id of the deck from anki (number in form of a string)
        """
        c = self.graph.execute("SELECT c FROM ontologies WHERE iri = '{}'".format(ontology_base_iri)).fetchone()[0]
        self.graph.execute("INSERT INTO ontology_lives_in_deck VALUES (?, ?)", (deck_id, c))

    def add_or_replace_xmind_files(self, entities: List[XmindFileDto]) -> None:
        """
        Adds an entry for an xmind file to the relation xmind_files, replaces it if an entry with the same path
        already exists
        :param entities: List of entries to be inserted into the xmind_files relation
        """
        self.graph.db.executemany("REPLACE INTO main.xmind_files VALUES (?, ?, ?, ?, ?)",
                                  (tuple(e) for e in entities))

    def add_xmind_sheets(self, entities: List[XmindSheetDto]) -> None:
        """
        Adds an entry for an xmind sheet to the relation xmind_sheets
        :param entities: List of entries to be inserted into the xmind_sheets relation
        """
        self.graph.db.executemany("INSERT INTO main.xmind_sheets VALUES (?, ?, ?, ?, ?)",
                                  (tuple(e) for e in entities))

    def add_or_replace_xmind_nodes(self, entities: List[XmindTopicDto]) -> None:
        """
        Adds entries for xmind nodes to the relation xmind_nodes, replaces them if entries with the same node ids
        already exist
        :param entities: List of entries for the xmind nodes relation
        """
        self.graph.db.executemany("REPLACE INTO main.xmind_nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (tuple(e) for e in entities))

    def add_or_replace_xmind_edges(self, entities: List[XmindTopicDto]) -> None:
        """
        Adds entries for xmind edges to the relation xmind_edges, replaces them if entries with the same edge ids
        already exist
        :param entities: List of entries for the xmind edges relation
        """
        self.graph.db.executemany("REPLACE INTO main.xmind_edges VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (tuple(e) for e in entities))

    def add_smr_triples(self, entities: List[SmrTripleDto]) -> None:
        """
        adds entries for triples of parent node, edge, and child node to the relation smr_triples
        :param entities: List of entries to add to the smr triples relation
        """
        self.graph.db.executemany("INSERT INTO main.smr_triples VALUES (?, ?, ?, ?)",
                                  (tuple(e) for e in entities))

    def add_xmind_media_to_anki_files(self, entities: List[XmindMediaToAnkiFilesDto]) -> None:
        """
        adds entries linking xmind file uris to anki file names to the relation xmind_media_to_anki_files
        :param entities: List containing the media to file entries to add to the relation
        """
        self.graph.db.executemany("INSERT INTO main.xmind_media_to_anki_files VALUES (?, ?) ON CONFLICT DO NOTHING",
                                  (tuple(e) for e in entities))

    def get_ontology_lives_in_deck(self) -> List[OntologyLivesInDeckDto]:
        """
        Gets all entries for ontologies and decks in the smr world
        :return: a list of OntologyLivesInDeckDto instances containing all entries of ontologies and decks
        """
        return [OntologyLivesInDeckDto(*row)
                for row in self.graph.execute("select * from ontology_lives_in_deck").fetchall()]

    def get_xmind_files_in_decks(self) -> Dict[int, List[XmindFileDto]]:
        """
        Gets all xmind file entries from the smr world with the deck in which they are located
        :return: a Dictionary where keys are the files' deck ids and values are Lists xmind file dtos that belong to
        the respective deck
        """
        xmind_files = [XmindFileDto(*row) for row in self.graph.execute("select * from xmind_files").fetchall()]
        files_in_decks = {}
        for xmind_file in xmind_files:
            try:
                files_in_decks[xmind_file.deck_id].append(xmind_file)
            except KeyError:
                files_in_decks[xmind_file.deck_id] = [xmind_file]
        return files_in_decks

    def get_xmind_sheets_in_file(self, file_directory: str, file_name: str) -> Dict[str, XmindSheetDto]:
        """
        Gets a list of all xmind sheets in the specified file
        :param file_directory: directory of the file to get the sheets of
        :param file_name: name of the file to get the sheets of
        :return: the sheets as a list of xmind sheet dtos
        """
        return {record.sheet_id: XmindSheetDto(*record) for record in self._get_records(
            f"SELECT * FROM xmind_sheets where file_directory = '{file_directory}' and file_name = '{file_name}'")}

    def get_changed_smr_notes(self, collection: Collection) -> Dict[str, Dict[str, Dict[str, Dict[str, Union[
        SmrNoteDto, Dict[str, Union[XmindTopicDto, Set[int]]], str, Dict[int, Union[TopicContentDto, Any]]]]]]]:
        """
        Gets all notes belonging to xmind files that were changed since the last smr synchronization
        :return: A hierarchical structure of dictionaries
        - on the first level, keys are xmind file paths
        - on the second level, keys are sheet names in the respective files
        - on the third level, keys are anki note_ids of the changed smr_notes and values are
           - an Smr Note Dto for changing the smr notes relation
           - an xmind node dto for changing the smind edges relation
        - on the fourth level, keys are order numbers of child nodes for the respective edge and values are Xmind
        node dtos for adjusting the xmind node relation
        """
        with AnkiCollectionAttachement(self, collection):
            data = self._get_records(f"""-- noinspection SqlResolve
select xs.file_directory,
       xs.file_name || '.xmind' file_name,
       xs.name                  sheet_name,
       sn.note_id,
       sn.edge_id,
       cn.mod                   last_modified,
xe.sheet_id,
       xe.title                 edge_title,
       xe.image                 edge_image,
       xe.link                  edge_link,
xe.last_modified edge_last_modified,
xe.order_number edge_order_number,
       xcn.title                node_title,
       xcn.image                node_image,
       xcn.link                 node_link,
xcn.last_modified node_last_modified,
xcn.order_number node_order_number,
       xcn.node_id,
       xcn.order_number,
       st.parent_node_id,
       st2.edge_id              child_edge_id,
       st2.child_node_id,
       cn.flds                  note_fields
from smr_notes sn
         join anki_collection.notes cn on sn.note_id = cn.id
         join xmind_edges xe on sn.edge_id = xe.edge_id
         join xmind_sheets xs on xe.sheet_id = xs.sheet_id
         join smr_triples st on xe.edge_id = st.edge_id
         join xmind_nodes xcn on st.child_node_id = xcn.node_id
         left join smr_triples st2 on st2.parent_node_id = xcn.node_id
where sn.last_modified < cn.mod""")
        smr_notes_in_files = {}
        for record in data:
            file_path = os.path.join(record.file_directory, record.file_name)
            try:
                smr_notes_in_files[file_path][record.sheet_name][record.note_id]['answers'][
                    record.order_number]['children'][record.child_edge_id].append(record.child_node_id)
            except KeyError:
                child_node_ids = [record.child_node_id]
                children = {record.child_edge_id: child_node_ids} if record.child_edge_id else {}
                try:
                    if record.child_edge_id:
                        smr_notes_in_files[file_path][record.sheet_name][record.note_id]['answers'][
                            record.order_number]['children'][record.child_edge_id] = child_node_ids
                    else:
                        smr_notes_in_files[file_path][record.sheet_name][record.note_id]['answers'][
                            record.order_number]['children'] = children
                except KeyError:
                    node = {'node': XmindTopicDto(
                        node_id=record.node_id, sheet_id=record.sheet_id, title=record.node_title,
                        image=record.node_image, link=record.node_link,
                        last_modified=record.node_last_modified, order_number=record.node_order_number),
                        'children': children}
                    try:
                        smr_notes_in_files[file_path][record.sheet_name][record.note_id]['answers'][
                            record.order_number] = node
                    except KeyError:
                        edge = XmindTopicDto(
                            node_id=record.edge_id, sheet_id=record.sheet_id, title=record.edge_title,
                            image=record.edge_image, link=record.edge_link,
                            last_modified=record.edge_last_modified, order_number=record.edge_order_number)
                        smr_note = SmrNoteDto(*record[3:6])
                        edge_dict = {'note': smr_note, 'edge': edge, 'note_fields': record.note_fields,
                                     'answers': {record.order_number: node}, 'parents': set()}
                        try:
                            smr_notes_in_files[file_path][record.sheet_name][record.note_id] = edge_dict
                        except KeyError:
                            sheet_dict = {record.note_id: edge_dict}
                            try:
                                smr_notes_in_files[file_path][record.sheet_name] = sheet_dict
                            except KeyError:
                                smr_notes_in_files[file_path] = {record.sheet_name: sheet_dict}
                finally:
                    smr_notes_in_files[file_path][record.sheet_name][record.note_id]['parents'].add(
                        record.parent_node_id)
        return smr_notes_in_files

    def _get_records(self, sql: str) -> List['Record']:
        """
        Executes the sql query and returns the results as a list of named tuples
        :param sql: The sql query to execute
        :return: The data as a list of named tuples where keys are column names and values are the query results
        """
        cursor = self.graph.execute(sql)
        Record = namedtuple('Record', next(zip(*cursor.description)))

        # noinspection PyUnusedLocal
        def record_factory(cur, row):
            # noinspection PyArgumentList
            return Record(*row)

        cursor.row_factory = record_factory
        data = cursor.fetchall()
        return data

    def update_smr_triples_card_ids(self, data: List[Tuple[int, int]], collection: Collection) -> None:
        """
        updates the card ids for all triples belonging to certain answers in smr notes
        :param data: List of tuples containing the note_id of the note the card belongs to and the order_number of
        the card with the card id to add to each triple
        :param collection: The collection that contains the cards whose ids to add
        """
        with AnkiCollectionAttachement(self, collection):
            self.graph.db.executemany("""with card_triples(edge_id, child_node_id, card_id) as (
    select smr_triples.edge_id, child_node_id, cards.id
    from smr_triples
             join smr_notes using (edge_id)
             join cards on smr_notes.note_id = cards.nid
             join xmind_nodes on smr_triples.child_node_id = xmind_nodes.node_id
    where smr_notes.note_id = ?
      and xmind_nodes.order_number = ?
      and ord = order_number - 1)
update smr_triples
set card_id = (select card_id from card_triples)
where edge_id = (select edge_id from card_triples)
  and child_node_id = (select child_node_id from card_triples)""", data)

    def add_or_replace_smr_notes(self, entities: List[SmrNoteDto]):
        """
        adds entries linking xmind edges to anki notes and saving the creation time in last_modified
        :param entities: smr note entries to add to the relation
        """
        self.graph.db.executemany("REPLACE INTO main.smr_notes VALUES (?, ?, ?)", (tuple(e) for e in entities))

    def get_smr_note_reference_fields(self, edge_ids: List[str]) -> Dict[str, str]:
        """
        gets the data for the reference fields from smr_world and replaces embedded media with the string (media)
        :param edge_ids: the xmind ids of the edges to to get the reference fields for
        :return: the reference fields' contents in a dictionary where the keys contain the edge_ids for which the
        reference field was retrieved and values contain the cleaned up reference fields
        """
        reference_data = self.graph.execute("""-- noinspection SqlResolveForFile
WITH ancestor AS (
    SELECT t1.parent_node_id,
           t1.edge_id AS root_id,
           0          AS level,
           {node_selection_clause}    AS node,
           ''         as edge
    FROM smr_triples t1
             JOIN xmind_edges e ON t1.edge_id = e.edge_id
             JOIN xmind_nodes n ON t1.parent_node_id = n.node_id
    WHERE t1.edge_id in ({edge_ids})
    UNION ALL
    SELECT t.parent_node_id,
           a.root_id,
           a.level + 1,
           {node_selection_clause},
--            only this edge
           {edge_selection_clause}
    FROM smr_triples t
             JOIN ancestor a
                  ON a.parent_node_id = t.child_node_id
             JOIN xmind_edges e ON t.edge_id = e.edge_id
             JOIN xmind_nodes n ON t.parent_node_id = n.node_id),
     ancestry as (SELECT distinct * from ancestor),
     concatenated as (
         select root_id, level, group_concat(node, ', ') as node, edge
         from ancestry
         group by root_id, level),
     rows as (select c1.root_id, c1.level, case when c2.edge is null then '' else '<li>' end ||
       case
           when c2.edge is null or c2.edge = '' then ''
           else c2.edge || case c1.node when '' then '' else ': ' end end || c1.node ||
       case when c2.edge is null then '' else '</li>' end as row
     from concatenated c1
         left outer join concatenated c2 on c1.root_id = c2.root_id and c1.level = c2.level - 1
     order by c1.root_id, c1.level desc
)
select root_id, group_concat(row, '') from rows group by root_id""".format(
            edge_ids="'" + "', '".join(edge_ids) + "'",
            node_selection_clause=get_xmind_content_selection_clause('n'),
            edge_selection_clause=get_xmind_content_selection_clause('e'))).fetchall()
        return {row[0]: replace_embedded_media(row[1]) for row in reference_data}

    def get_smr_note_question_fields(self, edge_ids: List[str]) -> Dict[str, str]:
        """
        gets the content of smr notes' question fields for the specified edge ids
        :param edge_ids: the edge ids of the edges that represents the questions to get the content for
        :return: the textual content for the note question fields in a dictionary where keys are the edge ids and
        values are the question field contents
        """
        question_fields = self.graph.execute(f"""
SELECT DISTINCT edge_id, {get_xmind_content_selection_clause('xmind_edges')}
FROM xmind_edges
WHERE edge_id in ({"'" + "', '".join(edge_ids) + "'"})
        """).fetchall()
        return {row[0]: row[1] for row in question_fields}

    def get_smr_note_tags(self, anki_collection: Collection, edge_ids: List[str]) -> Dict[str, str]:
        """
        Gets tags for all provided edges that are compatible with the hierarchical tags addon. The tag is built from
        the deck to which notes are imported, the file name, and the xmind sheet to which the the note belongs,
        replacing spaces with underscores to produce valid tags
        :param anki_collection: the anki collection to get the deck name from
        :param edge_ids: the xmind edge ids to get the tags for
        :return: the tags in a dictionary where keys are the edge ids and values are the tags for the respective notes
        """
        with AnkiCollectionAttachement(smr_world=self, anki_collection=anki_collection):
            tags = self.graph.execute(f"""-- noinspection SqlResolveForFile
select xe.edge_id edge_id, ad.name || '::' || xf.file_name || '::' || xs.name tag
from xmind_edges xe
         join xmind_sheets xs on xe.sheet_id = xs.sheet_id
         join xmind_files xf on xs.file_directory = xf.directory and xs.file_name = xf.file_name
         join anki_collection.decks ad on xf.deck_id = ad.id
where edge_id in ({"'" + "', '".join(edge_ids) + "'"})""").fetchall()
            return {row[0]: " " + row[1].replace(" ", "_") + " " for row in tags}

    def get_smr_note_answer_fields(self, edge_ids: List[str]) -> Dict[str, List[str]]:
        """
        gets the contents of the answer fields of the smr notes belonging to the specified edge ids
        :param edge_ids: xmind id of the edge that belongs to the node to get the answer fields for
        :return: A dictionary where keys are the edges to which answer fields belong and values are the answer fields
        as a list of strings
        """
        answer_fields = self.graph.execute(f"""
SELECT DISTINCT t.edge_id, {get_xmind_content_selection_clause('n')}
FROM smr_triples t
         JOIN xmind_nodes n ON t.child_node_id = n.node_id
WHERE edge_id in ({"'" + "', '".join(edge_ids) + "'"})
ORDER BY t.edge_id, n.order_number""").fetchall()
        grouped_answer_fields = {}
        for row in answer_fields:
            try:
                grouped_answer_fields[row[0]].append(row[1])
            except KeyError:
                grouped_answer_fields[row[0]] = [row[1]]
        return grouped_answer_fields

    def get_smr_note_sort_fields(self, edge_ids: List[str]) -> Dict[str, str]:
        """
        gets the data for the sort fields of the smr notes belonging to the specified edges and
        converts it into the fields that are used to sort the smr notes belonging to a certain map
        :param edge_ids: xmind ids of the edges representing the notes to get the sort fields for
        :return: Dictionary where keys are the edge ids of the notes and values are the sort fields for each
        respective note
        """
        sort_id_cte_clause = get_sort_id_recursive_cte_clause(
            f"""t1.edge_id in ({"'" + "', '".join(edge_ids) + "'"})""")
        sort_data = self.graph.execute(f"""{sort_id_cte_clause}
select root_id, group_concat(row, '')
from rows
group by root_id""").fetchall()
        return {row[0]: ''.join(sort_id_from_order_number(int(c)) for c in row[1]) for row in sort_data}

    def get_xmind_uri_from_anki_file_name(self, anki_file_name: str) -> Optional[str]:
        """
        Gets the xmind_uri stored in the relation xmind_media_to_anki_files for the provided anki file name
        :param anki_file_name: the anki file name to get the xmind uri for
        :return: the xmind file uri, None if there is no entry for the file yet
        """
        try:
            return self.graph.execute("SELECT xmind_uri FROM xmind_media_to_anki_files WHERE anki_file_name = ?",
                                      (anki_file_name,)).fetchone()[0]
        except TypeError:
            return None

    def get_anki_file_name_from_xmind_uri(self, xmind_uri: str) -> Optional[str]:
        """
        Gets the anki file name stored in the relation xmind_media_to_anki_files for the provided xmind uri
        :param xmind_uri: the xmind uri to get the anki filename for
        :return: the anki file name
        """
        return self.graph.execute("SELECT anki_file_name FROM xmind_media_to_anki_files WHERE xmind_uri = ?",
                                  (xmind_uri,)).fetchone()[0]

    def attach_anki_collection(self, anki_collection: Collection):
        """
        Attaches an anki collection to the smr world for joint queries to both databases
        :param anki_collection: the anki collection to attach to the smr_world
        """
        anki_collection.close(save=True)
        self.graph.execute("ATTACH DATABASE ? as ?", (anki_collection.path, ANKI_COLLECTION_DB_NAME))

    def detach_anki_collection(self, anki_collection: Collection):
        """
        Detaches an anki collection from the smr world and reopens it
        :param anki_collection: the anki collection to detach
        """
        self.graph.commit()
        self.graph.execute("DETACH DATABASE ?", (ANKI_COLLECTION_DB_NAME,))
        anki_collection.reopen()

    def remove_xmind_media_to_anki_file(self, xmind_uri: str) -> None:
        """
        Removes an entry from the xmind_media_to_anki_files relation
        :param xmind_uri: the uri that identifies the entry to delete
        """
        self.graph.execute("DELETE FROM main.xmind_media_to_anki_files WHERE xmind_uri = ?", (xmind_uri,))

    def storid_from_node_id(self, node_id: str) -> int:
        """
        gets the storid of the concept associated with the provided xmind id
        :param node_id: the xmind id to get the storid for
        :return: the storid
        """
        return self.graph.execute("SELECT s FROM datas WHERE o = ?", (node_id,)).fetchone()[0]

    def storid_from_edge_id(self, edge_id: str) -> int:
        """
        gets the storid of the relation associated with the provided xmind edge id
        :param edge_id: the xmind id to get the storid for
        :return: the storid
        """
        return self.graph.execute(f"""
SELECT oj.o
from datas dt
         join objs oj on dt.s = oj.s
where dt.o = '{edge_id}'
  and oj.p = {ANNOTATED_PROPERTY_STORID}
  and not oj.o = {self.parent_storid}
limit 1""").fetchone()[0]

    def remove_xmind_nodes(self, xmind_nodes_2_remove: List[str]):
        """
        Removes all entries with the specified node ids from the relation xmind nodes
        :param xmind_nodes_2_remove: List of node ids of the nodes to remove
        """
        self.graph.execute(f"""DELETE FROM xmind_nodes WHERE node_id IN ('{"', '".join(xmind_nodes_2_remove)}')""")

    def generate_notes(self, col, edge_ids) -> Dict[str, ForeignNote]:
        """
        Creates Notes for the specified edge_ids from the data saved in the smr world and returns them in a
        dictionary where keys are edge ids
        :param col: the anki collection to get the deck names for the note tags from
        :param edge_ids: List of xmind edge ids to create the notes from
        :return A dictionary where keys are the edge_ids belonging to the notes and values are the foreign notes
        created from the edge ids
        """
        reference_fields = self.get_smr_note_reference_fields(edge_ids=edge_ids)
        question_fields = self.get_smr_note_question_fields(edge_ids)
        answer_fields_of_all_edges = self.get_smr_note_answer_fields(edge_ids)
        sort_fields = self.get_smr_note_sort_fields(edge_ids=edge_ids)
        tags = self.get_smr_note_tags(anki_collection=col, edge_ids=edge_ids)
        notes = {}
        for edge_id in edge_ids:
            note = ForeignNote()
            note_answer_fields = answer_fields_of_all_edges[edge_id]
            note.fields = [reference_fields[edge_id]] + [question_fields[edge_id]] + note_answer_fields + \
                          (X_MAX_ANSWERS - len(note_answer_fields)) * [''] + [sort_fields[edge_id]]
            note.tags.append(tags[edge_id])
            # add the edge id to the tags list to be able to assign the note to the right edge during import
            note.tags.append(edge_id)
            # note.deck = self.deck_id
            note.cards = {i: ForeignCard() for i, _ in enumerate(note_answer_fields, start=1)}
            note.fieldsStr = joinFields(note.fields)
            notes[edge_id] = note
        return notes

    def get_updated_child_smr_notes(self, edge_ids: List[str]) -> Dict[str, SmrNoteDto]:
        """
        For all edges following the specified edges, returns smr note dtos with last_modified set to the time at
        which the method is called
        :param edge_ids: the xmind edge ids to get the child notes for
        :return: a dictionary in which keys are edge ids of the retrieved notes and values are smr note dtos with
        updated last modified values
        """
        child_records = self._get_records(f"""
WITH successor AS (
    SELECT st.edge_id, st.child_node_id
    FROM smr_triples st
    WHERE st.edge_id in ('{"', '".join(edge_ids)}')
    UNION ALL
    SELECT st2.edge_id, st2.child_node_id
    FROM smr_triples st2
             JOIN successor sc ON sc.child_node_id = st2.parent_node_id)
select distinct sc.edge_id, sn.note_id from successor sc
natural join smr_notes sn""")
        return {record.edge_id: SmrNoteDto(note_id=record.note_id, edge_id=record.edge_id,
                                           last_modified=intTime()) for record in child_records}

    def get_note_ids_from_sheet_id(self, sheet_id: str) -> List[int]:
        """
        Gets all note ids that are associated to the sheet with the specified id
        :param sheet_id: the xmind sheet id of the sheet to get the note ids for
        :return: a list of all note ids associated to the sheet
        """
        return [r[0] for r in self.graph.execute("""
SELECT note_id
from smr_notes
join xmind_edges xe on smr_notes.edge_id = xe.edge_id
where sheet_id = ?""", (sheet_id,))]

    def get_nodes_2_remove_by_sheet(self, sheet_id: str) -> List['Node2Remove']:
        """
        Gets the data for removing all nodes in the sheet with the specified xmind sheet id, sorted descending on
        sort ids of edges so that leave nodes are positioned before center nodes and nodes can be deleted without
        having to consider their children
        :param sheet_id: xmind id of the sheet to get the nodes for
        :return: List of Dictionaries with all required data for xontology's function remove_node()
        """
        sort_id_cte_clause = get_sort_id_recursive_cte_clause(f"e.sheet_id = '{sheet_id}'")
        records = self._get_records(f"""{sort_id_cte_clause},
     sort_ids as (
         select root_id edge_id, group_concat(row, '') sort_id
         from rows
         group by root_id)
select st.parent_node_id, xe.edge_id, xe.title, xe.image, xe.link, st.child_node_id node_id
from sort_ids si
         join xmind_edges xe on si.edge_id = xe.edge_id
         join smr_triples st on xe.edge_id = st.edge_id
order by si.sort_id desc""")
        nodes_2_remove = []
        first_record = records.pop(0)
        node_2_remove = get_node_2_remove(first_record)
        for record in records:
            if record.node_id == node_2_remove['xmind_node'].node_id:
                node_2_remove['parent_node_ids'].append(record.parent_node_id)
            else:
                nodes_2_remove.append(node_2_remove)
                node_2_remove = get_node_2_remove(record)
        nodes_2_remove.append(node_2_remove)
        return nodes_2_remove

    def get_xmind_nodes_in_sheet(self, sheet_id: str) -> Dict[str, XmindTopicDto]:
        """
        Gets all nodes that belong to the sheet with the specified id
        :param sheet_id: xmind id of the sheet to get the nodes for
        :return: The nodes in a dictionary where keys are the nodes' xmind ids and values are
        """
        return {record.node_id: XmindTopicDto(*record) for record in self._get_records(f"""
SELECT * FROM xmind_nodes WHERE sheet_id = '{sheet_id}'""")}

    def get_root_node_id(self, sheet_id: str) -> str:
        """
        Gets the xmind node id of the root of the sheet with the specified xmind id
        :param sheet_id: xmind id of the sheet to get the root node id for
        :return: the xmind node id of the root node of the sheet with the specified id
        """
        return self.graph.execute(f"""
WITH seed AS (
    SELECT edge_id
    FROM xmind_edges
    WHERE sheet_id ='{sheet_id}'
    LIMIT 1
),
ancestor AS (
    SELECT t.parent_node_id, 0 as level
    FROM smr_triples t
    natural join seed
    UNION ALL
    SELECT t.parent_node_id, a.level + 1
    FROM smr_triples t
             JOIN ancestor a ON a.parent_node_id = t.child_node_id
)
SELECT parent_node_id FROM ancestor
ORDER BY level DESC
LIMIT 1""").fetchone()[0]


class AnkiCollectionAttachement:
    """
    Context Manager for queries that use joins with the anki collection
    """

    def __init__(self, smr_world: SmrWorld, anki_collection: Collection):
        self.world = smr_world
        self.collection = anki_collection

    def __enter__(self):
        self.world.attach_anki_collection(self.collection)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.world.detach_anki_collection(self.collection)


def sort_id_from_order_number(order_number: int) -> chr:
    """
    converts the specified order number into a character used for sorting the notes generated from an xmind map. The
    returned characters are handled by anki so that a character belonging to a larger order number is sorted after
    one belonging to a smaller order number.
    :param order_number: the number to convert into a character
    :return: the character for the sort field
    """
    return chr(order_number + 122)
