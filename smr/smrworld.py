import os
from collections import namedtuple
from typing import List, TextIO, Tuple, Dict, Any, Union, Optional

from anki import Collection
from owlready2.namespace import World
from smr.consts import ADDON_PATH, USER_PATH
from smr.dto.nodecontentdto import NodeContentDto
from smr.dto.ontologylivesindeckdto import OntologyLivesInDeckDto
from smr.dto.smrnotedto import SmrNoteDto
from smr.dto.smrtripledto import SmrTripleDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindmediatoankifilesdto import XmindMediaToAnkiFilesDto
from smr.dto.xmindnodedto import XmindNodeDto
from smr.dto.xmindsheetdto import XmindSheetDto
from smr.utils import get_smr_model_id

FILE_NAME = 'smrworld.sqlite3'
SQL_FILE_NAME = 'smrworld.sql'
ANKI_COLLECTION_DB_NAME = "anki_collection"
SMR_WORLD_PATH = os.path.join(USER_PATH, FILE_NAME)


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
                         when {relation_name}.title is null then ''
                         else ' ' end ||
                     '<img src="' ||
                     (SELECT anki_file_name FROM xmind_media_to_anki_files WHERE xmind_uri = {relation_name}.image) ||
                     '">'
                end ||
            case
                when {relation_name}.link is null then ''
                else case
                         when {relation_name}.title is null and {relation_name}.image is null then ''
                         else ' ' end ||
                     '[sound:' ||
                     (SELECT anki_file_name FROM xmind_media_to_anki_files WHERE xmind_uri = {relation_name}.link) ||
                     ']'
                end"""


def get_xmind_hierarchy_recursive_cte_clause(edge_id: str):
    """
    gets a hierarchical recursive cte sql clause that can be used to access informations of a node's parents in a
    hierarchical manner.
    :param edge_id: the xmind id of the edge from where to start gathering parents' information
    :return: the cte clause
    """
    return f"""
WITH ancestor AS (
    SELECT parent_node_id,
           edge_id,
           child_node_id,
           0 level
    FROM smr_triples
    WHERE edge_id = '{edge_id}'
    UNION ALL
    SELECT t.parent_node_id,
           t.edge_id,
           t.child_node_id,
           a.level + 1
    FROM smr_triples t
             JOIN ancestor a
                  ON a.parent_node_id = t.child_node_id
)"""


class SmrWorld(World):
    """
    Class for managing all the data required by SMR. The smr world is an sqlite database containing the ontologies
    generated by owlready2 and all information needed by the SMR Addon to synchronize xmind files with the anki
    collection and manage the retrieval order.
    """

    def __init__(self):
        super().__init__()
        self.set_backend(filename=SMR_WORLD_PATH)
        self.graph.execute('PRAGMA foreign_keys = ON')
        self.save()

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

    def add_ontology_lives_in_deck(self, ontology_base_iri: str, deck_id: str) -> None:
        """
        Registers a deck for an imported ontology
        :param ontology_base_iri: base_iri of the imported ontology
        :param deck_id: the id of the deck from anki (number in form of a string)
        """
        c = self.graph.execute("SELECT c FROM ontologies WHERE iri = '{}'".format(ontology_base_iri)).fetchone()[0]
        self.graph.execute("INSERT INTO ontology_lives_in_deck VALUES (?, ?)", (int(deck_id), c))

    def add_xmind_files(self, entities: List[XmindFileDto]) -> None:
        """
        Adds an entry for an xmind file to the relation xmind_files
        :param entities: List of entries to be inserted into the xmind_files relation
        """
        self.graph.db.executemany("INSERT INTO main.xmind_files VALUES (?, ?, ?, ?, ?)",
                                  (tuple(e) for e in entities))

    def add_xmind_sheets(self, entities: List[XmindSheetDto]) -> None:
        """
        Adds an entry for an xmind sheet to the relation xmind_sheets
        :param entities: List of entries to be inserted into the xmind_sheets relation
        """
        self.graph.db.executemany("INSERT INTO main.xmind_sheets VALUES (?, ?, ?, ?, ?)",
                                  (tuple(e) for e in entities))

    def add_xmind_nodes(self, entities: List[XmindNodeDto]) -> None:
        """
        Adds entries for xmind nodes to the relation xmind_nodes
        :param entities: List of entries for the xmind nodes relation
        """
        self.graph.db.executemany("INSERT INTO main.xmind_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                  (tuple(e) for e in entities))

    def add_xmind_edges(self, entities: List[XmindNodeDto]) -> None:
        """
        Adds entries for xmind edges to the relation xmind_edges
        :param entities: List of entries for the xmind edges relation
        """
        self.graph.db.executemany("INSERT INTO main.xmind_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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

    def get_changed_smr_notes(self, collection: Collection) -> Dict[str, Dict[str, Dict[str, Dict[str, Union[
        SmrNoteDto, XmindNodeDto, str, Dict[int, Union[NodeContentDto, Any]]]]]]]:
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
            data = self._get_records(f"""
