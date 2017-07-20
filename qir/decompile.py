from . import *

import dis
import types
import random
import graphviz

from functools import reduce

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

        # In order to be able to compute the graph in linear time, we keep a
        # mapping of the block in which any instruction is contained.
        self.block_mapping = {}

        # Whether to use comprehension mode, which is designed to handle the
        # decompilation of list, set and map comprehensions. In this mode, a
        # FOR_ITER instruction will be turned into a ComprehensionLoopBlock
        # instead of a ForLoopBlock.
        self.comprehension_mode = False

    @property
    def first_block(self):
        return self.blocks[0]

    @property
    def previous_block(self):
        return self.blocks[-2]

    @property
    def current_block(self):
        return self.blocks[-1]

    def build_graph(self, instructions, ignore_loop=False):
        """
        Separate the instructions into blocks and build a control flow graph.

        instructions: The list of instructions to process.
        ignore_loop: Whether to ignore a SETUP_LOOP or a FOR_ITER instruction
        if it is the first instruction of the list. This is useful to avoid
        infinite recursion when using a separate Decompiler instance to
        process the inside of a LoopBlock.
        """

        # The offset before which all instructions should be added to the
        # current block as is, no matter their type.
        ignore_until = False

        # Whether to start a new block on the next instruction, even if it
        # is not a jump target.
        force_new = True

        for i, instruction in enumerate(instructions):
            if instruction.offset < ignore_until:
                self.current_block.add(instruction)

            elif (instruction.opname == 'FOR_ITER' and
                  (not ignore_loop or i > 0)):
                if self.comprehension_mode:
                    block_type = ComprehensionLoopBlock
                else:
                    block_type = ForLoopBlock

                self.blocks.append(block_type(self, instruction))
                ignore_until = instruction.argval
                force_new = True

            # We must determine whether the SETUP_LOOP instruction introduces
            # a for or a while loop in O(1), so what we can do is check
            # whether the next instruction is a jump target, in which case
            # either that instruction is FOR_ITER, and the loop is a for loop,
            # or the loop is a while loop.
            elif (instruction.opname == 'SETUP_LOOP' and
                  instructions[i + 1].opname != 'FOR_ITER' and
                  instructions[i + 1].is_jump_target and
                  (not ignore_loop or i > 0)):
                self.blocks.append(WhileLoopBlock(self, instruction))
                ignore_until = instruction.argval
                force_new = True

            elif instruction.opname in JUMP_OPNAMES:
                self.blocks.append(JumpBlock(self, instruction))
                force_new = True

            elif instruction.opname in BRANCH_OPNAMES:
                self.blocks.append(BranchBlock(self, instruction))
                force_new = True

            elif instruction.opname == 'FOR_ITER':
                self.blocks.append(ForIterBlock(self, instruction))
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

        visit(self.first_block)
        self.ordering = list(reversed(ordering))

    def detach_unreachable(self):
        """
        Detaches all the blocks which are not reachable from the first block.
        As the topological ordering that was computed earlier in sort_blocks
        only explores the first block's connected component, we can easily
        deduce which blocks should be removed.
        """
        for i in set(range(len(self.blocks))) - set(self.ordering):
            self.blocks[i].detach()

    def execute_blocks(self, starting_stack=[], starting_env={}):
        """
        Partially execute each block in topological ordering.
        """
        for index in self.ordering:
            self.blocks[index].execute(starting_stack, starting_env)

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

        # Whether the block contains a RETURN_VALUE instruction.
        self.contains_return = False

        # Whether the block contains a LIST_APPEND instruction.
        self.contains_append = False

        # The expression that the block returns, if any.
        self.returns = None

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
        if not self.contains_return:
            self.instructions.append(instruction)

        # Even though we only add the new instruction to the block if we have
        # not yet reached a RETURN_VALUE instruction, we still have to declare
        # that the block contains the new instruction, otherwise we might break
        # the translation from jump offsets to blocks that happens in
        # JumpBlock@close, BranchBlock@close and ForIterBlock@close.
        self.context.block_mapping[instruction.offset] = self

        if instruction.opname == 'RETURN_VALUE':
            self.contains_return = True

        if instruction.opname in ['LIST_APPEND', 'SET_ADD', 'MAP_ADD']:
            self.contains_append = True

    def close(self):
        # If the block contains a RETURN_VALUE instruction, we don't want to
        # jump to any other block at the end of this one.
        if self.contains_return:
            self.next = None

    def detach(self):
        """
        Detach the block from its neighbours and remove it from the graph.
        """
        for (successor, edge_type) in self.successors:
            successor.predecessors.remove((self, edge_type))

        for (predecessor, edge_type) in self.predecessors:
            if edge_type == NORMAL_FLOW:
                predecessor.next = None
            else:
                predecessor.next_jumped = None

        self.predecessors = []
        self.next = None
        self.next_jumped = None

    def execute(self, starting_stack=[], starting_env={}):
        """
        Ensure that all the block's direct predecessors share the same final
        stack state, and if so make it the initial state of the block's stack.

        The starting_stack is the stack which will be used if the block has no
        predecessors. This is used when dealing with loops, for instance, as
        LoopBlock execute the loop instructions inside a separate builder.
        """
        stacks = []

        for (predecessor, edge_type) in self.predecessors:
            # Getting the predecessor's final stack state is slightly tricky
            # when that predecessor is a BranchBlock, as the stack might be
            # popped right before the jump depending on the precise branching
            # instruction and the type of edge that links this block to the
            # predecessor.
            if isinstance(predecessor, (BranchBlock, ForIterBlock)):
                name = predecessor.instruction.opname
                if ((name == 'FOR_ITER' and
                        edge_type == NORMAL_FLOW) or
                    (name in BRANCH_MAY_POP_OPNAMES and
                        edge_type == JUMP_FLOW)):
                    stacks.append(predecessor.stack[:])
                else:
                    stacks.append(predecessor.stack[:-1])
            else:
                stacks.append(predecessor.stack[:])

        if len(stacks) < 1:
            self.stack = starting_stack[:]
        elif any(stacks[0] != stack for stack in stacks[1:]):
            # Just a little bit of debugging.
            for index in self.context.ordering:
                if index == self.index:
                    break

                block = self.context.blocks[index]
                print('[%d] %s' % (index, str(block.stack)))

            raise PredecessorStacksError((self.index, stacks))
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
    def execute(self, starting_stack=[], starting_env={}):
        super().execute(starting_stack, starting_env)

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
                stack.append(TupleCons(key, Null(), container))

            # Miscellaneous opcodes
            elif name in ['RETURN_VALUE', 'YIELD_VALUE']:
                self.returns = stack.pop()

            elif name in ['LIST_APPEND', 'SET_ADD']:
                value = stack.pop()
                tail = stack[-1 * instruction.argval]
                stack[-1 * instruction.argval] = ListCons(value, tail)

            elif name == 'MAP_ADD':
                key = stack.pop()
                value = stack.pop()
                tail = stack[-1 * instruction.argval]
                stack[-1 * instruction.argval] = TupleCons(key, value, tail)

            elif name == 'POP_BLOCK':
                pass

            elif name == 'LOAD_CONST':
                stack.append(encode(instruction.argval))

            elif (name == 'LOAD_NAME' or
                  name == 'LOAD_GLOBAL' or
                  name == 'LOAD_FAST' or
                  name == 'LOAD_DEREF'):
                stack.append(Identifier(instruction.argval))

            elif name == 'LOAD_CLOSURE':
                pass

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
                bindings.append((instruction.argval, Null()))

            elif name == 'DELETE_GLOBAL':
                raise NotImplementedError

            elif name == 'CALL_FUNCTION':
                count = instruction.argval
                inner = stack[-(count + 1)]

                # Because the QIR functions are currified, we have to make as
                # many applications as there are arguments. The good news is,
                # as the right-most argument is on top of the stack, this is
                # all pretty straightforward.
                for i in range(count):
                    inner = Application(inner, stack.pop())

                stack.pop()
                stack.append(inner)

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

            elif name == 'MAKE_FUNCTION':
                if instruction.argval > 0:
                    raise errors.NotYetImplementedError

                stack.pop()

            elif name == 'MAKE_CLOSURE':
                if instruction.argval > 0:
                    raise errors.NotYetImplementedError

                stack.pop()
                stack.pop(-2)

            elif name == 'SETUP_LOOP':
                pass

            elif name == 'GET_ITER':
                # TODO: Check if this is really the right thing to do.
                pass

            # Other opcodes
            else:
                raise NotImplementedError(name)

        self.stack = stack
        self.bindings = bindings

    def express(self):
        if self.returns is not None:
            inner = self.returns
        elif self.next is None:
            inner = Null()
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


