from copy import copy

TAKE_ERRANT = {0, 1, 2, 3, 5, 6, 10, 11, 12, 13, 14, 15, 16, 18, 19, 21, 22, 23, 24, 25, 26, 27, 29,
               31, 32, 38, 42, 43, 46, 48, 49}

TAKE_SERCL = {7, 8, 30, 39, 40}

RARE_AND_PUNCT_POS = {"PUNCT", "INTJ", "NUM", "SYM", "X"}

MODAL_VERBS = {'can', 'could', 'may', 'might', 'shall', 'should', 'will', 'would', 'must'}


# Input 1: Edit typed by errant
# Input 2: Edit typed by sercl
# Output: Edit typed by combining errant and sercl rules
def classification_combiner(errant_edit, sercl_edit):
    cond = errant_edit.cond
    new_edit = copy(errant_edit)
    sercl_type = errant_edit.type[:2] + sercl_edit.type
    sercl_annotation_parts = sercl_edit.type.split('->')
    assert len(sercl_annotation_parts) == 2

    if cond in TAKE_ERRANT:
        return new_edit

    elif cond in TAKE_SERCL:
        if sercl_annotation_parts[0] == 'None' and sercl_annotation_parts[1] == 'None':
            return new_edit
        if sercl_annotation_parts[0] == 'None':
            new_edit.type = errant_edit.type[:2] + sercl_annotation_parts[1]
        elif sercl_annotation_parts[1] == 'None' or sercl_annotation_parts[0] == sercl_annotation_parts[1]:
            new_edit.type = errant_edit.type[:2] + sercl_annotation_parts[0]
        else:
            new_edit.type = sercl_type

    elif cond in {44, 45}:
        new_edit.type = errant_edit.type + ':MW'  # stands for MultiWords

    elif cond in {36, 37, 47}:
        new_edit.type = errant_edit.type + ':WC'  # stands for Word Choice

    elif cond in {20, 41, 50}:  # TWO SIDED OTHER
        # Rare pos tags cause an unexpected behaviour of the parser, and because sercl is based on the parsing
        # it is likely to fail, so errant is preferred.
        # Punctuation is parsed to high level in terms of depth in the parsing tree, and sercl will be confused
        # and take it as the "head" of the edit, what we don't want.
        if sercl_annotation_parts[0] in RARE_AND_PUNCT_POS or sercl_annotation_parts[1] in RARE_AND_PUNCT_POS:
            new_edit.type = errant_edit.type
        # PROPN is frequently used by the parser when it doesn't understand a word, so OTHER is better in most of the cases.
        elif 'PROPN' in sercl_annotation_parts and sercl_edit.type != 'PROPN->PROPN':
            new_edit.type = errant_edit.type
        # X->X will be written as X
        elif sercl_annotation_parts[0] == sercl_annotation_parts[1]:
            new_edit.type = errant_edit.type[:2] + sercl_annotation_parts[0]
        # sercl gives more information
        else:
            new_edit.type = sercl_type

        if cond == 50:
            new_edit.type = new_edit.type + ':MW'  # stands for MultiWords

    elif cond in {17, 28, 33, 34}:  # MORPH
        # PROPN is frequently used by the parser when it doesn't understand a word, so OTHER is better in most
        # of the cases. An exception is the cases that it changed from/to ADJ, like China<->Chinese.
        if 'PROPN' in sercl_annotation_parts and 'ADJ' not in sercl_annotation_parts:
            new_edit.type = errant_edit.type
        # X->X will be written as X
        elif sercl_annotation_parts[0] == sercl_annotation_parts[1]:
            new_edit.type = errant_edit.type + ':' + sercl_annotation_parts[0]
        # sercl gives more information
        else:
            new_edit.type = sercl_type

    elif cond == 9:  # Orthography; i.e. whitespace and/or case errors.
        if errant_edit.o_start != 0 and errant_edit.c_start != 0 and (errant_edit.o_toks[0].pos_ == 'PROPN') + \
                (errant_edit.c_toks[0].pos_ == 'PROPN') == 1:
            new_edit.type = sercl_type

    elif cond == 4:  # Under aux relation, could be a tense issue, a modal verb, or other (one sided).
        if errant_edit.o_toks:
            token = errant_edit.o_toks[0]
        else:
            token = errant_edit.c_toks[0]
        # It is not a   simple tense issue
        if token.lemma_.lower() not in {'be', 'have'} and token.text.lower() != 'will':
            new_edit.type = sercl_type
        # Modal verbs addition/deletion
        if token.text.lower() in MODAL_VERBS:
            new_edit.type = errant_edit.type[:2] + 'MODAL'

    elif cond == 35:  # Under aux relation, could be a tense issue, a modal verb, or other (two sided).
        # It is not a simple tense issue
        if (errant_edit.o_toks[0].lemma_.lower() not in {'be', 'have'} and errant_edit.o_toks[0].text.lower() != 'will')\
                or (errant_edit.c_toks[0].lemma_.lower() not in {'be', 'have'} and errant_edit.c_toks[0].text.lower() != 'will'):
            new_edit.type = sercl_type
        # Modal verbs changing
        if errant_edit.o_toks[0].text.lower() in MODAL_VERBS and errant_edit.c_toks[0].text.lower() in MODAL_VERBS:
            new_edit.type = errant_edit.type[:2] + 'MODAL'

    return new_edit

