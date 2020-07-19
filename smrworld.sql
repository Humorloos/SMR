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
    path               TEXT PRIMARY KEY,
    map_last_modified  INTEGER,
    file_last_modified REAL,
    deck_id            INTEGER,
    FOREIGN KEY (deck_id) REFERENCES ontology_lives_in_deck (deck_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE xmind_sheets
(
    sheet_id      TEXT PRIMARY KEY,
    path          TEXT,
    last_modified INTEGER,
    FOREIGN KEY (path) REFERENCES xmind_files (path)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE xmind_edges
(
    edge_id       TEXT PRIMARY KEY,
    sheet_id      TEXT,
    title         TEXT,
    image         TEXT,
    link          TEXT,
    ontology_storid INTEGER,
    last_modified INTEGER,
    order_number  INTEGER,
    FOREIGN KEY (sheet_id) REFERENCES xmind_sheets (sheet_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (ontology_storid) references resources (storid)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE smr_notes
(
    note_id       TEXT PRIMARY KEY,
    edge_id       TEXT,
    last_modified TEXT,
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
    parent_node_id  TEXT,
    edge_id         TEXT,
    child_node_id   TEXT,
    card_id         INTEGER,
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
COMMIT;