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
CREATE TRIGGER on_delete_files
    AFTER DELETE
    ON xmind_files
BEGIN
    DELETE
    FROM xmind_sheets
    WHERE xmind_sheets.file_directory = OLD.directory
      AND xmind_sheets.file_name = OLD.file_name;
END;
CREATE TRIGGER on_delete_sheets
    AFTER DELETE
    ON xmind_sheets
BEGIN
    DELETE FROM xmind_edges WHERE xmind_edges.sheet_id = OLD.sheet_id;
    DELETE FROM xmind_nodes WHERE xmind_nodes.sheet_id = OLD.sheet_id;
END;
-- Triggers for deleting object relations after removing/renaming nodes
CREATE TRIGGER collect_objs_and_triples_on_delete_nodes
    AFTER DELETE
    ON xmind_nodes
BEGIN
    DELETE
    FROM objs
    WHERE EXISTS(SELECT NULL
                 FROM smr_triples st
                          left outer join xmind_nodes pn on st.parent_node_id = pn.node_id
                          join xmind_edges e on st.edge_id = e.edge_id
                          left outer join xmind_nodes cn on st.child_node_id = cn.node_id
                 where (
--                  Remove parent node's child relation
                         st.child_node_id = old.node_id
                         and objs.s = pn.storid
                         and objs.p = e.storid
                         and objs.o = old.storid
                         and not EXISTS(SELECT NULL
                                        FROM smr_triples st2
                                                 join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                                 join xmind_edges e2 on st2.edge_id = e2.edge_id
                                                 join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                        WHERE cn2.storid = old.storid
                                          and e2.storid = e.storid
                                          and pn2.storid = pn.storid)
                     )
--                     Remove node's parent relation
                    or (
                         not EXISTS(SELECT NULL
                                    FROM smr_triples st2
                                             join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                             join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                    WHERE cn2.storid = old.storid
                                      and pn2.storid = pn.storid) and objs.s = old.storid and objs.p = 305 and
                         objs.o = pn.storid and
                         st.child_node_id = old.node_id
                     )
                    or (
--                  Remove node's child relation
                         not EXISTS(SELECT NULL
                                    FROM smr_triples st2
                                             join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                             join xmind_edges e2 on st2.edge_id = e2.edge_id
                                             join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                    WHERE pn2.storid = old.storid
                                      and e2.storid = e.storid
                                      and cn2.storid = cn.storid) and objs.s = old.storid and objs.p = e.storid and
                         objs.o = cn.storid and
                         st.parent_node_id = old.node_id
                     )
                    or (
--                         Remove child node's parent relation
                         not EXISTS(SELECT NULL
                                    FROM smr_triples st2
                                             join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                             join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                    WHERE pn2.storid = old.storid
                                      and cn2.storid = cn.storid) and objs.s = cn.storid and objs.p = 305 and
                         objs.o = old.storid and
                         st.parent_node_id = old.node_id
                     )
              );
    DELETE FROM smr_triples WHERE smr_triples.parent_node_id = OLD.node_id;
    DELETE FROM smr_triples WHERE smr_triples.child_node_id = OLD.node_id;
END;
CREATE TRIGGER collect_objs_on_rename_node
    AFTER UPDATE
    on xmind_nodes
    WHEN NEW.storid is NULL
