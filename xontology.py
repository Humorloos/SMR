import os

import owlready2

from owlready2.namespace import Ontology, World

from .consts import ADDON_PATH


class XOntology(Ontology):
    def __init__(self):
        iri = os.path.join(ADDON_PATH, 'resources', 'onto.owl#')
        # owlready2.get_ontology(iri)
        Ontology.__init__(self, world=World(), base_iri=iri)
        self.setUpClasses()

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

            class Tag(owlready2.AnnotationProperty):
                pass

            class Sheet(owlready2.AnnotationProperty):
                pass

            class Doc(owlready2.AnnotationProperty):
                pass

    def getElements(self, triple):
        return [self.world._get_by_storid(s) for s in triple]

    def getRef(self, triple):
        elements = self.getElements(triple)
        return self.Reference[elements[0], elements[1], elements[2]]

    def getXid(self, triple):
        elements = self.getElements(triple)
        return self.Reference[elements[0], elements[1], elements[2]]

    def getImage(self, triple):
        elements = self.getElements(triple)
        return self.Image[elements[0], elements[1], elements[2]]

    def getMedia(self, triple):
        elements = self.getElements(triple)
        return self.Media[elements[0], elements[1], elements[2]]

    def getSortId(self, triple):
        elements = self.getElements(triple)
        return self.SortId[elements[0], elements[1], elements[2]]

    def getQuestionMeta(self, triple):
        return {'reference': self.getRef(triple),
                'sortId': self.getSortId(triple),
                'document': self.getDocument(triple),
                'sheetId': self.getSheetId(triple),
                'id': self.getXid(triple),
                'image': self.getImage(triple),
                'media': self.getMedia(triple)}