from importlib import import_module
import spacy
from errant.annotator import Annotator

# ERRANT version
__version__ = '3.0.0'

# Load an ERRANT Annotator object for a given language
def load(lang, nlp=None):
    # Make sure the language is supported
    supported = {"en"}
    if lang not in supported:
        raise Exception(f"{lang} is an unsupported or unknown language")

    # Load spacy (small model if no model supplied)
    nlp = nlp or spacy.load(f"{lang}_core_web_sm", disable=["ner"])

    # Load language edit merger
    merger = import_module(f"errant.{lang}.merger")

    # Load language edit classifier
    classifier = import_module(f"errant.{lang}.classifier")
    # The English classifier needs spacy
    if lang == "en": classifier.nlp = nlp

    # Return a configured ERRANT annotator
    return Annotator(lang, nlp, merger, classifier)