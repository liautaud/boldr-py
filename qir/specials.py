from . import base
from . import errors
import types


class Local(base.UnserializableExpression):
    """
    A special QIR expression which wraps any type of Python value which can't
    be serialized, and thus must only be evaluated locally.
    """
    fields = (('value', object),)

    def evaluate_locally(self, environment):
        return self

    def evalutate_remotely(self):
        # TODO: This approach (hijacking the evaluate_remotely function) won't
        # work because be might serialize from a parent. We should hijack the
        # serialize() function once it exists.
        raise errors.NotRemotelyEvaluableError

    def decode(self):
        return self.value


class Builtin(base.Expression):
    """ A QIR expression representing a Python builtin function. """
    fields = (
        ('module', str),
        ('name', str),
        ('function', types.BuiltinFunctionType, False))

    def evaluate_locally(self, environment):
        return Local(self.function)


class Bytecode(base.Expression):
    """ A QIR expression representing CPython bytecode. """
    fields = (('code', types.CodeType),)

    def __repr__(self):
        return 'Bytecode(...)'

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Reference(base.Expression):
    """ A QIR expression representing a reference to data from a database. """
    fields = (
        ('input', str),
        ('identifier', str))

    def evaluate_locally(self, environment):
        raise errors.NotLocallyEvaluableError
