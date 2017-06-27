from . import *

import collections
import google.protobuf
import qir_pb2

def serialize(expression):
    """
    Transform a QIR expression into the corresponding Protocol Buffer message.

    This message can then be transmitted in its binary encoding to a remote
    QIR server to evaluate it. This is done using the grpc library.
    """
    message = qir_pb2.Expression()

    def aux(expression, message):
        if isinstance(expression, base.UnserializableExpression):
            raise errors.NotSerializableError

        if not isinstance(expression, base.Expression):
            raise errors.NotSerializableError

        # Get all the properties of the expression which should be serialized.
        fields = filter(
            lambda field: len(field) < 3 or not field[2],
            expression.fields)

        node = getattr(message, expression.__class__.__name__)
        node.SetInParent()

        for field in fields:
            property = getattr(expression, field[0])

            # Maybe we need to serialize the property as well?
            if isinstance(property, base.Expression):
                aux(property, getattr(node, field[0]))
            else:
                setattr(node, field[0], property)

    aux(expression, message)
    return message


def unserialize(message):
    """
    Transform a Protocol Buffer message into the corresponding QIR expression.
    """
    if not isinstance(message, google.protobuf.message.Message):
        return message
    elif not isinstance(message, qir_pb2.Expression):
        raise errors.NotUnserializableError

    expression_type = message.WhichOneof('node')
    expression_class = globals()[expression_type]

    args = [unserialize(getattr(getattr(message, expression_type), field[0]))
            for field in expression_class.fields]

    return expression_class(*args)


def encode(value):
    if value is None:
        return Null
    elif isinstance(value, bool):
        return Boolean(value)
    elif isinstance(value, int):
        return Number(value)
    elif isinstance(value, float):
        return Double(value)
    elif isinstance(value, str):
        return String(value)
    elif isinstance(value, dict):
        return encode_dict(value)
    elif isinstance(value, collections.Iterable):
        return encode_list(list(value))

    raise TypeError


def encode_dict(source):
    inner = TupleNil()
    for key in source:
        inner = TupleCons(String(key), encode(source[key]), inner)
    return inner


def encode_list(source):
    inner = ListNil()
    for value in source:
        inner = ListCons(encode(value), inner)
    return inner


def decode(expression):
    return expression.decode()
