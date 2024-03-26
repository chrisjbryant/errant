from errant.edit import Edit
from typing import List
import copy
import pprint
from typing import List, Tuple, Union, Dict
import errant

def check_num_sents(
    srcs: List[str],
    hyps: List[str],
    refs: List[List[str]]
) -> None:
    for r in refs:
        assert len(r) == len(srcs) 
        assert len(r) == len(hyps)
    return

def compare_from_raw(
    orig: List[str],
    cor: List[str],
    refs: List[List[str]],
    beta: float=0.5,
    cat: int=1,
    detection: bool=False, # correction is default
    single: bool=False,
    multi: bool=False,
    filt: List[str]=[],
    verbose: bool=False
) -> Tuple[
        Dict[str, Union[int, float]],
        Dict[str, Dict[str, Union[int, float]]]
    ]:
    '''errant_compare given the raw text
    Args:
        orig: Original sentences
        cor: Corrected sentences
        refs: References
            refs can be multiple. The shape is (num_annotations, num_sents)
        beta: the beta for F_{beta}
        cat: 1 or 2 or 3.
            1: Only show operation tier scores; e.g. R.
            2: Only show main tier scores; e.g. NOUN.
            3: Show all category scores; e.g. R:NOUN.
        detection: To calculate detection score.
        single: Only evaluate single token edits; i.e. 0:1, 1:0 or 1:1
        mulit: Only evaluate multi token edits; i.e. 2+:n or n:2+
        filt: Do not evaluate the specified error types.
        verbose: Print verbose output.
    Returns:
        overall_score: The key is {'tp', 'fp', 'fn', 'p', 'r', 'f_{beta}'}.
        etype_score: Error-type-wise score. 
            This is two dimensional dictionaly.
            The first key is error type.
            The second key is {'tp', 'fp', 'fn', 'p', 'r', 'f_{beta}'}.
            The values is the number of corrections.
    '''
    # The references must be a two dimensions list
    if not isinstance(refs[0], list):
        # The shape of refs must be (num_annotations, num_sents)
        refs = [refs]
    check_num_sents(
        orig, cor, refs
    )
    annotator = errant.load('en')
    # parsed_s = []
    # for s in orig:
    #     s = annotator.parse(s)
    #     parsed_s.append(s)
    # # parsed_s = [annotator.parse(s) for s in sources]
    # hyp_edits: List[List[Edit]] = []
    # for i, h in enumerate(cor):
    #     parsed_h = annotator.parse(h)
    #     edits = annotator.annotate(parsed_s[i], parsed_h)
    #     hyp_edits.append(edits)
    # ref_edits: List[List[List[Edit]]] = []  # (num_refs, num_sents, num_edits)
    # for ref in refs:
    #     ref_ith_edits = []
    #     for i, r in enumerate(ref):
    #         parsed_r = annotator.parse(r)
    #         edits = annotator.annotate(parsed_s[i], parsed_r)
    #         ref_ith_edits.append(edits)
    #     ref_edits.append(ref_ith_edits)
    # Parse each sentences
    orig = [annotator.parse(o) for o in orig]
    cor = [annotator.parse(c) for c in cor]
    refs = [[annotator.parse(r) for r in ref] for ref in refs]
    # Generate Edit objects
    hyp_edits = [annotator.annotate(o, c) for o, c in zip(orig, cor)]
    ref_edits = [[annotator.annotate(o, r) for o, r in zip(orig, ref)] for ref in refs]
    overall_score, etype_score = compare_from_edits(
        hyp_edits,
        ref_edits,
        beta=beta,
        cat=cat,
        detection=detection,
        single=single,
        multi=multi,
        filt=filt,
        verbose=verbose
    )
    return overall_score, etype_score

def compute_f(tp: int, fp: int, fn: int, beta: float):
    '''Compute F_{beta} score given TP, FP, FN.
    This is copied from official imlementation:
        https://github.com/chrisjbryant/errant
    '''
    p = float(tp)/(tp+fp) if fp else 1.0
    r = float(tp)/(tp+fn) if fn else 1.0
    f = float((1+(beta**2))*p*r)/(((beta**2)*p)+r) if p+r else 0.0
    return round(p, 4), round(r, 4), round(f, 4)

def can_update_best(
    current_score: Dict[str, Dict[str, Union[int, float]]],
    new_score: Dict[str, Dict[str, Union[int, float]]],
    beta: float=0.5
):
    '''Check whether the new_score outperforms the current best score.
    '''
    # The inputs are error-type-wise scores, so we first convert them to entire score
    current_overall_score = calc_overall_score(current_score)
    new_overall_score = calc_overall_score(new_score)
    # Compute F_{beta} given TP/FP/FN
    cp, cr, cf = compute_f(
        current_overall_score['tp'],
        current_overall_score['fp'],
        current_overall_score['fn'],
        beta
    )
    np, nr, nf = compute_f(
        new_overall_score['tp'],
        new_overall_score['fp'],
        new_overall_score['fn'],
        beta
    )
    # This rule is the same as original implementation.
    if nf > cf:
        return True
    if nf == cf and new_overall_score['tp'] > current_overall_score['tp']:
        return True
    if nf == cf and new_overall_score['tp'] == current_overall_score['tp'] \
        and new_overall_score['fp'] < current_overall_score['fp']:
        return True
    if nf == cf and new_overall_score['tp'] == current_overall_score['tp'] \
        and new_overall_score['fp'] == current_overall_score['fp'] \
        and new_overall_score['fn'] < current_overall_score['fn']:
        return True
    return False

