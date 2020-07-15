import json
import os
import types

import owlready2
from consts import X_MAX_ANSWERS, USER_PATH
from owlready2.namespace import Ontology
from owlready2.prop import destroy_entity
from utils import file_dict
from xnotemanager import FieldTranslator, content_from_field

from aqt import mw


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


def get_rel_dict(aIndex, image, media, x_id, ref, sortId, doc, sheet, tag):
    return {
        'aIndex': aIndex,
        'image': image,
        'media': media,
        'x_id': x_id,
        'ref': ref,
        'sortId': sortId,
        'doc': doc,
        'sheet': sheet,
        'tag': tag}


def remove_answer_concept(answer_concept, q_id):
    """
    Removes the answer's x_id from concept or destroy the concept if no
    x_ids are left
    :param answer_concept: Concept of the answer to remove
    :param q_id: Xmind ID of the question that belongs to this answer
    """
    id_dict = json.loads(answer_concept.Xid[0])
    del id_dict[q_id]
    if id_dict:
        answer_concept.Xid[0] = json.dumps(id_dict)
    else:
        destroy_entity(answer_concept)


def remove_question(question_elements, q_id):
    answers = set(t['o'] for t in question_elements)
    parents = set(t['s'] for t in question_elements)
    remove_relations(answers=answers, parents=parents,
                     question_triples=question_elements)
    for answer in answers:
        remove_answer_concept(answer_concept=answer, q_id=q_id)


def remove_relations(answers, parents, question_triples):
    """
    Removes relations from parents to answers
    :param answers: List of object concepts the relations refer to
    :param parents: List of subject concepts the relations refer to
    :param question_triples: List of concept triples that represent the
    relations to remove
    """
    question = question_triples[0]['p']

    # Remove old question for all parents
    for parent in parents:
        left_answers = [a for a in getattr(parent, question.name) if
                        a not in answers]
        setattr(parent, question.name, left_answers)

    # Remove old parents for all answers
    for answer in answers:
        left_parents = [p for p in answer.Parent if p not in parents]
        answer.Parent = left_parents


