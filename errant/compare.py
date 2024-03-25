from .annotator import Annotator
from .edit import Edit
from typing import List
import copy
import pprint

def check_num_sents(
    srcs,
    hyps,
    refs
):
    for r in refs:
        assert len(r) == len(srcs) 
        assert len(r) == len(hyps)
    return

def compare_from_raw(
    orig: List[str],
    cor: List[str],
    refs: List[List[str]],
    beta=0.5,
    cat=1,
    detection=False, # correction is default
    single=False,
    multi=False,
    cat_filter=[],
    verbose=False
):
    # The references must be a two dimensions list
    if not isinstance(refs[0], list):
        refs = [refs]
    check_num_sents(
        orig, cor, refs
    )
    annotator = Annotator.load('en')
    parsed_s = []
    for s in orig:
        s = annotator.parse(s)
        parsed_s.append(s)
    # parsed_s = [annotator.parse(s) for s in sources]
    hyp_edits: List[List[Edit]] = []
    for i, h in enumerate(cor):
        parsed_h = annotator.parse(h)
        edits = annotator.annotate(parsed_s[i], parsed_h)
        hyp_edits.append(edits)
    ref_edits: List[List[List[Edit]]] = []  # (num_refs, num_sents, num_edits)
    for ref in refs:
        ref_ith_edits = []
        for i, r in enumerate(ref):
            parsed_r = annotator.parse(r)
            edits = annotator.annotate(parsed_s[i], parsed_r)
            ref_ith_edits.append(edits)
        ref_edits.append(ref_ith_edits)
    entire_score, etype_score = compare_from_edits(
        hyp_edits,
        ref_edits,
        beta=beta,
        cat=cat,
        detection=detection,
        single=single,
        multi=multi,
        cat_filter=cat_filter,
        verbose=verbose
    )
    return entire_score, etype_score

def compute_f(tp, fp, fn, beta):
    p = float(tp)/(tp+fp) if fp else 1.0
    r = float(tp)/(tp+fn) if fn else 1.0
    f = float((1+(beta**2))*p*r)/(((beta**2)*p)+r) if p+r else 0.0
    return round(p, 4), round(r, 4), round(f, 4)

def can_update_best(current_score, new_score, beta=0.5):
    current_entire_score = calc_entire_score(current_score)
    new_entire_score = calc_entire_score(new_score)
    cp, cr, cf = compute_f(
        current_entire_score['tp'],
        current_entire_score['fp'],
        current_entire_score['fn'],
        beta
    )
    np, nr, nf = compute_f(
        new_entire_score['tp'],
        new_entire_score['fp'],
        new_entire_score['fn'],
        beta
    )
    # if nf > cf or \
    #     (nf == cf and new_score['tp'] > current_score['tp']) or \
    #     (nf == cf and new_score['tp'] == current_score['tp'] and \
    #         new_score['fp'] < current_score['fp']) or \
    #     (nf == cf and new_score['tp'] == current_score['tp'] and \
    #         new_score['fp'] == current_score['fp'] and \
    #         new_score['fn'] < current_score['fn']):
    #     return True
    if nf > cf:
        return True
    if nf == cf and new_entire_score['tp'] > current_entire_score['tp']:
        return True
    if nf == cf and new_entire_score['tp'] == current_entire_score['tp'] \
        and new_entire_score['fp'] < current_entire_score['fp']:
        return True
    if nf == cf and new_entire_score['tp'] == current_entire_score['tp'] \
        and new_entire_score['fp'] == current_entire_score['fp'] \
        and new_entire_score['fn'] < current_entire_score['fn']:
        return True
    return False

def filter_edits(
    edits: List[List[Edit]],
    cat=1,
    detection=False, # correction is default
    single=False,
    multi=False,
    cat_filter=[],
):
    assert not (single and multi)
    new_edits = []
    for edit in edits:
        l = []
        for e in edit:
            if e.o_start == -1:
                continue
            if e.type in cat_filter:
                continue
            if single and e.is_multi():
                continue
            if multi and e.is_single():
                continue
            if detection:
                e.c_str = ''
            elif e.type in ['UNK']:
                # UNK is treated for only detection
                continue
            if cat == 1:
                e.type = e.type[0]
            elif cat == 2:
                e.type = e.type[2:]
            l.append(e)
        new_edits.append(l)
    return new_edits
    
