from . import *

import dis
import graphviz


NORMAL_FLOW = 0
JUMP_FLOW = 1

JUMP_OPNAMES = [
    'JUMP_FORWARD',
    'JUMP_ABSOLUTE',
    'CONTINUE_LOOP']

BRANCH_POP_OPNAMES = [
    'POP_JUMP_IF_TRUE',
    'POP_JUMP_IF_FALSE']

BRANCH_MAY_POP_OPNAMES = [
    'JUMP_IF_TRUE_OR_POP',
    'JUMP_IF_FALSE_OR_POP']

BRANCH_OPNAMES = \
    BRANCH_POP_OPNAMES + \
    BRANCH_MAY_POP_OPNAMES


class PredecessorStacksError(Exception):
    pass


class Decompiler():
    def __init__(self):
        self.blocks = []
        self.edges = []

        # In order to be able to compute the graph in linear time, we keep a
        # mapping of the block in which any instruction is contained.
        self.block_mapping = {}

    @property
    def first_block(self):
        return self.blocks[0]

    @property
    def previous_block(self):
        return self.blocks[-2]

    @property
    def current_block(self):
        return self.blocks[-1]

    def build_graph(self, instructions):
        """
        Separate the instructions into blocks and build a control flow graph.
        """

        # The offset before which all instructions should be added to the
        # current block as is, no matter their type.
        ignore_until = False

        # Whether to start a new block on the next instruction, even if it
        # is not a jump target.
        force_new = True

        for instruction in instructions:
            if instruction.offset < ignore_until:
                self.current_block.add(instruction)

            elif instruction.opname == 'SETUP_LOOP':
                self.blocks.append(LoopBlock(self, instruction))
                ignore_until = instruction.argval
                force_new = True

            elif instruction.opname in JUMP_OPNAMES:
                self.blocks.append(JumpBlock(self, instruction))
                force_new = True

            elif instruction.opname in BRANCH_OPNAMES:
                self.blocks.append(BranchBlock(self, instruction))
                force_new = True

            else:
                if instruction.is_jump_target or force_new:
                    force_new = False
                    self.blocks.append(LinearBlock(self))

                self.current_block.add(instruction)

        # Once all the blocks have been created - which also means that all
        # the instructions were assigned to one and only one block - we can
        # "close" the blocks. For instance, this allows JumpBlocks and
        # BranchBlocks to translate the offset of the instruction they
        # should jump to into the block which contains that instruction.
        for block in self.blocks:
            block.close()

        # Finally, we compute a reverse map of the direct predecessors of
        # every block so that execute_blocks can run in linear time.
        for block in self.blocks:
            for (successor, edge_type) in block.successors:
                successor.predecessors.append((block, edge_type))

    def sort_blocks(self):
        """
        Compute a topological ordering of the control flow graph.

        This is possible as we have removed cycles from the graph by hiding
        them into LoopBlocks, and so the graph is a DAG.
        """
        marked = [False] * len(self.blocks)
        ordering = []

        def visit(block):
            marked[block.index] = True

            for (next, _) in block.successors:
                if not marked[next.index]:
                    visit(next)

            ordering.append(block.index)

        for block in self.blocks:
            if not marked[block.index]:
                visit(block)

        self.ordering = list(reversed(ordering))

    def execute_blocks(self):
        """
        Partially execute each block in topological ordering.
        """
        for index in self.ordering:
            self.blocks[index].execute()

    def express_blocks(self):
        """
        Turn each block into a QIR expression in reversed topological ordering.
        """
        for index in reversed(self.ordering):
            self.blocks[index].express()


