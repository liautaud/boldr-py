from . import errors

# TODO: Debug only!
SERVER_HOST = 'localhost'
SERVER_PORT = 4242

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

def serialize(expression):
    raise errors.NotYetImplementedError


def unserialize(str):
    raise errors.NotYetImplementedError


def encode(value):
    raise errors.NotYetImplementedError


def decode(expression):
    return expression.decode()


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
            raise TypeError

        for field, argument in zip(self.fields, args):
            parameter, constraint = field

            if not isinstance(argument, constraint):
                raise TypeError

            setattr(self, parameter, argument)

    def __repr__(self):
        args = [getattr(self, parameter) for (parameter, _) in self.fields]
        return self.__class__.__name__ + ' (' + ', '.join(args) + ')'

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
        """
        Evaluate the QIR expression on a remote QIR server.

        To do so, we first serialize the entire QIR expression if possible,
        then send it to the remote server, wait for it to reply with a
        serialized QIR expression, which we finally unserialize.
        """
        # TODO: Handle the environment properly. This will suck.
        return 

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
