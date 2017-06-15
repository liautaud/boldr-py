from . import base
from . import errors


class Operator(base.Expression):
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
    fields = (('table', base.Expression),)

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Select(Operator):
    """
    A QIR expression representing the Select operator of relational algebra.

    When evaluated, Select(filter, input) will output the list of elements v
    in the list corresponding to input such that filter(v) reduces to true.
    """
    fields = (
        ('filter', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Project(Operator):
    """
    A QIR expression representing the Project operator of relational algebra.

    When evaluated, Project(format, input) will output the list of elements
    corresponding to format(v), with v ranging in the list corresponding to
    input.
    """
    fields = (
        ('format', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Sort(Operator):
    """
    A QIR expression representing the Sort operator of relational algebra.

    When evaluated, Sort(comp, input) will output the list of elements v in
    the list corresponding to input ordered according to comp(v) ascending.
    """
    fields = (
        ('comp', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Limit(Operator):
    """
    A QIR expression representing the Limit operator of relational algebra.

    When evaluated, Limit(limit, input) will output the list of the first
    limit elemenst of the list corresponding to input.
    """
    fields = (
        ('limit', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Group(Operator):
    """
    A QIR expression representing the Group operator of relational algebra.

    When evaluated, Group(eq, agg, input) will output the list of elements
    corresponding to agg(g) for each group g in the partition of the elements
    v in the list corresponding to input, according to eq(v).
    """
    fields = (
        ('eq', base.Expression),
        ('agg', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError


class Join(Operator):
    """
    A QIR expression representing the Join operator of relational algebra.

    When evaluated, Join(filter, left, right) will output the join of the
    elements v1 in the list corresponding to left and the elements v2 in the
    list corresponding to right, such that filter(v1, v2) reduces to true.
    """
    fields = (
        ('filter', base.Expression),
        ('left', base.Expression),
        ('right', base.Expression))

    def evaluate_locally(self, environment):
        raise errors.NotYetImplementedError
