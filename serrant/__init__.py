from importlib import import_module
import spacy
from serrant.annotator import Annotator

# SERRANT version
__version__ = '1.0'
# compatible to ERRANT version 2.2.2

# Load an ERRANT Annotator object for a given language
def load(lang, nlp=None):
    # Make sure the language is supported
    supported = {"en"}
    if lang not in supported:
        raise Exception("%s is an unsupported or unknown language" % lang)

    # Load spacy
    model_per_lang={"en":"en_core_web_sm"}
    nlp = nlp or spacy.load(model_per_lang[lang], disable=["ner"])

    # Load language edit merger
    merger = import_module("serrant.%s.merger" % lang)

    # Load language edit classifier
    classifier = import_module("serrant.%s.classifier" % lang)
    # Load sercl (syntactic classifier)
    syntax_classifier = import_module("serrant.syntactic_classifier")
    # Load combiner
    combiner = import_module("serrant.%s.sercl_errant_combine" % lang)
    # The English classifier needs spacy
    if lang == "en": classifier.nlp = nlp

    # Return a configured ERRANT annotator
    return Annotator(lang, nlp, merger, classifier, syntax_classifier, combiner)
