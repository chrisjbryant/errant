from typing import List, Iterable
import Levenshtein
from itertools import combinations, groupby
from string import punctuation
import re
import spacy.parts_of_speech as POS
from spacy.tokens import Doc, Token
from errant.minimum_edits import WagnerFischer
from errant.edit import Edit

_CONTENT_POS = {POS.ADJ, POS.ADV, POS.NOUN, POS.VERB}

RULES_MERGE = 'rules'
ALL_SPLIT_MERGE = 'all-split'
ALL_MERGE_MERGE = 'all-merge'
ALL_EQUAL_MERGE = 'all-equal'


def get_auto_aligned_edits(original_tokens: List[Token], corrected_tokens: List[Token], levenshtien_costs: bool = False, merge_type: str = RULES_MERGE) -> List[Edit]:

    # Align using Levenshtein.
    if levenshtien_costs: 
        minimal_edits = WagnerFischer(original_tokens, corrected_tokens,
                                      substitution_cost_fn=_levenshtein_substitution, 
                                      transposition_cost_fn=_levenshtein_transposition)
    # Otherwise, use linguistically enhanced Damerau-Levenshtein
    else: 
        minimal_edits = WagnerFischer(original_tokens, corrected_tokens, substitution_cost_fn=_token_substitution)
    # Get the alignment with the highest score. There is usually only 1 best in DL due to custom costs.
    op_codes = minimal_edits.get_best_match_opcodes()
    # Convert the alignment into edits; choose merge strategy
    if merge_type == RULES_MERGE:
        edits = _get_edits(original_tokens, corrected_tokens, op_codes)
    elif merge_type == ALL_SPLIT_MERGE:
        edits = _get_edits_split(op_codes)
    elif merge_type == ALL_MERGE_MERGE:
        edits = _get_edits_group_all(op_codes)
    elif merge_type == ALL_EQUAL_MERGE:
        edits = _get_edits_group_type(op_codes)
    proc_edits = []
    for edit in edits:
        source_span =  (edit[1], edit[2])
        target_span =  (edit[3], edit[4])
        error_type = None # We don't know the category yet
        cor_start = edit[3]
        cor_end = edit[4]
        edit_text = " ".join([tok.text for tok in corrected_tokens[cor_start:cor_end]])
        aligned_edit = Edit(source_span, target_span, edit_text, error_type)

        proc_edits.append(aligned_edit)
    return proc_edits


def _merge_edits(edits):
    if edits:
        return [("X", edits[0][1], edits[-1][2], edits[0][3], edits[-1][4])]
    else:
        return edits

# Input 1: Spacy source sentence
# Input 2: Spacy target sentence
# Input 3: The alignment between the 2; [e.g. M, M, S ,S M]
# Output: A list of processed edits that have been merged or split.
def _get_edits(source, target, edits):
    out_edits = []
    # Start: Split alignment intro groups of M, T and rest. T has a number after it.
    for op, group in groupby(edits, lambda x: x[0][0] if x[0][0] in {"M", "T"} else False):
        # Convert the generator to a list
        group = list(group)
        # Ignore M
        if op == "M": continue
        # Do not merge T
        elif op == "T": out_edits.extend(group)
        # Further processing required
        else: out_edits.extend(_process_edits(source, target, group))
    return out_edits

