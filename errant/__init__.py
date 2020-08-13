from importlib import import_module
import spacy
from errant.annotator import Annotator

# ERRANT version
__version__ = '2.2.1'

# Load an ERRANT Annotator object for a given language
def load(lang, nlp=None):
    # Make sure the language is supported
    supported = {"en"}
    if lang not in supported:
        raise Exception("%s is an unsupported or unknown language" % lang)

    # Load spacy
    nlp = nlp or spacy.load(lang, disable=["ner"])

    # Load language edit merger
    merger = import_module("errant.%s.merger" % lang)

    # Load language edit classifier
    classifier = import_module("errant.%s.classifier" % lang)
    # Load sercl (syntactic classifier)
    syntax_classifier = import_module("errant.syntactic_classifier")
    # Load combiner
    combiner = import_module("errant.%s.sercl_errant_combine" % lang)
    # The English classifier needs spacy
    if lang == "en": classifier.nlp = nlp

    # Return a configured ERRANT annotator
    return Annotator(lang, nlp, merger, classifier, syntax_classifier, combiner)
