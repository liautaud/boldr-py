class NotYetImplementedError(NotImplementedError):
    """
    An exception indicating that a function or method is not yet implemented,
    but will be in a future release of the library.
    """


class NotUnserializableError(Exception):
    pass


class NotSerializableError(Exception):
    pass


class NotRemotelyEvaluableError(Exception):
    """
    An exception indicating that a QIR expression can't be evaluated remotely.

    This typically happens when there is a Local(_) node somewhere in the
    expression tree, which makes it impossible to serialize the expression,
    and thus to evaluate it remotely.
    """


class NotLocallyEvaluableError(Exception):
    """
    An exception indicating that a QIR expression can't be evaluated locally.

    This typically happens when there is a Reference(_, _) node somewhere in
    the expression tree, which is only evaluable remotely - as its evaluation
    requires making calls to a database.
    """


class NotDecodableError:
    """
    An exception indicating that a QIR expression can't be decoded into a
    native Python value.

    Maybe you could try decode(expression.evaluate())?
    """


class NotEncodableError:
    """
    An exception indicating that a native Python value can't be encoded into
    a QIR expression accurately.

    This happens mostly with complex values such as (anonymous) functions,
    generators or modules.
    """
