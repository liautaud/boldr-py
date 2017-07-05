from . import base
from . import errors


class UnaryOperator(base.Expression):
    """
    A QIR unary algebraïc operator.

    This class is abstract, and should not be instantiated directly.
    """
    fields = (('element', base.Expression),)

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Not(UnaryOperator):
    pass


class BinaryOperator(base.Expression):
    """
    A QIR binary algebraïc operator.

    This class is abstract, and should not be instantiated directly.
    """
    fields = (
        ('left', base.Expression),
        ('right', base.Expression))

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Div(BinaryOperator):
    pass

class Minus(BinaryOperator):
    pass

class Mod(BinaryOperator):
    pass

class Plus(BinaryOperator):
    pass

class Star(BinaryOperator):
    pass

class Power(BinaryOperator):
    pass

class And(BinaryOperator):
    pass

class Or(BinaryOperator):
    pass

class Equal(BinaryOperator):
    pass

class LowerOrEqual(BinaryOperator):
    pass

class LowerThan(BinaryOperator):
    pass
