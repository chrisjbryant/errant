# SERRANT v1.0

# Overview

This repository combines ERRANT rules with SErCL rules. When ERRANT rules are less informative we go by SErCL notion of "a type is what changed into what".
The repository also allows for use of ERRANT or SErCL separately, do note that currntly SErCL only compares POS tags, so when POS tag doesn't change it does not compare the morphological change (e.g. book->books is of type Noun and not Noun:singular->plural), contributions are welcome.

This repository is under construction. 

The repository is based upon [ERRANT](https://github.com/chrisjbryant/errant) and [SErCl](https://github.com/borgr/GEC_UD_divergences)

# Installation

Just like source install in ERRANT:

```
git clone https://github.com/matanel-oren/serrant.git
cd serrant
python3 -m venv serrant_env
source serrant_env/bin/activate
pip3 install -e .
python3 -m spacy download en
```
This will clone the github SERRANT source into the current directory, build and activate a python environment inside it, and then install SERRANT and all its dependencies.

# Usage

We have followed ERRANT usage with small changes as detailed below.

## CLI

Three main commands are provided with SERRANT: `serrant_parallel`, `serrant_m2` and `serrant_compare`. You can run them from anywhere on the command line without having to invoke a specific python script.  

1. `serrant_parallel`  

     This is the main annotation command that takes an original text file and at least one parallel corrected text file as input, and outputs an annotated M2 file. By default, it is assumed that the original and corrected text files are word tokenised with one sentence per line.  
	 Example:
	 ```
	 serrant_parallel -orig <orig_file> -cor <cor_file1> [<cor_file2> ...] -out <out_m2> [-annotator {errant|
	 l|combined}]
	 ```
	 **SERRANT additional flag**: `-annotator {errant|sercl|combined}` that determines which approach to use: original ERRANT, pure SErCl, or the combination of both that seems to give us the most informative annotation.

2. `serrant_m2`  

     This is a variant of `serrant_parallel` that operates on an M2 file instead of parallel text files. This makes it easier to reprocess existing M2 files. You must also specify whether you want to use gold or auto edits; i.e. `-gold` will only classify the existing edits, while `-auto` will extract and classify automatic edits. In both settings, uncorrected edits and noops are preserved.  
     Example:
	 ```
	 serrant_m2 {-auto|-gold} m2_file -out <out_m2> [-annotator {errant|sercl|combined}]
	 ```
	 **SERRANT additional flag**: `-annotator {errant|sercl|combined}` that determines which approach to use: original ERRANT, pure SErCl, or the combination of both that seems to give us the most informative annotation.

3. `serrant_compare`  

     This is the evaluation command that compares a hypothesis M2 file against a reference M2 file. The default behaviour evaluates the hypothesis overall in terms of span-based correction. The `-cat {1,2,3}` flag can be used to evaluate error types at increasing levels of granularity, while the `-ds` or `-dt` flag can be used to evaluate in terms of span-based or token-based detection (i.e. ignoring the correction). All scores are presented in terms of Precision, Recall and F-score (default: F0.5), and counts for True Positives (TP), False Positives (FP) and False Negatives (FN) are also shown.  
	 Examples:
	 ```
     serrant_compare -hyp <hyp_m2> -ref <ref_m2>
     serrant_compare -hyp <hyp_m2> -ref <ref_m2> -cat {1,2,3}
     serrant_compare -hyp <hyp_m2> -ref <ref_m2> -ds
     serrant_compare -hyp <hyp_m2> -ref <ref_m2> -ds -cat {1,2,3}
	 ```

All these scripts also have additional advanced command line options which can be displayed using the `-h` flag.

## API

SERRANT API is the same as ERRANT except for those which are **NOTED** below.

### Quick Start

```
import serrant

annotator = serrant.load('en')
orig = annotator.parse('This are gramamtical sentence .')
cor = annotator.parse('This is a grammatical sentence .')
edits = annotator.annotate(orig, cor)
for e in edits:
    print(e.o_start, e.o_end, e.o_str, e.c_start, e.c_end, e.c_str, e.type)
```

### Loading

`serrant`.**load**(lang, nlp=None)  
Create an SERRANT Annotator object. The `lang` parameter currently only accepts `'en'` for English, but we hope to extend it for other languages in the future. The optional `nlp` parameter can be used if you have already preloaded spacy and do not want SERRANT to load it again.

```
import serrant
import spacy

nlp = spacy.load('en')
annotator = serrant.load('en', nlp)
```

### Annotator Objects

An Annotator object is the main interface for SERRANT.

#### Methods

`annotator`.**parse**(string, tokenise=False)  
Lemmatise, POS tag, and parse a text string with spacy. Set `tokenise` to True to also word tokenise with spacy. Returns a spacy Doc object.

`annotator`.**align**(orig, cor, lev=False)  
Align spacy-parsed original and corrected text. The default uses a linguistically-enhanced Damerau-Levenshtein alignment, but the `lev` flag can be used for a standard Levenshtein alignment. Returns an Alignment object.

`annotator`.**merge**(alignment, merging='rules')  
Extract edits from the optimum alignment in an Alignment object. Four different merging strategies are available:
1. rules: Use a rule-based merging strategy (default)
2. all-split: Merge nothing: MSSDI -> M, S, S, D, I
3. all-merge: Merge adjacent non-matches: MSSDI -> M, SSDI
4. all-equal: Merge adjacent same-type non-matches: MSSDI -> M, SS, D, I

Returns a list of Edit objects.

**ADDED**: `annotator`.**classify_by_errant**(edit)
Classify an edit according to ERRANT rules. Sets the `edit.type` attribute in an Edit object and returns the same Edit object.

**ADDED**: `annotator`.**classify_syntactically**(edit)
Classify an edit according to SErCl rules. Sets the `edit.type` attribute in an Edit object and returns the same Edit object.

**ADDED**: `annotator`.**errant_annotate**(orig, cor, lev=False, merging='rules')  
Run the full annotation pipeline to align two sequences and extract and classify the edits by ERRANT. Equivalent to running `annotator.align`, `annotator.merge` and `annotator.classify` in sequence. Returns a list of Edit objects.

**ADDED**: `annotator`.**sercl_annotate**(orig, cor, lev=False, merging='rules')  
Run the full annotation pipeline to align two sequences and extract and classify_syntactically the edits by SErCl. Equivalent to running `annotator.align`, `annotator.merge` and `annotator.classify` in sequence. Returns a list of Edit objects.

**CHANGED**: `annotator`.**annotate**(orig, cor, lev=False, merging='rules', annotator='combined')  
Run the full annotation pipeline to align two sequences and extract and classify the edits by the specified classifier (the options are: "errant", "sercl", and "combined").

```
import serrant

annotator = serrant.load('en')
orig = annotator.parse('This are gramamtical sentence .')
cor = annotator.parse('This is a grammatical sentence .')
alignment = annotator.align(orig, cor)
edits = annotator.merge(alignment)
for e in edits:
    e = annotator.classify_syntactically(e)
```

**CHANGED**: `annotator`.**import_edit**(orig, cor, edit, min=True, old_cat=False, annotator='combined')  
Load an Edit object from a list. `orig` and `cor` must be spacy-parsed Doc objects and the edit must be of the form: `[o_start, o_end, c_start, c_end(, type)]`. The values must be integers that correspond to the token start and end offsets in the original and corrected Doc objects. The `type` value is an optional string that denotes the error type of the edit (if known). Set `min` to True to minimise the edit (e.g. [a b -> a c] = [b -> c]) and `old_cat` to True to preserve the old error type category (i.e. turn off the classifier). use `annotator` parameter to choose the classifier from "errant", "sercl", and "combined".

```
import serrant

annotator = serrant.load('en')
orig = annotator.parse('This are gramamtical sentence .')
cor = annotator.parse('This is a grammatical sentence .')
edit = [1, 2, 1, 2, 'SVA'] # are -> is
edit = annotator.import_edit(orig, cor, edit)
print(edit.to_m2())
```

### Alignment Objects

An Alignment object is created from two spacy-parsed text sequences.

#### Attributes

`alignment`.**orig**  
`alignment`.**cor**  
The spacy-parsed original and corrected text sequences.

`alignment`.**cost_matrix**   
`alignment`.**op_matrix**  
The cost matrix and operation matrix produced by the alignment.

`alignment`.**align_seq**  
The first cheapest alignment between the two sequences.

### Edit Objects

An Edit object represents a transformation between two text sequences.

#### Attributes

`edit`.**o_start**  
`edit`.**o_end**  
`edit`.**o_toks**  
`edit`.**o_str**  
The start and end offsets, the spacy tokens, and the string for the edit in the *original* text.

`edit`.**c_start**  
`edit`.**c_end**  
`edit`.**c_toks**  
`edit`.**c_str**  
The start and end offsets, the spacy tokens, and the string for the edit in the *corrected* text.

`edit`.**type**  
The error type string.

**ADDED**: `edit`.**cond**  
Which case of ERRANT conditions was typed this error.

#### Methods

`edit`.**to_m2**(id=0)  
Format the edit for an output M2 file. `id` is the annotator id.

## Cite
This work is a composition of two previous work. While a technical report would be soon published and should be cited upon use, we kindly ask that the original work would be cited as well.

This work:
```Soon to appear```

SerCl:
```@inproceedings{choshen-etal-2020-classifying,
    title = "Classifying Syntactic Errors in Learner Language",
    author = "Choshen, Leshem  and
      Nikolaev, Dmitry  and
      Berzak, Yevgeni  and
      Abend, Omri",
    booktitle = "Proceedings of the 24th Conference on Computational Natural Language Learning",
    month = nov,
    year = "2020",
    address = "Online",
    publisher = "Association for Computational Linguistics",
    url = "https://www.aclweb.org/anthology/2020.conll-1.7",
    pages = "97--107",
    }```

Errant:
```@inproceedings{bryant-etal-2017-automatic,
    title = "Automatic Annotation and Evaluation of Error Types for Grammatical Error Correction",
    author = "Bryant, Christopher  and
      Felice, Mariano  and
      Briscoe, Ted",
    booktitle = "Proceedings of the 55th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
    month = jul,
    year = "2017",
    address = "Vancouver, Canada",
    publisher = "Association for Computational Linguistics",
    url = "https://www.aclweb.org/anthology/P17-1074",
    doi = "10.18653/v1/P17-1074",
    pages = "793--805",
}```
