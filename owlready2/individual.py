# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2013-2019 Jean-Baptiste LAMY
# LIMICS (Laboratoire d'informatique médicale et d'ingénierie des connaissances en santé), UMR_S 1142
# University Paris 13, Sorbonne paris-Cité, Bobigny, France

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import owlready2
from owlready2.namespace import *
from owlready2.namespace import _cache_entity
from owlready2.entity    import *
from owlready2.entity    import _inherited_property_value_restrictions

class _EquivalentToList(CallbackList):
  __slots__ = ["_indirect"]
  def __init__(self, l, obj, callback):
    CallbackList.__init__(self, l, obj, callback)
    self._indirect = None
    
  def _build_indirect(self):
    n = self._obj.namespace
    self._indirect = list({
      n.ontology._to_python(o)
      for o in n.world._get_obj_triples_transitive_sym(self._obj.storid, owl_equivalentindividual)
      if o != self._obj.storid
    })
    
  def indirect(self):
    if self._indirect is None: self._build_indirect()
    return self._indirect
  
  def self_and_indirect_equivalent(self):
    yield self._obj
    if self._indirect is None: self._build_indirect()
    yield from self._indirect
    
  
    
class Thing(metaclass = ThingClass):
  namespace = owl
  
  def get_name(self): return self._name
  def set_name(self, name):
    self._name = name
    self.namespace.world._refactor(self.storid, "%s%s" % (self.namespace.base_iri, name))
  name = property(get_name, set_name)
  
  def get_iri(self):
    if self.storid < 0: return ""
    return "%s%s" % (self.namespace.base_iri, self._name)
  def set_iri(self, new_iri):
    splitted = new_iri.rsplit("#", 1)
    if len(splitted) == 2:
      self.namespace = self.namespace.ontology.get_namespace("%s#" % splitted[0])
    else:
      splitted = new_iri.rsplit("/", 1)
      self.namespace = self.namespace.ontology.get_namespace("%s/" % splitted[0])
    self._name = splitted[1]
    self.namespace.world._refactor(self.storid, new_iri)
  iri = property(get_iri, set_iri)
  
  def __new__(Class, name = None, namespace = None, **kargs):
    if name:
      if isinstance(name, Thing):
        namespace = name.namespace
        name      = name.name
      else:
        namespace = namespace or (CURRENT_NAMESPACES.get() and CURRENT_NAMESPACES.get()[-1]) or Class.namespace
      if LOADING or (name == ""):
        already_existing = None
      else:
        already_existing = namespace.world["%s%s" % (namespace.base_iri, name)]
        
      if not already_existing is None:
        if not isinstance(already_existing, Class):
          if isinstance(Class, FusionClass): Classes =  Class.__bases__
          else:                              Classes = (Class,)
          for C in Classes:
            if not C in already_existing.is_a:
              already_existing.is_a._append(C)
              if not LOADING:
                already_existing.namespace.ontology._add_obj_triple_spo(already_existing.storid, rdf_type, C.storid)
                
        bases = ThingClass._find_base_classes(already_existing.is_a)
        if len(bases) == 1:
          already_existing.__class__ = bases[0]
        else:
          already_existing.__class__ = FusionClass._get_fusion_class(bases)
          
        if not LOADING:
          for attr, value in kargs.items(): setattr(already_existing, attr, value)
          
        return already_existing
      
    #_cache_entity(entity)
    #return object.__new__(Class)
    return _cache_entity(object.__new__(Class))
  
  def __init__(self, name = None, namespace = None, **kargs):
    self.namespace = namespace or (CURRENT_NAMESPACES.get() and CURRENT_NAMESPACES.get()[-1]) or self.__class__.namespace
    if   isinstance(name, int):
      is_new = True
      iri = ""
      self._name = ""
    elif name:
      is_new = not "storid" in self.__dict__
      iri = "%s%s" % (self.namespace.base_iri, name)
      self._name = name
    else:
      is_new = True
      iri = self.namespace.world._new_numbered_iri("%s%s" % (self.namespace.base_iri, self.generate_default_name()))
      self._name = iri[len(self.namespace.base_iri):]
      
    if is_new:
      self.__dict__["_equivalent_to"] = None
      if isinstance(name, int): self.storid = name or self.namespace.world.graph.new_blank_node()
      else:                     self.storid = self.namespace.world._abbreviate(iri)
      self.namespace.world._entities[self.storid] = self
      if isinstance(self.__class__, FusionClass):
        self.__dict__["is_a"] = CallbackList(self.__class__.__bases__, self, Thing._instance_is_a_changed)
      else:
        self.__dict__["is_a"] = CallbackList([self.__class__], self, Thing._instance_is_a_changed)
        
      if not LOADING:
        if self.storid > 0: self.namespace.ontology._add_obj_triple_spo(self.storid, rdf_type, owl_named_individual)
        for parent in self.is_a:
          self.namespace.ontology._add_obj_triple_spo(self.storid, rdf_type, parent.storid)
          
        for attr, value in kargs.items(): setattr(self, attr, value)
    
  def generate_default_name(self): return self.__class__.name.lower()
  
  def _get_is_instance_of(self):    return self.is_a
  def _set_is_instance_of(self, v): self.is_a = v
  is_instance_of = property(_get_is_instance_of, _set_is_instance_of)
  
  def _instance_is_a_changed(self, old):
    new = set(self.is_a)
    old = set(old)
    
    for base in old - new:
      if not LOADING: self.namespace.ontology._del_obj_triple_spo(self.storid, rdf_type, base.storid)
      if isinstance(base, ClassConstruct): base._set_ontology(None)
    bases = ThingClass._find_base_classes(self.is_a)
    if len(bases) == 1:
      self.__class__ = bases[0]
    elif bases:
      self.__class__ = FusionClass._get_fusion_class(bases)
    else:
      self.__class__ = Thing
      list.insert(self.is_a, 0, Thing)
      
    for base in new - old:
      if isinstance(base, ClassConstruct): base._set_ontology_copy_if_needed(self.namespace.ontology, self.is_a)
      if not LOADING: self.namespace.ontology._add_obj_triple_spo(self.storid, rdf_type, base.storid)
      
  #def __attrs__(self): # Not Python standard, but used by EditObj
  
  def get_equivalent_to(self):
    if self._equivalent_to is None:
      self._equivalent_to = _EquivalentToList(
        [self.namespace.world._to_python(o, default_to_none = True)
         for o in self.namespace.world._get_obj_triples_sp_o(self.storid, owl_equivalentindividual)
        ], self, Thing._instance_equivalent_to_changed)
    return self._equivalent_to
  
  def set_equivalent_to(self, value): self.equivalent_to.reinit(value)

  # Cannot use property because it name-clashes with the Class similar property
  #equivalent_to = property(get_equivalent_to, set_equivalent_to)
  
  def _instance_equivalent_to_changed(self, old):
    new = frozenset(self._equivalent_to)
    old = frozenset(old)
    
    for x in old - new:
      self.namespace.ontology._del_obj_triple_spo(self.storid, owl_equivalentindividual, x.storid)
      if isinstance(x, ClassConstruct): x._set_ontology(None)
      else: # Invalidate it
        if x.equivalent_to._indirect:
          for x2 in x.equivalent_to._indirect: x2._equivalent_to._indirect = None
          x._equivalent_to._indirect = None
          
    for x in new - old:
      self.namespace.ontology._add_obj_triple_spo(self.storid, owl_equivalentindividual, x.storid)
      if isinstance(x, ClassConstruct): x._set_ontology_copy_if_needed(self.namespace.ontology, self._equivalent_to)
      else: # Invalidate it
        if x.equivalent_to._indirect:
          for x2 in x.equivalent_to._indirect: x2._equivalent_to._indirect = None
          x._equivalent_to._indirect = None
          
    self._equivalent_to._indirect = None # Invalidate, because the addition / removal may add its own equivalent.
    
  def differents(self):
    for c, s, p, o in self.namespace.world._get_obj_triples_cspo_cspo(None, None, rdf_type, owl_alldifferent):
      onto = self.namespace.world.graph.context_2_user_context(c)
      list_bnode = self.namespace.world._get_obj_triple_sp_o(s, owl_distinctmembers)
      storids = set(storid for storid, dropit in onto._parse_list_as_rdf(list_bnode))
      if self.storid in storids: yield onto._parse_bnode(s)
      
      
  def __getattr__(self, attr):
    if attr.startswith("INDIRECT_"):
      Prop = self.namespace.world._props.get(attr[9:])
      if not Prop:
        if   attr == "INDIRECT_equivalent_to":
          eq = self.equivalent_to
          if eq._indirect is None: eq._build_indirect()
          return eq._indirect
        elif (attr == "INDIRECT_is_a") or (attr == "INDIRECT_is_instance_of"):
          #return list({ ancestor for parent in self.is_a if isinstance(parent, ThingClass) for ancestor in parent.ancestors() })
          return list({ ancestor for parent in self.is_a for ancestor in parent.ancestors(True, True) })
        else: raise AttributeError("'%s' property is not defined." % attr)
        
      if Prop.is_functional_for(self.__class__):
        return Prop._get_indirect_value_for_individual(self)
      else:
        return list(Prop._get_indirect_values_for_individual(self))
      
    elif attr.startswith("INVERSE_"):
      Prop = self.namespace.world._props.get(attr[8:])
      if Prop.inverse:
        return getattr(self, Prop.inverse.python_name)
      else:
        if issubclass_python(Prop, InverseFunctionalProperty): self.__dict__[attr] = r = Prop._get_inverse_value_for_individual (self)
        else:                                                  self.__dict__[attr] = r = Prop._get_inverse_values_for_individual(self)
        return r
      
    else:
      Prop = self.namespace.world._props.get(attr)
      if not Prop:
        if attr == "equivalent_to": return self.get_equivalent_to() # Needed
        raise AttributeError("'%s' property is not defined." % attr)
      if Prop.is_functional_for(self.__class__): self.__dict__[attr] = r = Prop._get_value_for_individual (self)
      else:                                      self.__dict__[attr] = r = Prop._get_values_for_individual(self)
      return r
    
  def __setattr__(self, attr, value):
    if attr in SPECIAL_ATTRS:
      if   attr == "is_a":          self.is_a.reinit(value)
      elif attr == "equivalent_to": self.set_equivalent_to(value) # Needed
      else:                         super().__setattr__(attr, value)
    else:
      Prop = self.namespace.world._props.get(attr)
      if Prop:
        if Prop.is_functional_for(self.__class__):
          if   Prop._owl_type == owl_object_property:
            old_value = self.__dict__.get(attr, None)
            #if Prop.inverse_property and (not old_value is None):
            #  old_value.__dict__.pop(Prop.inverse_property.python_name, None) # Remove => force reloading; XXX optimizable
            #  self.namespace.ontology._del_obj_triple_spo(old_value.storid, Prop.inverse_property.storid, self.storid) # Also remove inverse
            if not old_value is None:
              if Prop.inverse_property:
                old_value.__dict__.pop(Prop.inverse_property.python_name, None) # Remove => force reloading; XXX optimizable
                self.namespace.ontology._del_obj_triple_spo(old_value.storid, Prop.inverse_property.storid, self.storid) # Also remove inverse
              else:
                old_value.__dict__.pop("INVERSE_%s" % Prop.python_name, None) # Remove => force reloading; XXX optimizable
                
            super().__setattr__(attr, value)
            
            if value is None:
              self.namespace.ontology._del_obj_triple_spo(self.storid, Prop.storid, None)
            else:
              self.namespace.ontology._set_obj_triple_spo(self.storid, Prop.storid, value.storid)
              if Prop.inverse_property: value.__dict__.pop(Prop.inverse_property.python_name, None) # Remove => force reloading; XXX optimizable
              
          elif Prop._owl_type == owl_data_property:
            old_value = self.__dict__.get(attr, None)
            
            super().__setattr__(attr, value)
            
            if value is None:
              self.namespace.ontology._del_data_triple_spod(self.storid, Prop.storid, None, None)
            else:
              self.namespace.ontology._set_data_triple_spod(self.storid, Prop.storid, *self.namespace.ontology._to_rdf(value))
              
        else:
          if not isinstance(value, list):
            if isinstance(Prop, AnnotationPropertyClass):
              if value is None: value = []
              else:             value = [value]
            else:
              raise ValueError("Property '%s' is not functional, cannot assign directly (use .append() or assign a list)." % attr)
          getattr(self, attr).reinit(value)
          
      elif attr.startswith("INVERSE_"):
        Prop = self.namespace.world._props.get(attr[8:])
        if Prop:
          if Prop.inverse: setattr(self, Prop.inverse.python_name, value)
          else:
            if issubclass_python(Prop, InverseFunctionalProperty):
              old_value = self.__dict__.get(attr, None)
              if not old_value is None:
                if Prop.is_functional_for(old_value): setattr(old_value, Prop.python_name, None)
                else:                                 getattr(old_value, Prop.python_name).remove(self)
              if not value is None:
                if Prop.is_functional_for(value): setattr(value, Prop.python_name, self)
                else:                             getattr(value, Prop.python_name).append(self)
            else:
              if not isinstance(value, list): raise ValueError("Property '%s' is not inverse functional, cannot assign directly (use .append() or assign a list)." % attr)
              getattr(self, attr).reinit(value)
            
        else:
          raise ValueError("Property '%s' do not exist, cannot use its INVERSE." % attr[8:])
        
      else: super().__setattr__(attr, value)
        
  def _get_instance_possible_relations(self, ignore_domainless_properties = False):
    for Prop in self.namespace.world._reasoning_props.values():
      all_domains = set(Prop.domains_indirect())
      if ignore_domainless_properties and (not all_domains):
        for restrict in _inherited_property_value_restrictions(self, Prop, set()):
          yield Prop
          break
      else:
        for domain in all_domains:
          if not domain._satisfied_by(self): break
        else:
          yield Prop
          
  def get_properties(self):
    l = set()
    for storid in self.namespace.world._get_triples_s_p(self.storid):
      Prop = self.namespace.world._get_by_storid(storid)
      if not Prop is None: # None is is-a
        l.add(Prop)
    for storid in self.namespace.world._get_obj_triples_o_p(self.storid):
      Prop = self.namespace.world._get_by_storid(storid)
      if not Prop is None: # None is is-a
        if Prop._inverse_property:
          l.add(Prop._inverse_property)
    return l
  
  def INDIRECT_get_properties(self):
    l = self.get_properties()
    l.update(self.__class__.INDIRECT_get_class_properties())
    return l
  
  def __dir__(self):
    return set(object.__dir__(self)) | { Prop.python_name for Prop in self.get_properties() }
  
  def get_inverse_properties(self):
    for s,p,o in self.namespace.world._get_obj_triples_spo_spo(None, None, self.storid):
      Prop    = self.namespace.world._get_by_storid(p)
      if not Prop is None: # None is is-a
        subject = self.namespace.world._get_by_storid(s)
        yield subject, Prop
        


