from . import base
from . import functions


class ListConstr(base.Expression):
    """
    A QIR expression representing a list constructor.

    This class is abstract, and should not be instantiated directly.
    """


class ListNil(ListConstr):
    """ A QIR expression representing the empty list constructor. """
    fields = ()

    def evaluate_locally(self, environment):
        return self

    def decode(self):
        return ()


class ListCons(ListConstr):
    """ A QIR expression representing the (::) list constructor. """
    fields = (
        ('head', base.Expression),
        ('tail', base.Expression))

    def evaluate_locally(self, environment):
        return ListCons(
            self.head.evaluate(environment),
            self.tail.evaluate(environment))

    def decode(self):
        return (self.head().decode(),) + self.tail().decode()


class ListDestr(base.Expression):
    """
    A QIR expression representing the list destructor.

    When evaluated, it will output on_nil if input evaluates to the empty
    list, and on_cons(head(input), tail(input)) otherwise.
    """
    fields = (
        ('input', base.Expression),
        ('on_nil', base.Expression),
        ('on_cons', base.Expression))

    def evaluate_locally(self, environment):
        input = self.input.evaluate(environment)

        if isinstance(input, ListNil):
            return self.on_nil.evaluate(environment)
        elif isinstance(input, ListCons):
            return \
                functions.Application(
                    functions.Application(
                        self.on_cons.evaluate(environment),
                        input.head),
                    input.tail
                ).evaluate(environment)
        else:
            raise TypeError
