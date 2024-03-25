from .annotator import Annotator
from .compare import compare_from_raw, compare_from_edits
from .edit import Edit

# ERRANT version
__version__ = '3.0.0'

# Load an ERRANT Annotator object for a given language
def load(lang, nlp=None):
    return Annotator.load(lang, nlp)