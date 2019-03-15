from typing import List, TypeVar, Callable, Iterable, Tuple, Optional, NamedTuple
import collections


T = TypeVar('T')

Opcode = Tuple[str, int, int, int, int]

class _Trace(NamedTuple):
    cost: int
    ops: List[str]

class WagnerFischer:

    def __init__(self,
                 a: List[T],
                 b: List[T],
                 stringify: Callable[[T], str] = lambda t: str(t),
                 insertion_cost_fn: Optional[Callable[[List[T]], float]] = None,
                 deletion_cost_fn: Optional[Callable[[List[T]], float]] = None,
                 substitution_cost_fn: Optional[Callable[[List[T], List[T]], float]] = None,
                 transposition_cost_fn:  Optional[Callable[[List[T], List[T]], float]] = None):


        a_str = [stringify(x) for x in a]
        b_srt = [stringify(x) for x in b]
        # Keep lowercased versions for transpositions
        al = [x.lower() for x in a_str]
        bl = [x.lower() for x in b_srt]

        # Initializes table.
        self.asz = len(a)
        self.bsz = len(b)
        table = [[None for _ in range(self.bsz + 1)] for
                       _ in range(self.asz + 1)]
        # From now on, all indexing done using self.__getitem__.
        ## Fills in edges.
        table[0][0] = _Trace(0, ["O"])  # Start cell.
        for i in range(1, self.asz + 1):
            deletion_cost = deletion_cost_fn(a[i - 1]) if deletion_cost_fn else 1
            table[i][0] = _Trace(table[i - 1][0].cost + deletion_cost, ["D"])
        for j in range(1, self.bsz + 1):
            insertion_cost = insertion_cost_fn(b[j - 1]) if insertion_cost_fn else 1
            table[0][j] = _Trace(table[0][j - 1].cost + insertion_cost, ["I"])
        
        ## Fills in rest.
        for i in range(len(a)):
            for j in range(len(b)):
                # Cleans it up in case there are more than one check for match
                # first, as it is always the cheapest option.
                if a_str[i] == b_srt[j]:
                    table[i + 1][j + 1] = _Trace(table[i][j].cost, ["M"])
                # Checks for other types.
                else:
                    deletion_cost = deletion_cost_fn(a[i]) if deletion_cost_fn else 1
                    insertion_cost = insertion_cost_fn(b[j]) if insertion_cost_fn else 1
                    substitution_cost = substitution_cost_fn(a[i], b[j]) if substitution_cost_fn else 1

                    costD = table[i][j + 1].cost + deletion_cost
                    costI = table[i + 1][j].cost + insertion_cost
                    costS = table[i][j].cost + substitution_cost
                    costT = float("inf") # We don't know it yet
                    min_val = min(costI, costD, costS)

                    # Multiword transpositions:
                    # Find a sequence of equal elements in different order
                    # We only need to check diagonally because we require the same number of elements
                    k = 1
                    while i > 0 and j > 0 and (i - k) >= 0 and (j - k) >= 0 and table[i-k+1][j-k+1].cost - table[i-k][j-k].cost > 0: # An operation that has a cost (i.e. I, D or S > 0)
                        if collections.Counter(al[i-k:i+1]) == collections.Counter(bl[j-k:j+1]):
                            transposition_cost = transposition_cost_fn(a[i-k:i+1], b[j-k:j+1]) if transposition_cost_fn else k
                            costT = table[i-k][j-k].cost + transposition_cost
                            min_val = min(min_val, costT)
                            break
                        k += 1
                    
                    trace = _Trace(min_val, []) # Use a list to preserve the order
                    # Adds _all_ operations matching minimum value.
                    if costD == min_val:
                        trace.ops.append("D")
                    if costI == min_val:
                        trace.ops.append("I")
                    if costS == min_val:
                        trace.ops.append("S")
                    if costT == min_val:
                        trace.ops.append("T" + str(k+1))
                    table[i + 1][j + 1] = trace
                                        
        # Stores optimum cost as a property.
        self.cost = table[-1][-1].cost
        self._table = table

    def __iter__(self):
        for row in self._table:
            yield row

    def __getitem__(self, i: int):
        """
        Returns the i-th row of the table, which is a list and so
        can be indexed. Therefore, e.g.,  self._table[2][3] == self._table[2][3]
        """
        return self._table[i]

    def alignments(self, depth_first: bool = False) -> Iterable[List[str]]:
        """
        Generate all alignments with optimal cost by traversing an
        implicit graph on the dynamic programming table. Use
        breadth-first traversal by default.
        """
        # Each cell of the queue is a tuple of (i, j, trace, path_back)
        # where i, j is the current index, trace is the trace object at
        # this cell
        if depth_first:
            return self._depth_first_alignments()
        else:
            return self._breadth_first_alignments()

    def costs(self) -> collections.Counter:
        """
        Estimates insertions, deletions, and substitution _count_ (not
        costs). Non-integer values arise when there are multiple possible
        alignments with the same cost.
        """
        npaths = 0
        opcounts = collections.Counter()
        for alignment in self.alignments():
            # Counts edit types for this path, ignoring "M" (which is free).
            opcounts += collections.Counter(op for op in alignment if op != "M")
            npaths += 1
        # Averages over all paths.
        return collections.Counter({o: c / npaths for (o, c) in
                                    opcounts.items()})

    @staticmethod
    def get_opcodes(alignment: List[List[str]]) -> List[Opcode]:
        s_start = 0
        s_end   = 0
        t_start = 0
        t_end   = 0
        opcodes = []
        for op in alignment:
            if op[0] == "D": # Deletion
                s_end += 1
            elif op[0] == "I": # Insertion
                t_end += 1
            elif op[0].startswith("T"): # Transposition
                # Extract number of elements involved (default is 2)
                k = int(op[1:] or 2)
                s_end += k
                t_end += k
            else: # Match or substitution
                s_end += 1
                t_end += 1
            # Save
            opcodes.append((op, s_start, s_end, t_start, t_end))
            # Start from here
            s_start = s_end
            t_start = t_end
        return opcodes

    # Stuff for generating alignments.
    def _stepback(self, i: int, j: int, trace: _Trace, path_back: List[str]):
        """
        Given a cell location (i, j) and a _Trace object trace, generate
        all traces they point back to in the table
        """
        for op in trace.ops:
            if op == "M":
                yield i - 1, j - 1, self._table[i - 1][j - 1], path_back + ["M"]
            elif op == "I":
                yield i, j - 1, self._table[i][j - 1], path_back + ["I"]
            elif op == "D":
                yield i - 1, j, self._table[i - 1][j], path_back + ["D"]
            elif op == "S":
                yield i - 1, j - 1, self._table[i - 1][j - 1], path_back + ["S"]
            elif op.startswith("T"):
                # Extract stepback (default is a transposition of 2 elements)
                k = int(op[1:] or 2)
                yield i - k, j - k, self._table[i - k][j - k], path_back + [op]
            elif op == "O":
                return  # Origin cell, so we're done.
            else:
                raise ValueError("Unknown op {!r}".format(op))
    
    def get_best_match_opcodes(self) -> List[Opcode]:
        best_alignment = next(self.alignments(depth_first=True))
        return WagnerFischer.get_opcodes(best_alignment)

    def _depth_first_alignments(self) -> Iterable[List[str]]:
        """
        Generate alignments via depth-first traversal.
        """
        stack = list(self._stepback(self.asz, self.bsz, self._table[-1][-1], []))
        while stack:
            (i, j, trace, path_back) = stack.pop()
            if trace.ops[0] == "O":
                yield path_back[::-1]
                continue
            stack.extend(self._stepback(i, j, trace, path_back))

    def _breadth_first_alignments(self) -> Iterable[List[str]]:
        """
        Generate alignments via breadth-first traversal.
        """
        # Each cell of the queue is a tuple of (i, j, trace, path_back)
        # where i, j is the current index, trace is the trace object at
        # this cell, and path_back is a reversed list of edit operations
        # which is initialized as an empty list.
        queue = collections.deque(self._stepback(self.asz, self.bsz,
                                                 self._table[-1][-1], []))
        while queue:
            (i, j, trace, path_back) = queue.popleft()
            if trace.ops[0] == "O":
                # We have reached the origin, the end of a reverse path, so
                # yield the list of edit operations in reverse.
                yield path_back[::-1]
                continue
            queue.extend(self._stepback(i, j, trace, path_back))



if __name__ == "__main__":
    a = input("a: ").split()
    b = input("b: ").split()
    al = WagnerFischer(a, b).alignments()
    for a in al:
        print(a)