BEGIN TRANSACTION;
CREATE TABLE ontology_lives_in_deck
(
    deck_id  INTEGER PRIMARY KEY,
    ontology INTEGER,
    FOREIGN KEY (ontology) REFERENCES ontologies (c)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE xmind_files
(
    directory          TEXT,
    file_name          TEXT,
    map_last_modified  INTEGER,
    file_last_modified REAL,
    deck_id            INTEGER,
    PRIMARY KEY (directory, file_name),
    FOREIGN KEY (deck_id) REFERENCES ontology_lives_in_deck (deck_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE xmind_sheets
(
    sheet_id       TEXT PRIMARY KEY,
    name           TEXT,
    file_directory TEXT,
    file_name      TEXT,
    last_modified  INTEGER,
    FOREIGN KEY (file_directory, file_name) REFERENCES xmind_files (directory, file_name)
        ON UPDATE CASCADE
);

CREATE TABLE xmind_media_to_anki_files
(
    xmind_uri      TEXT PRIMARY KEY,
    anki_file_name TEXT
);

CREATE TABLE xmind_edges
(
    edge_id      TEXT PRIMARY KEY,
    sheet_id     TEXT,
    title        TEXT,
    image        TEXT,
    link         TEXT,
    order_number INTEGER,
    storid       INTEGER,
    FOREIGN KEY (sheet_id) REFERENCES xmind_sheets (sheet_id)
        ON UPDATE CASCADE,
    FOREIGN KEY (image) REFERENCES xmind_media_to_anki_files (xmind_uri)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    FOREIGN KEY (link) REFERENCES xmind_media_to_anki_files (xmind_uri)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    FOREIGN KEY (storid) REFERENCES resources (storid)
        ON UPDATE CASCADE
);
CREATE TABLE xmind_nodes
(
    node_id      TEXT PRIMARY KEY,
    sheet_id     TEXT,
    title        TEXT,
    image        TEXT,
    link         TEXT,
    order_number INTEGER,
    storid       INTEGER,
    FOREIGN KEY (sheet_id) REFERENCES xmind_sheets (sheet_id)
        ON UPDATE CASCADE,
    FOREIGN KEY (image) REFERENCES xmind_media_to_anki_files (xmind_uri)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    FOREIGN KEY (link) REFERENCES xmind_media_to_anki_files (xmind_uri)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    FOREIGN KEY (storid) REFERENCES resources (storid)
        ON UPDATE CASCADE
);
CREATE TABLE smr_notes
(
    note_id       INTEGER PRIMARY KEY,
    edge_id       TEXT,
    last_modified INTEGER,
    FOREIGN KEY (edge_id) REFERENCES xmind_edges (edge_id)
        ON UPDATE CASCADE
);
CREATE TABLE smr_triples
(
    parent_node_id TEXT,
    edge_id        TEXT,
    child_node_id  TEXT,
    PRIMARY KEY (parent_node_id, edge_id, child_node_id),
    FOREIGN KEY (parent_node_id) REFERENCES xmind_nodes (node_id)
        ON UPDATE CASCADE,
    FOREIGN KEY (edge_id) REFERENCES xmind_edges (edge_id)
        ON UPDATE CASCADE,
    FOREIGN KEY (child_node_id) REFERENCES xmind_nodes (node_id)
        ON UPDATE CASCADE
);
CREATE VIEW onto_triples as
select st.parent_node_id,
       st.edge_id,
       st.child_node_id,
       pn.storid parent_storid,
       e.storid  edge_storid,
       cn.storid child_storid
from smr_triples st
         join xmind_nodes pn on st.parent_node_id = pn.node_id
         join xmind_edges e on st.edge_id = e.edge_id
         join xmind_nodes cn on st.child_node_id = cn.node_id;
CREATE TRIGGER on_delete_sheets
    AFTER DELETE
    ON xmind_sheets
BEGIN
    DELETE FROM xmind_edges WHERE xmind_edges.sheet_id = OLD.sheet_id;
    DELETE FROM xmind_nodes WHERE xmind_nodes.sheet_id = OLD.sheet_id;
END;
CREATE TRIGGER on_delete_files
    AFTER DELETE
    ON xmind_files
BEGIN
    DELETE
    FROM xmind_sheets
    WHERE xmind_sheets.file_directory = OLD.directory
      AND xmind_sheets.file_name = OLD.file_name;
END;
CREATE TRIGGER delete_triples_on_delete_nodes
    BEFORE DELETE
    ON xmind_nodes
BEGIN
    DELETE FROM smr_triples WHERE smr_triples.parent_node_id = OLD.node_id;
    DELETE FROM smr_triples WHERE smr_triples.child_node_id = OLD.node_id;
END;
CREATE TRIGGER delete_objs_on_delete_triples
    BEFORE DELETE
    ON smr_triples
BEGIN
    DELETE
    FROM objs
    WHERE (s, o) = (select (select storid from xmind_nodes where node_id = OLD.parent_node_id),
                           (select storid from xmind_nodes where node_id = OLD.child_node_id));
    DELETE
    FROM objs
    WHERE (s, o) = (select (select storid from xmind_nodes where node_id = OLD.child_node_id),
                           (select storid from xmind_nodes where node_id = OLD.parent_node_id));
END;
CREATE TRIGGER delete_concepts_on_delete_nodes
    AFTER DELETE
    ON xmind_nodes
    WHEN not EXISTS(select *
                    from xmind_nodes
                    where storid = OLD.storid)
BEGIN
    DELETE FROM resources WHERE storid = OLD.storid;
END;
CREATE TRIGGER on_delete_edges
    AFTER DELETE
    ON xmind_edges
BEGIN
    DELETE FROM smr_triples WHERE smr_triples.edge_id = OLD.edge_id;
    DELETE FROM smr_notes WHERE smr_notes.edge_id = OLD.edge_id;
END;
CREATE TRIGGER delete_relations_on_delete_edges
    AFTER DELETE
    ON xmind_edges
    WHEN not EXISTS(select *
                    from xmind_edges
                    where storid = OLD.storid)
BEGIN
    DELETE FROM resources WHERE storid = OLD.storid;
END;
CREATE INDEX smr_triples_parent_node_id
    ON smr_triples (parent_node_id);
CREATE INDEX smr_triples_edge_id
    ON smr_triples (edge_id);
CREATE INDEX smr_triples_child_node_id
    ON smr_triples (child_node_id);
CREATE INDEX smr_notes_edge_id
    ON smr_notes (edge_id);
CREATE INDEX smr_notes_last_modified
    ON smr_notes (last_modified);
CREATE INDEX xmind_nodes_order_number
    ON xmind_nodes (order_number);
CREATE INDEX xmind_edges_sheet_id
    ON xmind_edges (sheet_id);
CREATE INDEX xmind_media_to_anki_files_anki_file_name
    ON xmind_media_to_anki_files (anki_file_name);
CREATE INDEX datas_o
    ON datas (o);
COMMIT;