class BaseBranchBlock(Block):
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


class BranchBlock(BaseBranchBlock):
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


class ForIterBlock(BaseBranchBlock):
    def execute(self, starting_stack=[], starting_env={}):
        super().execute(starting_stack, starting_env)

        # We must push a reference to the current value of the iterator on the
        # stack, so that blocks inside the loop's body can use it. We use the
        # instruction's offset as a way to avoid name clashes in nested loops.
        self.stack.append(Identifier('cv_' + str(self.instruction.offset)))

    def express(self):
        self.expression = self.next.expression


class LoopBlock(Block):
    def __init__(self, context, instruction):
        super().__init__(context)
        self.instruction = instruction
        self.add(instruction)

    def execute(self, starting_stack=[], starting_env={}):
        super().execute(starting_stack, starting_env)

        # We use a separate instance of the decompiler to process the code
        # inside the loop. We have to add a placeholder for the instruction
        # following the end of the loop.
        instructions = self.instructions + \
            [dis.Instruction('AFTER_LOOP', -1, None, None,
             None, self.instruction.argval, None, True)]

        # For some reason, breaks are translated into BREAK_LOOP instructions
        # instead of the standard JUMP_ABSOLUTE, so we must fix that manually.
        for i in range(len(instructions)):
            instr = instructions[i]

            if instr.opname == 'BREAK_LOOP':
                instructions[i] = dis.Instruction(
                    'JUMP_ABSOLUTE', 113, self.instruction.argval,
                    self.instruction.argval, None, instr.offset,
                    instr.starts_line, instr.is_jump_target)

        decompiler = Decompiler()
        decompiler.comprehension_mode = self.context.comprehension_mode
        decompiler.build_graph(instructions, True)

        start_block = decompiler.first_block
        last_block = decompiler.current_block

        decompiler.sort_blocks()
        decompiler.detach_unreachable()

        # We then identify the edges which jump back to the start_block, and
        # make them point to a placeholder block instead. This block, once
        # expressed, will turn into a call to on_loop.
        loop_placeholder = PlaceholderBlock(
            decompiler, Application(Identifier('on_loop'), Null()))

        decompiler.blocks.append(loop_placeholder)

        previous_predecessors = start_block.predecessors
        start_block.predecessors = []

        for (predecessor, edge_type) in previous_predecessors:
            if predecessor.index < start_block.index:
                start_block.predecessors.append((predecessor, edge_type))
            elif edge_type == JUMP_FLOW:
                predecessor.next_jumped = loop_placeholder
                loop_placeholder.predecessors.append(
                    (predecessor, JUMP_FLOW))
            else:
                predecessor.next = loop_placeholder
                loop_placeholder.predecessors.append(
                    (predecessor, NORMAL_FLOW))

        # We also replace all the references to the last block, which only
        # contains the AFTER_LOOP instruction that we added earlier, with a
        # placeholder block which will turn into a call to on_after.
        after_placeholder = PlaceholderBlock(
            decompiler, Application(Identifier('on_after'), Null()))

        after_placeholder.index = last_block.index
        decompiler.blocks[last_block.index] = after_placeholder

        for (predecessor, edge_type) in last_block.predecessors:
            if edge_type == JUMP_FLOW:
                predecessor.next_jumped = after_placeholder
                after_placeholder.predecessors.append(
                    (predecessor, JUMP_FLOW))
            else:
                predecessor.next = after_placeholder
                after_placeholder.predecessors.append(
                    (predecessor, NORMAL_FLOW))

        # This is not pretty, but we must remove the edge that is created
        # between a block and the one which follows it.
        loop_placeholder.next = None
        after_placeholder.next = None

        display_graph(decompiler)

        self.loop_placeholder, self.after_placeholder, self.decompiler =\
            loop_placeholder, after_placeholder, decompiler


