import dis
import graphviz


NORMAL_FLOW = 0
JUMP_FLOW = 1

JUMP_OPNAMES = [
    'JUMP_FORWARD',
    'JUMP_ABSOLUTE',
    'CONTINUE_LOOP']

BRANCH_OPNAMES = [
    'POP_JUMP_IF_TRUE',
    'POP_JUMP_IF_FALSE',
    'JUMP_IF_TRUE_OR_POP',
    'JUMP_IF_FALSE_OR_POP',
    'FOR_ITER']


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

        # The offset before which all next instructions should be added to the
        # current block as is, no matter its type.
        ignore_until = False

        # Whether to start a new block on the next instruction, even if it is
        # not a jump target.
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

    def sort_blocks(self):
        pass

    def execute_blocks(self):
        pass

    def express_blocks(self):
        pass


class Block():
    def __init__(self, context):
        self.context = context

        # The index of this block in the graph that is being built.
        self.index = len(context.blocks)

        # The instructions which belong to this block.
        self.instructions = []

        # The block to which we should jump once we reach the end of this one.
        self.next = None

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

        # Even though we only add the instruction to the block if it has not
        # reached a RETURN_VALUE instruction before, we still have to declare
        # that the block contains the instruction, otherwise we might break
        # the translation from jump offsets to blocks that happens in
        # JumpBlock@close and BranchBlock@close.
        self.context.block_mapping[instruction.offset] = self

        if instruction.opname == 'RETURN_VALUE':
            self.reached_return = True

    def close(self):
        # If the block has reached a RETURN_VALUE instruction, we don't want
        # to jump to any other block at the end of this one.
        if self.reached_return:
            self.next = None


class LinearBlock(Block):
    pass


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


class LoopBlock(Block):
    def __init__(self, context, instruction):
        super().__init__(context)
        self.instruction = instruction
        self.add(instruction)


class ExpressedBlock(Block):
    pass


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

    for block in decompiler.blocks:
        name = block.__class__.__name__

        if isinstance(block, (JumpBlock, BranchBlock)):
            label = name + '(' + block.instruction.opname + ')'
        else:
            offsets = ', '.join(
                map(lambda instr: str(instr.offset), block.instructions))
            label = name + '(' + offsets + ')'

        graph.node(str(block.index), label)

        for (next, type) in block.successors:
            graph.edge(str(block.index), str(next.index), label=TYPES[type])

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


preview(baz)
dis.dis(baz)
