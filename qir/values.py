from . import base


class Value(base.Expression):
    """
    A QIR expression representing a value.

    Those values are the basic building blocks of the QIR data model, which is
    independent of both the data models of the host language (Python in this
    case) and the target database.

    This class is abstract, and should not be instantiated directly.
    """
    def evaluate_locally(self, environment):
        return self

    def decode(self):
        return self.value


class Null(Value):
    """  A QIR expression representing the null value. """
    fields = ()

    def decode(self):
        return None


class Number(Value):
    """ A QIR expression representing an integer value. """
    fields = (('value', int),)


class Double(Value):
    """ A QIR expression representing a floating point value. """
    fields = (('value', float),)


class String(Value):
    """ A QIR expression representing a string value. """
    fields = (('value', str),)


class Boolean(Value):
    """ A QIR expression representing a boolean value. """
    fields = (('value', bool),)
