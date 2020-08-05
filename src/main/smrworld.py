import os
from typing import List, TextIO, Tuple, Optional

from bs4 import Tag

from anki import Collection
from main.consts import ADDON_PATH, USER_PATH
from main.dto.nodecontentdto import NodeContentDTO
from owlready2.namespace import World
from main.xmanager import XManager

FILE_NAME = 'smrworld.sqlite3'
SQL_FILE_NAME = 'smrworld.sql'
REFERENCE_FILE_NAME = 'reference.sql'
ANKI_COLLECTION_DB_NAME = "anki_collection"


def get_xmind_content_selection_clause(relation_name: str) -> str:
    """
    builds an sql select clause that returns title, image, and media in the correct format to be displayed in anki
    fields
    :param relation_name: the name of the relation in the smr world to get the content from
    :return: the select clause
    """
    return """
    ifnull({relation_name}.title, '') || IFNULL(' <img src="' || (
    SELECT anki_file_name FROM xmind_media_to_anki_files WHERE xmind_uri = {relation_name}.image) || '">', '') ||
                                      IFNULL(' [sound:' || (
                                          SELECT anki_file_name
                                          FROM xmind_media_to_anki_files
                                          WHERE xmind_uri = {relation_name}.link) || ']', '')
                                          """.format(relation_name=relation_name)


def get_xmind_hierarchy_recursive_cte_clause(edge_id: str):
    """
    gets a hierarchical recursive cte sql clause that can be used to access informations of a node's parents in a
    hierarchical manner.
    :param edge_id: the xmind id of the edge from where to start gathering parents' information
    :return: the cte clause
    """
    return """
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
)""".format(edge_id=edge_id)


class SmrWorld(World):
    """
    Class for managing all the data required by SMR. The smr world is an sqlite database containing the ontologies
    generated by owlready2 and all information needed by the SMR Addon to synchronize xmind files with the anki
    collection and manage the retrieval order.
    """

    def __init__(self):
        super().__init__()
        self.set_backend(filename=os.path.join(USER_PATH, FILE_NAME))
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

    def add_xmind_file(self, x_manager: XManager, deck_id: int) -> None:
        """
        Adds an entry for an xmind file to the relation xmind_files
        :param x_manager: the x_manager that manages the file
        :param deck_id: the id of the deck from anki (number in form of a string)
        """
        self.graph.execute("INSERT INTO main.xmind_files VALUES (?, ?, ?, ?)", (
            x_manager.get_file(), x_manager.get_map_last_modified(), x_manager.get_file_last_modified(), int(deck_id)))

    def add_xmind_sheet(self, x_manager: XManager, sheet_name: str) -> None:
        """
        Adds an entry for an xmind sheet to the relation xmind_sheets
        :param x_manager: the x_manager that manages the file
        :param sheet_name: the name of the sheet to import
        """
        self.graph.execute("INSERT INTO main.xmind_sheets VALUES (?, ?, ?)", (
            x_manager.get_sheet_id(sheet_name), x_manager.get_file(), x_manager.get_sheet_last_modified(sheet_name)))

    def add_xmind_node(self, node: Tag, node_content: NodeContentDTO, ontology_storid: int, sheet_id: str,
                       order_number: int) -> None:
        """
        Adds an entry for an xmind node to the relation xmind_nodes
        :param node: the tag representing the node to add
        :param node_content: the node's content as a dictionary
        :param ontology_storid: the storid of the concept in the ontology that represents the node
        :param sheet_id: xmind id of the sheet that contains the node
        :param order_number: order number of the node with respect to its siblings 
        """
        self.graph.execute(
            "INSERT INTO main.xmind_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                node['id'], sheet_id, node_content.title, node_content.image,
                node_content.media, ontology_storid, node['timestamp'], order_number))

    def add_xmind_edge(self, edge: Tag, edge_content: NodeContentDTO, sheet_id: str, order_number: int,
                       ontology_storid: int) -> None:
        """
        Adds an entry for an xmind edge to the relation xmind_edges
        :param edge: the tag representing the edge to add
        :param edge_content: the edge's content as a dictionary
        :param sheet_id: xmind id of the sheet that contains the edge
        :param order_number: order number of the edge with respect to its siblings
        :param ontology_storid: storid of the respective relation in the ontology
        """
        self.graph.execute("INSERT INTO main.xmind_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            edge['id'], sheet_id, edge_content.title, edge_content.image,
            edge_content.media, ontology_storid, edge['timestamp'], order_number))

    def add_smr_triple(self, parent_node_id: str, edge_id: str, child_node_id: str, card_id: Optional[int]) -> None:
        """
        adds an entry for a triple of parent node, edge, and child node to the relation smr_triples
        :param parent_node_id: the parent node's xmind id
        :param edge_id: the edge's xmind id
        :param child_node_id: the child node's xmind id
        :param card_id: anki's id for the card that corresponds to this triple
        """
        self.graph.execute("INSERT INTO main.smr_triples VALUES (?, ?, ?, ?)",
                           (parent_node_id, edge_id, child_node_id, card_id))

    def update_smr_triples_card_id(self, note_id: int, order_number: int, card_id: int) -> None:
        """
        updates the card id for all triples belonging to a certain answer in an smr note
        :param note_id: anki's id of the note to which the triple belongs
        :param order_number: order number of the child node in the triple (also indicates which answer the child node
        represents in the note
        :param card_id: anki's card id which is to be written to the smr triple
        """
        self.graph.execute("""WITH card_triples(edge_id, child_node_id) AS (
    SELECT smr_triples.edge_id, child_node_id
    FROM smr_triples
             JOIN smr_notes USING (edge_id)
             JOIN xmind_nodes ON smr_triples.child_node_id = xmind_nodes.node_id
    WHERE note_id = ?
      AND order_number = ?)
UPDATE smr_triples
SET card_id = ?
WHERE edge_id IN (SELECT edge_id FROM card_triples)
  AND child_node_id IN (SELECT child_node_id FROM card_triples);""", (note_id, order_number, card_id))

    def add_image_and_media_to_collection_and_self(self, content: NodeContentDTO, collection: Collection,
                                                   x_manager: XManager) -> None:
        """
        - If present, adds media and image specified in the content DTO to the specified anki collection and media
        folder
        - Adds an entry in the smr world linking the potentially new file name to the media attachment /
        hyperlink from the xmind map
        :param content: the content of the xmind node to add the image and media for
        :param collection: the anki collection to add the files to
        :param x_manager: the xmind manager instance that manages the xmind file from which to get the files
        """
        if content.media:
            # xmind 8 adds prefix attachments, xmind zen adds prefix resources
            if content.media.startswith(('attachments', 'resources')):
                new_media_name = collection.media.write_data(desired_fname=content.media,
                                                             data=x_manager.read_attachment(content.media))
            # if media file was not attached but only referenced via hyperlink
            else:
                new_media_name = collection.media.add_file(content.media)
            self.add_xmind_media_to_anki_file(xmind_uri=content.media, anki_file_name=new_media_name)
        if content.image:
            new_image_name = collection.media.write_data(desired_fname=content.image,
                                                         data=x_manager.read_attachment(content.image))
            self.add_xmind_media_to_anki_file(xmind_uri=content.image, anki_file_name=new_image_name)

    def add_xmind_media_to_anki_file(self, xmind_uri: str, anki_file_name: str):
        """
        adds an entry linking an xmind file uri to an anki file name to the relation xmind_media_to_anki_files
        :param xmind_uri: the uri the file is identified by in the xmind file (attachment or hyperlink)
        :param anki_file_name: the filename by which the file is identified in anki
        """
        self.graph.execute("INSERT INTO main.xmind_media_to_anki_files VALUES (?, ?)", (xmind_uri, anki_file_name))

    def add_smr_note(self, note_id: int, edge_id: str, last_modified: int):
        """
        adds an entry linking an xmind edge to an anki note and saving the creation time in last_modified
        :param note_id: the note's id from the anki collection
        :param edge_id: the edge's id from the xmind file
        :param last_modified: the time the note was created in epoch seconds
        """
        self.graph.execute("INSERT INTO main.smr_notes VALUES (?, ?, ?)", (note_id, edge_id, last_modified))

    def get_smr_note_reference_data(self, edge_id: str) -> List[Tuple[str, str]]:
        """
        gets the data needed to generate the reference for an smr note from the smr world. The returned data
        consists of a List of tuples. In each tuple, the first value is the field content of a node and the second
        value is the field content of the edge following the node. The list contains all tuples up to the edge with
        the provided id.
        :param edge_id: id of the edge up to which to get the reference
        :return: list of tuples containing the data to generate the reference for an smr note
        """
        return self.graph.execute("""
        {hierarchy_recursive_cte_clause}
    SELECT DISTINCT group_concat(DISTINCT {node_selection_clause}) AS node,
                    group_concat(DISTINCT {edge_selection_clause}) AS edge
    FROM ancestor a
             JOIN xmind_edges e ON a.edge_id = e.edge_id
             JOIN xmind_nodes n ON a.parent_node_id = n.node_id
    GROUP BY a.edge_id
    ORDER BY avg(a.level) DESC""".format(
            hierarchy_recursive_cte_clause=get_xmind_hierarchy_recursive_cte_clause(edge_id),
            node_selection_clause=get_xmind_content_selection_clause('n'),
            edge_selection_clause=get_xmind_content_selection_clause('e'))).fetchall()

    def get_smr_note_question_field(self, edge_id: str) -> str:
        """
        gets the content of an smr note's question field for the specified edge id
        :param edge_id: the edge id of the edge that represents the question to get the content for
        :return: the textual content for the note question field
        """
        return self.graph.execute("""
SELECT {edge_selection_clause}
FROM xmind_edges
WHERE edge_id = ?;
        """.format(edge_selection_clause=get_xmind_content_selection_clause('xmind_edges')), (edge_id,)).fetchone()[0]

    def get_smr_note_answer_fields(self, edge_id: str) -> List[str]:
        """
        gets the contents of the answer fields of the smr note belonging to the specified edge id
        :param edge_id: xmind id of the edge that belongs to the node to get the answer fields for
        :return: answer fields as a llist of strings
        """
        return [a[0] for a in self.graph.execute("""SELECT DISTINCT {node_selection_clause}
FROM smr_triples t
         JOIN xmind_nodes n ON t.child_node_id = n.node_id
WHERE edge_id = ?
ORDER BY n.order_number""".format(node_selection_clause=get_xmind_content_selection_clause('n')),
                                                 (edge_id,)).fetchall()]

    def get_smr_note_sort_data(self, edge_id: str) -> List[Tuple[int, int]]:
        """
        gets the data for generating the sort field for the notde belonging to the specified edge id
        :param edge_id: xmind id of the edge that belongs to the node to get the answer fields for
        :return: the data for generating the sort field IN a list of tuples
        """
        return self.graph.execute("""
        {hierarchy_recursive_cte_clause}
SELECT cast(count(DISTINCT n.order_number) > 1 AS INTEGER) + max(n.order_number), e.order_number
FROM ancestor a
         JOIN xmind_edges e ON a.edge_id = e.edge_id
         JOIN xmind_nodes n ON a.parent_node_id = n.node_id
GROUP BY a.edge_id
ORDER BY avg(a.level) DESC;""".format(hierarchy_recursive_cte_clause=get_xmind_hierarchy_recursive_cte_clause(
            edge_id))).fetchall()

    def attach_anki_collection(self, anki_collection):
        self.graph.execute("ATTACH DATABASE '{anki_collection_path}' as {anki_collection_db_name}".format(
            anki_collection_path=anki_collection.path, anki_collection_db_name=ANKI_COLLECTION_DB_NAME))