class Nothing(Thing): pass

class FusionClass(ThingClass):
  ontology = anonymous
  
  _CACHES         = {}
  _FUSION_CLASSES = {}

  def __repr__(self): return "<FusionClass %s>" % ", ".join(repr(c) for c in self.__bases__)
  
  @staticmethod
  def _get_fusion_class(Classes0):
    key = frozenset(Classes0)
    Class = FusionClass._CACHES.get(key)
    if Class: return Class
    
    Classes = _keep_most_specific(Classes0, consider_equivalence = False)
    try:
      fusion_class = FusionClass._create_fusion_class(key, Classes)
      
    except: # Too complex hierarchy => do not consider equivalent classes
      Classes = _keep_most_specific(Classes0, consider_equivalence = True)
      fusion_class = FusionClass._create_fusion_class(key, Classes)
      
    return fusion_class
  
  @staticmethod
  def _create_fusion_class(key, Classes):
    if len(Classes) == 1:
      FusionClass._CACHES[key] = Class = tuple(Classes)[0]
      return Class
    
    Classes = tuple(sorted(Classes, key = lambda Class: Class.__name__))
    if Classes in FusionClass._FUSION_CLASSES: return FusionClass._FUSION_CLASSES[Classes]
    name = "_AND_".join(Class.__name__ for Class in Classes)
    
    with anonymous: # Force triple insertion into anonymous
      fusion_class = FusionClass(name, Classes, { "namespace" : anonymous })
      
    FusionClass._FUSION_CLASSES[Classes] = FusionClass._CACHES[key] = fusion_class
    return fusion_class
  
