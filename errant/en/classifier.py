from pathlib import Path
import Levenshtein
from errant.en.lancaster import LancasterStemmer
import spacy
import spacy.symbols as POS

# Load Hunspell word list
def load_word_list(path):
    with open(path) as word_list:
        return set([word.strip() for word in word_list])

# Load Universal Dependency POS Tags map file.
# https://universaldependencies.org/tagset-conversion/en-penn-uposf.html
def load_pos_map(path):
    map_dict = {}
    with open(path) as map_file:
        for line in map_file:
            line = line.strip().split("\t")
            # Change ADP to PREP for readability
            if line[1] == "ADP": map_dict[line[0]] = "PREP"
            # Change PROPN to NOUN; we don't need a prop noun tag
            elif line[1] == "PROPN": map_dict[line[0]] = "NOUN"
            # Change CCONJ to CONJ
            elif line[1] == "CCONJ": map_dict[line[0]] = "CONJ"
            # Otherwise
            else: map_dict[line[0]] = line[1].strip()
        # Add some spacy PTB tags not in the original mapping.
        map_dict['""'] = "PUNCT"
        map_dict["SP"] = "SPACE"
        map_dict["_SP"] = "SPACE"
        map_dict["BES"] = "VERB"
        map_dict["HVS"] = "VERB"
        map_dict["ADD"] = "X"
        map_dict["GW"] = "X"
        map_dict["NFP"] = "X"
        map_dict["XX"] = "X"
    return map_dict

# Classifier resources
base_dir = Path(__file__).resolve().parent
# Spacy
nlp = None
# Lancaster Stemmer
stemmer = LancasterStemmer()
# GB English word list (inc -ise and -ize)
spell = load_word_list(base_dir/"resources"/"en_GB-large.txt")
# Part of speech map file
pos_map = load_pos_map(base_dir/"resources"/"en-ptb_map")
# Open class coarse Spacy POS tags 
open_pos1 = {POS.ADJ, POS.ADV, POS.NOUN, POS.VERB}
# Open class coarse Spacy POS tags (strings)
open_pos2 = {"ADJ", "ADV", "NOUN", "VERB"}
# Rare POS tags that make uninformative error categories
rare_pos = {"INTJ", "NUM", "SYM", "X"}
# Contractions
conts = {"'d", "'ll", "'m", "n't", "'re", "'s", "'ve"}
# Special auxiliaries in contractions.
aux_conts = {"ca": "can", "sha": "shall", "wo": "will"}
# Some dep labels that map to pos tags.
dep_map = {
    "acomp": "ADJ",
    "amod": "ADJ",
    "advmod": "ADV",
    "det": "DET", 
    "prep": "PREP",
    "prt": "PART",
    "punct": "PUNCT"}

# Input: An Edit object
# Output: The same Edit object with an updated error type
def classify(edit):
    # Nothing to nothing is a detected but not corrected edit
    if not edit.o_toks and not edit.c_toks:
        edit.type = "UNK"
    # Missing
    elif not edit.o_toks and edit.c_toks:
        op = "M:"
        cat = get_one_sided_type(edit.c_toks)
        edit.type = op+cat
    # Unnecessary
    elif edit.o_toks and not edit.c_toks:
        op = "U:"
        cat = get_one_sided_type(edit.o_toks)
        edit.type = op+cat
    # Replacement and special cases
    else:
        # Same to same is a detected but not corrected edit
        if edit.o_str == edit.c_str:
            edit.type = "UNK"
        # Special: Ignore case change at the end of multi token edits
        # E.g. [Doctor -> The doctor], [, since -> . Since]
        # Classify the edit as if the last token wasn't there
        elif edit.o_toks[-1].lower == edit.c_toks[-1].lower and \
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
        # Replacement
        else:
            op = "R:"
            cat = get_two_sided_type(edit.o_toks, edit.c_toks)
            edit.type = op+cat
    return edit

# Input: Spacy tokens
# Output: A list of pos and dep tag strings
def get_edit_info(toks):
    pos = []
    dep = []
    for tok in toks:
        pos.append(pos_map[tok.tag_])
        dep.append(tok.dep_)
    return pos, dep

# Input: Spacy tokens
# Output: An error type string based on input tokens from orig or cor
# When one side of the edit is null, we can only use the other side
def get_one_sided_type(toks):
    # Special cases
    if len(toks) == 1:
        # Possessive noun suffixes; e.g. ' -> 's
        if toks[0].tag_ == "POS":
            return "NOUN:POSS"
        # Contractions. Rule must come after possessive
        if toks[0].lower_ in conts:
            return "CONTR"
        # Infinitival "to" is treated as part of a verb form
        if toks[0].lower_ == "to" and toks[0].pos == POS.PART and \
                toks[0].dep_ != "prep":
            return "VERB:FORM"
    # Extract pos tags and parse info from the toks
    pos_list, dep_list = get_edit_info(toks)
    # Auxiliary verbs
    if set(dep_list).issubset({"aux", "auxpass"}):
        return "VERB:TENSE"
    # POS-based tags. Ignores rare, uninformative categories
    if len(set(pos_list)) == 1 and pos_list[0] not in rare_pos:
        return pos_list[0]
    # More POS-based tags using special dependency labels
    if len(set(dep_list)) == 1 and dep_list[0] in dep_map.keys():
        return dep_map[dep_list[0]]
    # To-infinitives and phrasal verbs
    if set(pos_list) == {"PART", "VERB"}:
        return "VERB"
    # Tricky cases
    else:
        return "OTHER"

# Input 1: Spacy orig tokens
# Input 2: Spacy cor tokens
# Output: An error type string based on orig AND cor
def get_two_sided_type(o_toks, c_toks):
    # Extract pos tags and parse info from the toks as lists
    o_pos, o_dep = get_edit_info(o_toks)
    c_pos, c_dep = get_edit_info(c_toks)

    # Orthography; i.e. whitespace and/or case errors.
    if only_orth_change(o_toks, c_toks):
        return "ORTH"
    # Word Order; only matches exact reordering.
    if exact_reordering(o_toks, c_toks):
        return "WO"

    # 1:1 replacements (very common)
    if len(o_toks) == len(c_toks) == 1:
        # 1. SPECIAL CASES
        # Possessive noun suffixes; e.g. ' -> 's
        if o_toks[0].tag_ == "POS" or c_toks[0].tag_ == "POS":
            return "NOUN:POSS"
        # Contraction. Rule must come after possessive.
        if (o_toks[0].lower_ in conts or \
                c_toks[0].lower_ in conts) and \
                o_pos == c_pos:
            return "CONTR"
        # Special auxiliaries in contractions (1); e.g. ca -> can, wo -> will
        # Rule was broken in V1. Turned off this fix for compatibility.
        if (o_toks[0].lower_ in aux_conts and \
                c_toks[0].lower_ == aux_conts[o_toks[0].lower_]) or \
                (c_toks[0].lower_ in aux_conts and \
                o_toks[0].lower_ == aux_conts[c_toks[0].lower_]):
            return "CONTR"
        # Special auxiliaries in contractions (2); e.g. ca -> could, wo -> should
        if o_toks[0].lower_ in aux_conts or \
                c_toks[0].lower_ in aux_conts:
            return "VERB:TENSE"
        # Special: "was" and "were" are the only past tense SVA
        if {o_toks[0].lower_, c_toks[0].lower_} == {"was", "were"}:
            return "VERB:SVA"

        # 2. SPELLING AND INFLECTION
        # Only check alphabetical strings on the original side
        # Spelling errors take precedence over POS errors; this rule is ordered
        if o_toks[0].text.isalpha():
            # Check a GB English dict for both orig and lower case.
            # E.g. "cat" is in the dict, but "Cat" is not.
            if o_toks[0].text not in spell and \
                    o_toks[0].lower_ not in spell:
                # Check if both sides have a common lemma
                if o_toks[0].lemma == c_toks[0].lemma:
                    # Inflection; often count vs mass nouns or e.g. got vs getted
                    if o_pos == c_pos and o_pos[0] in {"NOUN", "VERB"}:
                        return o_pos[0]+":INFL"
                    # Unknown morphology; i.e. we cannot be more specific.
                    else:
                        return "MORPH"
                # Use string similarity to detect true spelling errors.
                else:
                    char_ratio = Levenshtein.ratio(o_toks[0].text, c_toks[0].text)
                    # Ratio > 0.5 means both side share at least half the same chars.
                    # WARNING: THIS IS AN APPROXIMATION.
                    if char_ratio > 0.5:
                        return "SPELL"
                    # If ratio is <= 0.5, the error is more complex e.g. tolk -> say
                    else:
                        # If POS is the same, this takes precedence over spelling.
                        if o_pos == c_pos and \
                                o_pos[0] not in rare_pos:
                            return o_pos[0]
                        # Tricky cases.
                        else:
                            return "OTHER"

        # 3. MORPHOLOGY
        # Only ADJ, ADV, NOUN and VERB can have inflectional changes.
        if o_toks[0].lemma == c_toks[0].lemma and \
                o_pos[0] in open_pos2 and \
                c_pos[0] in open_pos2:
            # Same POS on both sides
            if o_pos == c_pos:
                # Adjective form; e.g. comparatives
                if o_pos[0] == "ADJ":
                    return "ADJ:FORM"
                # Noun number
                if o_pos[0] == "NOUN":
                    return "NOUN:NUM"
                # Verbs - various types
                if o_pos[0] == "VERB":
                    # NOTE: These rules are carefully ordered.
                    # Use the dep parse to find some form errors.
                    # Main verbs preceded by aux cannot be tense or SVA.
                    if preceded_by_aux(o_toks, c_toks):
                        return "VERB:FORM"
                    # Use fine PTB tags to find various errors.
                    # FORM errors normally involve VBG or VBN.
                    if o_toks[0].tag_ in {"VBG", "VBN"} or \
                            c_toks[0].tag_ in {"VBG", "VBN"}:
                        return "VERB:FORM"
                    # Of what's left, TENSE errors normally involved VBD.
                    if o_toks[0].tag_ == "VBD" or c_toks[0].tag_ == "VBD":
                        return "VERB:TENSE"
                    # Of what's left, SVA errors normally involve VBZ.
                    if o_toks[0].tag_ == "VBZ" or c_toks[0].tag_ == "VBZ":
                        return "VERB:SVA"
                    # Any remaining aux verbs are called TENSE.
                    if o_dep[0].startswith("aux") and \
                            c_dep[0].startswith("aux"):
                        return "VERB:TENSE"
            # Use dep labels to find some more ADJ:FORM
            if set(o_dep+c_dep).issubset({"acomp", "amod"}):
                return "ADJ:FORM"
            # Adj to plural noun is usually noun number; e.g. musical -> musicals.
            if o_pos[0] == "ADJ" and c_toks[0].tag_ == "NNS":
                return "NOUN:NUM"
            # For remaining verb errors (rare), rely on c_pos
            if c_toks[0].tag_ in {"VBG", "VBN"}:
                return "VERB:FORM"
            if c_toks[0].tag_ == "VBD":
                return "VERB:TENSE"
            if c_toks[0].tag_ == "VBZ":
                return "VERB:SVA"
            # Tricky cases that all have the same lemma.
            else:
                return "MORPH"
        # Derivational morphology.
        if stemmer.stem(o_toks[0].text) == stemmer.stem(c_toks[0].text) and \
                o_pos[0] in open_pos2 and \
                c_pos[0] in open_pos2:
            return "MORPH"

        # 4. GENERAL
        # Auxiliaries with different lemmas
        if o_dep[0].startswith("aux") and c_dep[0].startswith("aux"):
            return "VERB:TENSE"
        # POS-based tags. Some of these are context sensitive mispellings.
        if o_pos == c_pos and o_pos[0] not in rare_pos:
            return o_pos[0]
        # Some dep labels map to POS-based tags.
        if o_dep == c_dep and o_dep[0] in dep_map.keys():
            return dep_map[o_dep[0]]
        # Phrasal verb particles.
        if set(o_pos+c_pos) == {"PART", "PREP"} or \
                set(o_dep+c_dep) == {"prt", "prep"}:
            return "PART"
        # Can use dep labels to resolve DET + PRON combinations.
        if set(o_pos+c_pos) == {"DET", "PRON"}:
            # DET cannot be a subject or object.
            if c_dep[0] in {"nsubj", "nsubjpass", "dobj", "pobj"}:
                return "PRON"
            # "poss" indicates possessive determiner
            if c_dep[0] == "poss":
                return "DET"
        # Tricky cases.
        else:
            return "OTHER"

    # Multi-token replacements (uncommon)
    # All auxiliaries
    if set(o_dep+c_dep).issubset({"aux", "auxpass"}):
        return "VERB:TENSE"
    # All same POS
    if len(set(o_pos+c_pos)) == 1:
        # Final verbs with the same lemma are tense; e.g. eat -> has eaten 
        if o_pos[0] == "VERB" and \
                o_toks[-1].lemma == c_toks[-1].lemma:
            return "VERB:TENSE"
        # POS-based tags.
        elif o_pos[0] not in rare_pos:
            return o_pos[0]
    # All same special dep labels.
    if len(set(o_dep+c_dep)) == 1 and \
            o_dep[0] in dep_map.keys():
        return dep_map[o_dep[0]]
    # Infinitives, gerunds, phrasal verbs.
    if set(o_pos+c_pos) == {"PART", "VERB"}:
        # Final verbs with the same lemma are form; e.g. to eat -> eating
        if o_toks[-1].lemma == c_toks[-1].lemma:
            return "VERB:FORM"
        # Remaining edits are often verb; e.g. to eat -> consuming, look at -> see
        else:
            return "VERB"
    # Possessive nouns; e.g. friends -> friend 's
    if (o_pos == ["NOUN", "PART"] or c_pos == ["NOUN", "PART"]) and \
            o_toks[0].lemma == c_toks[0].lemma:
        return "NOUN:POSS"
    # Adjective forms with "most" and "more"; e.g. more free -> freer
    if (o_toks[0].lower_ in {"most", "more"} or \
            c_toks[0].lower_ in {"most", "more"}) and \
            o_toks[-1].lemma == c_toks[-1].lemma and \
            len(o_toks) <= 2 and len(c_toks) <= 2:
        return "ADJ:FORM"

    # Tricky cases.
    else:
        return "OTHER"