def calc_entire_score(score):
    '''Convert error type based scores into an entire score.
    '''
    entire_score = {'tp': 0, 'fp': 0, 'fn': 0}
    for etype in score:
        for k in ['tp', 'fp', 'fn']:
            entire_score[k] += score[etype][k]
    return entire_score

def merge_dict(d1, d2):
    '''Add d2 information to d1
    '''
    if d1 is None:
        return d2
    for etype in d2.keys():
        d1[etype] = d1.get(etype, {'tp': 0, 'fp': 0, 'fn': 0})
        for k in ['tp', 'fp', 'fn']:
            d1[etype][k] += d2[etype][k]
    return d1

def print_table(table):
    longest_cols = [
        (max([len(str(row[i])) for row in table]) + 3)
        for i in range(len(table[0]))
    ]
    row_format = "".join(["{:>" + str(longest_col) + "}" for longest_col in longest_cols])
    for row in table:
        print(row_format.format(*row))

def compare_from_edits(
    hyp_edits: List[List[Edit]],
    ref_edits: List[List[List[Edit]]],
    beta=0.5,
    cat=1,
    detection=False, # correction is default
    single=False,
    multi=False,
    cat_filter=[],
    verbose=False
):
    if not isinstance(hyp_edits[0], list):
        hyp_edits = [hyp_edits]
    filter_args = {
        'cat': cat,
        'detection': detection,
        'single': single,
        'multi': multi,
        'cat_filter': cat_filter
    }
    # Removed correction to not be evaluated according to the setting
    hyp_edits = filter_edits(hyp_edits, **filter_args)
    ref_edits = [filter_edits(r, **filter_args) for r in ref_edits]
    for ref_id in range(len(ref_edits)):
        assert len(hyp_edits) == len(ref_edits[ref_id])
    etype_score = None
    # The shape of ref_edits is (num_refs, num_sents, num_edits)
    num_sents = len(ref_edits[0])
    num_annotator = len(ref_edits)
    for sent_id in range(num_sents):
        # best_score: sentence-level best score
        # shape: best_score[error_type]['tp'|'fp'|'fn'] = int
        best_score = None
        best_ref = 0
        for ref_id in range(num_annotator):
            current_score = dict()
            h_edits = hyp_edits[sent_id]
            r_edits = ref_edits[ref_id][sent_id]
            # True positive and False positive
            for edit in r_edits:
                current_score[edit.type] = current_score.get(
                    edit.type,
                    {'tp': 0, 'fp': 0, 'fn': 0}
                )
                if edit in h_edits:
                    current_score[edit.type]['tp'] += 1
                else:
                    current_score[edit.type]['fn'] += 1
            # False negative
            for edit in h_edits:
                if edit not in r_edits:
                    current_score[edit.type] = current_score.get(
                        edit.type,
                        {'tp': 0, 'fp': 0, 'fn': 0}
                    )
                    current_score[edit.type]['fp'] += 1
            # Update the best sentence-level score
            if best_score is None:
                # For the first refernece
                best_score = current_score
            elif can_update_best(
                merge_dict(copy.deepcopy(etype_score), best_score),
                merge_dict(copy.deepcopy(etype_score), current_score),
                beta
            ):
                # For the second or subsequent reference, chose the best one
                best_score = current_score
                best_ref = ref_id
        if verbose:
            print('{:-^40}'.format(""))
            print(f'^^ HYP 0, REF {best_ref} chosen for sentence {sent_id}')
            print('Local results:')
            header = ["Category", "TP", "FP", "FN"]
            body = [[k, v['tp'], v['fp'], v['fn']] for k, v in best_score.items()]
            print_table([header] + body)
        # print(f'=== Sent {sent_id} ===')
        # print(calc_entire_score(best_score))
        # Add to the best sentence-level score to the overall scores
        etype_score = merge_dict(etype_score, best_score)
    # print(etype_score)
    for etype in etype_score.keys():
        etype_score[etype]['p'], etype_score[etype]['r'], etype_score[etype][f'f_{beta}'] = compute_f(
            etype_score[etype]['tp'],
            etype_score[etype]['fp'],
            etype_score[etype]['fn'],
            beta
        )
    entire_score = calc_entire_score(etype_score)
    entire_score['p'], entire_score['r'], entire_score[f'f_{beta}'] = compute_f(
        entire_score['tp'],
        entire_score['fp'],
        entire_score['fn'],
        beta
    )
    return entire_score, etype_score