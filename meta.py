import dis
import types
import builtins


def is_builtin(value):
    """ Return whether the value is a built-in function. """
    return isinstance(
        value, (types.BuiltinFunctionType, types.BuiltinMethodType))


class Function:
    """
    A simple wrapper around a Python function which augments it with
    introspection capabilities.

    Instance variables:
    code -- The `code` object which holds the function's compiled bytecode.
    module -- The name of the module in which the function was declared.
    function -- The underlying Python `function` object.
    """

    def __init__(self, function):
        """ Form a Function wrapper. """
        if not isinstance(function, types.FunctionType):
            raise TypeError

        self.function = function
        self.module = function.__module__
        self.code = function.__code__

    def local_names(self):
        """
        Return a set containing the name of the function's local variables.

        In this context, the term "local variables" refers to names in the
        current scope that are referenced from this scope, i.e. names of
        the variables that are (re-)bound inside the current scope as
        well as names of the function's parameters.
        """
        return set(self.code.co_varnames)

    def free_names(self):
        """
        Return a set containing the name of the function's free variables.

        In this context, the term "closure variables" refers to names in
        the current scope that are referenced by inner scopes or names in
        outer scopes that are referenced from this scope. It does not
        include references to global or builtin scopes.
        """
        return set(self.code.co_freevars)

    def global_names(self):
        """
        Return a set containing the name of the function's global variables.

        In this context, the term "global variables" refers to names in
        the global scope that are referenced from this scope.

        For the sake of convience, we have decided that access to nested
        names only counts as "one big name". For instance, given the
        function lambda x: math.sqrt(x), this method would return
        set('math.sqrt') instead of set('math', 'sqrt').
        """
        variables = []
        previous_opname = None

        for instr in dis.get_instructions(self.code):
            if instr.opname == 'LOAD_GLOBAL':
                variables.append((instr.argval,))

            elif instr.opname == 'LOAD_ATTR' and \
                    previous_opname in ['LOAD_GLOBAL', 'LOAD_ATTR']:
                variables.append(variables.pop() + (instr.argval,))

            previous_opname = instr.opname

        return set(map('.'.join, variables))

    def global_value(self, variable):
        """
        Return the current value of one of the function's global variables.

        This value comes from the function's __globals__ attribute, which
        contains the name and value of every variable in the function's
        global scope. This is important in order to support functions
        which are defined in another module because what Python
        calls a "global scope" is actually just limited to the
        module where the function was defined.

        If the value is not found in the function's __globals__ attribute,
        the function also searches the builtins module.
        """
        def lookup(variable, source):
            parts = variable.split('.', 1)

            if isinstance(source, dict):
                source = source[parts[0]]
            else:
                source = getattr(source, parts[0])

            if len(parts) == 1:
                return source
            else:
                return lookup(parts[1], source)

        try:
            return lookup(variable, self.function.__globals__)
        except (LookupError, AttributeError):
            return lookup(variable, builtins)

    def global_values(self):
        """
        Return a dictionary containing the name and value of the function's
        global variables. The dictionary doesn't contain the variables
        whose name is not yet defined in the function's global scope.
        """
        values = {}

        for variable in self.global_names():
            try:
                values[variable] = self.global_value(variable)
            except (LookupError, AttributeError):
                pass

        return values
