with ancestor as (
    SELECT parent_node_id,
           edge_id,
           child_node_id,
           0 level
    from smr_triples
    where edge_id = ?
    UNION ALL
    SELECT t.parent_node_id,
           t.edge_id,
           t.child_node_id,
           a.level + 1
    from smr_triples t
             JOIN ancestor a
                  on a.parent_node_id = t.child_node_id
)
select distinct group_concat(distinct ifnull(n.title, '') || IFNULL(' <img src="' || (
    SELECT anki_file_name from xmind_media_to_anki_files where xmind_uri = n.image) || '">', '') ||
                                      ifnull(' [sound:' || (
                                          SELECT anki_file_name
                                          from xmind_media_to_anki_files
                                          where xmind_uri = n.link) || ']', '')) as node,
                group_concat(distinct ifnull(e.title, '') || IFNULL(' <img src="' || (
                    SELECT anki_file_name from xmind_media_to_anki_files where xmind_uri = e.image) || '">', '') ||
                                      ifnull(' [sound:' || (
                                          SELECT anki_file_name
                                          from xmind_media_to_anki_files
                                          where xmind_uri = e.link) || ']', '')) as edge
from ancestor a
         join xmind_edges e on a.edge_id = e.edge_id
         join xmind_nodes n on a.parent_node_id = n.node_id
group by a.edge_id
order by avg(a.level) desc;