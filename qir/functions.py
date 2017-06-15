from . import base
from . import specials
from . import errors
import types


class Identifier(base.Expression):
    """ A QIR expression representing the name of a variable. """
    fields = (('name', str),)

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Lambda(base.Expression):
    """ A QIR expression representing a one-parameter anonymous function. """
    fields = (
        ('parameter', Identifier),
        ('body', base.Expression))

    def evaluate_locally(self, environment):
        # The body of a function must not be evaluated before the function
        # gets applied to an argument.
        return self


class Application(base.Expression):
    """ A QIR expression representing a function application. """
    fields = (
        ('function', base.Expression),
        ('argument', base.Expression))

    def evaluate_locally(self, environment):
        # Beware that we must evaluate the argument before the function.
        evaluated_argument = self.argument.evaluate(environment)
        evaluated_function = self.function.evaluate(environment)

        if (isinstance(evaluated_function, specials.Local) and
            isinstance(evaluated_function.value, types.FunctionType)):
            return \
                base.encode(
                    evaluated_function.value(
                        base.decode(evaluated_argument)))

        if isinstance(evaluated_function, Lambda):
            raise errors.NotYetImplementedError

        else:
            raise TypeError


class Conditional(base.Expression):
    """ A QIR expression representing a conditional statement. """
    fields = (
        ('condition', base.Expression),
        ('on_true', base.Expression),
        ('on_false', base.Expression))

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError
