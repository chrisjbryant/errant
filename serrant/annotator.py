from serrant.alignment import Alignment
from serrant.edit import Edit
from copy import copy
from spacy.tokens import Doc


# Main ERRANT Annotator class
class Annotator:    

    # Input 1: A string language id: e.g. "en"
    # Input 2: A spacy processing object for the language
    # Input 3: A merging module for the language
    # Input 4: A classifier module for the language
    def __init__(self, lang, nlp=None, merger=None, classifier=None, syntax_classifier=None,
                 classification_combiner=None):
        self.lang = lang
        self.nlp = nlp
        self.merger = merger
        self.errant_classifier = classifier
        self.syntax_classifier = syntax_classifier
        self.combiner = classification_combiner

    # Input 1: A text string
    # Input 2: A flag for word tokenisation
    # Output: The input string parsed by spacy
    def parse(self, text, tokenise=False):
        if tokenise:
            text = self.nlp(text)
        else:
            text = Doc(self.nlp.vocab, text.split())
            self.nlp.tagger(text)
            self.nlp.parser(text)
        return text

    # Input 1: An original text string parsed by spacy
    # Input 2: A corrected text string parsed by spacy
    # Input 3: A flag for standard Levenshtein alignment
    # Output: An Alignment object
    def align(self, orig, cor, lev=False):
        return Alignment(orig, cor, lev)

    # Input 1: An Alignment object
    # Input 2: A flag for merging strategy
    # Output: A list of Edit objects
    def merge(self, alignment, merging="rules"):
        # rules: Rule-based merging
        if merging == "rules":
            edits = self.merger.get_rule_edits(alignment)
        # all-split: Don't merge anything
        elif merging == "all-split":
            edits = alignment.get_all_split_edits()
        # all-merge: Merge all adjacent non-match ops
        elif merging == "all-merge":
            edits = alignment.get_all_merge_edits()
        # all-equal: Merge all edits of the same operation type
        elif merging == "all-equal":
            edits = alignment.get_all_equal_edits()
        # Unknown
        else:
            raise Exception("Unknown merging strategy. Choose from: "
                "rules, all-split, all-merge, all-equal.")
        return edits

    # Input: An Edit object
    # Output: The same Edit object with an updated error type by errant
    def classify_by_errant(self, edit):
        return self.errant_classifier.classify(edit)

    # Input: An Edit object
    # Output: The same Edit object with an updated error type by sercl
    def classify_syntactically(self, edit):
        return self.syntax_classifier.classify(edit)

    # Input 1: An original text string parsed by spacy
    # Input 2: A corrected text string parsed by spacy
    # Input 3: A flag for standard Levenshtein alignment
    # Input 4: A flag for merging strategy
    # Output: A list of automatically extracted, typed Edit objects by errant
    def errant_annotate(self, orig, cor, lev=False, merging="rules"):
        alignment = self.align(orig, cor, lev)
        edits = self.merge(alignment, merging)
        for edit in edits:
            edit = self.classify_by_errant(edit)
        return edits

    # Input 1: An original text string parsed by spacy
    # Input 2: A corrected text string parsed by spacy
    # Input 3: A flag for standard Levenshtein alignment
    # Input 4: A flag for merging strategy
    # Output: A list of automatically extracted, typed Edit objects by sercl
    def syntax_annotate(self, orig, cor, lev=False, merging="rules"):
        alignment = self.align(orig, cor, lev)
        edits = self.merge(alignment, merging)
        for edit in edits:
            edit = self.classify_syntactically(edit)
        return edits

    # Input 1: An original text string parsed by spacy
    # Input 2: A corrected text string parsed by spacy
    # Input 3: A flag for standard Levenshtein alignment
    # Input 4: A flag for merging strategy
    # Input 5: A flag for annotating strategy
    # Output: A list of automatically extracted, typed Edit objects
    def annotate(self, orig, cor, lev=False, merging="rules", annotator='combined'):
        errant_edits = self.errant_annotate(orig, cor, lev, merging)
        sercl_edits = self.syntax_annotate(orig, cor, lev, merging)

        assert len(errant_edits) == len(sercl_edits)
        if self.combiner is None or annotator == 'errant':
            return errant_edits
        if annotator == 'sercl':
            return sercl_edits
        return [self.combiner.classification_combiner(errant_edit, sercl_edit) for errant_edit, sercl_edit in
                zip(errant_edits, sercl_edits)]

    # Input 1: An original text string parsed by spacy
    # Input 2: A corrected text string parsed by spacy
    # Input 3: A token span edit list; [o_start, o_end, c_start, c_end, (cat)]
    # Input 4: A flag for gold edit minimisation; e.g. [a b -> a c] = [b -> c]
    # Input 5: A flag to preserve the old error category (i.e. turn off classifier)
    # Input 5: A flag for annotating strategy (if old_cat==False)
    # Output: An Edit object
    def import_edit(self, orig, cor, edit, min=True, old_cat=False, annotator='combined'):
        # Undefined error type
        if len(edit) == 4:
            edit = Edit(orig, cor, edit)
        # Existing error type
        elif len(edit) == 5:
            edit = Edit(orig, cor, edit[:4], edit[4])
        # Unknown edit format
        else:
            raise Exception("Edit not of the form: "
                "[o_start, o_end, c_start, c_end, (cat)]")
        # Minimise edit
        if min: 
            edit = edit.minimise()
        # Classify edit
        if not old_cat:
            errant_edit = self.classify_by_errant(copy(edit))
            sercl_edit = self.classify_syntactically(copy(edit))
            if self.combiner is None or annotator == 'errant':
                edit = errant_edit
            elif annotator == 'sercl':
                edit = sercl_edit
            else:
                edit = self.combiner.classification_combiner(errant_edit, sercl_edit)
        return edit