def filter_edits(
    edits: List[List[Edit]],
    cat: int=1,
    detection: bool=False, # correction is default
    single: bool=False,
    multi: bool=False,
    filt: list=[],
):
    '''To remove the corrections that not to be evaluated.
    '''
    assert not (single and multi)
    new_edits = []
    for edit in edits:
        l = []
        for e in edit:
            # 'noop' edits are ignored
            if e.o_start == -1:
                continue
            # Filtered error types are ignored
            if e.type in filt:
                continue
            if single and e.is_multi():
                continue
            if multi and e.is_single():
                continue 
            if detection:
                # To ignore c_str in the detection scoring,
                #   it is replaced with an empty string.
                e.c_str = ''
            elif e.type in ['UNK']:
                # UNK is treated for only detection
                continue
            if cat == 1:
                # e.g. 'M:NOUN:NUM' -> 'M'
                e.type = e.type[0]
            elif cat == 2:
                # e.g. 'M:NOUN:NUM' -> 'NOUN:NUM'
                e.type = e.type[2:]
            l.append(e)
        new_edits.append(l)
    return new_edits
    
def calc_overall_score(score: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    '''Convert error type based scores into an entire score.
    Args:
        score: Dict[str, Dict[str, int]]
            The first key is error type.
            The second key is 'tp' or 'fp' or 'fn'.
            The values is the number of corrections.
    '''
    overall_score = {'tp': 0, 'fp': 0, 'fn': 0}
    for etype in score:
        for k in ['tp', 'fp', 'fn']:
            overall_score[k] += score[etype][k]
    return overall_score

def merge_dict(
    d1: Dict[str, Dict[str, int]],
    d2: Dict[str, Dict[str, int]]
):
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
    '''This is for verbose setting.
    This is copied from official imlementation:
        https://github.com/chrisjbryant/errant
    '''
    longest_cols = [
        (max([len(str(row[i])) for row in table]) + 3)
        for i in range(len(table[0]))
    ]
    row_format = "".join(["{:>" + str(longest_col) + "}" for longest_col in longest_cols])
    for row in table:
        print(row_format.format(*row))

def compare_from_edits(
    hyp_edits: List[List[Edit]],  # (num_sents, num_edits)
    ref_edits: List[List[List[Edit]]],  # (num_annotations, num_sents, num_edts)
    beta: float=0.5,
    cat: int=1,
    detection: bool=False, # correction is default
    single: bool=False,
    multi: bool=False,
    filt: List[str]=[],
    verbose: bool=False
):
    '''errant_compare given edits, which are the results of errant.Annotator.annotate()
    Args:
        hyp_edits: The edits between original and correction.
        ref_edits: The edits between original and references.
            This can be multiple. The shape is (num_annotations, num_sents, num_edits)
    Other args and returns is the same as compare_from_raw().
    '''
    filter_args = {
        'cat': cat,
        'detection': detection,
        'single': single,
        'multi': multi,
        'filt': filt
    }
    # Removed correction not to be evaluated
    hyp_edits = filter_edits(hyp_edits, **filter_args)
    ref_edits = [filter_edits(r, **filter_args) for r in ref_edits]
    for ref_id in range(len(ref_edits)):
        assert len(hyp_edits) == len(ref_edits[ref_id])
    etype_score = None  # This will be final scores
    num_annotator = len(ref_edits)
    num_sents = len(ref_edits[0])
    for sent_id in range(num_sents):
        # best_score: sentence-level best score
        best_score: Dict[str, Dict[str, int]] = None
        best_ref = 0
        for ref_id in range(num_annotator):
            current_score = dict()
            h_edits = hyp_edits[sent_id]
            r_edits = ref_edits[ref_id][sent_id]
            # True positive and False negative
            for edit in r_edits:
                current_score[edit.type] = current_score.get(
                    edit.type,
                    {'tp': 0, 'fp': 0, 'fn': 0}
                )
                if edit in h_edits:
                    current_score[edit.type]['tp'] += 1
                else:
                    current_score[edit.type]['fn'] += 1
            # False positive
            for edit in h_edits:
                if edit not in r_edits:
                    current_score[edit.type] = current_score.get(
                        edit.type,
                        {'tp': 0, 'fp': 0, 'fn': 0}
                    )
                    current_score[edit.type]['fp'] += 1
            # Update the best sentence-level score
            if best_score is None:
                best_score = current_score
            elif can_update_best(
                merge_dict(copy.deepcopy(etype_score), best_score),
                merge_dict(copy.deepcopy(etype_score), current_score),
                beta
            ):
                # For the second or subsequent reference, chose the best one
                # Note that the comparison is based on the value when added to the cumulative score so far
                best_score = current_score
                best_ref = ref_id
        if verbose:
            print('{:-^40}'.format(""))
            print(f'^^ HYP 0, REF {best_ref} chosen for sentence {sent_id}')
            print('Local results:')
            header = ["Category", "TP", "FP", "FN"]
            body = [[k, v['tp'], v['fp'], v['fn']] for k, v in best_score.items()]
            print_table([header] + body)
        # Add to the best sentence-level score to the overall score
        etype_score = merge_dict(etype_score, best_score)
    # Calculate precision, recall, F_{beta} for each error type
    for etype in etype_score.keys():
        etype_score[etype]['p'], etype_score[etype]['r'], etype_score[etype][f'f_{beta}'] = compute_f(
            etype_score[etype]['tp'],
            etype_score[etype]['fp'],
            etype_score[etype]['fn'],
            beta
        )
    # Calculate overall score from error type wise score
    overall_score = calc_overall_score(etype_score)
    # And precision, recall and F_{beta}
    overall_score['p'], overall_score['r'], overall_score[f'f_{beta}'] = compute_f(
        overall_score['tp'],
        overall_score['fp'],
        overall_score['fn'],
        beta
    )
    return overall_score, etype_score