class WhileLoopBlock(LoopBlock):
    def __init__(self, context, instruction):
        super().__init__(context, instruction)

        # We don't want SETUP_LOOP to appear in the instructions, as the first
        # block of the loop's body should be the jump target.
        if instruction.opname == 'SETUP_LOOP':
            del self.instructions[0]

    def execute(self, starting_stack=[], starting_env={}):
        super().execute(starting_stack, starting_env)
        self.decompiler.execute_blocks(self.stack[:])

    def express(self):
        self.decompiler.express_blocks()

        on_loop = self.decompiler.first_block.expression
        on_after = self.next.expression

        # Using the Y fixed-point combinator, we return a recursive function
        # which can either call itself again (to run the loop once more) or
        # call the rest of the code.
        self.expression = Application(
            Lambda(
                Identifier('on_after'),
                Application(
                    Fixed(),
                    Lambda(
                        Identifier('on_loop'),
                        Lambda(Identifier('_'), on_loop)))),
            Lambda(
                Identifier('_'),
                on_after))


class ForLoopBlock(LoopBlock):
    def execute(self, starting_stack=[], starting_env={}):
        super().execute(starting_stack, starting_env)
        self.decompiler.execute_blocks(self.stack[:])

        # We have to remove the iterator from the stack to reproduce what
        # FOR_ITER does once it jumps out of the loop, but we must also store
        # it somewhere in order to get it back in express().
        self.iterator = self.stack.pop()

    def express(self):
        self.decompiler.express_blocks()

        identifier = 'cv_' + str(self.instruction.offset)
        on_loop = self.decompiler.first_block.expression
        on_after = self.next.expression

        # We have to use the Y fixed-point combinator together with calls to
        # ListDestr. This isn't very pretty, but it's the only way that makes
        # it possible to change variable bindings between iterations - which
        # is not possible with Project().
        self.expression = Application(
            Lambda(
                Identifier('on_after'),
                Application(
                    Lambda(
                        Identifier('current_iterator'),
                        Application(
                            Fixed(),
                            Lambda(
                                Identifier('on_loop'),
                                Lambda(
                                    Identifier('_'),
                                    ListDestr(
                                        Identifier('current_iterator'),
                                        Application(
                                            Identifier('on_after'),
                                            Null()
                                        ),
                                        Lambda(
                                            Identifier(identifier),
                                            Lambda(
                                                Identifier('current_iterator'),
                                                on_loop
                                            )
                                        )
                                    )
                                )))),
                    self.iterator)),
            Lambda(
                Identifier('_'),
                on_after))


