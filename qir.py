from errors import *
from meta import *

import types

# TODO:
# - Finding a way to evaluate lambda functions locally without dirty hacks,
#   for instance by passing on an environment containing the bindings in
#   the current scope. Then, evaluateing a lambda would just mean evaluating
#   its body in the new environment.
# - Creating a fluent interface to construct QIR expressions, which would
#   automatically handle making calls to encode() and decode().
# - Finding out how to make sure that .evaluate() gets called on an expression
#   as late as possible.
# - Handling the encoding and decoding of QIR expressions to native Python
#   values.


def encode(value):
    raise NotYetImplementedError


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

    def evaluate(self):
        """
        Evaluate the QIR expression.

        We first try to evaluate the expression on a remote QIR server, which
        typically yields better performance as the QIR server implements a
        normalization module that can optimize away complex user-defined
        functions and prevent query avalanche.

        Sometimes, however, the expression cannot be evaluated remotely,
        typically because there is a Local(_) node somewhere in the expression
        tree, and so we have to evaluate it directly in Python at the cost of
        potential query avalanches.
        """
        try:
            return self.evaluate_remotely()
        except NotRemotelyEvaluableError:
            return self.evaluate_locally()

    def evaluate_remotely(self):
        raise NotYetImplementedError

    def evaluate_locally(self):
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
                evaluated.append(argument.evaluate())
            else:
                evaluated.append(argument)

        return self.__class__(*evaluated)

    def decode(self):
        raise NotDecodableError


class Value(Expression):
    """
    A QIR expression representing a value.

    Those values are the basic building blocks of the QIR data model, which is
    independent of both the data models of the host language (Python in this
    case) and the target database.

    This class is abstract, and should not be instantiated directly.
    """
    def evaluate_locally(self):
        return self

    def decode(self):
        return self.value


class Null(Value):
    """  A QIR expression representing the null value. """
    fields = ()

    def decode(self):
        return None


class Number(Value):
    """ A QIR expression representing an integer value. """
    fields = (('value', int))


class Double(Value):
    """ A QIR expression representing a floating point value. """
    fields = (('value', int))


class String(Value):
    """ A QIR expression representing a string value. """
    fields = (('value', str))


class Boolean(Value):
    """ A QIR expression representing a boolean value. """
    fields = (('value', bool))


class Operator(Expression):
    """
    A QIR operator.

    Operators represent computations on database tables. They are designed to
    be close to operators of relational algebra, in order to facilitate
    rewritings and translation to database native languages.

    This class is abstract, and should not be instantiated directly.
    """


class Scan(Operator):
    """
    A QIR expression representing the Scan operator of relational algebra.

    When evaluated, Scan(table) will output the unordered list of elements in
    the target table corresponding to table.
    """
    fields = (('table', Expression))

    def evaluate_locally(self):
        raise NotYetImplementedError


class Select(Operator):
    """
    A QIR expression representing the Select operator of relational algebra.

    When evaluated, Select(filter, input) will output the list of elements v
    in the list corresponding to input such that filter(v) reduces to true.
    """
    fields = (
        ('filter', Expression),
        ('input', Expression))

    def evaluate_locally(self):
        raise NotYetImplementedError


class Project(Operator):
    """
    A QIR expression representing the Project operator of relational algebra.

    When evaluated, Project(format, input) will output the list of elements
    corresponding to format(v), with v ranging in the list corresponding to
    input.
    """
    fields = (
        ('format', Expression),
        ('input', Expression))

    def evaluate_locally(self):
        raise NotYetImplementedError


class Sort(Operator):
    """
    A QIR expression representing the Sort operator of relational algebra.

    When evaluated, Sort(comp, input) will output the list of elements v in
    the list corresponding to input ordered according to comp(v) ascending.
    """
    fields = (
        ('comp', Expression),
        ('input', Expression))

    def evaluate_locally(self):
        raise NotYetImplementedError


class Limit(Operator):
    """
    A QIR expression representing the Limit operator of relational algebra.

    When evaluated, Limit(limit, input) will output the list of the first
    limit elemenst of the list corresponding to input.
    """
    fields = (
        ('limit', Expression),
        ('input', Expression))

    def evaluate_locally(self):
        raise NotYetImplementedError


class Group(Operator):
    """
    A QIR expression representing the Group operator of relational algebra.

    When evaluated, Group(eq, agg, input) will output the list of elements
    corresponding to agg(g) for each group g in the partition of the elements
    v in the list corresponding to input, according to eq(v).
    """
    fields = (
        ('eq', Expression),
        ('agg', Expression),
        ('input', Expression))

    def evaluate_locally(self):
        raise NotYetImplementedError


class Join(Operator):
    """
    A QIR expression representing the Join operator of relational algebra.

    When evaluated, Join(filter, left, right) will output the join of the
    elements v1 in the list corresponding to left and the elements v2 in the
    list corresponding to right, such that filter(v1, v2) reduces to true.
    """
    fields = (
        ('filter', Expression),
        ('left', Expression),
        ('right', Expression))

    def evaluate_locally(self):
        raise NotYetImplementedError


