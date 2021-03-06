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

    def evaluate_locally(self, environment={}):
        raise errors.NotYetImplementedError


class Filter(Operator):
    """
    A QIR expression representing the Filter operator of relational algebra.

    When evaluated, Filter(filter, input) will output the list of elements v
    in the list corresponding to input such that filter(v) reduces to true.
    """
    fields = (
        ('filter', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment={}):
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

    def evaluate_locally(self, environment={}):
        raise errors.NotYetImplementedError


class Sort(Operator):
    """
    A QIR expression representing the Sort operator of relational algebra.

    When evaluated, Sort(rows, ascending, input) will output the list of
    elements v in the list corresponding to input ordered based on the rows of
    the list corresponding to rows, in ascending or descending ordering
    depending on ascending.
    """
    fields = (
        ('rows', base.Expression),
        ('ascending', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment={}):
        raise errors.NotYetImplementedError


class Limit(Operator):
    """
    A QIR expression representing the Limit operator of relational algebra.

    When evaluated, Limit(limit, input) will output the list of the first
    limit elements of the list corresponding to input.
    """
    fields = (
        ('limit', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment={}):
        raise errors.NotYetImplementedError


class Group(Operator):
    """
    A QIR expression representing the Group operator of relational algebra.

    When evaluated, Group(rows, input) will output the list of elements v in
    the list corresponding to input, grouped by the rows in the list
    corresponding to rows.
    """
    fields = (
        ('rows', base.Expression),
        ('input', base.Expression))

    def evaluate_locally(self, environment={}):
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

    def evaluate_locally(self, environment={}):
        raise errors.NotYetImplementedError