# Input 1: Spacy source sentence
# Input 2: Spacy target sentence
# Input 3: A list of non-matching alignments: D, I and/or S
# Output: A list of processed edits that have been merged or split.
def _process_edits(source, target, edits):
    # Return single alignments
    if len(edits) <= 1: return edits
    # Get the ops for the whole edit sequence
    ops = [op[0] for op in edits]
    # Merge ops that are all D xor I. (95% of human multi-token edits contain S).
    if set(ops) == {"D"} or set(ops) == {"I"}: return _merge_edits(edits)
    
    content = False # True if edit includes a content word
    # Get indices of all combinations of start and end ranges in the edits: 012 -> 01, 02, 12
    combos = list(combinations(range(0, len(edits)), 2))
    # Sort them starting with largest spans first
    combos.sort(key = lambda x: x[1]-x[0], reverse=True)
    # Loop through combos
    for start, end in combos:
        # Ignore ranges that do NOT contain a substitution.
        if "S" not in ops[start:end+1]: continue
        # Get the tokens in original_tokens and corrected_tokens. They will never be empty due to above rule.
        s = source[edits[start][1]:edits[end][2]]
        t = target[edits[start][3]:edits[end][4]]
        # Possessive suffixes merged with previous token: [friends -> friend 's]
        if s[-1].tag_ == "POS" or t[-1].tag_ == "POS":
            return _process_edits(source, target, edits[:end-1]) + _merge_edits(edits[end-1:end+1]) + _process_edits(source, target, edits[end+1:])
        # Case changes
        if s[-1].lower_ == t[-1].lower_:
            # Merge first token I or D of arbitrary length: [Cat -> The big cat]
            if start == 0 and ((len(s) == 1 and t[0].text[0].isupper()) or (len(t) == 1 and s[0].text[0].isupper())):
                return _merge_edits(edits[start:end+1]) + _process_edits(source, target, edits[end+1:])
            # Merge with previous punctuation: [, we -> . We], [we -> . We]
            if (len(s) > 1 and _is_punct(s[-2])) or (len(t) > 1 and _is_punct(t[-2])):
                return _process_edits(source, target, edits[:end-1]) + _merge_edits(edits[end-1:end+1]) + _process_edits(source, target, edits[end+1:])
        # Whitespace/hyphens: [bestfriend -> best friend], [sub - way -> subway]
        s_str = re.sub("['-]", "", "".join([tok.lower_ for tok in s]))
        t_str = re.sub("['-]", "", "".join([tok.lower_ for tok in t]))
        if s_str == t_str:
            return _process_edits(source, target, edits[:start]) + _merge_edits(edits[start:end+1]) + _process_edits(source, target, edits[end+1:])
        # POS-based merging: Same POS or infinitive/phrasal verbs: [to eat -> eating], [watch -> look at]
        pos_set = set([tok.pos for tok in s]+[tok.pos for tok in t])
        if (len(pos_set) == 1 and len(s) != len(t)) or pos_set == {POS.PART, POS.VERB}:
            return _process_edits(source, target, edits[:start]) + _merge_edits(edits[start:end+1]) + _process_edits(source, target, edits[end+1:])
        # Split rules take effect when we get to smallest chunks
        if end-start < 2:
            # Split adjacent substitutions
            if len(s) == len(t) == 2:
                return _process_edits(source, target, edits[:start+1]) + _process_edits(source, target, edits[start+1:])
            # Similar substitutions at start or end
            if (ops[start] == "S" and _char_cost(s[0].text, t[0].text) < 0.25) or \
                (ops[end] == "S" and _char_cost(s[-1].text, t[-1].text) < 0.25):
                return _process_edits(source, target, edits[:start+1]) + _process_edits(source, target, edits[start+1:])	
            # Split final determiners
            if end == len(edits)-1 and ((ops[-1] in {"D", "S"} and s[-1].pos == POS.DET) or \
                (ops[-1] in {"I", "S"} and t[-1].pos == POS.DET)):
                return _process_edits(source, target, edits[:-1]) + [edits[-1]]
        # Set content word flag
        if not pos_set.isdisjoint(_CONTENT_POS): content = True
    # If all else fails, merge edits that contain content words
    if content: return _merge_edits(edits)
    else: return edits


# all-split: No edits are ever merged. Everything is 1:1, 1:0 or 0:1 only.
def _get_edits_split(edits):
    new_edits = []
    for edit in edits:
        op = edit[0]
        if op != "M":
             new_edits.append(edit)
    return new_edits

# all-merge: Merge all adjacent edits of any operation type, except M.
def _get_edits_group_all(edits):
    new_edits = []
    for op, group in groupby(edits, lambda x: True if x[0] == "M" else False):
        if not op:
             new_edits.extend(_merge_edits(list(group)))
    return new_edits

# all-equal: Merge all edits of the same operation type.
def _get_edits_group_type(edits):
    new_edits = []
    for op, group in groupby(edits, lambda x: x[0]):
        if op != "M":
             new_edits.extend(_merge_edits(list(group)))
    return new_edits


# If there is a substitution, calculate the more informative cost.
def _token_substitution(a: Token, b: Token):
    # If lower case strings are the same, don't bother checking pos etc.
    # This helps catch case marking substitution errors.
    if a.text.lower() == b.text.lower():
        return 0
    
    cost = _lemma_cost(a, b) + _pos_cost(a, b) + _char_cost(a.text, b.text)

    return cost

# Change cost of Transpositions to be the same as Levenshtein.
def _levenshtein_transposition(a: Token, b: Token):
    return float("inf")

# Change cost of Substitution to be the same as Levenshtein.
def _levenshtein_substitution(a: Token, b: Token):
    return 1


# Is the token a content word?
def _is_content(a: Token):
    return a.pos in _CONTENT_POS

# Check whether token is punctuation
def _is_punct(token: Token):
    return token.pos == POS.PUNCT or token.text in punctuation


# Cost is 0 if lemmas are the same, otherwise 0.499. Maximum S cost is 1.999.
# This prevents unintuitive transpositions.
def _lemma_cost(a: Token, b: Token):
    if a.lemma == b.lemma:
        return 0
    else: 
        return 0.499

# Cost is 0 if POS are the same, else 0.25 if both are content, else 0.5.
# Content words more likely to align to other content words.
def _pos_cost(a: Token, b: Token):
    if a.pos == b.pos:
        return 0
    elif _is_content(a) and _is_content(b):
        return 0.25
    else:
        return 0.5

# Calculate the cost of character alignment; i.e. char similarity
def _char_cost(a: str, b: str):
    return 1 - Levenshtein.ratio(a, b)
