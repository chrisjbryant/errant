import os
from typing import List, Optional

import spacy
from nltk.stem import LancasterStemmer
from spacy.language import Language
from spacy.tokens import Doc, Token

from errant import alignment, categorizer
from errant.edit import Edit, ErrorType
from errant.toolbox import load_dictionary, load_tag_map


class Errant:
    def __init__(self, spacy_model: Optional[Language] = None):
        # Spacy model
        self.nlp = spacy_model or spacy.load("en", disable=["ner"])
        # Lancaster Stemmer
        self.stemmer = LancasterStemmer()
        # GB English word list (inc -ise and -ize)
        self.gb_spell = load_dictionary()
        # Part of speech map file
        self.tag_map = load_tag_map()

    def parse(self, text: str, tokenize: bool = True) -> List[Token]:
        if tokenize:
            doc = self.nlp(text)
        elif text:
            doc = self.nlp.tokenizer.tokens_from_list(text.split(" "))
            self.nlp.tagger(doc)
            self.nlp.parser(doc)
        else:
            doc = []
        return [tok for tok in doc]

    def get_typed_edits(
        self,
        original_tokens: List[Token],
        corrected_tokens: List[Token],
        levenshtien_costs: bool = False,
        merge_type: str = alignment.RULES_MERGE,
    ) -> List[Edit]:
        edits = alignment.get_auto_aligned_edits(
            original_tokens, corrected_tokens, levenshtien_costs, merge_type
        )
        for edit in edits:
            edit.error_type = self.find_error_type(
                edit, original_tokens, corrected_tokens
            )
        return edits

    def find_error_type(
        self, edit: Edit, original_tokens: List[Token], corrected_tokens: List[Token]
    ) -> ErrorType:

        return categorizer.categorize(
            edit,
            original_tokens,
            corrected_tokens,
            self.gb_spell,
            self.tag_map,
            self.nlp,
            self.stemmer,
        )
