# noinspection PyPep8Naming
class cached_property(object):
    """
    property for caching of attributes, code adapted from
    https://stackoverflow.com/questions/17330160/how-does-the-property-decorator-work
    """
    def __init__(self, fget, fset=None, fdel=None, name=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__name__ = name or fget.__name__
        self.__module__ = fget.__module__
        self.__doc__ = doc or fget.__doc__

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.__name__]
        except KeyError:
            value = self.fget(obj)
            obj.__dict__[self.__name__] = value
            return value

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def __delete__(self, obj):
        try:
            del obj.__dict__[self.__name__]
        except KeyError:
            pass
        if self.fdel is not None:
            self.fdel(obj)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__name__, self.__doc__)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel, self.__name__, self.__doc__)
