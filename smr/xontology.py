import os
import types
from typing import List, Union, Dict

import owlready2
from owlready2 import ThingClass
from owlready2.namespace import Ontology
from owlready2.prop import destroy_entity, ObjectPropertyClass
from smr.consts import USER_PATH
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.fieldtranslator import FieldTranslator
from smr.smrworld import SmrWorld
from smr.xmindtopic import XmindNode


def get_question_sets(q_id_elements):
    # Sort triples by question id for Triples pertaining to the same
    # question to appear next to each other
    ascendingQId = sorted(q_id_elements, key=lambda t: t['q_id'])
    questionList = []

    # Initiate tripleList with first triple
    tripleList = [ascendingQId[0]]
    for x, t in enumerate(ascendingQId[0:-1], start=1):

        # Add the triple to the questionList if the next triple has a
        # different question id
        if t['q_id'] != ascendingQId[x]['q_id']:
            questionList.append(tripleList)
            tripleList = [ascendingQId[x]]

        # Add the triple to the tripleList if it pertains to the same
        # question as the next triple
        else:
            tripleList.append(ascendingQId[x])

    # Finally add the last triple_list to the question_list
    questionList.append(tripleList)
    return questionList


# def remove_question(question_elements, q_id):
#     answers = set(t['o'] for t in question_elements)
#     parents = set(t['s'] for t in question_elements)
#     remove_relations(answers=answers, parents=parents,
#                      question_triples=question_elements)
#     for answer in answers:
#         remove_concept(concept_storid=answer, q_id=q_id)