class ComprehensionLoopBlock(LoopBlock):
    def execute(self, starting_stack=[], starting_env={}):
        super().execute(starting_stack, starting_env)

        identifier = 'cv_' + str(self.instruction.offset)

        # Even though the graph might contain multiple paths leading to the
        # loop_placeholder block, only one of them contains the LIST_APPEND
        # (or SET_ADD or MAP_ADD) instruction.
        def find_append_path(start, already_found):
            """
            Find the path in the graph which contains the LIST_APPEND, SET_ADD
            or MAP_ADD instruction.

            start: The block from which to start the path.
            already_found: Whether the instruction was already found earlier.
            """
            if start.index == 0:
                return [start] if already_found else None

            if start.contains_append:
                already_found = True

            for (predecessor, edge_type) in start.predecessors:
                path = find_append_path(predecessor, already_found)

                if path is not None:
                    return path + [start]

            return None

        # We keep an environment with the current bindings of all variables so
        # that we can try to substitute identifiers with their values in the
        # terms we encounter along the path.
        environment = starting_env.copy()

        # We also build a conjunction of QIR expressions which must evaluate
        # to True in order for the path to be taken.
        append_when = []

        path = find_append_path(self.loop_placeholder, False)

        for i in range(len(path)):
            block = path[i]
            block.execute(self.stack[:], environment)

            if isinstance(block, LinearBlock):
                for (key, value) in block.bindings:
                    environment[key] = value

            elif isinstance(block, BranchBlock):
                condition = substitute(block.stack[-1], environment)
                is_normal_flow = (path[i + 1].index == block.next.index)

                if ((is_normal_flow and block.instruction.opname in
                     ['POP_JUMP_IF_TRUE', 'JUMP_IF_TRUE_OR_POP']) or
                    (not is_normal_flow and block.instruction.opname in
                     ['POP_JUMP_IF_FALSE', 'JUMP_IF_FALSE_OR_POP'])):
                        condition = Not(condition)

                append_when.append(condition)

        # We have to remove the iterator from the stack to reproduce what
        # FOR_ITER does once it jumps out of the loop, but we must also store
        # it somewhere in order to use it later.
        iterator = self.stack.pop()

        # If the conjunction is not empty, we must filter the iterator to keep
        # only the elements for which the path will be taken.
        if len(append_when) > 0:
            condition = reduce(lambda a, b: And(a, b), append_when)
            iterator = Filter(
                Lambda(Identifier(identifier), condition), iterator)

        # The stack of the last block in the path (excluding loop_placeholder)
        # should now contain a ListCons(head, tail), where head is what gets
        # appened to the list in the comprehension's body; or, in the case of
        # nested loops, a Project() expression.
        source_list = next(item for item in path[-2].stack
                           if isinstance(item, (ListCons, Project)))

        if isinstance(source_list, ListCons):
            source_expression = substitute(source_list.head, environment)
        else:
            source_expression = source_list

        # The trick, now, is just to replace that list with a Project().
        self.stack[-1] = Project(
            Lambda(Identifier(identifier), source_expression), iterator)

    def express(self):
        # We don't want to turn our loop comprehensions into expressions, but
        # rather replace the list on top of the stack, which was supposed to
        # be filled during the iterations of the loop, with a Project(...).
        if self.next is None:
            self.expression = Null()
        else:
            self.expression = self.next.expression


