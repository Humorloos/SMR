import os

import owlready2

from owlready2.namespace import Ontology, World

from .consts import ADDON_PATH, X_MAX_ANSWERS
from .utils import unclassify


class XOntology(Ontology):
    def __init__(self):
        iri = os.path.join(ADDON_PATH, 'resources', 'onto.owl#')
        # owlready2.get_ontology(iri)
        Ontology.__init__(self, world=World(), base_iri=iri)
        self.setUpClasses()
        self.parentStorid = self.Parent.storid

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
            class Image(owlready2.AnnotationProperty):
                pass

            class Media(owlready2.AnnotationProperty):
                pass

            class Xid(owlready2.AnnotationProperty):
                pass

            # Annotation properties for relation triples
            class Reference(owlready2.AnnotationProperty):
                pass

            class SortId(owlready2.AnnotationProperty):
                pass

            class Doc(owlready2.AnnotationProperty):
                pass

            class Sheet(owlready2.AnnotationProperty):
                pass

            class NoteTag(owlready2.AnnotationProperty):
                pass

    def getElements(self, triple):
        elements = [self.world._get_by_storid(s) for s in triple]
        return {'s': elements[0], 'p': elements[1], 'o': elements[2]}

    def getRef(self, elements):
        return self.Reference[elements['s'], elements['p'], elements['o']]

    def getSortId(self, elements):
        return self.SortId[elements['s'], elements['p'], elements['o']]

    def getDoc(self, elements):
        return self.Doc[elements['s'], elements['p'], elements['o']]

    def getXid(self, elements):
        return self.Xid[elements['s'], elements['p'], elements['o']]

    def getSheet(self, elements):
        return self.Sheet[elements['s'], elements['p'], elements['o']]

    def getImage(self, elements):
        return self.Image[elements['s'], elements['p'], elements['o']]

    def getMedia(self, elements):
        return self.Media[elements['s'], elements['p'], elements['o']]

    def getNoteTag(self, elements):
        return self.NoteTag[elements['s'], elements['p'], elements['o']]

    def getNoteData(self, questionList):
        elements = self.getElements(questionList[0])
        answerDids = list(set(t[2] for t in questionList))
        answerDicts = [dict() for _ in range(X_MAX_ANSWERS)]
        images = []
        media = []
        for i, answerDict in enumerate(answerDicts[0:len(answerDids)]):
            concept = self.world._get_by_storid(answerDids[i])
            answerDict['text'] = concept.name
            answerDict['id'] = concept.Xid[0]
            if concept.Image:
                images.append(concept.Image)
            if concept.Media:
                media.append(concept.media)
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
            'reference': self.getRef(elements)[0],
            'question': unclassify(elements['p'].name),
            'answers': answerDicts,
            'sortId': self.getSortId(elements)[0],
            'document': self.getDoc(elements)[0],
            'sheetId': self.getSheet(elements)[0],
            'questionId': self.getXid(elements)[0],
            'subjects': parentDicts,
            'images': images,
            'media': media,
            'tag': self.getNoteTag(elements)[0]
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
        return [None if len(f) == 0 else f[0] for f in files]

    def getChildQuestionIds(self, childElements):
        children = {'childQuestions': set(), 'bridges': list()}
        for elements in childElements:
            if elements['p'].name != 'Child':
                children['childQuestions'].add(self.getXid(elements)[0])
            else:
                nextChildTriples = self.getChildTriples(s=elements['o'].storid)
                nextChildElements = [
                    self.getElements(t) for t in nextChildTriples]
                bridge = {'objectTitle': elements['s'].name}
                bridge.update(self.getChildQuestionIds(nextChildElements))
                children['bridges'].append(bridge)
        children['childQuestions'] = list(children['childQuestions'])
        return children

    def getParentQuestionIds(self, parentElements):
        parents = {'parentQuestions': set(), 'bridges': list()}
        for elements in parentElements:
            # Add id of question to set if parent is a normal question
            if elements['p'].name != 'Child':
                parents['parentQuestions'].add(self.getXid(elements)[0])
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
