import owlready2
import types

from owlready2.namespace import Ontology, World
from owlready2.prop import destroy_entity

from .consts import ADDON_PATH, X_MAX_ANSWERS
from .xnotemanager import *


def classify(content):
    classified = content['content'].replace(" ", "_")
    if content['media']['image']:
        classified += "ximage_" + re.sub(
            'attachments/', '', content['media']['image'])
        classified = re.sub('(\\.)(' + '|'.join(X_IMG_EXTENSIONS) + ')',
                            '_extension_\\2', classified)
    if content['media']['media']:
        classified += "xmedia_" + re.sub(
            'attachments/', '', content['media']['media'])
        classified = re.sub('(\\.)(' + '|'.join(X_MEDIA_EXTENSIONS) + ')',
                            '_extension_\\2', classified)
    return classified


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
    def __init__(self, iri=None):
        if not iri:
            base_iri = os.path.join(ADDON_PATH, 'resources', 'onto.owl#')
        else:
            base_iri = iri + '#'

        Ontology.__init__(self, world=World(), base_iri=base_iri)
        if iri and os.path.exists(iri):
            self.load()
        self.setUpClasses()
        self.parentStorid = self.Parent.storid
        self.field_translator = FieldTranslator()

    def add_answer(self, parents, q_id, a_id, answer_field, file, rel_dict,
                   question_class):
        answer_content = content_from_field(answer_field)
        answer_concept = self.add_concept(nodeContent=answer_content, q_id=q_id,
                                          a_id=a_id, file=file)
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
            concept = self.Root(classify(nodeContent))
            q_id = 'root'
        else:
            # Some concept names (e.g. 'are') can lead to errors, catch
            # them
            try:
                concept = self.Concept(classify(nodeContent))
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

    def change_answer(self, q_id, a_id, new_answer):
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
        file = answer.Doc[0]
        rel_dict = self.rel_dict_from_triple(answer_triples[0])
        self.remove_answer(q_id=q_id, a_id=a_id)

        new_answer = self.add_answer(
            parents=parents, q_id=q_id, a_id=a_id, answer_field=new_answer,
            file=file, rel_dict=rel_dict, question_class=question_class)

        for o in objects_2_answer:
            self.add_relation(child=o['child'], class_text=o['class_text'],
                              parent=new_answer, rel_dict=o['rel_dict'])

    def change_question(self, x_id, new_question):
        question_triples = self.get_question(x_id)
        answers = set(t['o'] for t in question_triples)
        parents = set(t['s'] for t in question_triples)

        remove_relations(answers, parents, question_triples)

        class_text = classify(content_from_field(new_question))
        # add new relationship
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
        inverse_elements = [e for e in elements if self.get_trpl_x_id(e) == x_id]
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
        triples = self.getNoteTriples()
        elements = [self.getElements(t) for t in triples]
        question_elements = [e for e in elements if self.get_trpl_x_id(e) == x_id]
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

    def getNoteTriples(self):
        noNoteRels = ['Parent', 'Child']
        questionsStorids = [p.storid for p in self.object_properties() if
                            p.name not in noNoteRels]
        return [t for t in self.get_triples() if t[1] in questionsStorids]

    def getParentTriples(self, o):
        questionsStorids = [p.storid for p in self.object_properties() if
                            p.name != 'Parent']
        return [t for t in self.get_triples(o=o) if t[1] in questionsStorids]

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

    def remove_answer(self, q_id, a_id):
        question_triples = self.get_question(q_id)
        parents = set(t['s'] for t in question_triples)
        answer = next(t['o'] for t in question_triples if
                      a_id == json.loads(t['o'].Xid[0])[q_id]['src'])

        # Remove answer from question
        remove_relations(answers=[answer], parents=parents,
                         question_triples=question_triples)

        # Remove answer's x_id from concept or destroy concept if no x_ids
        # are left
        id_dict = json.loads(answer.Xid[0])
        del id_dict[q_id]
        if id_dict:
            answer.Xid[0] = json.dumps(id_dict)
        else:
            destroy_entity(answer)

    def save_changes(self):
        self.save(file=self.name + '.rdf', format='rdfxml')

    def setUpClasses(self):
        with self:
            class Concept(owlready2.Thing):
                pass

            class Root(Concept):
                pass

            # standard object properties
            class Parent(Concept >> Concept):
                pass

            class Child(Concept >> Concept):
                pass

            # Annotation properties for Concepts

            # For Image String from Xmind file
            class Image(owlready2.AnnotationProperty):
                pass

            # For Media String from Xmind file
            class Media(owlready2.AnnotationProperty):
                pass

            # For Node Id in Xmind file
            class Xid(owlready2.AnnotationProperty):
                pass

            # For Id of crosslink pointing to this concept in Xmind file
            class Crosslink(owlready2.AnnotationProperty):
                pass

            # Xmind file that contains the node
            class Doc(owlready2.AnnotationProperty):
                pass

            # Annotation properties for relation triples

            # For reference field
            class Reference(owlready2.AnnotationProperty):
                pass

            # For sortId field
            class SortId(owlready2.AnnotationProperty):
                pass

            # Sheet that contains the node
            class Sheet(owlready2.AnnotationProperty):
                pass

            # Tag that will identify the note
            class NoteTag(owlready2.AnnotationProperty):
                pass

            # Answer Index for getting the right order of answers
            class AIndex(owlready2.AnnotationProperty):
                pass
