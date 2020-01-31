import owlready2
import types

from owlready2.namespace import Ontology, World

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


def rel_dict(aIndex, image, media, x_id, timestamp,
             ref, sortId, doc, sheet, tag):
    return {
        'aIndex': aIndex,
        'image': image,
        'media': media,
        'x_id': x_id,
        'timestamp': timestamp,
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
        # owlready2.get_ontology(iri)
        Ontology.__init__(self, world=World(), base_iri=base_iri)
        if iri:
            self.load()
        self.setUpClasses()
        self.parentStorid = self.Parent.storid
        self.field_translator = FieldTranslator()

    def add_answer(self, parents, q_id, a_id, answer_field, file, rel_dict):
        answer_content = content_from_field(answer_field)
        answer_concept = self.add_concept(nodeContent=answer_content, q_id=q_id,
                                          a_id=a_id, file=file)
        for parent in parents:
            self.add_relation(child=answer_concept, class_text=classify(
                answer_content), parent=parent, rel_dict=rel_dict)
        print('add answer')

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
        self.Mod[parent, relProp, child] = rel_dict['timestamp']

        # set annotation properties for parent relation
        self.Xid[child, self.Parent, parent] = rel_dict['x_id']

    def change_answer(self, q_id, a_id, new_answer):
        answer = self.get_answer_by_a_id(a_id=a_id, q_id=q_id)
        answer_triples = [t for t in self.get_question(q_id) if t['o'] ==
                          answer]
        parents = set(t['s'] for t in answer_triples)
        file = answer.Doc[0]
        rel_dict = self.rel_dict_from_triple(answer_triples[0])
        self.remove_answer(q_id=q_id, a_id=a_id)

        self.add_answer(parents=parents, q_id=q_id, a_id=a_id,
                        answer_field=new_answer, file=file, rel_dict=rel_dict)

        print('change answer')

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
        return rel_dict(
            aIndex=self.get_AIndex(question_triple),
            image=self.getImage(question_triple),
            media=self.getMedia(question_triple),
            x_id=self.getXid(question_triple),
            timestamp=self.getMod(question_triple),
            ref=self.getRef(question_triple),
            sortId=self.getSortId(question_triple),
            doc=self.getDoc(question_triple),
            sheet=self.getSheet(question_triple),
            tag=self.getNoteTag(question_triple))

    def get_AIndex(self, elements):
        return self.AIndex[elements['s'], elements['p'], elements['o']][0]

    def get_answer_by_a_id(self, a_id, q_id):
        return self.search(Xid='*{"' + q_id + '": {"src": "' + a_id + '*')[0]

    def get_all_parent_triples(self):
        return [t for t in self.get_triples() if t[1] == self.Parent.storid]

    def getDoc(self, elements):
        return self.Doc[elements['s'], elements['p'], elements['o']][0]

    def getElements(self, triple):
        elements = [self.world._get_by_storid(s) for s in triple]
        return {'s': elements[0], 'p': elements[1], 'o': elements[2]}

    def getImage(self, elements):
        try:
            return self.Image[elements['s'], elements['p'], elements['o']][0]
        except IndexError:
            return ''

    def get_inverse(self, x_id):
        triples = self.get_all_parent_triples()
        elements = [self.getElements(t) for t in triples]
        inverse_elements = [e for e in elements if self.getXid(e) == x_id]
        return inverse_elements

    def getMedia(self, elements):
        try:
            return self.Media[elements['s'], elements['p'], elements['o']][0]
        except IndexError:
            return ''

    def getMod(self, elements):
        return self.Mod[elements['s'], elements['p'], elements['o']][0]

    def getNoteTag(self, elements):
        return self.NoteTag[elements['s'], elements['p'], elements['o']][0]

    def getParentQuestionIds(self, parentElements):
        parents = {'parentQuestions': set(), 'bridges': list()}
        for elements in parentElements:
            # Add id of question to set if parent is a normal question
            if elements['p'].name != 'Child':
                parents['parentQuestions'].add(self.getXid(elements))
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
        question_elements = [e for e in elements if self.getXid(e) == x_id]
        return question_elements

    def getRef(self, elements):
        return self.Reference[elements['s'], elements['p'], elements['o']][0]

    def getSheet(self, elements):
        return self.Sheet[elements['s'], elements['p'], elements['o']][0]

    def getSortId(self, elements):
        return self.SortId[elements['s'], elements['p'], elements['o']][0]

    def getXid(self, elements):
        return self.Xid[elements['s'], elements['p'], elements['o']][0]

    def getNoteData(self, questionList):
        elements = self.getElements(questionList[0])
        q_id = self.getXid(elements)
        answerDids = set(t[2] for t in questionList)
        # Sort answerDids by answer index to get the answers' order right
        answerDids = sorted(answerDids, key=lambda d: self.get_AIndex(
            self.getElements(next(t for t in questionList if t[2] == d))))
        answerDicts = [dict() for _ in range(X_MAX_ANSWERS)]
        images = []
        media = []
        for i, answerDict in enumerate(answerDicts[0:len(answerDids)]):
            concept = self.world._get_by_storid(answerDids[i])
            answerDict['text'] = self.field_translator.field_from_class(
                concept.name)
            id_dict = json.loads(concept.Xid[0])
            answerDict['src'] = id_dict[q_id]['src']
            answerDict['crosslink'] = id_dict[q_id]['crosslink']
            if concept.Image:
                images.append(file_dict(identifier=concept.Image[0],
                                        doc=concept.Doc[0]))
            if concept.Media:
                media.append(file_dict(identifier=concept.Media[0],
                                       doc=concept.Doc[0]))
            childTriples = self.getChildTriples(s=answerDids[i])
            childElements = [self.getElements(t) for t in childTriples]
            answerDict['children'] = self.getChildQuestionIds(childElements)

        parentDids = list(set(t[0] for t in questionList))
        parentDicts = []
        for did in parentDids:
            parentDict = dict()
            concept = self.world._get_by_storid(did)
            parentDict['text'] = concept.name
            parentDict['id'] = concept.Xid[0]
            parentTriples = self.getParentTriples(o=did)
            parentElements = [self.getElements(t) for t in parentTriples]
            parentDict['parents'] = self.getParentQuestionIds(parentElements)
            parentDicts.append(parentDict)

        files = self.getFiles(elements)
        if files[0]:
            images.append(files[0])
        if files[1]:
            media.append(files[1])
        return {
            'reference': self.getRef(elements),
            'question': self.field_translator.field_from_class(
                elements['p'].name),
            'answers': answerDicts,
            'sortId': self.getSortId(elements),
            'document': self.getDoc(elements),
            'sheetId': self.getSheet(elements),
            'questionId': q_id,
            'subjects': parentDicts,
            'images': images,
            'media': media,
            'tag': self.getNoteTag(elements),
            'questionMod': self.getMod(elements)
        }

    def getNoteTriples(self):
        noNoteRels = ['Parent', 'Child']
        questionsStorids = [p.storid for p in self.object_properties() if
                            p.name not in noNoteRels]
        return [t for t in self.get_triples() if t[1] in questionsStorids]

    def getChildTriples(self, s):
        questionStorids = [p.storid for p in self.object_properties() if
                           p.name != 'Parent']
        return [t for t in self.get_triples(s=s) if t[1] in questionStorids]

    def getParentTriples(self, o):
        questionsStorids = [p.storid for p in self.object_properties() if
                            p.name != 'Parent']
        return [t for t in self.get_triples(o=o) if t[1] in questionsStorids]

    def getFiles(self, elements):
        files = [self.getImage(elements), self.getMedia(elements)]
        return [None if not f else file_dict(
            identifier=f, doc=self.getDoc(elements)) for f in files]

    def getChildQuestionIds(self, childElements):
        children = {'childQuestions': set(), 'bridges': list()}
        for elements in childElements:
            if elements['p'].name != 'Child':
                children['childQuestions'].add(self.getXid(elements))
            else:
                nextChildTriples = self.getChildTriples(s=elements['o'].storid)
                nextChildElements = [
                    self.getElements(t) for t in nextChildTriples]
                bridge = {'objectTitle': elements['s'].name}
                bridge.update(self.getChildQuestionIds(nextChildElements))
                children['bridges'].append(bridge)
        children['childQuestions'] = list(children['childQuestions'])
        return children

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
            self.destroy_entity(answer)

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