class XOntology(Ontology):
    def __init__(self, deck_id):
        base_iri = os.path.join(USER_PATH, str(deck_id) + '#')
        Ontology.__init__(self, world=mw.smr_world, base_iri=base_iri)
        # set up classes and register ontology only if the ontology has not been set up before
        try:
            next(self.classes())
        except StopIteration:
            self.set_up_classes()
            mw.smr_world.add_ontology_to_deck(ontology_base_iri=base_iri, deck_id=deck_id)
        self.field_translator = FieldTranslator()

    def add_answer(self, a_id, answer_field, rel_dict, question_class,
                   parents=None):
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
        answer_concept = self.add_concept(nodeContent=answer_content,
                                          q_id=rel_dict['x_id'],
                                          a_id=a_id, file=rel_dict['doc'])
        if not parents:
            parents = set(q['s'] for q in self.get_question(rel_dict['x_id']))
        for parent in parents:
            self.add_relation(child=answer_concept, class_text=question_class,
                              parent=parent, rel_dict=rel_dict)
        return answer_concept

    def add_concept(self, nodeContent, q_id, a_id, file, root=False,
                    crosslink=None):
        """
        Adds a new concept to the ontology
        :param nodeContent: Content dict containing concept's title, image, and
        media.
        :param a_id: Id attribute of the topic in the xmind file
        :param file: Path to the xmind file
        :param q_id: Id attribute of the question topic in the xmind file
        :param root: Whether the concept is the xmind file's root or not
        :param crosslink: If the note contains a crosslink
        :return: Answer Concept
        """
        if root:
            concept = self.Root(self.field_translator.class_from_content(nodeContent))
            q_id = 'root'
        else:
            # Some concept names (e.g. 'are') can lead to errors, catch
            # them
            try:
                concept = self.Concept(self.field_translator.class_from_content(
                    nodeContent))
            except TypeError:
                raise NameError('Invalid concept name')
        if nodeContent['media']['image']:
            concept.Image = nodeContent['media']['image']
        if nodeContent['media']['media']:
            concept.Media = nodeContent['media']['media']
        concept.Doc = file
        id_dict = {'src': a_id,
                   'crosslink': crosslink}
        if not concept.Xid:
            concept.Xid.append(json.dumps({q_id: id_dict}))
        else:
            id_prop = json.loads(concept.Xid[0])
            id_prop[q_id] = id_dict
            concept.Xid[0] = (json.dumps(id_prop))
        return concept

    def add_relation(self, child, class_text, parent, rel_dict):
        relProp = getattr(self, class_text)

        # Add objectproperty if not yet in ontology
        if not relProp:
            with self:
                relProp = types.new_class(
                    class_text, (owlready2.ObjectProperty,))
                relProp.domain = [self.Concept]
                relProp.range = [self.Concept]

        current_children = getattr(parent, class_text)
        new_children = current_children + [child]
        setattr(parent, class_text, new_children)

        current_parents = getattr(child, 'Parent')
        new_parents = current_parents + [parent]
        setattr(child, 'Parent', new_parents)

        # set annotation porperties for child relation
        self.Reference[parent, relProp, child] = rel_dict['ref']
        if rel_dict['sortId']:
            self.SortId[parent, relProp, child] = rel_dict['sortId']
        self.Doc[parent, relProp, child] = rel_dict['doc']
        self.Sheet[parent, relProp, child] = rel_dict['sheet']
        self.Xid[parent, relProp, child] = rel_dict['x_id']
        if rel_dict['image']:
            self.Image[parent, relProp, child] = rel_dict['image']
        if rel_dict['media']:
            self.Media[parent, relProp, child] = rel_dict['media']
        self.NoteTag[parent, relProp, child] = rel_dict['tag']
        self.AIndex[parent, relProp, child] = rel_dict['aIndex']

        # set annotation properties for parent relation
        self.Xid[child, self.Parent, parent] = rel_dict['x_id']

        return relProp

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
        self.remove_answer(q_id=q_id, a_id=a_id)

        new_answer = self.add_answer(
            parents=parents, a_id=a_id, answer_field=a_field,
            rel_dict=rel_dict, question_class=question_class)

        for o in objects_2_answer:
            self.add_relation(child=o['child'], class_text=o['class_text'],
                              parent=new_answer, rel_dict=o['rel_dict'])

    def change_question(self, x_id, new_question):
        """
        Changes a question in the ontology
        :param x_id: Xmind id of the question
        :param new_question: Field string of the new question
        """
        question_triples = self.get_question(x_id)
        answers = set(t['o'] for t in question_triples)
        parents = set(t['s'] for t in question_triples)

        remove_relations(answers, parents, question_triples)

        # Add new relationship
        class_text = self.field_translator.class_from_content(content_from_field(
            new_question))
        for parent in parents:
            for child in answers:
                self.relation_from_triple(
                    child=child, class_text=class_text, parent=parent,
                    question_triple=question_triples[0])

    def relation_from_triple(self, child, class_text, parent, question_triple):
        """
        Creates a new relation between the child and the parent with the
        given name and the attributes of the relation described in
        question_triple
        :param child: Object concept (answer)
        :param class_text: Name of the relation to add (question name)
        :param parent: Subject concept (parent to question)
        :param question_triple: Dictionary of three concepts that provides the
        attributes of the question relation
        """
        self.add_relation(
            child=child, class_text=class_text, parent=parent,
            rel_dict=self.rel_dict_from_triple(question_triple=question_triple))

    def rel_dict_from_triple(self, question_triple):
        return get_rel_dict(
            aIndex=self.get_trpl_a_index(question_triple),
            image=self.get_trpl_image(question_triple),
            media=self.get_trpl_media(question_triple),
            x_id=self.get_trpl_x_id(question_triple),
            ref=self.get_trpl_ref(question_triple),
            sortId=self.get_trpl_sort_id(question_triple),
            doc=self.get_trpl_doc(question_triple),
            sheet=self.get_trpl_sheet(question_triple),
            tag=self.getNoteTag(question_triple))

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

    def remove_answer(self, q_id, a_id):
        question_triples = self.get_question(q_id)
        parents = set(t['s'] for t in question_triples)
        answer = next(t['o'] for t in question_triples if
                      a_id == json.loads(t['o'].Xid[0])[q_id]['src'])

        # Remove answer from question
        remove_relations(answers=[answer], parents=parents,
                         question_triples=question_triples)

        remove_answer_concept(answer_concept=answer, q_id=q_id)

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
            remove_answer_concept(
                answer_concept=question_sets[-1][0]['triple']['s'], q_id='root')

    def save_changes(self):
        self.save(file=self.name + '.rdf', format='rdfxml')

    def set_trpl_a_index(self, a_id, q_id, a_index):
        q_trpls = self.get_question(q_id)
        a_concept = self.get_answer_by_a_id(a_id=a_id, q_id=q_id)
        a_trpls = [t for t in q_trpls if t['o'] == a_concept]
        for trpl in a_trpls:
            self.AIndex[trpl['s'], trpl['p'], trpl['o']] = a_index

    def set_up_classes(self):
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