class PlaceholderBlock(Block):
    def __init__(self, context, expression):
        super().__init__(context)
        self.expression = expression

    def execute(self, starting_stack=[], starting_env={}):
        # We don't want to call super().execute() because that might raise a
        # PredecessorStacksError, as we use the same PlaceholderBlock in
        # different branches of While and For loops for instance.
        pass

    def express(self):
        pass


def decompile(code):
    decompiler = Decompiler()
    decompiler.comprehension_mode =\
        code.co_name in ['<listcomp>', '<setcomp>', '<dictcomp>', '<genexpr>']

    decompiler.build_graph(list(dis.get_instructions(code)))
    decompiler.sort_blocks()
    decompiler.detach_unreachable()
    decompiler.execute_blocks()
    decompiler.express_blocks()

    inner = decompiler.first_block.expression

    # Wrap the inner expression around a Lambda function with the right
    # argument names. This works because, apparently, the names of the
    # arguments always come before the names of the local variables in
    # code.co_varnames.
    for name in reversed(code.co_varnames[:code.co_argcount]):
        inner = Lambda(Identifier(name), inner)

    return inner


def preview(code):
    decompiler = Decompiler()
    decompiler.build_graph(list(dis.get_instructions(code)))

    dis.dis(code)
    display_graph(decompiler)


def display_graph(decompiler):
    TYPES = ['NORMAL_FLOW', 'JUMP_FLOW']
    graph = graphviz.Digraph()

    for block in decompiler.blocks:
        name = block.__class__.__name__

        if isinstance(block, (JumpBlock, BranchBlock, ForIterBlock)):
            label = name + '(' + block.instruction.opname + ')'
        elif isinstance(block, PlaceholderBlock):
            label = name + '(' + str(block.expression) + ')'
        elif (isinstance(block, LinearBlock) and
              len(block.instructions) == 1):
            instr = block.instructions[0]
            operation = instr.opname + '(' + str(instr.argval) + ')'
            label = name + '(' + operation + ')'
        else:
            offsets = ', '.join(
                map(lambda instr: str(instr.offset), block.instructions))
            label = name + '(' + offsets + ')'

        graph.node(str(block.index), '[' + str(block.index) + '] ' + label)

        for (next, edge_type) in block.successors:
            graph.edge(
                str(block.index), str(next.index), label=TYPES[edge_type])

    graph.render('test/%d.gv' % random.randint(0, 9999), view=True)


def print_state(decompiler):
    for block in decompiler.blocks:
        if hasattr(block, 'stack'):
            print('[%d] Stack: %s' % (block.index, str(block.stack)))

        if hasattr(block, 'bindings'):
            print('    Bindings: %s' % str(block.bindings))


def foo(x, z):
    y = x + 2
    if y % 2 == 0:
        z = True
    else:
        z = False
    return z

def bar(x):
    for z in range(x, 0, -1):
        w = print(z)
    return None

def bor(x):
    y = 0
    while x + y < 12:
        if x % 2 == 9:
            break
        elif x % 2 == 8:
            continue
        y -= 6
    return 6

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
    u = x < y < z
    return u