BEGIN
    DELETE
    FROM objs
    WHERE EXISTS(SELECT NULL
                 FROM smr_triples st
                          join xmind_nodes pn on st.parent_node_id = pn.node_id
                          join xmind_edges e on st.edge_id = e.edge_id
                          join xmind_nodes cn on st.child_node_id = cn.node_id
                 where (
--                  Remove parent node's child relation
                         st.child_node_id = old.node_id
                         and objs.s = pn.storid
                         and objs.p = e.storid
                         and objs.o = old.storid
                         and not EXISTS(SELECT NULL
                                        FROM smr_triples st2
                                                 join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                                 join xmind_edges e2 on st2.edge_id = e2.edge_id
                                                 join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                        WHERE cn2.storid = old.storid
                                          and e2.storid = e.storid
                                          and pn2.storid = pn.storid)
                     )
--                     Remove node's parent relation
                    or (
                         st.child_node_id = old.node_id
                         and objs.s = old.storid
                         and objs.p = 305
                         and objs.o = pn.storid
                         and not EXISTS(SELECT NULL
                                        FROM smr_triples st2
                                                 join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                                 join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                        WHERE cn2.storid = old.storid
                                          and pn2.storid = pn.storid)
                     )
                    or (
--                  Remove node's child relation
                         not EXISTS(SELECT NULL
                                    FROM smr_triples st2
                                             join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                             join xmind_edges e2 on st2.edge_id = e2.edge_id
                                             join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                    WHERE pn2.storid = old.storid
                                      and e2.storid = e.storid
                                      and cn2.storid = cn.storid) and objs.s = old.storid and objs.p = e.storid and
                         objs.o = cn.storid and
                         st.parent_node_id = old.node_id
                     )
                    or (
--                         Remove child node's parent relation
                         st.parent_node_id = old.node_id
                         and objs.s = cn.storid
                         and objs.p = 305
                         and objs.o = old.storid
                         and not EXISTS(SELECT NULL
                                        FROM smr_triples st2
                                                 join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                                 join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                        WHERE pn2.storid = old.storid
                                          and cn2.storid = cn.storid)
                     )
              );
END;
-- Triggers for removing concepts after deleting/renaming nodes
CREATE TRIGGER collect_concepts_on_delete_nodes
    AFTER DELETE
    ON xmind_nodes
    WHEN not EXISTS(select NULL
                    from xmind_nodes
                    where storid = OLD.storid)
BEGIN
    DELETE FROM resources WHERE storid = OLD.storid;
    DELETE FROM objs WHERE s = OLD.storid;
END;
CREATE TRIGGER collect_concepts_on_rename_node
    AFTER UPDATE
    on xmind_nodes
    WHEN NEW.storid is null and not EXISTS(select NULL
                                           from xmind_nodes
                                           where storid = OLD.storid)
BEGIN
    DELETE FROM resources WHERE storid = OLD.storid;
    DELETE FROM objs WHERE s = OLD.storid;
END;
-- Triggers for removing object relations after removing / renaming edges
CREATE TRIGGER collect_objects_triples_and_notes_on_delete_edges
    AFTER DELETE
    ON xmind_edges
BEGIN
    DELETE
    FROM objs
    WHERE EXISTS(SELECT NULL
                 FROM smr_triples st
                          join xmind_nodes pn on st.parent_node_id = pn.node_id
                          left outer join xmind_edges e on st.edge_id = e.edge_id
                          join xmind_nodes cn on st.child_node_id = cn.node_id
                 where (
--                  Remove edge's child relation
                         st.edge_id = old.edge_id
                         and objs.s = pn.storid
                         and objs.p = old.storid
                         and objs.o = cn.storid
                         and not EXISTS(SELECT NULL
                                        FROM smr_triples st2
                                                 join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                                 join xmind_edges e2 on st2.edge_id = e2.edge_id
                                                 join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                        WHERE cn2.storid = cn.storid
                                          and e2.storid = old.storid
                                          and pn2.storid = pn.storid)
                     )
                    or (
--                  Remove edge's parent relation
                         st.edge_id = old.edge_id
                         and objs.s = cn.storid
                         and objs.p = 305
                         and objs.o = pn.storid
                         and not EXISTS(SELECT NULL
                                        FROM smr_triples st2
                                                 join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
--                                         inner join with edges is necessary to exclude triples with the removed edge
                                                 join xmind_edges e2 on st2.edge_id = e2.edge_id
                                                 join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                        WHERE cn2.storid = cn.storid
                                          and pn2.storid = pn.storid)
                     )
              );
    DELETE FROM smr_triples WHERE smr_triples.edge_id = OLD.edge_id;
    DELETE FROM smr_notes WHERE smr_notes.edge_id = OLD.edge_id;
END;
CREATE TRIGGER collect_objs_on_rename_edges
    AFTER UPDATE
    ON xmind_edges
    WHEN NEW.storid is null
