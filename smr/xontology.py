import json
import os
import types
from typing import List, Union, Set

import owlready2
from smr.consts import X_MAX_ANSWERS, USER_PATH
from smr.dto.nodecontentdto import NodeContentDto
from smr.dto.xmindnodedto import XmindNodeDto
from smr.smrworld import SmrWorld
from owlready2 import ThingClass
from owlready2.namespace import Ontology
from owlready2.prop import destroy_entity, ObjectPropertyClass
from smr.utils import file_dict
from smr.xnotemanager import FieldTranslator, content_from_field


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


def remove_question(question_elements, q_id):
    answers = set(t['o'] for t in question_elements)
    parents = set(t['s'] for t in question_elements)
    remove_relations(answers=answers, parents=parents,
                     question_triples=question_elements)
    for answer in answers:
        remove_concept(concept_storid=answer, q_id=q_id)


class XOntology(Ontology):
    CHILD_CLASS_NAME = 'Child'

    def __init__(self, deck_id: int, smr_world: SmrWorld):
        self.smr_world = smr_world
        self.deck_id = deck_id
        self.field_translator = None
        # set base_iri eagerly because checking whether base iri is initiated via if not self._base_iri is not
        # possible for an ontology because _base_iri would be considered an Ontology object
        self.base_iri = os.path.join(USER_PATH, str(self.deck_id) + '#')
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
    def base_iri(self) -> str:
        return self._base_iri

    @base_iri.setter
    def base_iri(self, value: str):
        self._base_iri = value

    @property
    def field_translator(self) -> FieldTranslator:
        if not self._field_translator:
            self.field_translator = FieldTranslator()
        return self._field_translator

    @field_translator.setter
    def field_translator(self, value: FieldTranslator):
        self._field_translator = value

    def get(self, storid: int) -> Union[ObjectPropertyClass, ThingClass]:
        """
        Gets the relationship property or concept identified by the specified storid
        :param storid: The storid of the object to get
        :return: The relationship property or Concept identified by the specified storid
        """
        # noinspection PyProtectedMember
        return self.world._get_by_storid(storid)

    def add_answer(self, a_id, answer_field, rel_dict, question_class, parents=None):
        """
        Adds an answer to a given question to the ontology
        :param parents: Set of parent concepts of the question for the answer
        :param a_id: Xmind id of the answer topic
        :param answer_field: Anki note field of the answer
        :param rel_dict: Relationship dictionary, as created by get_rel_dict()
        :param question_class: Class name of the question
        :return: The answer concept
        """
        answer_content = content_from_field(answer_field)
        answer_concept = self.concept_from_node_content(node_content=answer_content,
                                                        question_xmind_id=rel_dict['x_id'],
                                                        answer_xmind_id=a_id, file=rel_dict['doc'])
        if not parents:
            parents = set(q['s'] for q in self.get_question(rel_dict['x_id']))
        for parent in parents:
            self.add_relation(child_thing=answer_concept, relationship_class_name=question_class,
                              parent_thing=parent, rel_dict=rel_dict)
        return answer_concept

    def connect_concepts(self, child_thing: ThingClass, parent_thing: ThingClass, relationship_class_name: str,
                         edge_id: str) -> None:
        """
        - assigns the child concept to the parent concept with the specified relation
        - assigns the parent concept to the child concept with the relation 'Parent'
        :param child_thing: the child concept in the relation
        :param parent_thing: the parent concept in the relation
        :param relationship_class_name: the relation's class name
        :param edge_id: id of the xmind edge that belongs to the added relation
        """
        current_children = getattr(parent_thing, relationship_class_name)
        new_children = current_children + [child_thing]
        setattr(parent_thing, relationship_class_name, new_children)
        self.XmindId[parent_thing, getattr(self, relationship_class_name), child_thing].append(edge_id)
        current_parents = getattr(child_thing, 'Parent')
        new_parents = current_parents + [parent_thing]
        setattr(child_thing, 'Parent', new_parents)
        self.XmindId[child_thing, self.Parent, parent_thing].append(edge_id)

    def concept_from_node_content(self, node_content: NodeContentDto, node_id: str,
                                  node_is_root: bool = False) -> ThingClass:
        """
        Adds a new concept to the ontology and returns it
        :param node_content: node content DTO containing concept's title, image, and media.
        :param node_id: xmind id of the node for which to create the concept
        :param node_is_root: Whether the concept is the xmind file's root or not
        :return: the concept
        """
        if node_is_root:
            generate_concept: ThingClass = self.Root
        else:
            generate_concept: ThingClass = self.Concept
        # Some concept names (e.g. 'are') can lead to errors, so catch them
        try:
            concept: ThingClass = generate_concept(self.field_translator.class_from_content(node_content))
        except TypeError:
            raise NameError('Invalid concept name')
        concept.XmindId.append(node_id)
        return concept

    def add_relation(self, relationship_class_name: str) -> ObjectPropertyClass:
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
        return relationship_property

    def remove_node(self, xmind_node: XmindNodeDto, xmind_edge: XmindNodeDto, parent_concept_storids: List[int]):
        """
        Removes the node's xmind id from the respective concept
         - if there are more nodes left belonging to the concept, removes the relations between parent nodes and
         specified node
         - if there are no more nodes left belonging to the concept, destroys the concept
        :param xmind_node: xmind node dto belonging to the node to be deleted
        :param xmind_edge: xmind node dto belonging to the parent edge of the node to be deleted
        :param parent_concept_storids: list of storids belonging to the concepts belonging to the
        parent nodes of the node to be deleted
        """
        concept = self.get(xmind_node.ontology_storid)
        currently_associated_ids = concept.XmindId
        currently_associated_ids.remove(xmind_node.node_id)
        if not currently_associated_ids:
            destroy_entity(concept)
        else:
            # remove the relations between the node and it's parents in case the concept itself is not removed
            self.remove_relations(parents=[self.get(i) for i in parent_concept_storids],
                                  relation_name=self.field_translator.relation_class_from_content(xmind_edge.content),
                                  children=[concept], edge_id=xmind_edge.node_id)

    def change_answer(self, q_id, a_id, a_field):
        answer = self.get_answer_by_a_id(a_id=a_id, q_id=q_id)
        answer_triples = [t for t in self.get_question(q_id) if t['o'] ==
                          answer]
        q_id = next(self.get_trpl_x_id(t) for t in answer_triples)
        q_ref = next(self.get_trpl_ref(t) for t in answer_triples)
        questions_2_answer = [t for t in self.get_child_elements(
            answer.storid) if q_ref in self.get_trpl_ref(t)]
        objects_2_answer = [{
            'child': t['o'], 'rel_dict': self.rel_dict_from_triple(t),
            'class_text': t['p'].name} for t in questions_2_answer]
        question_class = answer_triples[0]['p'].name
        parents = set(t['s'] for t in answer_triples)
        rel_dict = self.rel_dict_from_triple(answer_triples[0])
        self.remove_node(q_id=q_id, a_id=a_id)

        new_answer = self.add_answer(
            parents=parents, a_id=a_id, answer_field=a_field,
            rel_dict=rel_dict, question_class=question_class)

        for o in objects_2_answer:
            self.add_relation(child_thing=o['child'], relationship_class_name=o['class_text'],
                              parent_thing=new_answer, rel_dict=o['rel_dict'])

    def change_relationship_class_name(self, parent_storids: List[int], relation_storid: int,
                                       child_storids: List[int], new_question_content: NodeContentDto,
                                       edge_id: str) -> ObjectPropertyClass:
        """
        - Changes a relation in the ontology by removing the old relation from parents and children and adding the new
        relation specified by new_question_field to them
        - Returns the newly assigned relationship property
        :param relation_storid: the ontology storid of the relationship property to
        :param child_storids: ontology storids of the children to assign the new relation to
        :param parent_storids: ontology storids of the parents to assign the new relation to
        :param new_question_content: Content dto of the question representing the new relation that is to be set
        :param edge_id: xmind id of the whose relationship name is to be changed
        :return the newly assigned relationship property
        """
        parents = [self.get(storid) for storid in parent_storids]
        children = [self.get(storid) for storid in child_storids]
        # Remove old relation
        self.remove_relations(parents=parents, relation_name=self.get(relation_storid).name, children=children,
                              edge_id=edge_id)
        # Add new relation
        class_text = self.field_translator.relation_class_from_content(new_question_content)
        new_relation = self.add_relation(class_text)
        for parent in parents:
            for child in children:
                self.connect_concepts(parent_thing=parent, relationship_class_name=class_text, child_thing=child,
                                      edge_id=edge_id)
        return new_relation

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
                parent_triples = self.XmindId[child, self.Parent, parent]
                parent_triples.remove(edge_id)
                # If edge list has become empty remove parent relation
                if not parent_triples:
                    child.Parent.remove(parent)

    def relation_from_triple(self, parent: ThingClass, relation_name: str, child: ThingClass):
        """
        Creates a new relation between the child and the parent with the
        given name and the attributes of the relation described in
        question_triple
        :param child: Object concept (answer)
        :param relation_name: Name of the relation to add (question name)
        :param parent: Subject concept (parent to question)
        """
        self.add_relation(
            child_thing=child, relationship_class_name=relation_name, parent_thing=parent,
            rel_dict=self.rel_dict_from_triple(question_triple=question_triple))

    def get_answer_by_a_id(self, a_id, q_id):
        return self.search(Xid='*"' + q_id + '": {"src": "' + a_id + '*')[0]

    def get_all_parent_triples(self):
        return [t for t in self.get_triples() if t[1] == self.Parent.storid]

    def getChildQuestionIds(self, childElements):
        children = {'childQuestions': set(), 'bridges': list()}
        for elements in childElements:
            if elements['p'].name != 'Child':
                children['childQuestions'].add(self.get_trpl_x_id(elements))
            else:
                nextChildElements = self.get_child_elements(
                    elements['o'].storid)
                bridge = {'objectTitle': elements['s'].name}
                bridge.update(self.getChildQuestionIds(nextChildElements))
                children['bridges'].append(bridge)
        children['childQuestions'] = list(children['childQuestions'])
        return children

    def get_child_elements(self, s_storid):
        nextChildTriples = self.getChildTriples(s=s_storid)
        nextChildElements = [
            self.getElements(t) for t in nextChildTriples]
        return nextChildElements

    def getChildTriples(self, s):
        questionStorids = [p.storid for p in self.object_properties() if
                           p.name != 'Parent']
        return [t for t in self.get_triples(s=s) if t[1] in questionStorids]

    def getElements(self, triple):
        elements = [self.world._get_by_storid(s) for s in triple]
        return {'s': elements[0], 'p': elements[1], 'o': elements[2]}

    def getFiles(self, elements):
        files = [self.get_trpl_image(elements), self.get_trpl_media(elements)]
        return [None if not f else file_dict(
            identifier=f, doc=self.get_trpl_doc(elements)) for f in files]

    def get_inverse(self, x_id):
        triples = self.get_all_parent_triples()
        elements = [self.getElements(t) for t in triples]
        inverse_elements = [e for e in elements if
                            self.get_trpl_x_id(e) == x_id]
        return inverse_elements

    def getNoteTag(self, elements):
        return self.NoteTag[elements['s'], elements['p'], elements['o']][0]

    def getParentQuestionIds(self, parentElements):
        parents = {'parentQuestions': set(), 'bridges': list()}
        for elements in parentElements:
            # Add id of question to set if parent is a normal question
            if elements['p'].name != 'Child':
                parents['parentQuestions'].add(self.get_trpl_x_id(elements))
            # If parent is a bridge, add a dictionary titled by the answer
            # containing parents of the bridge
            else:
                nextParentTriples = self.getParentTriples(o=elements[
                    's'].storid)
                nextParentElements = [
                    self.getElements(t) for t in nextParentTriples]
                # Named dictionary is necessary to understand map structure
                # in case of bridges following bridges
                bridge = {'subjectTitle': elements['o'].name}
                bridge.update(self.getChildQuestionIds(nextParentElements))
                parents['bridges'].append(bridge)
        parents['parentQuestions'] = list(parents['parentQuestions'])
        return parents

    def get_question(self, x_id):
        # much faster:
        # with rels as (select s, objs.o as o, objs.p as p
        #               from datas
        #                        join objs using (s)
        #               where datas.o = '4lrqok8ac9hec8u2c2ul4mpo4k')
        # select source, property, target
        # from (select s, o as source
        #       from rels
        #       where p = (select storid
        #                  from resources
        #                  where iri like '%annotatedSource'))
        #          join (select s, o as property
        #                from rels
        #                         join resources on o = storid
        #                where p = (select storid
        #                           from resources
        #                           where iri like '%annotatedProperty')
        #                  /*Do not include parent relationships*/
        #                  and iri not like '%Parent') using (s)
        #          join (select s, o as target
        #                from rels
        #                where p = (select storid
        #                           from resources
        #                           where iri like '%annotatedTarget'
        #                )) using (s);
        triples = self.getNoteTriples()
        elements = [self.getElements(t) for t in triples]
        question_elements = [e for e in elements if
                             self.get_trpl_x_id(e) == x_id]
        return question_elements

    def getNoteData(self, questionList):
        question_elements = next(l['triple'] for l in questionList)
        q_id = self.get_trpl_x_id(question_elements)
        answers = set(l['triple']['o'] for l in questionList)

        # Sort answers by answer index to get the answers' order right
        answers = sorted(answers, key=lambda d: self.get_trpl_a_index(
            next(t['triple'] for t in questionList if t['triple']['o'] == d)))
        answerDicts = [dict() for _ in range(X_MAX_ANSWERS)]
        images = []
        media = []
        for i, answerDict in enumerate(answerDicts[0:len(answers)]):
            answerDict['text'] = self.field_translator.field_from_class(
                answers[i].name)
            id_dict = json.loads(answers[i].Xid[0])
            answerDict['src'] = id_dict[q_id]['src']
            answerDict['crosslink'] = id_dict[q_id]['crosslink']
            if answers[i].Image:
                images.append(file_dict(identifier=answers[i].Image[0],
                                        doc=answers[i].Doc[0]))
            if answers[i].Media:
                media.append(file_dict(identifier=answers[i].Media[0],
                                       doc=answers[i].Doc[0]))
            childElements = self.get_child_elements(answers[i].storid)
            answerDict['children'] = self.getChildQuestionIds(childElements)

        parents = list(set(t['triple']['s'] for t in questionList))
        parentDicts = []
        for parent in parents:
            parentDict = dict()
            parentDict['text'] = parent.name
            parentDict['id'] = parent.Xid[0]
            parentTriples = self.getParentTriples(o=parent.storid)
            parentElements = [self.getElements(t) for t in parentTriples]
            parentDict['parents'] = self.getParentQuestionIds(parentElements)
            parentDicts.append(parentDict)

        files = self.getFiles(question_elements)
        if files[0]:
            images.append(files[0])
        if files[1]:
            media.append(files[1])
        return {
            'reference': self.get_trpl_ref(question_elements),
            'question': self.field_translator.field_from_class(
                question_elements['p'].name),
            'answers': answerDicts,
            'sortId': self.get_trpl_sort_id(question_elements),
            'document': self.get_trpl_doc(question_elements),
            'sheetId': self.get_trpl_sheet(question_elements),
            'questionId': q_id,
            'subjects': parentDicts,
            'images': images,
            'media': media,
            'tag': self.getNoteTag(question_elements)
        }

    def get_note_elements(self):
        return [self.getElements(t) for t in self.getNoteTriples()]

    def getNoteTriples(self):
        noNoteRels = ['Parent', 'Child']
        questionsStorids = [p.storid for p in self.object_properties() if
                            p.name not in noNoteRels]
        return [t for t in self.get_triples() if t[1] in questionsStorids]

    def getParentTriples(self, o):
        questionsStorids = [p.storid for p in self.object_properties() if
                            p.name != 'Parent']
        return [t for t in self.get_triples(o=o) if t[1] in questionsStorids]

    def get_sheet_elements(self, sheet_id):
        note_elements = self.get_note_elements()
        return [e for e in note_elements if self.get_trpl_sheet(e) == sheet_id]

    def get_trpl_a_index(self, elements):
        return self.AIndex[elements['s'], elements['p'], elements['o']][0]

    def get_trpl_doc(self, elements):
        return self.Doc[elements['s'], elements['p'], elements['o']][0]

    def get_trpl_image(self, elements):
        try:
            return self.Image[elements['s'], elements['p'], elements['o']][0]
        except IndexError:
            return ''

    def get_trpl_media(self, elements):
        try:
            return self.Media[elements['s'], elements['p'], elements['o']][0]
        except IndexError:
            return ''

    def get_trpl_ref(self, elements):
        return self.Reference[elements['s'], elements['p'], elements['o']][
            0]

    def get_trpl_sheet(self, elements):
        return self.Sheet[elements['s'], elements['p'], elements['o']][0]

    def get_trpl_sort_id(self, elements):
        return self.SortId[elements['s'], elements['p'], elements['o']][0]

    def get_trpl_x_id(self, elements):
        return self.Xid[elements['s'], elements['p'], elements['o']][0]

    def q_id_elements(self, elements):
        return {'triple': elements, 'q_id': self.get_trpl_x_id(elements)}

    def remove_answer(self, concept_storid: int, node_id: str):
        question_triples = self.get_question(q_id)
        parents = set(t['s'] for t in question_triples)
        answer = next(t['o'] for t in question_triples if
                      a_id == json.loads(t['o'].Xid[0])[q_id]['src'])

        # Remove answer from question
        remove_relations(answers=[answer], parents=parents,
                         question_triples=question_triples)

        remove_concept(concept_storid=answer, q_id=q_id)

    def remove_questions(self, q_ids):
        question_elements = {q: self.get_question(q) for q in q_ids}
        for q_id in question_elements:
            remove_question(question_elements=question_elements[q_id],
                            q_id=q_id)
        print()

    def remove_sheet(self, sheet_id):
        sheet_elements = self.get_sheet_elements(sheet_id)
        q_id_elements = [self.q_id_elements(e) for e in sheet_elements]

        # Sort questions in descending order by sort_id to first remove
        # questions whose answers are leaves and continue removing in
        # hierarchical order
        question_sets = sorted(
            get_question_sets(q_id_elements),
            key=lambda s: self.get_trpl_sort_id(s[0]['triple']),
            reverse=True)
        for question_set in question_sets:
            remove_question(
                question_elements=[s['triple'] for s in question_set],
                q_id=next(s['q_id'] for s in question_set))
        else:
            # Remove root
            remove_concept(
                concept_storid=question_sets[-1][0]['triple']['s'], q_id='root')

    def set_trpl_a_index(self, a_id, q_id, a_index):
        q_trpls = self.get_question(q_id)
        a_concept = self.get_answer_by_a_id(a_id=a_id, q_id=q_id)
        a_trpls = [t for t in q_trpls if t['o'] == a_concept]
        for trpl in a_trpls:
            self.AIndex[trpl['s'], trpl['p'], trpl['o']] = a_index

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
            class Parent(Concept >> Concept):
                pass

            class Child(Concept >> Concept):
                pass

            class XmindId(owlready2.AnnotationProperty):
                pass
