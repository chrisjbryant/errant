from copy import copy

TAKE_ERRANT = {0, 1, 2, 3, 5, 6, 10, 11, 12, 13, 14, 15, 16, 18, 19, 21, 22, 23, 24, 25, 26, 27, 29,
               31, 32, 35, 39, 42, 43, 46, 48, 49}
TAKE_SERCL = {8, 31, 40, 41}

# Input 1: Edit typed by errant
# Input 2: Edit typed by sercl
# Output: Edit typed by combining errant and sercl rules
def classification_combiner(errant_edit, sercl_edit):
    cond = errant_edit.cond
    new_edit = copy(errant_edit)
    sercl_type = errant_edit.type[:2] + sercl_edit.type

    if cond in TAKE_ERRANT:
        return new_edit
    elif cond in TAKE_SERCL:
        sercl_annotation_parts = sercl_edit.type.split('->')
        assert len(sercl_annotation_parts) == 2
        if sercl_annotation_parts[0] == 'None' and sercl_annotation_parts[1] == 'None':
            return new_edit
        if sercl_annotation_parts[0] == 'None':
            new_edit.type = errant_edit.type[:2] + sercl_annotation_parts[1]
        elif sercl_annotation_parts[1] == 'None' or sercl_annotation_parts[0] == sercl_annotation_parts[1]:
            new_edit.type = errant_edit.type[:2] + sercl_annotation_parts[0]
        else:
            new_edit.type = sercl_type
    elif cond in {44, 45}:
        new_edit.type = errant_edit.type + ':MW'
    elif cond in {36, 37, 47}:
        new_edit.type = errant_edit.type + ':WC'
    elif cond in {20, 41, 50}:
        new_edit.type = sercl_type  # TWO SIDED OTHER
    elif cond in {17, 33, 34}:
        new_edit.type = sercl_type  # MORPH
    elif cond == 9:
        if errant_edit.o_start != 0 and errant_edit.c_start != 0 and (errant_edit.o_toks[0].pos_ == 'PROPN') + \
                (errant_edit.c_toks[0].pos_ == 'PROPN') == 1:
            new_edit.type = sercl_type
    elif cond == 4:
        if errant_edit.o_toks:
            token = errant_edit.o_toks[0]
        else:
            token = errant_edit.c_toks[0]
        if token.lemma_.lower() not in {'be', 'will', 'have'}:
            new_edit.type = sercl_type
    return new_edit
