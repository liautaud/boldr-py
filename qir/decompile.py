import dis
import graphviz


MOD_NEXT_LINE = 0
MOD_ALWAYS_JUMP = 1
MOD_DID_JUMP = 2
MOD_DID_NOT_JUMP = 3

ALWAYS_JUMP_OPNAMES = [
    'JUMP_FORWARD',
    'JUMP_ABSOLUTE',
    'CONTINUE_LOOP']

COND_JUMP_OPNAMES = [
    'POP_JUMP_IF_TRUE',
    'POP_JUMP_IF_FALSE',
    'JUMP_IF_TRUE_OR_POP',
    'JUMP_IF_FALSE_OR_POP',
    'FOR_ITER']


class Block():
    pass

class LinearBlock():
    pass

class BranchingBlock():
    pass


def cfg(code):
    # The vertices of the control flow graph will be blocks of "linear
    # instructions", i.e. instructions which are necessarily executed one
    # after the other.
    vertices = []

    # The edges of the control flow graph, which will be stored as adjacency
    # lists, will represent the possible jumps between blocks.
    edges = []

    # In order to be able to compute the graph in linear time, we keep a
    # mapping of the block in which any instruction is contained, as well as
    # the offset of the instruction after any instruction.
    block_mapping = {}
    next_mapping = {}

    current_block = []
    current_jumps = []

    previous_offset = -1
    previous_instruction = None

    def new_block():
        """ Stores the current block in the graph and starts a new one. """
        if len(current_block) > 0 or len(current_jumps) > 0:
            current_index = len(vertices)
            vertices.append(current_block.copy())
            edges.append(current_jumps.copy())

            for instruction in current_block:
                block_mapping[instruction.offset] = current_index

            current_block.clear()
            current_jumps.clear()

    # We do a first pass of all the instructions to separate them into blocks
    # and to add edges to the graph when needed.
    for instruction in dis.get_instructions(code):
        if (instruction.offset > 0 and instruction.is_jump_target) or \
           instruction.opname in ALWAYS_JUMP_OPNAMES or \
           instruction.opname in COND_JUMP_OPNAMES:
            # If the previous instruction was not a jump instruction, then
            # this instruction will come right after it, so we must add an
            # edge from the previous block to this one.
            if previous_instruction.opname not in ALWAYS_JUMP_OPNAMES and\
               previous_instruction.opname not in COND_JUMP_OPNAMES:
                current_jumps.append((len(vertices) + 1, None, MOD_NEXT_LINE))

            new_block()

        if instruction.opname in ALWAYS_JUMP_OPNAMES:
            # We use (-1) as a placeholder for the edge's target block, which
            # we will compute in a second pass - because we might jump to a
            # line which has not yet been processed, and so we wouldn't know
            # which block belongs to.
            current_block.append(instruction)
            current_jumps.append((-1, instruction, MOD_ALWAYS_JUMP))

            new_block()

        elif instruction.opname in COND_JUMP_OPNAMES:
            # The value at the end of the tuple is 2 if the edge corresponds
            # to when the condition for the jump was fulfilled, and 3 when it
            # wasn't.
            current_block.append(instruction)
            current_jumps.append((-1, instruction, MOD_DID_JUMP))
            current_jumps.append((-1, instruction, MOD_DID_NOT_JUMP))

            new_block()

        else:
            current_block.append(instruction)

        if previous_offset >= 0:
            next_mapping[previous_offset] = instruction.offset

        previous_offset = instruction.offset
        previous_instruction = instruction

    new_block()

    # We do a second pass on the edges alone to resolve their jump targets to
    # block indexes.
    for jumps in edges:
        for i in range(len(jumps)):
            (_, instruction, modifier) = jumps[i]

            if modifier == MOD_NEXT_LINE:
                # We have already resolved the jump target in the first pass.
                continue
            elif modifier == MOD_DID_NOT_JUMP:
                # We are jumping to the next instruction.
                index = block_mapping[next_mapping[instruction.offset]]
            else:
                # We use instruction.argval because it always contains the
                # absolute offset of the jump target, even when
                # instruction.arg contains a relative offset.
                print(instruction)
                index = block_mapping[instruction.argval]

            jumps[i] = (index, instruction, modifier)

    # We also do a second pass on the blocks to "clean them up", i.e. to
    # remove the instructions and jumps which will never be reached.
    for i, block in enumerate(vertices):
        for j, instruction in enumerate(block):
            if instruction.opname == 'RETURN_VALUE':
                vertices[i] = block[:j + 1]
                edges[i].clear()
                break

    return (vertices, edges)


def preview(code):
    mods = ['NEXT_LINE', 'ALWAYS_JUMP', 'DID_JUMP', 'DID_NOT_JUMP']

    (vertices, edges) = cfg(code)
    graph = graphviz.Digraph()

    for i, block in enumerate(vertices):
        label = ', '.join(map(lambda instr: str(instr.offset), block))
        graph.node(str(i), label)

    for u in range(len(edges)):
        for (v, instr, modifier) in edges[u]:
            if instr is None:
                label = ''
            else:
                label = str((instr.opname, mods[modifier]))

            graph.edge(str(u), str(v), label=label)

    graph.render('test/cfg.gv', view=True)


def foo(x):
    y = x + 2
    if y % 2 == 0:
        z = True
    else:
        z = False
    return z


def bar(z):
    n = z - 1
    while n > 0:
        print('test')
        if n == 10:
            break
        n -= 1

    return 'foo'

def baz(z):
    if foo:
        return True
    else:
        return False

    return 'bla'


preview(foo)
dis.dis(foo)