class XOntology(Ontology):

    def __init__(self, deck_id: int, smr_world: SmrWorld):
        self.smr_world = smr_world
        self.deck_id = deck_id
        self.field_translator = None
        self.base_iri = None
        Ontology.__init__(self, world=self.smr_world, base_iri=self.base_iri)
        # set up classes and register ontology only if the ontology has not been set up before
        try:
            next(self.classes())
        except StopIteration:
            self._set_up_classes()
            self.smr_world.add_ontology_lives_in_deck(ontology_base_iri=self.base_iri, deck_id=self.deck_id)

    @property
    def smr_world(self) -> SmrWorld:
        return self._smr_world

    @smr_world.setter
    def smr_world(self, value: SmrWorld):
        self._smr_world = value

    @property
    def deck_id(self) -> int:
        return self._deck_id

    @deck_id.setter
    def deck_id(self, value: int):
        self._deck_id = value

    @property
    def field_translator(self) -> FieldTranslator:
        if not self._field_translator:
            self.field_translator = FieldTranslator()
        return self._field_translator

    @field_translator.setter
    def field_translator(self, value: FieldTranslator):
        self._field_translator = value

    @property
    def base_iri(self) -> str:
        if self._base_iri is None:
            self.base_iri = os.path.join(USER_PATH, str(self.deck_id) + '#')
        return self._base_iri

    @base_iri.setter
    def base_iri(self, value: str):
        self._base_iri = value

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
        new_concept = self.add_concept_from_node(node_2_add)
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
        current_parents = getattr(child_concept, self.smr_world.parent_relation_name)
        new_parents = current_parents + [parent_concept]
        setattr(child_concept, self.smr_world.parent_relation_name, new_parents)
        self.XmindId[child_concept, getattr(self, self.smr_world.parent_relation_name), parent_concept].append(edge_id)

    def add_concept_from_node(self, node: XmindTopicDto):
        """
        Adds a new concept to the ontology and returns it
        :param node: the node dto to create the concept from
        :return: the concept
        """
        # Some concept names (e.g. 'are') can lead to errors, so catch them
        try:
            concept = self.Concept(self.field_translator.class_from_content(node.content))
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
                relationship_property = types.new_class(relationship_class_name, (owlready2.ObjectProperty,))
                relationship_property.domain = [self.Concept]
                relationship_property.range = [self.Concept]

    def remove_node(self, parent_node_ids: List[str], xmind_edge: XmindTopicDto, xmind_node: XmindTopicDto,
                    children: Dict[str, List[str]]):
        """
        Removes the node's xmind id from the respective concept
         - if there are more nodes left belonging to the concept, removes the relations between parent and child
         nodes and specified node
         - if there are no more nodes left belonging to the concept, destroys the concept
        :param parent_node_ids: list of node ids belonging to the parent nodes of the edge preceding the node to remove
        :param xmind_node: xmind node dto belonging to the node to be deleted
        :param xmind_edge: xmind node dto belonging to the parent edge of the node to be deleted
        :param children: dictionary where keys are edge_ids of edges following the node to remove and values are
        dictionaries containing the edge's storid and a list of storids belonging to the edge's child nodes
        parent nodes of the node to be deleted
        """
        concept = self.get_concept_from_node_id(xmind_node.node_id)
        currently_associated_ids = concept.XmindId
        currently_associated_ids.remove(xmind_node.node_id)
        if not currently_associated_ids:
            destroy_entity(concept)
        else:
            # remove the relations between the node and its parents and its children in case the concept itself is not
            # removed
            self.remove_relations(parents=[self.get_concept_from_node_id(i) for i in parent_node_ids],
                                  relation_name=self.field_translator.relation_class_from_content(xmind_edge.content),
                                  children=[concept], edge_id=xmind_edge.node_id)
            for edge_id, child_node_ids in children.items():
                child_concepts = [self.get_concept_from_node_id(i) for i in child_node_ids]
                self.remove_relations(parents=[concept], relation_name=self.get_relation_from_edge_id(edge_id).name,
                                      children=child_concepts, edge_id=edge_id)

    def rename_node(self, parent_node_ids: List[str], xmind_edge: XmindTopicDto, xmind_node: XmindTopicDto,
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
        parent_relation_name = self.get_relation_from_edge_id(xmind_edge.node_id).name
        child_relation_names = [self.get_relation_from_edge_id(i).name for i in children]
        self.remove_node(xmind_node=xmind_node, xmind_edge=xmind_edge, parent_node_ids=parent_node_ids,
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
                                       xmind_edge: XmindTopicDto):
        """
        - Changes a relation in the ontology by removing the old relation from parents and children and adding the new
        relation specified by new_question_field to them
        - Returns the newly assigned relationship property
        :param child_node_ids: ontology storids of the children to assign the new relation to
        :param parent_node_ids: xmind node ids of the parents to assign the new relation to
        :param xmind_edge: xmind topic dto containing id and content of the edge representing the new relation to be set
        :return the newly assigned relationship property
        """
        parents = [self.get_concept_from_node_id(node_id) for node_id in parent_node_ids]
        children = [self.get_concept_from_node_id(node_id) for node_id in child_node_ids]
        # Remove old relation
        self.remove_relations(parents=parents, relation_name=self.get_relation_from_edge_id(xmind_edge.node_id).name,
                              children=children, edge_id=xmind_edge.node_id)
        # Add new relation
        class_text = self.field_translator.relation_class_from_content(xmind_edge.content)
        self.add_relation(class_text)
        for parent_node_id in parent_node_ids:
            for child_node_id in child_node_ids:
                self.connect_concepts(
                    parent_node_id=parent_node_id, relationship_class_name=class_text, child_node_id=child_node_id,
                    edge_id=xmind_edge.node_id)

    def remove_relations(self, parents: List[ThingClass], relation_name: str, children: List[ThingClass],
                         edge_id: str):
        """
        For both the specified relation from parents to children and the parent relations from children to parents:
        - removes the edge_id from the relation triples
        - if there are no more edge_ids associated with the triple, removes the relation triple
        :param parents: List of subject concepts the relations refer to
        :param relation_name: name of the relations to remove
        :param children: List of object concepts the relations refer to
        :param edge_id: xmind id of the edge for which to remove the relations
        """
        for parent in parents:
            for child in children:
                # Remove edge from edge list for this relation
                relation_triples = self.XmindId[parent, getattr(self, relation_name), child]
                relation_triples.remove(edge_id)
                # If edge list has become empty, remove the relation
                if not relation_triples:
                    getattr(parent, relation_name).remove(child)
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
            if node['xmind_edge'].content.is_empty():
                node['xmind_edge'].title = self.smr_world.CHILD_NAME
            self.remove_node(parent_node_ids=node['parent_node_ids'],
                             xmind_edge=node['xmind_edge'], xmind_node=node['xmind_node'], children={})
        # finally, remove the root node which is not included in the output of nodes_2_remove and has no parent_node_ids
        self.remove_node(parent_node_ids=[], xmind_edge=XmindTopicDto(), xmind_node=XmindTopicDto(node_id=root_node_id),
                         children={})

    def _set_up_classes(self):
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
            types.new_class(self.smr_world.parent_relation_name, (owlready2.ObjectProperty,))

            types.new_class(self.smr_world.child_relation_name, (owlready2.ObjectProperty,))

            class XmindId(owlready2.AnnotationProperty):
                pass

    # def relation_from_triple(self, parent: ThingClass, relation_name: str, child: ThingClass):
    #     """
    #     Creates a new relation between the child and the parent with the
    #     given name and the attributes of the relation described in
    #     question_triple
    #     :param child: Object concept (answer)
    #     :param relation_name: Name of the relation to add (question name)
    #     :param parent: Subject concept (parent to question)
    #     """
    #     self.add_relation(
    #         child_thing=child, relationship_class_name=relation_name, parent_thing=parent,
    #         rel_dict=self.rel_dict_from_triple(question_triple=question_triple))

    # def get_answer_by_a_id(self, a_id, q_id):
    #     return self.search(Xid='*"' + q_id + '": {"src": "' + a_id + '*')[0]
    #
    # def get_all_parent_triples(self):
    #     return [t for t in self.get_triples() if t[1] == self.Parent.storid]
    #
    # def getChildQuestionIds(self, childElements):
    #     children = {'childQuestions': set(), 'bridges': list()}
    #     for elements in childElements:
    #         if elements['p'].name != 'Child':
    #             children['childQuestions'].add(self.get_trpl_x_id(elements))
    #         else:
    #             nextChildElements = self.get_child_elements(
    #                 elements['o'].storid)
    #             bridge = {'objectTitle': elements['s'].name}
    #             bridge.update(self.getChildQuestionIds(nextChildElements))
    #             children['bridges'].append(bridge)
    #     children['childQuestions'] = list(children['childQuestions'])
    #     return children
    #
    # def get_child_elements(self, s_storid):
    #     nextChildTriples = self.getChildTriples(s=s_storid)
    #     nextChildElements = [
    #         self.getElements(t) for t in nextChildTriples]
    #     return nextChildElements
    #
    # def getChildTriples(self, s):
    #     questionStorids = [p.storid for p in self.object_properties() if
    #                        p.name != 'Parent']
    #     return [t for t in self.get_triples(s=s) if t[1] in questionStorids]
    #
    # def getElements(self, triple):
    #     elements = [self.world._get_by_storid(s) for s in triple]
    #     return {'s': elements[0], 'p': elements[1], 'o': elements[2]}
    #
    # def getFiles(self, elements):
    #     files = [self.get_trpl_image(elements), self.get_trpl_media(elements)]
    #     return [None if not f else file_dict(
    #         identifier=f, doc=self.get_trpl_doc(elements)) for f in files]
    #
    # def get_inverse(self, x_id):
    #     triples = self.get_all_parent_triples()
    #     elements = [self.getElements(t) for t in triples]
    #     inverse_elements = [e for e in elements if
    #                         self.get_trpl_x_id(e) == x_id]
    #     return inverse_elements
    #
    # def getNoteTag(self, elements):
    #     return self.NoteTag[elements['s'], elements['p'], elements['o']][0]
    #
    # def getParentQuestionIds(self, parentElements):
    #     parents = {'parentQuestions': set(), 'bridges': list()}
    #     for elements in parentElements:
    #         # Add id of question to set if parent is a normal question
    #         if elements['p'].name != 'Child':
    #             parents['parentQuestions'].add(self.get_trpl_x_id(elements))
    #         # If parent is a bridge, add a dictionary titled by the answer
    #         # containing parents of the bridge
    #         else:
    #             nextParentTriples = self.getParentTriples(o=elements[
    #                 's'].storid)
    #             nextParentElements = [
    #                 self.getElements(t) for t in nextParentTriples]
    #             # Named dictionary is necessary to understand map structure
    #             # in case of bridges following bridges
    #             bridge = {'subjectTitle': elements['o'].name}
    #             bridge.update(self.getChildQuestionIds(nextParentElements))
    #             parents['bridges'].append(bridge)
    #     parents['parentQuestions'] = list(parents['parentQuestions'])
    #     return parents
    #
    # def get_question(self, x_id):
    #     # much faster:
    #     # with rels as (select s, objs.o as o, objs.p as p
    #     #               from datas
    #     #                        join objs using (s)
    #     #               where datas.o = '4lrqok8ac9hec8u2c2ul4mpo4k')
    #     # select source, property, target
    #     # from (select s, o as source
    #     #       from rels
    #     #       where p = (select storid
    #     #                  from resources
    #     #                  where iri like '%annotatedSource'))
    #     #          join (select s, o as property
    #     #                from rels
    #     #                         join resources on o = storid
    #     #                where p = (select storid
    #     #                           from resources
    #     #                           where iri like '%annotatedProperty')
    #     #                  /*Do not include parent relationships*/
    #     #                  and iri not like '%Parent') using (s)
    #     #          join (select s, o as target
    #     #                from rels
    #     #                where p = (select storid
    #     #                           from resources
    #     #                           where iri like '%annotatedTarget'
    #     #                )) using (s);
    #     triples = self.getNoteTriples()
    #     elements = [self.getElements(t) for t in triples]
    #     question_elements = [e for e in elements if
    #                          self.get_trpl_x_id(e) == x_id]
    #     return question_elements
    #
    # def getNoteData(self, questionList):
    #     question_elements = next(l['triple'] for l in questionList)
    #     q_id = self.get_trpl_x_id(question_elements)
    #     answers = set(l['triple']['o'] for l in questionList)
    #
    #     # Sort answers by answer index to get the answers' order right
    #     answers = sorted(answers, key=lambda d: self.get_trpl_a_index(
    #         next(t['triple'] for t in questionList if t['triple']['o'] == d)))
    #     answerDicts = [dict() for _ in range(X_MAX_ANSWERS)]
    #     images = []
    #     media = []
    #     for i, answerDict in enumerate(answerDicts[0:len(answers)]):
    #         answerDict['text'] = self.field_translator.field_from_class(
    #             answers[i].name)
    #         id_dict = json.loads(answers[i].Xid[0])
    #         answerDict['src'] = id_dict[q_id]['src']
    #         answerDict['crosslink'] = id_dict[q_id]['crosslink']
    #         if answers[i].Image:
    #             images.append(file_dict(identifier=answers[i].Image[0],
    #                                     doc=answers[i].Doc[0]))
    #         if answers[i].Media:
    #             media.append(file_dict(identifier=answers[i].Media[0],
    #                                    doc=answers[i].Doc[0]))
    #         childElements = self.get_child_elements(answers[i].storid)
    #         answerDict['children'] = self.getChildQuestionIds(childElements)
    #
    #     parents = list(set(t['triple']['s'] for t in questionList))
    #     parentDicts = []
    #     for parent in parents:
    #         parentDict = dict()
    #         parentDict['text'] = parent.name
    #         parentDict['id'] = parent.Xid[0]
    #         parentTriples = self.getParentTriples(o=parent.storid)
    #         parentElements = [self.getElements(t) for t in parentTriples]
    #         parentDict['parents'] = self.getParentQuestionIds(parentElements)
    #         parentDicts.append(parentDict)
    #
    #     files = self.getFiles(question_elements)
    #     if files[0]:
    #         images.append(files[0])
    #     if files[1]:
    #         media.append(files[1])
    #     return {
    #         'reference': self.get_trpl_ref(question_elements),
    #         'question': self.field_translator.field_from_class(
    #             question_elements['p'].name),
    #         'answers': answerDicts,
    #         'sortId': self.get_trpl_sort_id(question_elements),
    #         'document': self.get_trpl_doc(question_elements),
    #         'sheetId': self.get_trpl_sheet(question_elements),
    #         'questionId': q_id,
    #         'subjects': parentDicts,
    #         'images': images,
    #         'media': media,
    #         'tag': self.getNoteTag(question_elements)
    #     }
    #
    # def get_note_elements(self):
    #     return [self.getElements(t) for t in self.getNoteTriples()]
    #
    # def getNoteTriples(self):
    #     noNoteRels = ['Parent', 'Child']
    #     questionsStorids = [p.storid for p in self.object_properties() if
    #                         p.name not in noNoteRels]
    #     return [t for t in self.get_triples() if t[1] in questionsStorids]
    #
    # def getParentTriples(self, o):
    #     questionsStorids = [p.storid for p in self.object_properties() if
    #                         p.name != 'Parent']
    #     return [t for t in self.get_triples(o=o) if t[1] in questionsStorids]
    #
    # def get_trpl_a_index(self, elements):
    #     return self.AIndex[elements['s'], elements['p'], elements['o']][0]
    #
    # def get_trpl_doc(self, elements):
    #     return self.Doc[elements['s'], elements['p'], elements['o']][0]
    #
    # def get_trpl_image(self, elements):
    #     try:
    #         return self.Image[elements['s'], elements['p'], elements['o']][0]
    #     except IndexError:
    #         return ''
    #
    # def get_trpl_media(self, elements):
    #     try:
    #         return self.Media[elements['s'], elements['p'], elements['o']][0]
    #     except IndexError:
    #         return ''
    #
    # def get_trpl_ref(self, elements):
    #     return self.Reference[elements['s'], elements['p'], elements['o']][
    #         0]
    #
    # def get_trpl_sheet(self, elements):
    #     return self.Sheet[elements['s'], elements['p'], elements['o']][0]
    #
    # def get_trpl_sort_id(self, elements):
    #     return self.SortId[elements['s'], elements['p'], elements['o']][0]
    #
    # def get_trpl_x_id(self, elements):
    #     return self.Xid[elements['s'], elements['p'], elements['o']][0]
    #
    # def q_id_elements(self, elements):
    #     return {'triple': elements, 'q_id': self.get_trpl_x_id(elements)}
    #
    # def remove_answer(self, concept_storid: int, node_id: str):
    #     question_triples = self.get_question(q_id)
    #     parents = set(t['s'] for t in question_triples)
    #     answer = next(t['o'] for t in question_triples if
    #                   a_id == json.loads(t['o'].Xid[0])[q_id]['src'])
    #
    #     # Remove answer from question
    #     remove_relations(answers=[answer], parents=parents,
    #                      question_triples=question_triples)
    #
    #     remove_concept(concept_storid=answer, q_id=q_id)
    #
    # def remove_questions(self, q_ids):
    #     question_elements = {q: self.get_question(q) for q in q_ids}
    #     for q_id in question_elements:
    #         remove_question(question_elements=question_elements[q_id],
    #                         q_id=q_id)
    #     print()

    def set_trpl_a_index(self, a_id, q_id, a_index):
        q_trpls = self.get_question(q_id)
        a_concept = self.get_answer_by_a_id(a_id=a_id, q_id=q_id)
        a_trpls = [t for t in q_trpls if t['o'] == a_concept]
        for trpl in a_trpls:
            self.AIndex[trpl['s'], trpl['p'], trpl['o']] = a_index
