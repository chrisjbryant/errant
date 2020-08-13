# Input: A list of Spacy tokens
# Output: The highest token, that has the least depth in the dependency tree.
def highest_token(tokens):
    def get_token_depth(token):
        depth = 1
        while token.dep_ != 'ROOT':
            token = token.head
            depth += 1
        return depth

    if not tokens:
        return None
    return min(tokens, key=get_token_depth)


# Input: An Edit object
# Output: This Edit, typed by sercl
def classify(edit):
    # Nothing to nothing is a detected but not corrected edit
    if (not edit.o_toks and not edit.c_toks) or (edit.o_str == edit.c_str):
        edit.type = "UNK"
    elif edit.o_toks and edit.c_toks and edit.o_toks[-1].lower == edit.c_toks[-1].lower and \
            (len(edit.o_toks) > 1 or len(edit.c_toks) > 1):
        # Store a copy of the full orig and cor toks
        all_o_toks = edit.o_toks[:]
        all_c_toks = edit.c_toks[:]
        # Truncate the instance toks for classification
        edit.o_toks = edit.o_toks[:-1]
        edit.c_toks = edit.c_toks[:-1]
        # Classify the truncated edit
        edit = classify(edit)
        # Restore the full orig and cor toks
        edit.o_toks = all_o_toks
        edit.c_toks = all_c_toks
        return edit

    if edit.o_end == edit.o_start:
        head = None
    else:
        head = highest_token(edit.o_toks)

    if edit.c_end == edit.c_start:
        tail = None
    else:
        tail = highest_token(edit.c_toks)

    src_pos = "None" if head is None else head.pos_
    corr_pos = "None" if tail is None else tail.pos_

    edit.type = src_pos + "->" + corr_pos
    return edit
