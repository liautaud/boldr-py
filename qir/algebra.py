from . import base
from . import errors
from . import values
from . import utils


class UnaryOperator(base.Expression):
    """
    A QIR unary algebraïc operator.

    This class is abstract, and should not be instantiated directly.
    """
    fields = (('element', base.Expression),)

    def evaluate_locally(self, environment={}):
        evaluated = self.element.evaluate_locally(environment)

        if not isinstance(evaluated, values.Value):
            raise errors.NotLocallyEvaluableError

        return utils.encode(self.__class__.operate(evaluated.value))


class Not(UnaryOperator):
    def operate(x):
        return not x


class BinaryOperator(base.Expression):
    """
    A QIR binary algebraïc operator.

    This class is abstract, and should not be instantiated directly.
    """
    fields = (
        ('left', base.Expression),
        ('right', base.Expression))

    def evaluate_locally(self, environment={}):
        evaluated_left = self.left.evaluate_locally(environment)
        evaluated_right = self.right.evaluate_locally(environment)

        if (not isinstance(evaluated_left, values.Value) or
            not isinstance(evaluated_right, values.Value)):
            raise errors.NotLocallyEvaluableError

        return utils.encode(self.__class__.operate(
            evaluated_left.value,
            evaluated_right.value))


class Div(BinaryOperator):
    def operate(x, y):
        return x / y


class Minus(BinaryOperator):
    def operate(x, y):
        return x / y


class Mod(BinaryOperator):
    def operate(x, y):
        return x % y


class Plus(BinaryOperator):
    def operate(x, y):
        return x + y


class Star(BinaryOperator):
    def operate(x, y):
        return x * y


class Power(BinaryOperator):
    def operate(x, y):
        return x ** y


class And(BinaryOperator):
    def operate(x, y):
        return x and y


class Or(BinaryOperator):
    def operate(x, y):
        return x or y


class Equal(BinaryOperator):
    def operate(x, y):
        return x == y


class LowerOrEqual(BinaryOperator):
    def operate(x, y):
        return x <= y


class LowerThan(BinaryOperator):
    def operate(x, y):
        return x < y


class GreaterOrEqual(BinaryOperator):
    def operate(x, y):
        return x >= y


class GreaterThan(BinaryOperator):
    def operate(x, y):
        return x > y
