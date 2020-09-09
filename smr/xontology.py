import os
import types
from typing import List, Union, Dict, Optional, Set

import owlready2
from owlready2 import ThingClass
from owlready2.namespace import Ontology, weakref, _clear_cache
from owlready2.prop import destroy_entity, ObjectPropertyClass
from smr.cachedproperty import cached_property
from smr.consts import USER_PATH
from smr.dto.smrtripledto import SmrTripleDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.fieldtranslator import PARENT_RELATION_NAME, CHILD_RELATION_NAME, class_from_content, \
    relation_class_from_content
from smr.smrworld import SmrWorld


class XOntology(Ontology):

    def __init__(self, deck_id: int, smr_world: SmrWorld):
        self.deck_id = deck_id
        Ontology.__init__(self, world=smr_world, base_iri=self.base_iri)
        # set up classes and register ontology only if the ontology has not been set up before
        try:
            next(self.classes())
        except StopIteration:
            self._set_up_classes()
            self.world.add_ontology_lives_in_deck(ontology_base_iri=self.base_iri, deck_id=self.deck_id)

    @cached_property
    def base_iri(self) -> str:
        return os.path.join(USER_PATH, str(self.deck_id) + '#')

    @base_iri.setter
    def base_iri(self, value: str):
        self.__dict__['base_iri'] = value

    @cached_property
    def world(self) -> Optional[SmrWorld]:
        return None

    @world.setter
    def world(self, value: SmrWorld):
        self.__dict__['world'] = value

    def get(self, storid: int) -> Union[ObjectPropertyClass, ThingClass]:
        """
        Gets the relationship property or concept identified by the specified storid
        :param storid: The storid of the object to get
        :return: The relationship property or Concept identified by the specified storid
        """
        # noinspection PyProtectedMember
        return self.world._get_by_storid(storid)

    def get_concept_from_node_id(self, xmind_id: str) -> ThingClass:
        """
        Gets the concept associated with the specified xmind id
        :param xmind_id: the xmind id to get the concept for
        :return: the concept associated to the xmind id
        """
        return self.get(self.world.storid_from_node_id(xmind_id))

    def reload(self) -> None:
        """
        Reloads the ontology from the smr world
        """
        self._destroy_cached_entities()
        self.world.reload()

    def get_relation_from_edge_id(self, edge_id: str) -> ObjectPropertyClass:
        """
        Gets the relation associated with the specified edge id
        :param edge_id: the xmind edge id to get the relation for
        :return: the relation associated to the edge id
        """
        return self.get(self.world.storid_from_edge_id(edge_id))

    def connect_concepts(self, parent_storid: int, child_storid: int, relation_storid: Optional[int] = None,
                         relation_class_name: Optional[str] = None) -> None:
        """
        - assigns the child concept to the parent concept with the specified relation
        - assigns the parent concept to the child concept with the relation 'Parent'
        :param child_storid: storid of the child concept in the relation
        :param parent_storid: storid of the parent concept in the relation
        :param relation_storid: storid of the relation with which to connect the concepts, alternative to
        relation_class_name
        :param relation_class_name: the name of the relation to connect the concepts with, alternative to
        relation_storid
        """
        parent_concept = self.get(parent_storid)
        child_concept = self.get(child_storid)
        if relation_class_name is None:
            relation_class_name = self.get(relation_storid).name
        current_children = getattr(parent_concept, relation_class_name)
        new_children = current_children + [child_concept]
        setattr(parent_concept, relation_class_name, new_children)
        current_parents = getattr(child_concept, PARENT_RELATION_NAME)
        new_parents = current_parents + [parent_concept]
        setattr(child_concept, PARENT_RELATION_NAME, new_parents)

    def add_concepts_from_nodes(self, nodes: List[XmindTopicDto]):
        """
        Adds a new concept to the ontology if necessary and adds / updates the related nodes in the smr world
        :param nodes: the node dto to create the concept from
        :return: the concept's storid
        """
        for node in nodes:
            # Some concept names (e.g. 'are') can lead to errors, so catch them
            try:
                concept = self.Concept(class_from_content(node.content))
            except TypeError as error_info:
                raise NameError('Invalid concept name')
            node.storid = concept.storid
        self.world.add_or_replace_xmind_nodes(nodes)

    def add_relations_from_edges(self, edges: List[XmindTopicDto]) -> None:
        """
        For all edges, creates relationship properties if necessary, assigns the relations' storids to the edges and
        adds or replaces the edges in the smr world
        :param edges: Dictionary where keys are relationship class names and values are xmind topic dtos of the edges
        to add
        """
        for edge in edges:
            relation_class_name = relation_class_from_content(edge.content)
            relationship_property = getattr(self, relation_class_name)
            # add objectproperty if not yet in ontology
            if not relationship_property or not isinstance(relationship_property, ObjectPropertyClass):
                with self:
                    # noinspection PyTypeChecker
                    relationship_property = types.new_class(relation_class_name, (owlready2.ObjectProperty,))
                    relationship_property.domain = [self.Concept]
                    relationship_property.range = [self.Concept]
            edge.storid = relationship_property.storid
        self.world.add_or_replace_xmind_edges(edges)

    def rename_node(self, xmind_node: XmindTopicDto):
        """
        changes the name of a node while retaining the relations to related concepts (children and parents)
        :param xmind_node: the xmind node to rename, with already updated node content
        lists of node ids belonging to the edge's child nodes
        """
        self.disconnect_node(node_id=xmind_node.node_id)
        self.add_concepts_from_nodes([xmind_node])
        storid_triples = self.world.get_storid_triples_surrounding_node(xmind_node.node_id)
        for triple in storid_triples:
            self.connect_concepts(parent_storid=triple.parent_storid, relation_storid=triple.relation_storid,
                                  child_storid=triple.child_storid)

    def rename_relation(self, edge: XmindTopicDto) -> None:
        """
        - Changes a relation in the ontology by removing the old relation from parents and children and adding the new
        relation from the specified xmind edge
        :param edge: xmind topic dto containing id and content of the edge representing the new relation to be set
        """
        # Remove old relation
        self.disconnect_edge(edge.node_id)
        self.add_relations_from_edges([edge])
        parent_storids, child_storids = self.world.get_edge_parent_and_child_storids(edge.node_id)
        # Add new relation
        for parent_storid in parent_storids:
            for child_storid in child_storids:
                self.connect_concepts(parent_storid=parent_storid, child_storid=child_storid,
                                      relation_class_name=relation_class_from_content(edge.content))

    def move_edges(self, edges_2_new_parents: Dict[str, Set[str]]) -> None:
        """
        Adds and removes records from the relation smr_triples so that the specified relations are moved from the old
        parent nodes to the new parent nodes
        Moves a relation in the ontology by removing it at its old place and adding it at the new place
        :param edges_2_new_parents:
        """
        edge_children = self.world.get_edge_id_2_child_node_ids_dict(set(edges_2_new_parents))
        # remove old triples
        self.world.remove_smr_triples_by_edge_ids([(e,) for e in edges_2_new_parents])
        self.reload()
        # add new triples
        new_triples = [SmrTripleDto(parent_node_id=parent_node_id, edge_id=edge_id, child_node_id=child_node_id)
                       for edge_id, parent_node_ids in edges_2_new_parents.items()
                       for parent_node_id in parent_node_ids
                       for child_node_id in edge_children[edge_id]]
        self.connect_triples(new_triples)

    def connect_triples(self, triples: List[SmrTripleDto]) -> None:
        """
        Connects the concepts in the provided triples in the ontology with the relations in the provided triples
        :param triples: triples to connect
        """
        self.world.add_smr_triples(triples)
        storid_dict = self.world.get_topic_id_2_storid_dict({i for triple in triples for i in tuple(triple)})
        for triple in triples:
            self.connect_concepts(parent_storid=storid_dict[triple.parent_node_id],
                                  relation_storid=storid_dict[triple.edge_id],
                                  child_storid=storid_dict[triple.child_node_id])

    def move_nodes(self, pairs: Dict[str, str]) -> None:
        """
        Adds and removes records from the relation smr_triples so that the specified nodes are moved from the old
        parent edge to the new parent edge
        Moves a node in the ontology by removing it from its old parents and adding it to the new parents with the
        specified edge
        :param pairs: Dictionary where keys are new parent edge ids and values are ids of nodes to move
        """
        edge_parents = self.world.get_edge_id_2_parent_node_ids_dict(set(pairs))
        # remove old triples
        self.world.remove_smr_triples_by_child_node_ids([(value,) for value in pairs.values()])
        self.reload()
        # add new triples
        new_triples = [SmrTripleDto(parent_node_id=parent_node_id, edge_id=edge_id, child_node_id=child_node_id) for
                       edge_id, child_node_id in pairs.items() for parent_node_id in edge_parents[edge_id]]
        self.connect_triples(new_triples)

    def disconnect_node(self, node_id: str) -> None:
        """
        Sets the storid of the node with the specified xmind node id to null which causes the triggers to remove all
        associated relations and the concept if it is not represented by any concepts anymore
        :param node_id: the xmind id of the node to disconnect
        """
        self.world.graph.execute(f"UPDATE xmind_nodes set storid = null where node_id = '{node_id}'")
        self.reload()

    def disconnect_node_concept(self, node_id: str) -> None:
        """
        Sets the storid of the node with the specified xmind node id to null which causes the triggers to remove all
        associated relations and the concept if it is not represented by any concepts anymore
        :param node_id: the xmind id of the node to disconnect
        """
        self.world.graph.execute(f"UPDATE xmind_nodes set storid = null where node_id = '{node_id}'")
        self.reload()

    def disconnect_edge(self, edge_id: str) -> None:
        """
        Sets the storid of the node with the specified xmind node id to null which causes the triggers to remove all
        associated relations and the relation if it is not represented by any edges anymore
        :param edge_id: the xmind id of the edge to disconnect
        """
        self.graph.execute(f"UPDATE xmind_edges set storid = null where edge_id = '{edge_id}'")
        self.reload()

    def remove_xmind_nodes(self, xmind_nodes_2_remove: List[str]):
        """
        Removes all entries with the specified node ids from the relation xmind nodes which causes the triggers to
        remove all associated relations and concepts if they are not represented by any nodes anymore
        :param xmind_nodes_2_remove: List of node ids of the nodes to remove
        """
        self.graph.execute(f"""DELETE FROM xmind_nodes WHERE node_id IN ('{"', '".join(xmind_nodes_2_remove)}')""")
        self.reload()

    def remove_xmind_edges(self, edge_ids: Set[str]):
        """
        Removes all entries with the specified edge ids from the relation xmind edges and via sqlite foreign key
        cascade also all smr notes and smr triples with the specified edge ids from the respective relations
        :param edge_ids: Set of edge ids of the edges to remove
        """
        self.graph.execute(f"""DELETE FROM xmind_edges WHERE edge_id IN ('{"', '".join(edge_ids)}')""")
        self.reload()

    def _set_up_classes(self) -> None:
        """
        Sets up all necessary classes and relationships for representing concept maps as ontologies.
        """
        with self:
            # every thing is a concept, the central concept of a concept map is a root
            class Concept(owlready2.Thing):
                pass

            # standard object properties
            types.new_class(PARENT_RELATION_NAME, (owlready2.ObjectProperty,))

            types.new_class(CHILD_RELATION_NAME, (owlready2.ObjectProperty,))
