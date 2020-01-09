from importlib import import_module
import logging
import spacy
from errant.annotator import Annotator

# ERRANT version
__version__ = '2.1.0'

# Load an ERRANT Annotator object for a given language
def load(lang, nlp=None):
    # Make sure the language is supported
    supported = {"en"}
    if lang not in supported:
        raise Exception("%s is an unsupported or unknown language" % lang)

    # Load spacy
    nlp = nlp or spacy.load(lang, disable=["ner"])
    # Warning for spacy 2
    if spacy.__version__[0] == "2":
        logging.warning("ERRANT is 4x slower and 2% less accurate with spaCy 2. "
            "We strongly recommend spaCy 1.9.0!")

    # Load language edit merger
    merger = import_module("errant.%s.merger" % lang)

    # Load language edit classifier
    classifier = import_module("errant.%s.classifier" % lang)
    # The English classifier needs spacy
    if lang == "en": classifier.nlp = nlp

    # Return a configured ERRANT annotator
    return Annotator(lang, nlp, merger, classifier)