class Block():
    def __init__(self, context):
        self.context = context

        # The index of this block in the graph that is being built.
        self.index = len(context.blocks)

        # The instructions which belong to this block.
        self.instructions = []

        # The block to which we should jump once we reach the end of this one.
        self.next = None

        # The blocks from which we could come from.
        # This reverse map will be filled automatically by build_graph.
        self.predecessors = []

        # Whether the block has already reached a RETURN_VALUE instruction.
        self.reached_return = False

        # We add an edge between the previous block and this one.
        if self.index > 0:
            self.context.current_block.next = self

    @property
    def successors(self):
        if self.next is not None:
            return [(self.next, NORMAL_FLOW)]
        else:
            return []

    def add(self, instruction):
        if not self.reached_return:
            self.instructions.append(instruction)

        # Even though we only add the new instruction to the block if we have
        # not yet reached a RETURN_VALUE instruction, we still have to declare
        # that the block contains the new instruction, otherwise we might break
        # the translation from jump offsets to blocks that happens in
        # JumpBlock@close and BranchBlock@close.
        self.context.block_mapping[instruction.offset] = self

        if instruction.opname == 'RETURN_VALUE':
            self.reached_return = True

    def close(self):
        # If the block contains a RETURN_VALUE instruction, we don't want to
        # jump to any other block at the end of this one.
        if self.reached_return:
            self.next = None

    def execute(self):
        """
        Ensure that all the block's direct predecessors share the same final
        stack state, and if so make it the initial state of the block's stack.
        """
        stacks = []

        for (predecessor, edge_type) in self.predecessors:
            # Getting the predecessor's final stack state is slightly tricky
            # when that predecessor is a BranchBlock, as the stack might be
            # popped right before the jump depending on the precise branching
            # instruction and the type of edge that links this block to the
            # predecessor.
            if (isinstance(predecessor, BranchBlock) and
                (predecessor.instruction.opname in BRANCH_POP_OPNAMES or
                 edge_type == NORMAL_FLOW)):
                stacks.append(predecessor.stack[:-1])
            else:
                stacks.append(predecessor.stack[:])

        if len(stacks) < 1:
            self.stack = []
        elif any(stacks[0] != stack for stack in stacks[1:]):
            raise PredecessorStacksError
        else:
            self.stack = stacks[0]


BINARY_OPERATIONS = {
    'BINARY_POWER': Power,
    'BINARY_MULTIPLY': Star,
    'BINARY_TRUE_DIVIDE': Div,
    'BINARY_MODULO': Mod,
    'BINARY_ADD': Plus,
    'BINARY_SUBTRACT': Minus}

INPLACE_OPERATIONS = {
    'INPLACE_POWER': Power,
    'INPLACE_MULTIPLY': Star,
    'INPLACE_TRUE_DIVIDE': Div,
    'INPLACE_MODULO': Mod,
    'INPLACE_ADD': Plus,
    'INPLACE_SUBTRACT': Minus}

COMPARE_OPERATIONS = {
    '==': Equal,
    '<=': LowerOrEqual,
    '<': LowerThan}

class LinearBlock(Block):
    def execute(self):
        super().execute()

        stack = self.stack
        bindings = []

        for instruction in self.instructions:
            name = instruction.opname

            # General instructions
            if name == 'NOP':
                pass
            elif name == 'POP_TOP':
                stack.pop()
            elif name == 'ROT_TWO':
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif name == 'ROT_THREE':
                stack[-1], stack[-2], stack[-3] =\
                    stack[-2], stack[-3], stack[-1]
            elif name == 'DUP_TOP':
                stack.append(stack[-1])
            elif name == 'DUP_TOP_TWO':
                stack.append(stack[-2])
                stack.append(stack[-2])

            # Binary and in-place operations
            elif name in BINARY_OPERATIONS:
                right = stack.pop()
                left = stack.pop()
                stack.append(BINARY_OPERATIONS[name](left, right))
            elif name in INPLACE_OPERATIONS:
                right = stack.pop()
                left = stack.pop()
                stack.append(INPLACE_OPERATIONS[name](left, right))
            elif (name == 'COMPARE_OP' and
                  instruction.argval in COMPARE_OPERATIONS):
                right = stack.pop()
                left = stack.pop()
                stack.append(
                    COMPARE_OPERATIONS[instruction.argval](left, right))
            elif name == 'BINARY_SUBSCR':
                key = stack.pop()
                container = stack.pop()
                stack.append(TupleDestr(container, key))
            elif name == 'STORE_SUBSCR':
                key = stack.pop()
                container = stack.pop()
                value = stack.pop()
                stack.append(TupleCons(key, value, container))
            elif name == 'DELETE_SUBSCR':
                container = stack.pop()
                value = stack.pop()
                stack.append(TupleCons(key, Null, container))

            # Miscellaneous opcodes
            elif name == 'RETURN_VALUE':
                self.returns = True
            elif name == 'LOAD_CONST':
                stack.append(encode(instruction.argval))
            elif (name == 'LOAD_NAME' or
                  name == 'LOAD_GLOBAL' or
                  name == 'LOAD_FAST'):
                stack.append(Identifier(instruction.argval))
            elif name == 'LOAD_ATTR':
                container = stack.pop()
                stack.append(TupleDestr(container, String(instruction.argval)))
            elif (name == 'STORE_NAME' or
                  name == 'STORE_FAST'):
                value = stack.pop()
                bindings.append((instruction.argval, value))
            elif name == 'STORE_GLOBAL':
                raise NotImplementedError
            elif (name == 'DELETE_NAME' or
                  name == 'DELETE_FAST'):
                bindings.append((instruction.argval, Null))
            elif name == 'DELETE_GLOBAL':
                raise NotImplementedError

            elif (name == 'BUILD_TUPLE' or
                  name == 'BUILD_LIST' or
                  name == 'BUILD_SET'):
                pos = (-1) * instruction.argval
                values = stack[pos:]
                stack = stack[:pos]

                container = ListNil()
                for value in values:
                    container = ListCons(value, container)

                stack.append(container)

            elif name == 'BUILD_MAP':
                pos = (-1) * instruction.argval
                values = stack[pos:]
                stack = stack[:pos]

                container = TupleNil()
                for key, value in zip(values[0::2], values[1::2]):
                    container = TupleCons(key, value, container)

                stack.append(container)

            elif name == 'BUILD_STRING':
                pos = (-1) * instruction.argval
                values = stack[pos:]
                stack = stack[:pos]

                string = ''.join(map(lambda x: x.value, values))
                stack.append(String(string))

            # Other opcodes
            else:
                raise NotImplementedError

        self.stack = stack
        self.bindings = bindings

    def express(self):
        if self.next is None and self.reached_return:
            inner = self.stack[-1]
        elif self.next is None:
            inner = Null
        else:
            inner = self.next.expression

        # Wrap the expression inside all the variable bindings.
        for (name, value) in reversed(self.bindings):
            inner = Application(Lambda(Identifier(name), inner), value)

        self.expression = inner

