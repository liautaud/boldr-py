from . import base
from . import values
from . import specials
import types


class Identifier(base.Expression):
    """ A QIR expression representing the name of a variable. """
    fields = (('name', str),)

    def evaluate_locally(self, environment={}):
        if self.name in environment:
            return environment[self.name]
        else:
            return self


class Lambda(base.Expression):
    """ A QIR expression representing a one-parameter anonymous function. """
    fields = (
        ('parameter', Identifier),
        ('body', base.Expression))

    def evaluate_locally(self, environment={}):
        return self


class Fixed(base.Expression):
    """ A shortcut for the Y fixed-point combinator. """
    fields = ()

    def evaluate_locally(self, environment={}):
        return Lambda(
            Identifier('f'),
            Application(
                Lambda(
                    Identifier('x'),
                    Application(
                        Identifier('f'),
                        Application(
                            Identifier('x'),
                            Identifier('x')))),
                Lambda(
                    Identifier('x'),
                    Application(
                        Identifier('f'),
                        Application(
                            Identifier('x'),
                            Identifier('x'))))))


class Application(base.Expression):
    """ A QIR expression representing a function application. """
    fields = (
        ('function', base.Expression),
        ('argument', base.Expression))

    def evaluate_locally(self, environment={}):
        # We must evaluate the argument before the function.
        evaluated_argument = self.argument.evaluate_locally(environment)
        evaluated_function = self.function.evaluate_locally(environment)

        if (isinstance(evaluated_function, specials.Native) and
            isinstance(evaluated_function.value, types.FunctionType)):
            return base.encode(
                evaluated_function.value(
                    base.decode(evaluated_argument)))

        if isinstance(evaluated_function, Lambda):
            inner_environment = environment.copy()

            parameter_name = evaluated_function.parameter.name
            inner_environment[parameter_name] = evaluated_argument

            return evaluated_function.body.evaluate_locally(inner_environment)

        else:
            raise TypeError


class Conditional(base.Expression):
    """ A QIR expression representing a conditional statement. """
    fields = (
        ('condition', base.Expression),
        ('on_true', base.Expression),
        ('on_false', base.Expression))

    def evaluate_locally(self, environment={}):
        # We must only evaluate the branch that matches the condition.
        evaluated_condition = self.condition.evaluate_locally(environment)

        if not isinstance(evaluated_condition, values.Boolean):
            raise TypeError

        if evaluated_condition.value:
            branch = self.on_true
        else:
            branch = self.on_false

        return branch.evaluate_locally(environment)