class Identifier(Expression):
    """ A QIR expression representing the name of a variable. """
    fields = (('name', str))

    def evaluate_locally(self):
        raise NotYetImplementedError


class Lambda(Expression):
    """ A QIR expression representing a one-parameter anonymous function. """
    fields = (
        ('parameter', Identifier),
        ('body', Expression))

    def evaluate_locally(self):
        # The body of a function must not be evaluated before the function
        # gets applied to an argument.
        return self


class Application(Expression):
    """ A QIR expression representing a function application. """
    fields = (
        ('function', Expression),
        ('argument', Expression))

    def evaluate_locally(self):
        # Beware that we must evaluate the argument before the function.
        evaluated_argument = self.argument.evaluate()
        evaluated_function = self.function.evaluate()

        if (isinstance(evaluated_function, Local) and
            isinstance(evaluated_function.value, types.FunctionType)):
            return encode(
                evaluated_function.value(
                    decode(evaluated_argument)))

        if isinstance(evaluated_function, Lambda):
            raise NotYetImplementedError

        else:
            raise TypeError


class Conditional(Expression):
    """ A QIR expression representing a conditional statement. """
    fields = (
        ('condition', Expression),
        ('on_true', Expression),
        ('on_false', Expression))

    def evaluate_locally(self):
        raise NotYetImplementedError


class ListConstr(Expression):
    """
    A QIR expression representing a list constructor.

    This class is abstract, and should not be instantiated directly.
    """


class ListNil(ListConstr):
    """ A QIR expression representing the empty list constructor. """
    fields = ()

    def evaluate_locally(self):
        return self

    def decode(self):
        return ()


class ListCons(ListConstr):
    """ A QIR expression representing the (::) list constructor. """
    fields = (
        ('head', Expression),
        ('tail', Expression))

    def evaluate_locally(self):
        return ListCons(self.head.evaluate(), self.tail.evaluate())

    def decode(self):
        return (self.head().decode(),) + self.tail().decode()


class ListDestr(Expression):
    """
    A QIR expression representing the list destructor.

    When evaluated, it will output on_nil if input evaluates to the empty
    list, and on_cons(head(input), tail(input)) otherwise.
    """
    fields = (
        ('input', Expression),
        ('on_nil', Expression),
        ('on_cons', Expression))

    def evaluate_locally(self):
        input = self.input.evaluate()

        if isinstance(input, ListNil):
            return self.on_nil.evaluate()
        elif isinstance(input, ListCons):
            return \
                Application(
                    Application(self.on_cons.evaluate(), input.head),
                    input.tail
                ).evaluate()
        else:
            raise TypeError


class TupleConstr(Expression):
    """
    A QIR expression representing a tuple constructor.

    Note that tuples in the QIR data model are actually just linked lists of
    (key, value) pairs, so the implementation of List and Tuple is similar.

    This class is abstract, and should not be instantiated directly.
    """


class TupleNil(TupleConstr):
    """ A QIR expression representing the empty tuple constructor. """
    fields = ()

    def evaluate_locally(self):
        return self

    def decode(self):
        return {}


class TupleCons(TupleConstr):
    """ A QIR expression representing the (::) tuple constructor. """
    fields = (
        ('key', Expression),
        ('value', Expression),
        ('tail', Expression))

    def evaluate_locally(self):
        return TupleCons(
            self.key.evaluate(),
            self.value.evaluate(),
            self.tail.evaluate())

    def decode(self):
        decoded = self.tail.decode()
        decoded[self.key.decode()] = self.value.decode()
        return decoded


class TupleDestr(Expression):
    """ A QIR expression representing the tuple key accessor. """
    fields = (
        ('input', Expression),
        ('key', Expression))

    def evaluate_locally(self):
        input = self.input.evaluate()
        key = self.key.evaluate()

        if not isinstance(key, String):
            return Null

        def traverse(input):
            if isinstance(input, TupleNil):
                return Null
            elif isinstance(input, TupleCons) and input.key == key:
                return input.value
            elif isinstance(input, TupleCons):
                return traverse(input.tail)
            else:
                raise TypeError

        return traverse(input)


class Local(Expression):
    """
    A special QIR expression which wraps any type of Python value which can
    not be serialized, and thus should only be evaluated locally.
    """
    fields = (('value', object))

    def evaluate_locally(self):
        return self

    def evalutate_remotely(self):
        raise NotRemotelyEvaluableError

    def decode(self):
        return self.value


class Builtin(Expression):
    """ A QIR expression representing a Python builtin function. """
    fields = (
        ('module', str),
        ('name', str),
        ('function', types.BuiltinFunctionType))

    def evaluate_locally(self):
        return Local(self.function)


class Reference(Expression):
    """ A QIR expression representing a reference to data from a database. """
    fields = (
        ('input', str),
        ('identifier', str))

    def evaluate_locally(self):
        raise NotLocallyEvaluableError


class Bytecode(Expression):
    """ A QIR expression representing CPython bytecode. """
    fields = (('code', types.CodeType))

    def __repr__(self):
        return 'Bytecode (◾)'

    def evaluate_locally(self):
        raise NotYetImplementedError