class JumpBlock(Block):
    def __init__(self, context, instruction):
        super().__init__(context)
        self.instruction = instruction
        self.add(instruction)

    def close(self):
        super().close()

        # Because we will always take the jump, we can replace the edge which
        # was created between this block and the one that follows it with a
        # new edge between this block and the one it should jump to.
        self.next = self.context.block_mapping[self.instruction.argval]

    def express(self):
        self.expression = self.next.expression


class BranchBlock(Block):
    def __init__(self, context, instruction):
        super().__init__(context)
        self.instruction = instruction
        self.add(instruction)

    @property
    def successors(self):
            return [(self.next, NORMAL_FLOW), (self.next_jumped, JUMP_FLOW)]

    def close(self):
        super().close()

        # We keep self.next untouched - it will point to the block to go to if
        # we don't take the jump, and we add self.next_jumped which will point
        # to the block to go to if we take the jump.
        self.next_jumped = self.context.block_mapping[self.instruction.argval]

    def express(self):
        condition = self.stack[-1]

        if self.instruction.opname in \
                ['POP_JUMP_IF_FALSE', 'JUMP_IF_FALSE_OR_POP']:
            on_true = self.next.expression
            on_false = self.next_jumped.expression

        elif self.instruction.opname in \
                ['POP_JUMP_IF_TRUE', 'JUMP_IF_TRUE_OR_POP']:
            on_true = self.next_jumped.expression
            on_false = self.next.expression

        self.expression = Conditional(condition, on_true, on_false)


class LoopBlock(Block):
    def __init__(self, context, instruction):
        super().__init__(context)
        self.instruction = instruction
        self.add(instruction)


def decompile(code):
    decompiler = Decompiler()
    decompiler.build_graph(dis.get_instructions(code))
    decompiler.sort_blocks()
    decompiler.execute_blocks()
    decompiler.express_blocks()

    return decompiler.first_block.expression


def preview(code):
    TYPES = ['NORMAL_FLOW', 'JUMP_FLOW']

    graph = graphviz.Digraph()

    decompiler = Decompiler()
    decompiler.build_graph(dis.get_instructions(code))

    dis.dis(code)

    for block in decompiler.blocks:
        name = block.__class__.__name__

        if isinstance(block, (JumpBlock, BranchBlock)):
            label = name + '(' + block.instruction.opname + ')'
        else:
            offsets = ', '.join(
                map(lambda instr: str(instr.offset), block.instructions))
            label = name + '(' + offsets + ')'

        graph.node(str(block.index), '[' + str(block.index) + '] ' + label)

        for (next, edge_type) in block.successors:
            graph.edge(
                str(block.index), str(next.index), label=TYPES[edge_type])

    graph.render('test/cfg.gv', view=True)


def foo(x):
    y = x + 2
    if y % 2 == 0:
        z = True
    else:
        z = False
    return z

def bar(x):
    for z in range(x, 0, -1):
        print(z)
    return None

def baz(z):
    if foo:
        return True
    else:
        return False

    return 'bla'

def buz(x, y):
    if x or y:
        z = 1
    else:
        z = 2
    return z

def bol(x, y, z):
    z = z + 1
    u = x < y == z
    return u
