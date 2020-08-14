BEGIN TRANSACTION;
CREATE TABLE ontology_lives_in_deck
(
    deck_id  INTEGER PRIMARY KEY,
    ontology INT,
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
    sheet_id      TEXT PRIMARY KEY,
    name          TEXT,
    file_directory TEXT,
    file_name     TEXT,
    last_modified INTEGER,
    FOREIGN KEY (file_directory, file_name) REFERENCES xmind_files (directory, file_name)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE xmind_media_to_anki_files
(
    xmind_uri      TEXT PRIMARY KEY,
    anki_file_name TEXT
);

CREATE TABLE xmind_edges
(
    edge_id         TEXT PRIMARY KEY,
    sheet_id        TEXT,
    title           TEXT,
    image           TEXT,
    link            TEXT,
    ontology_storid INTEGER,
    last_modified   INTEGER,
    order_number    INTEGER,
    FOREIGN KEY (sheet_id) REFERENCES xmind_sheets (sheet_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (image) REFERENCES xmind_media_to_anki_files (xmind_uri)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (link) REFERENCES xmind_media_to_anki_files (xmind_uri)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (ontology_storid) references resources (storid)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE smr_notes
(
    note_id       INTEGER PRIMARY KEY,
    edge_id       TEXT,
    last_modified INTEGER,
    FOREIGN KEY (edge_id) REFERENCES xmind_edges (edge_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE xmind_nodes
(
    node_id         TEXT PRIMARY KEY,
    sheet_id        TEXT,
    title           TEXT,
    image           TEXT,
    link            TEXT,
    ontology_storid INTEGER,
    last_modified   INTEGER,
    order_number    INTEGER,
    FOREIGN KEY (ontology_storid) references resources (storid)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (sheet_id) REFERENCES xmind_sheets (sheet_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE smr_triples
(
    parent_node_id TEXT,
    edge_id        TEXT,
    child_node_id  TEXT,
    card_id        INTEGER,
    PRIMARY KEY (parent_node_id, edge_id, child_node_id),
    FOREIGN KEY (parent_node_id) REFERENCES xmind_nodes (node_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (edge_id) REFERENCES xmind_edges (edge_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (child_node_id) REFERENCES xmind_nodes (node_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE INDEX smr_triples_parent_node_id
    ON smr_triples (parent_node_id);
CREATE INDEX smr_triples_edge_id
    ON smr_triples (edge_id);
CREATE INDEX smr_triples_child_node_id
    ON smr_triples (child_node_id);
CREATE INDEX smr_notes_edge_id
    ON smr_notes (edge_id);
CREATE INDEX xmind_nodes_order_number
    ON xmind_nodes (order_number);
COMMIT;