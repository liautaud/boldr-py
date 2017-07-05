def sort_blocks(blocks):
    """
    Compute a topological ordering of the control flow graph.

    This is possible as we have removed cycles from the graph by hiding
    them into LoopBlocks, and so the graph is a DAG.
    """
    marked = [False] * len(blocks)
    ordering = []

    def visit(block):
        marked[block.index] = True

        for next in block.successors:
            if not marked[next]:
                visit(blocks[next])

        ordering.append(block.index)

    visit(blocks[0])

    return list(reversed(ordering))


class Block():
    def __init__(self, index, successors):
        self.index = index
        self.successors = successors


blocks = [
    Block(0, [1]),
    Block(1, [2, 3]),
    Block(2, [4]),
    Block(3, [6]),
    Block(4, [5]),
    Block(5, [6]),
    Block(6, []),
    Block(7, [3])]

print(sort_blocks(blocks))
