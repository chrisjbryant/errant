from itertools import groupby
import Levenshtein
import spacy.parts_of_speech as POS
from errant.edit import Edit

class Alignment:
    # Protected class resource
    _open_pos = {POS.ADJ, POS.ADV, POS.NOUN, POS.VERB}

    # Input 1: An original text string parsed by spacy
    # Input 2: A corrected text string parsed by spacy
    # Input 3: A flag for standard Levenshtein alignment
    def __init__(self, orig, cor, lev=False):
        # Set orig and cor
        self.orig = orig
        self.cor = cor
        # Align orig and cor and get the cost and op matrices
        self.cost_matrix, self.op_matrix = self.align(lev)
        # Get the cheapest align sequence from the op matrix
        self.align_seq = self.get_cheapest_align_seq()

    # Input: A flag for standard Levenshtein alignment
    # Output: The cost matrix and the operation matrix of the alignment
    def align(self, lev):
        # Sentence lengths
        o_len = len(self.orig)
        c_len = len(self.cor)
        # Lower case token IDs (for transpositions)
        o_low = [o.lower for o in self.orig]
        c_low = [c.lower for c in self.cor]
        # Create the cost_matrix and the op_matrix
        cost_matrix = [[0.0 for j in range(c_len+1)] for i in range(o_len+1)]
        op_matrix = [["O" for j in range(c_len+1)] for i in range(o_len+1)]
        # Fill in the edges
        for i in range(1, o_len+1):
            cost_matrix[i][0] = cost_matrix[i-1][0] + 1
            op_matrix[i][0] = "D"
        for j in range(1, c_len+1):
            cost_matrix[0][j] = cost_matrix[0][j-1] + 1
            op_matrix[0][j] = "I"

        # Loop through the cost_matrix
        for i in range(o_len):
            for j in range(c_len):
                # Matches
                if self.orig[i].orth == self.cor[j].orth:
                    cost_matrix[i+1][j+1] = cost_matrix[i][j]
                    op_matrix[i+1][j+1] = "M"
                # Non-matches
                else:
                    del_cost = cost_matrix[i][j+1] + 1
                    ins_cost = cost_matrix[i+1][j] + 1
                    trans_cost = float("inf")
                    # Standard Levenshtein (S = 1)
                    if lev: sub_cost = cost_matrix[i][j] + 1
                    # Linguistic Damerau-Levenshtein
                    else:
                        # Custom substitution
                        sub_cost = cost_matrix[i][j] + \
                            self.get_sub_cost(self.orig[i], self.cor[j])
                        # Transpositions require >=2 tokens
                        # Traverse the diagonal while there is not a Match.
                        k = 1
                        while i-k >= 0 and j-k >= 0 and \
                                cost_matrix[i-k+1][j-k+1] != cost_matrix[i-k][j-k]:
                            if sorted(o_low[i-k:i+1]) == sorted(c_low[j-k:j+1]):
                                trans_cost = cost_matrix[i-k][j-k] + k
                                break
                            k += 1
                    # Costs
                    costs = [trans_cost, sub_cost, ins_cost, del_cost]
                    # Get the index of the cheapest (first cheapest if tied)
                    l = costs.index(min(costs))
                    # Save the cost and the op in the matrices
                    cost_matrix[i+1][j+1] = costs[l]
                    if   l == 0: op_matrix[i+1][j+1] = "T"+str(k+1)
                    elif l == 1: op_matrix[i+1][j+1] = "S"
                    elif l == 2: op_matrix[i+1][j+1] = "I"
                    else: op_matrix[i+1][j+1] = "D"
        # Return the matrices
        return cost_matrix, op_matrix

    # Input 1: A spacy orig Token
    # Input 2: A spacy cor Token
    # Output: A linguistic cost between 0 < x < 2
    def get_sub_cost(self, o, c):
        # Short circuit if the only difference is case
        if o.lower == c.lower: return 0
        # Lemma cost
        if o.lemma == c.lemma: lemma_cost = 0
        else: lemma_cost = 0.499
        # POS cost
        if o.pos == c.pos: pos_cost = 0
        elif o.pos in self._open_pos and c.pos in self._open_pos: pos_cost = 0.25
        else: pos_cost = 0.5
        # Char cost
        char_cost = 1-Levenshtein.ratio(o.text, c.text)
        # Combine the costs
        return lemma_cost + pos_cost + char_cost

    # Get the cheapest alignment sequence and indices from the op matrix
    # align_seq = [(op, o_start, o_end, c_start, c_end), ...]
    def get_cheapest_align_seq(self):
        i = len(self.op_matrix)-1
        j = len(self.op_matrix[0])-1
        align_seq = []
        # Work backwards from bottom right until we hit top left
        while i + j != 0:
            # Get the edit operation in the current cell
            op = self.op_matrix[i][j]
            # Matches and substitutions
            if op in {"M", "S"}:
                align_seq.append((op, i-1, i, j-1, j))
                i -= 1
                j -= 1
            # Deletions
            elif op == "D":
                align_seq.append((op, i-1, i, j, j))
                i -= 1
            # Insertions
            elif op == "I":
                align_seq.append((op, i, i, j-1, j))
                j -= 1
            # Transpositions
            else:
                # Get the size of the transposition
                k = int(op[1:])
                align_seq.append((op, i-k, i, j-k, j))
                i -= k
                j -= k
        # Reverse the list to go from left to right and return
        align_seq.reverse()
        return align_seq

    # all-split: Don't merge anything
    def get_all_split_edits(self):
        edits = []
        for align in self.align_seq:
            if align[0] != "M": 
                edits.append(Edit(self.orig, self.cor, align[1:]))
        return edits

    # all-merge: Merge all adjacent non-match ops
    def get_all_merge_edits(self):
        edits = []
        for op, group in groupby(self.align_seq, 
                lambda x: True if x[0] == "M" else False):
            if not op:
                merged = self.merge_edits(list(group))
                edits.append(Edit(self.orig, self.cor, merged[0][1:]))
        return edits

    # all-equal: Merge all edits of the same operation type.
    def get_all_equal_edits(self):
        edits = []
        for op, group in groupby(self.align_seq, lambda x: x[0]):
            if op != "M":
                merged = self.merge_edits(list(group))
                edits.append(Edit(self.orig, self.cor, merged[0][1:]))
        return edits

    # Merge the input alignment sequence to a single edit span
    def merge_edits(self, seq):
        if seq: return [("X", seq[0][1], seq[-1][2], seq[0][3], seq[-1][4])]
        else: return seq

    # Alignment object string representation
    def __str__(self):
        orig = " ".join(["Orig:"]+[tok.text for tok in self.orig])
        cor = " ".join(["Cor:"]+[tok.text for tok in self.cor])
        cost_matrix = "\n".join(["Cost Matrix:"]+[str(row) for row in self.cost_matrix])
        op_matrix = "\n".join(["Operation Matrix:"]+[str(row) for row in self.op_matrix])
        seq = "Best alignment: "+str([a[0] for a in self.align_seq])
        return "\n".join([orig, cor, cost_matrix, op_matrix, seq])