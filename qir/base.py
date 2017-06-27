from . import errors

import grpc
import qir_pb2_grpc

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8080


# TODO:
# - Finding a way to evaluate lambda functions locally without dirty hacks,
#   for instance by passing on an environment containing the bindings in
#   the current scope. Then, evaluateing a lambda would just mean evaluating
#   its body in the new environment.
# - Creating a fluent interface to construct QIR expressions, which would
#   automatically handle making calls to encode() and decode().
# - Finding out how to make sure that evaluate gets called on an expression
#   as late as possible.
# - Handling the encoding and decoding of QIR expressions to native Python
#   values.


class Expression:
    """
    A QIR expression.

    This class is abstract, and should not be instantiated directly.
    """
    fields = None

    def __init__(self, *args):
        if self.fields is None:
            raise NotImplementedError

        if len(args) != len(self.fields):
            raise TypeError(
                'Expected %d arguments for %s, got %d' %
                (len(self.fields), self.__name__, len(args)))

        for field, argument in zip(self.fields, args):
            if not isinstance(argument, field[1]):
                raise TypeError(
                    'Expected argument `%s` to be an instance of %s, got %s' %
                    (field[0], field[1], argument))

            setattr(self, field[0], argument)

    def __repr__(self):
        args = [repr(getattr(self, field[0])) for field in self.fields]
        return self.__class__.__name__ + '(' + ', '.join(args) + ')'

    def evaluate(self, environment={}):
        """
        Evaluate the QIR expression.

        We first try to evaluate the expression on a remote QIR server, which
        typically yields better performance as the QIR server implements a
        normalization module that can optimize away complex user-defined
        functions and prevent query avalanche.

        Sometimes, however, the expression cannot be evaluated remotely,
        typically because there is a Local(_) node somewhere in the
        expression tree, so we have to evaluate it directly in Python.
        """
        try:
            return self.evaluate_remotely(environment)

        except errors.NotRemotelyEvaluableError:
            return self.evaluate_locally(environment)

    def evaluate_remotely(self, environment):
        from . import utils

        """
        Evaluate the QIR expression on a remote QIR server.

        To do so, we first serialize the entire QIR expression if possible,
        then send it to the remote server, wait for it to reply with a
        serialized QIR expression, which we finally unserialize.
        """
        # TODO: Handle the environment properly. This will suck.
        try:
            address = SERVER_HOST + ':' + str(SERVER_PORT)
            channel = grpc.insecure_channel(address)
            stub = qir_pb2_grpc.EvaluatorStub(channel)

            return utils.unserialize(stub.Evaluate(utils.serialize(self)))

        except errors.NotSerializableError:
            raise errors.NotRemotelyEvaluableError

    def evaluate_locally(self, environment):
        """
        Evaluate the QIR expression directly in Python.

        The default behavior is to recursively evaluate all the arguments of
        the expression from first to last, and then return a new instance of
        the expression where the arguments are replaced with their evaluated
        counterparts.
        """
        evaluated = []

        for (parameter, _) in self.fields:
            argument = getattr(self, parameter)

            if isinstance(argument, Expression):
                evaluated.append(argument.evaluate(environment))
            else:
                evaluated.append(argument)

        return self.__class__(*evaluated)

    def decode(self):
        raise errors.NotDecodableError


class UnserializableExpression(Expression):
    pass
