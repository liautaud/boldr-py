from . import base
from . import errors
import types


class Native(base.UnserializableExpression):
    """
    A special QIR expression which wraps any native Python value.
    """
    fields = (('value', object),)

    def evaluate_locally(self, environment={}):
        return self

    def evalutate_remotely(self, environment={}):
        raise errors.NotRemotelyEvaluableError

    def decode(self):
        return self.value


class Builtin(base.Expression):
    """ A QIR expression representing a Python builtin function. """
    fields = (
        ('module', str),
        ('name', str),
        ('function', types.BuiltinFunctionType, False))

    def evaluate_locally(self, environment={}):
        return Native(self.function)


class Bytecode(base.Expression):
    """ A QIR expression representing CPython bytecode. """
    fields = (('code', types.CodeType),)

    def __repr__(self):
        return 'Bytecode(<code>)'

    def evaluate_locally(self, environment={}):
        return Native(types.FunctionType(self.code))


class Database(base.Expression):
    """ A QIR expression representing a reference to a database table. """
    fields = (
        ('driver', str),
        ('name', str),
        ('host', str),
        ('port', int),
        ('username', str),
        ('password', str))

    def evaluate_locally(self, environment={}):
        raise errors.NotLocallyEvaluableError


class Table(base.Expression):
    fields = (
        ('database', Database),
        ('name', str))

    def evaluate_locally(self, environment={}):
        # Because the Python client is not directly connected to the database
        # servers, we must evaluate the node on the QIR server.
        return self.evaluate_remotely()