-- noinspection SqlResolve
select xs.file_directory,
       xs.file_name || '.xmind' file_name,
       xs.name                  sheet_name,
       sn.note_id,
       sn.edge_id,
       mod                      last_modified,
       xe.title                 edge_title,
       xe.image                 edge_image,
       xe.link                  edge_link,
       xn.title                 node_title,
       xn.image                 node_image,
       xn.link                  node_link,
       xn.node_id,
       xn.order_number,
       cn.flds                  note_fields
from smr_notes sn
         left join anki_collection.notes cn on sn.note_id = cn.id and
                                          sn.last_modified < cn.mod
         join xmind_edges xe on sn.edge_id = xe.edge_id
         join xmind_sheets xs on xe.sheet_id = xs.sheet_id
         join smr_triples st on xe.edge_id = st.edge_id
         join xmind_nodes xn on st.child_node_id = xn.node_id""")
        smr_notes_in_files = {}
        for record in data:
            file_path = os.path.join(record.file_directory, record.file_name)
            node = XmindNodeDto(image=record.node_image, link=record.node_link, title=record.node_title,
                                node_id=record.node_id)
            try:
                smr_notes_in_files[file_path][record.sheet_name][record.note_id]['answers'][
                    record.order_number] = node
            except KeyError:
                edge = XmindNodeDto(image=record.edge_image, link=record.edge_link, title=record.edge_title,
                                    node_id=record.edge_id)
                smr_note = SmrNoteDto(*record[3:6])
                edge_dict = {'note': smr_note, 'edge': edge, 'note_fields': record.note_fields,
                             'answers': {record.order_number: node}}
                try:
                    smr_notes_in_files[file_path][record.sheet_name][record.note_id] = edge_dict
                except KeyError:
                    sheet_dict = {record.note_id: edge_dict}
                    try:
                        smr_notes_in_files[file_path][record.sheet_name] = sheet_dict
                    except KeyError:
                        smr_notes_in_files[file_path] = {record.sheet_name: sheet_dict}
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

    def add_smr_notes(self, entities: List[SmrNoteDto]):
        """
        adds entries linking xmind edges to anki notes and saving the creation time in last_modified
        :param entities: smr note entries to add to the relation
        """
        self.graph.db.executemany("INSERT INTO main.smr_notes VALUES (?, ?, ?)", (tuple(e) for e in entities))

    def get_smr_note_references(self, edge_ids: List[str]) -> Dict[str, str]:
        """
        gets a dictionary of reference fields for the notes belonging to the specified xmind edge ids. the keys in
        the dictionary are the respective edge ids to which each reference field belongs
        :param edge_ids: ids of the edges up to which to get the reference
        :return: a dictionary in which keys are the provided edge ids and values are the respective reference fields
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
        return {row[0]: row[1] for row in reference_data}

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

    def get_smr_notes_sort_data(self, edge_ids: List[str]) -> Dict[str, str]:
        """
        gets the data for generating the sort field for the notds belonging to the specified edge ids
        :param edge_ids: list of xmind ids of the edges that belong to the notes to get the sort fields for
        :return: a dictionary where keys are the edge ids and values are the sort ids for the respective notes
        """
        sort_data = self.graph.execute(f"""-- noinspection SqlResolveForFile
WITH ancestor AS (
    SELECT t1.parent_node_id, t1.edge_id AS root_id, 0 AS level, n.order_number as node, e.order_number as edge
    FROM smr_triples t1
             JOIN xmind_edges e ON t1.edge_id = e.edge_id
             JOIN xmind_nodes n ON t1.parent_node_id = n.node_id
    WHERE t1.edge_id in ({"'" + "', '".join(edge_ids) + "'"})
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
     )
select root_id, group_concat(row, '')
from rows
group by root_id""").fetchall()
        return {row[0]: row[1] for row in sort_data}

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