BEGIN
    DELETE
    FROM objs
    WHERE EXISTS(SELECT NULL
                 FROM smr_triples st
                          join xmind_nodes pn on st.parent_node_id = pn.node_id
                          join xmind_edges e on st.edge_id = e.edge_id
                          join xmind_nodes cn on st.child_node_id = cn.node_id
                 where (
--                  Remove edge's child relation
                         st.edge_id = old.edge_id
                         and objs.s = pn.storid
                         and objs.p = old.storid
                         and objs.o = cn.storid
                         and not EXISTS(SELECT NULL
                                        FROM smr_triples st2
                                                 join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                                 join xmind_edges e2 on st2.edge_id = e2.edge_id
                                                 join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                        WHERE cn2.storid = cn.storid
                                          and e2.storid = old.storid
                                          and pn2.storid = pn.storid)
                     )
                    or (
--                  Remove edge's parent relation
                         st.edge_id = old.edge_id
                         and objs.s = cn.storid
                         and objs.p = 305
                         and objs.o = pn.storid
                         and not EXISTS(SELECT NULL
                                        FROM smr_triples st2
                                                 join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
--                                         inner join with edges is necessary to exclude triples with the removed edge
                                                 join xmind_edges e2 on st2.edge_id = e2.edge_id
                                                 join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                        WHERE cn2.storid = cn.storid
                                          and e2.storid is not null
                                          and pn2.storid = pn.storid)
                     )
              );
END;
-- Triggers for removing relationship properties after removing / renaming edges
CREATE TRIGGER collect_relations_on_delete_edges
    AFTER DELETE
    ON xmind_edges
    WHEN not EXISTS(select NULL
                    from xmind_edges
                    where storid = OLD.storid)
BEGIN
    DELETE FROM resources WHERE storid = OLD.storid;
    DELETE FROM objs WHERE s = OLD.storid;
END;
CREATE TRIGGER collect_relations_on_rename_edge
    AFTER UPDATE
    on xmind_edges
    WHEN NEW.storid is null and not EXISTS(
            select NULL
            from xmind_edges
            where storid = OLD.storid)
BEGIN
    DELETE FROM resources WHERE storid = OLD.storid;
    DELETE FROM objs WHERE s = OLD.storid;
END;
CREATE TRIGGER collect_objs_on_delete_triples
    BEFORE DELETE
    ON smr_triples
BEGIN
    DELETE
    FROM objs
    WHERE EXISTS(SELECT NULL
                 FROM smr_triples st
                          join xmind_nodes pn on st.parent_node_id = pn.node_id
                          join xmind_edges e on st.edge_id = e.edge_id
                          join xmind_nodes cn on st.child_node_id = cn.node_id
                 where st.child_node_id = old.child_node_id
                   and st.edge_id = old.edge_id
                   and st.parent_node_id = old.parent_node_id
                   and ((
--                  Remove parent node's child relation if necessary
                                objs.s = pn.storid
                                and objs.p = e.storid
                                and objs.o = cn.storid
                                and not EXISTS(SELECT NULL
                                               FROM smr_triples st2
                                                        join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                                        join xmind_edges e2 on st2.edge_id = e2.edge_id
                                                        join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                               WHERE cn2.storid = cn.storid
                                                 and e2.storid = e.storid
                                                 and pn2.storid = pn.storid
                                                 and not (st2.child_node_id = old.child_node_id
                                                   and st2.edge_id = old.edge_id
                                                   and st2.parent_node_id = old.parent_node_id))
                            )
--                     Remove child node's parent relation if necessary
                     or (
                                objs.s = cn.storid
                                and objs.p = 305
                                and objs.o = pn.storid
                                and not EXISTS(SELECT NULL
                                               FROM smr_triples st2
                                                        join xmind_nodes pn2 on st2.parent_node_id = pn2.node_id
                                                        join xmind_nodes cn2 on st2.child_node_id = cn2.node_id
                                               WHERE cn2.storid = cn.storid
                                                 and pn2.storid = pn.storid
                                                 and not (st2.child_node_id = old.child_node_id
                                                   and st2.edge_id = old.edge_id
                                                   and st2.parent_node_id = old.parent_node_id))
                            ))
              );
end;
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