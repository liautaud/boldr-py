from . import base
from . import utils


class LocalOperator:
    def __call__(self, element):
        if isinstance(element, base.Expression):
            return element.evaluate_locally()
        else:
            return utils.encode(element).evaluate_locally()

    def __mod__(self, element):
        return self.__call__(element)


class BatchOperator:
    def __call__(self, element):
        if isinstance(element, base.Expression):
            return element.evaluate_remotely()
        else:
            return utils.encode(element).evaluate_remotely()

    def __mod__(self, element):
        return self.__call__(element)


local = LocalOperator()
batch = BatchOperator()
