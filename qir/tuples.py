from . import base
from . import values


class TupleConstr(base.Expression):
    """
    A QIR expression representing a tuple constructor.

    Note that tuples in the QIR data model are actually just linked lists of
    (key, value) pairs, so the implementation of List and Tuple is similar.

    This class is abstract, and should not be instantiated directly.
    """


class TupleNil(TupleConstr):
    """ A QIR expression representing the empty tuple constructor. """
    fields = ()

    def evaluate_locally(self, environment={}):
        return self

    def decode(self):
        return {}


class TupleCons(TupleConstr):
    """ A QIR expression representing the (::) tuple constructor. """
    fields = (
        ('key', base.Expression),
        ('value', base.Expression),
        ('tail', base.Expression))

    def evaluate_locally(self, environment={}):
        return TupleCons(
            self.key.evaluate_locally(environment),
            self.value.evaluate_locally(environment),
            self.tail.evaluate_locally(environment))

    def decode(self):
        decoded = self.tail.decode()
        decoded[self.key.decode()] = self.value.decode()
        return decoded


class TupleDestr(base.Expression):
    """ A QIR expression representing the tuple key accessor. """
    fields = (
        ('input', base.Expression),
        ('key', base.Expression))

    def evaluate_locally(self, environment={}):
        input = self.input.evaluate_locally(environment)
        key = self.key.evaluate_locally(environment)

        if not isinstance(key, values.String):
            return values.Null

        def traverse(input):
            if isinstance(input, TupleNil):
                return values.Null
            elif isinstance(input, TupleCons) and input.key == key:
                return input.value
            elif isinstance(input, TupleCons):
                return traverse(input.tail)
            else:
                raise TypeError

        return traverse(input)
