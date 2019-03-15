from typing import Dict, Tuple, List, Optional
from operator import itemgetter
import os
import pathlib
from spacy.language import Language
from spacy.tokens import Doc, Token
from errant.edit import Edit, ErrorType

_BASENAME = os.path.dirname(os.path.realpath(__file__))
_DEFAULT_DICT_PATH = pathlib.Path(_BASENAME + "/resources/en_GB-large.txt")
_DEFAULT_TAG_PATH = pathlib.Path(_BASENAME + "/resources/en-ptb_map")

# Load latest Hunspell dictionaries:
def load_dictionary(path: pathlib.Path = _DEFAULT_DICT_PATH):
    with path.open() as dict_file:
        return set(dict_file.read().split())

# Load Stanford Universal Tags map file.
def load_tag_map(path: pathlib.Path = _DEFAULT_TAG_PATH):
    map_dict = {}
    with path.open() as tag_file:
        for line in tag_file.readlines():
            line = line.strip().split("\t")
            # Change ADP to PREP; makes it clearer
            if line[1].strip() == "ADP":
                map_dict[line[0]] = "PREP"
            # Also change PROPN to NOUN; we don't need a prop noun tag
            elif line[1].strip() == "PROPN":
                map_dict[line[0]] = "NOUN"
            else:
                map_dict[line[0]] = line[1].strip()
    # Add some spacy PTB tags not in the original mapping.
    map_dict['""'] = "PUNCT"
    map_dict["SP"] = "SPACE"
    map_dict[""] = "SPACE"
    map_dict["_SP"] = "SPACE"
    map_dict["ADD"] = "X"
    map_dict["GW"] = "X"
    map_dict["NFP"] = "X"
    map_dict["XX"] = "X"
    return map_dict


# Input: A sentence + edit block in an m2 file.
# Output 1: The original sentence (a list of tokens)
# Output 2: A dictionary; key is coder id, value is a tuple. 
# tuple[0] is the corrected sentence (a list of tokens), tuple[1] is the edits.
# Process M2 to extract sentences and edits.
def process_m2(info: str) -> Tuple[List[str], Dict[str, Tuple[List[str], List[Edit]]]]:
    info = info.split("\n")
    orig_sent = info[0][2:].split() # [2:] ignore the leading "S "
    all_edits = info[1:]
    # Simplify the edits and group by coder id.
    edit_dict = process_edits(all_edits)
    out_dict = {}
    # Loop through each coder and their edits.
    for coder, edits in edit_dict.items():
        # Copy orig_sent. We will apply the edits to it to make cor_sent
        cor_sent = orig_sent[:]
        gold_edits = []
        offset = 0
        # Sort edits by start and end offset only. If they are the same, do not reorder.
        edits = sorted(edits, key=itemgetter(0)) # Sort by start offset
        edits = sorted(edits, key=itemgetter(1)) # Sort by end offset
        for edit in edits:
            # Do not apply noop or Um edits, but save them
            if edit[2] in {"noop", "Um"}:
                error_type = ErrorType.from_string(edit[2])
                edit = Edit((edit[0], edit[1]), (-1, -1), edit[3], error_type)
                gold_edits.append(edit)
                gold_edits.append(edit)
                continue
            orig_start = edit[0]
            orig_end = edit[1]
            cor_toks = edit[3].split()
            # Apply the edit.
            cor_sent[orig_start+offset:orig_end+offset] = cor_toks
            # Get the cor token start and end positions in cor_sent
            cor_start = orig_start+offset
            cor_end = cor_start+len(cor_toks)
            # Keep track of how this affects orig edit offsets.
            offset = offset-(orig_end-orig_start)+len(cor_toks)
            # Save the edit with cor_start and cor_end
            
            error_type = ErrorType.from_string(edit[2])
            edit = Edit((orig_start, orig_end), (cor_start, cor_end), edit[3], error_type)
            gold_edits.append(edit)
        # Save the cor_sent and gold_edits for each annotator in the out_dict.
        out_dict[coder] = (cor_sent, gold_edits)
    return orig_sent, out_dict

# Input: A list of edit lines for a sentence in an m2 file.
# Output: An edit dictionary; key is coder id, value is a list of edits.
def process_edits(edits: List[str]) -> Dict[str, Tuple[int, int, str, str]]:
    edit_dict = {}
    for edit in edits:
        edit = edit.split("|||")
        span = edit[0][2:].split() # [2:] ignore the leading "A "
        start = int(span[0])
        end = int(span[1])
        cat = edit[1]
        cor = edit[2]
        id = edit[-1]
        # Save the useful info as a list
        proc_edit = [start, end, cat, cor]
        # Save the proc edit inside the edit_dict using coder id.
        if id in edit_dict.keys():
            edit_dict[id].append(proc_edit)
        else:
            edit_dict[id] = [proc_edit]
    return edit_dict

# Input 1: An edit list. [orig_start, orig_end, cat, cor, cor_start, cor_end]
# Input 2: An original SpaCy sentence.
# Input 3: A corrected SpaCy sentence.
# Output: A minimised edit with duplicate words on both sides removed.
# E.g. [was eaten -> has eaten] becomes [was -> has]
def minimise_edit(edit: Edit, orig: List[Token], cor: List[Token]) -> Optional[Edit]:
    # edit = [orig_start, orig_end, cat, cor, cor_start, cor_end]
    orig_toks = orig[edit.original_span[0]:edit.original_span[1]]
    cor_toks = cor[edit.corrected_span[0]:edit.corrected_span[1]]
    # While the first token is the same string in both (and both are not null)
    while orig_toks and cor_toks and orig_toks[0].text == cor_toks[0].text:
        # Remove that token from the span, and adjust the start offset.
        orig_toks = orig_toks[1:]
        cor_toks = cor_toks[1:]
        edit.original_span = (edit.original_span[0]+1, edit.original_span[1])
        edit.corrected_span = (edit.corrected_span[0]+1, edit.corrected_span[1])
    # Then do the same from the last token.
    while orig_toks and cor_toks and orig_toks[-1].text == cor_toks[-1].text:
        # Remove that token from the span, and adjust the start offset.
        orig_toks = orig_toks[:-1]
        cor_toks = cor_toks[:-1]
        edit.original_span = (edit.original_span[0], edit.original_span[1]-1)
        edit.corrected_span = (edit.corrected_span[0], edit.corrected_span[1]-1)
    # If both sides are not null, save the new correction string.
    if orig_toks or cor_toks:
        edit.edit_text = " ".join([tok.text for tok in cor_toks])
        return edit

# Input 1: An edit list = [orig_start, orig_end, cat, cor, cor_start, cor_end]
# Input 2: A coder id for the specific annotator.
# Output: An edit in m2 file format.
def format_edit(edit: Edit, coder_id: int = 0) -> str:
    span = " ".join(["A", str(edit.original_span[0]), str(edit.original_span[1])])
    category_str = str(edit.error_type) if edit.error_type else ''
    return "|||".join([span, category_str, edit.edit_text, "REQUIRED", "-NONE-", str(coder_id)])