# Input 1: Spacy orig tokens
# Input 2: Spacy cor tokens
# Output: Boolean; the difference between orig and cor is only whitespace or case
def only_orth_change(o_toks, c_toks):
    o_join = "".join([o.lower_ for o in o_toks])
    c_join = "".join([c.lower_ for c in c_toks])
    if o_join == c_join:
        return True
    return False

# Input 1: Spacy orig tokens
# Input 2: Spacy cor tokens
# Output: Boolean; the tokens are exactly the same but in a different order
def exact_reordering(o_toks, c_toks):
    # Sorting lets us keep duplicates.
    o_set = sorted([o.lower_ for o in o_toks])
    c_set = sorted([c.lower_ for c in c_toks])
    if o_set == c_set:
        return True
    return False

# Input 1: An original text spacy token. 
# Input 2: A corrected text spacy token.
# Output: Boolean; both tokens have a dependant auxiliary verb.
def preceded_by_aux(o_tok, c_tok):
    # If the toks are aux, we need to check if they are the first aux.
    if o_tok[0].dep_.startswith("aux") and c_tok[0].dep_.startswith("aux"):
        # Find the parent verb
        o_head = o_tok[0].head
        c_head = c_tok[0].head
        # Find the children of the parent
        o_children = o_head.children
        c_children = c_head.children
        # Check the orig children.
        for o_child in o_children:
            # Look at the first aux...
            if o_child.dep_.startswith("aux"):
                # Check if the string matches o_tok
                if o_child.text != o_tok[0].text:
                    # If it doesn't, o_tok is not first so check cor
                    for c_child in c_children:
                        # Find the first aux in cor...
                        if c_child.dep_.startswith("aux"):
                            # If that doesn't match either, neither are first aux
                            if c_child.text != c_tok[0].text:
                                return True
                            # Break after the first cor aux
                            break
                # Break after the first orig aux.
                break
    # Otherwise, the toks are main verbs so we need to look for any aux.
    else:
        o_deps = [o_dep.dep_ for o_dep in o_tok[0].children]
        c_deps = [c_dep.dep_ for c_dep in c_tok[0].children]
        if "aux" in o_deps or "auxpass" in o_deps:
            if "aux" in c_deps or "auxpass" in c_deps:
                return True
    return False