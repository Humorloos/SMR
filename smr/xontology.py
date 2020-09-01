import os
import types
from typing import List, Union, Dict, Optional, Set

import owlready2
from owlready2 import ThingClass
from owlready2.namespace import Ontology
from owlready2.prop import destroy_entity, ObjectPropertyClass
from smr.cachedproperty import cached_property
from smr.consts import USER_PATH
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.fieldtranslator import PARENT_RELATION_NAME, CHILD_RELATION_NAME, class_from_content, \
    relation_class_from_content
from smr.smrworld import SmrWorld


class XOntology(Ontology):

    def __init__(self, deck_id: int, smr_world: SmrWorld):
        self.smr_world = smr_world
        self.deck_id = deck_id
        Ontology.__init__(self, world=self.smr_world, base_iri=self.base_iri)
        # set up classes and register ontology only if the ontology has not been set up before
        try:
            next(self.classes())
        except StopIteration:
            self._set_up_classes()
            self.smr_world.add_ontology_lives_in_deck(ontology_base_iri=self.base_iri, deck_id=self.deck_id)

    @cached_property
    def base_iri(self) -> str:
        return os.path.join(USER_PATH, str(self.deck_id) + '#')

    @base_iri.setter
    def base_iri(self, value: str):
        self.__dict__['base_iri'] = value

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
        return self.get(self.smr_world.storid_from_node_id(xmind_id))

    def get_relation_from_edge_id(self, edge_id: str) -> ObjectPropertyClass:
        """
        Gets the relation associated with the specified edge id
        :param edge_id: the xmind edge id to get the relation for
        :return: the relation associated to the edge id
        """
        return self.get(self.smr_world.storid_from_edge_id(edge_id))

    def add_node(self, parent_node_ids: List[str], parent_edge: XmindTopicDto, relationship_class_name: str,
                 node_2_add: XmindTopicDto):
        """
        - If the concept for the node already exists, adds the node id to the concept's node ids, else creates the
        concept
        - Connects the concept to its parents with the specified edge's information
        :param parent_edge: xmind node dto of the edge preceding the node to add
        :param relationship_class_name: class name of the relationship with which to connect the new node
        :param node_2_add: xmind node dto of the node to add with already updated content
        :param parent_node_ids: xmind node ids of the parent nodes of the node to add
        """
        self.add_concept_from_node(node_2_add)
        for parent_node_id in parent_node_ids:
            self.connect_concepts(child_node_id=node_2_add.node_id, parent_node_id=parent_node_id,
                                  relationship_class_name=relationship_class_name, edge_id=parent_edge.node_id)

    def connect_concepts(self, parent_node_id: str, relationship_class_name: str,
                         edge_id: str, child_node_id: str) -> None:
        """
        - assigns the child concept to the parent concept with the specified relation
        - assigns the parent concept to the child concept with the relation 'Parent'
        :param child_node_id: the child concept in the relation
        :param parent_node_id: the parent concept in the relation
        :param relationship_class_name: the relation's class name
        :param edge_id: id of the xmind edge that belongs to the added relation
        """
        parent_concept = self.get_concept_from_node_id(parent_node_id)
        child_concept = self.get_concept_from_node_id(child_node_id)
        current_children = getattr(parent_concept, relationship_class_name)
        new_children = current_children + [child_concept]
        setattr(parent_concept, relationship_class_name, new_children)
        self.XmindId[parent_concept, getattr(self, relationship_class_name), child_concept].append(edge_id)
        current_parents = getattr(child_concept, PARENT_RELATION_NAME)
        new_parents = current_parents + [parent_concept]
        setattr(child_concept, PARENT_RELATION_NAME, new_parents)
        self.XmindId[child_concept, getattr(self, PARENT_RELATION_NAME), parent_concept].append(edge_id)

    def add_concept_from_node(self, node: XmindTopicDto):
        """
        Adds a new concept to the ontology and returns it
        :param node: the node dto to create the concept from
        :return: the concept
        """
        # Some concept names (e.g. 'are') can lead to errors, so catch them
        try:
            concept = self.Concept(class_from_content(node.content))
        except TypeError:
            raise NameError('Invalid concept name')
        concept.XmindId.append(node.node_id)

    def add_relation(self, relationship_class_name: str):
        """
        if the specified relation has not been created yet, creates it and returns it
        :param relationship_class_name: class text of the relationship property between parent and child concept
        :return: the created or acquired relationship property
        """
        relationship_property: ObjectPropertyClass = getattr(self, relationship_class_name)
        # add objectproperty if not yet in ontology
        if not relationship_property or not isinstance(relationship_property, ObjectPropertyClass):
            with self:
                # noinspection PyTypeChecker
                relationship_property = types.new_class(relationship_class_name, (owlready2.ObjectProperty,))
                relationship_property.domain = [self.Concept]
                relationship_property.range = [self.Concept]

    def remove_node(self, parent_node_ids: List[str], parent_edge_id: str, node_id: str,
                    children: Dict[str, List[str]]):
        """
        Removes the node's xmind id from the respective concept
         - if there are more nodes left belonging to the concept, removes the relations between parent and child
         nodes and specified node
         - if there are no more nodes left belonging to the concept, destroys the concept
        :param parent_node_ids: list of node ids belonging to the parent nodes of the edge preceding the node to remove
        :param node_id: xmind id of the node to delete
        :param parent_edge_id: xmind id of the node's parent edge
        :param children: dictionary where keys are edge_ids of edges following the node to remove and values are
        dictionaries containing the edge's node_ids and a list of node ids belonging to the edge's child nodes
        parent nodes of the node to be deleted (only necessary when removing a node in the middle of a map which is
        only necessary in case of renaming a node)
        """
        concept = self.get_concept_from_node_id(node_id)
        currently_associated_ids = concept.XmindId
        currently_associated_ids.remove(node_id)
        if not currently_associated_ids:
            destroy_entity(concept)
        else:
            # remove the relations between the node and its parents and its children in case the concept itself is not
            # removed
            self.remove_relations(parents=[self.get_concept_from_node_id(i) for i in parent_node_ids],
                                  children=[concept], edge_id=parent_edge_id)
            for child_edge_id, child_node_ids in children.items():
                child_concepts = [self.get_concept_from_node_id(i) for i in child_node_ids]
                self.remove_relations(parents=[concept], children=child_concepts, edge_id=child_edge_id)

    def rename_node(self, parent_node_ids: List[str], xmind_edge: Optional[XmindTopicDto], xmind_node: XmindTopicDto,
                    children: Dict[str, List[str]]) -> None:
        """
        changes the name of a node while retaining the relations to related concepts (children and parents)
        :param parent_node_ids: node ids of all nodes preceding the node to change
        :param xmind_node: the xmind node to rename, with already updated node content
        :param xmind_edge: the xmind edge preceding the node to rename
        :param children: dictionary where keys are edge_ids of edges following the node to change and values are
        lists of node ids belonging to the edge's child nodes
        """
        # get names of relations up front in case they are deleted together with the node
        if xmind_edge:
            parent_edge_id = xmind_edge.node_id
            parent_relation_name = self.get_relation_from_edge_id(parent_edge_id).name
        else:
            parent_edge_id = None
            parent_relation_name = None
        child_relation_names = [self.get_relation_from_edge_id(i).name for i in children]
        self.remove_node(parent_node_ids=parent_node_ids, parent_edge_id=parent_edge_id, node_id=xmind_node.node_id,
                         children=children)
        self.add_node(parent_edge=xmind_edge, relationship_class_name=parent_relation_name,
                      node_2_add=xmind_node, parent_node_ids=parent_node_ids)
        # connect concept to former children of removed node
        for (edge_id, child_node_ids), child_relation_name in zip(children.items(), child_relation_names):
            for child_node_id in child_node_ids:
                self.connect_concepts(
                    child_node_id=child_node_id, parent_node_id=xmind_node.node_id,
                    relationship_class_name=child_relation_name, edge_id=edge_id)

    def change_relationship_class_name(self, parent_node_ids: List[str], child_node_ids: List[str],
                                       xmind_edge: XmindTopicDto) -> None:
        """
        - Changes a relation in the ontology by removing the old relation from parents and children and adding the new
        relation from the specified xmind edge
        :param child_node_ids: ontology storids of the children to assign the new relation to
        :param parent_node_ids: xmind node ids of the parents to assign the new relation to
        :param xmind_edge: xmind topic dto containing id and content of the edge representing the new relation to be set
        """
        parents = [self.get_concept_from_node_id(node_id) for node_id in parent_node_ids]
        children = [self.get_concept_from_node_id(node_id) for node_id in child_node_ids]
        # Remove old relation
        self.remove_relations(parents=parents, children=children, edge_id=xmind_edge.node_id)
        # Add new relation
        class_text = relation_class_from_content(xmind_edge.content)
        self.add_relation(class_text)
        for parent_node_id in parent_node_ids:
            for child_node_id in child_node_ids:
                self.connect_concepts(
                    parent_node_id=parent_node_id, relationship_class_name=class_text, child_node_id=child_node_id,
                    edge_id=xmind_edge.node_id)

    def move_edge(self, old_parent_node_ids: List[str], new_parent_node_ids: List[str], edge_id: str,
                  child_node_ids: List[str]) -> None:
        """
        Moves a relation in the ontology by removing it at its old place and adding it at the new place
        :param old_parent_node_ids: xmind node ids of the relation's old parents
        :param new_parent_node_ids: xmind node ids of the relation's new parents
        :param edge_id: xmind node id of the edge representing the moved relation
        :param child_node_ids: xmind node ids of the relation's children
        :return:
        """
        relation_class_name = self.get_relation_from_edge_id(edge_id).name
        old_parents = [self.get_concept_from_node_id(i) for i in old_parent_node_ids]
        children = [self.get_concept_from_node_id(i) for i in child_node_ids]
        self.remove_relations(parents=old_parents, children=children, edge_id=edge_id)
        for parent_node_id in new_parent_node_ids:
            for child_node_id in child_node_ids:
                self.connect_concepts(parent_node_id=parent_node_id, relationship_class_name=relation_class_name,
                                      edge_id=edge_id, child_node_id=child_node_id)

    def move_node(self, old_parent_node_ids: Set[str], new_parent_node_ids: List[str], old_parent_edge_id: str,
                  new_parent_edge_id: str, node_id: str) -> None:
        """
        Moves a node in the ontology by removing it from its old parents and adding it to the new parents with the
        specified edge
        :param old_parent_node_ids: xmind node ids of the former parent nodes
        :param new_parent_node_ids: xmind node ids of the new parent nodes
        :param old_parent_edge_id: xmind edge id of the node's former parent edge
        :param new_parent_edge_id: xmind edge id of the node's new parent edge
        :param node_id: xmind id of the node to move
        :return:
        """
        relation_class_name = self.get_relation_from_edge_id(new_parent_edge_id).name
        self.remove_relations(parents=[self.get_concept_from_node_id(i) for i in old_parent_node_ids],
                              children=[self.get_concept_from_node_id(node_id)],
                              edge_id=old_parent_edge_id)
        for parent_node_id in new_parent_node_ids:
            self.connect_concepts(parent_node_id=parent_node_id, relationship_class_name=relation_class_name,
                                  edge_id=new_parent_edge_id, child_node_id=node_id)

    def remove_relations(self, parents: List[ThingClass], children: List[ThingClass],
                         edge_id: str) -> None:
        """
        For both the specified relation from parents to children and the parent relations from children to parents:
        - removes the edge_id from the relation triples
        - if there are no more edge_ids associated with the triple, removes the relation triple
        :param parents: List of subject concepts the relations refer to
        :param children: List of object concepts the relations refer to
        :param edge_id: xmind id of the edge for which to remove the relations
        """
        relation = self.get_relation_from_edge_id(edge_id)
        for parent in parents:
            for child in children:
                # Remove edge from edge list for this relation
                relation_triples = self.XmindId[parent, relation, child]
                relation_triples.remove(edge_id)
                # If edge list has become empty, remove the relation
                if not relation_triples:
                    getattr(parent, relation.name).remove(child)
                # Remove edge from edge list for parent relation
                parent_triples = self.XmindId[child, self.smrparent_xrelation, parent]
                parent_triples.remove(edge_id)
                # If edge list has become empty remove parent relation
                if not parent_triples:
                    child.smrparent_xrelation.remove(parent)

    def remove_sheet(self, sheet_id: str, root_node_id: str) -> None:
        """
        Removes all nodes and the relations associated to the nodes belonging to the specified sheet from the ontology
        :param sheet_id: the xmind id of the sheet to remove the nodes for
        :param root_node_id: the xmind node id of the root node of the sheet
        """
        # get all ids of nodes belonging to a sheet ordered by sort id so that leaves are positioned first,
        # together with parent edges (only ids and content) and parent node ids
        nodes_2_remove = self.smr_world.get_nodes_2_remove_by_sheet(sheet_id)
        # remove all nodes starting from leave nodes continuing towards the root
        for node in nodes_2_remove:
            self.remove_node(parent_node_ids=node['parent_node_ids'], parent_edge_id=node['parent_edge_id'],
                             node_id=node['node_id'], children={})
        # finally, remove the root node which is not included in the output of nodes_2_remove and has no parent_node_ids
        self.remove_node(parent_node_ids=[], parent_edge_id='', node_id=root_node_id, children={})

    def _set_up_classes(self) -> None:
        """
        Sets up all necessary classes and relationships for representing concept maps as ontologies.
        """
        with self:
            # every thing is a concept, the central concept of a concept map is a root
            class Concept(owlready2.Thing):
                pass

            class Root(Concept):
                pass

            # standard object properties
            types.new_class(PARENT_RELATION_NAME, (owlready2.ObjectProperty,))

            types.new_class(CHILD_RELATION_NAME, (owlready2.ObjectProperty,))

            class XmindId(owlready2.AnnotationProperty):
                pass
