# Changelog

This log describes all the changes made to ERRANT since its release.

## v3.0.0 (04-11-23)

1. Finally updated ERRANT to support Spacy 3! 
    * I specifically tested Spacy 3.2 - 3.7 and found a negligible difference in performance on the BEA19 dev set. 
    * This update also comes with an unexpected 10-20% speed gain.

2. Added a `.gitignore` file. [#39](https://github.com/chrisjbryant/errant/issues/39)

3. Renamed `master` branch to `main`.

## v2.3.3 (14-04-22)

1. Missed one case of changing Levenshtein to rapidfuzz... Now fixed.

## v2.3.2 (14-04-22)

1. Add more details to verbose ERRANT scoring. [#29](https://github.com/chrisjbryant/errant/pull/29)
2. Simplified the new rapidfuzz functions. [#35](https://github.com/chrisjbryant/errant/pull/35)

## v2.3.1 (13-04-22)

1. Replaced the dependency on [python-Levenshtein](https://pypi.org/project/python-Levenshtein/) with [rapidfuzz](https://pypi.org/project/rapidfuzz/) to overcome a licensing conflict. ERRANT and its dependencies now all use the MIT license. [#34](https://github.com/chrisjbryant/errant/issues/34)

## v2.3.0 (15-07-21)

1. Added some new rules to reduce the number of OTHER-type 1:1 edits and classify them as something else. Specifically, there are now ~40% fewer 1:1 OTHER edits and ~15% fewer n:n OTHER edits overall (tested on the FCE and W&I training sets combined). The changes are as follows:

    * A possessive suffix at the start of a merge sequence is now always split:
    
    | Example | people life -> people 's lives                             |
    |---------|------------------------------------------------------------|
    | Old     |  _life_ -> _'s lives_ (R:OTHER)                            |
    | New     |  _ε_ -> _'s_ (M:NOUN:POSS), _life_ -> _lives_ (R:NOUN:NUM) |
    
    * NUM <-> DET edits are now classified as R:DET; e.g. _one (cat)_ -> _a (cat)_. Thanks to [@katkorre](https://github.com/katkorre/ERRANT-reclassification)!
    
    * Changed the string similarity score in the classifier from the Levenshtein ratio to the normalised Levenshtein distance based on the length of the longest input string. This is because we felt some ratio scores were unintuitive; e.g. _smt_ -> _something_ has a ratio score of 0.5 despite the insertion of 6 characters (the new normalised score is 0.33).  
    
    * The non-word spelling error rules were updated slightly to take the new normalised Levenshtein score into account. Additionally, dissimilar strings are now classified based on the POS tag of the correction rather than as OTHER; e.g. _amougnht_ -> _number_ (R:NOUN).

    * The new normalised Levenshtein score is also used to classify many of the remaining 1:1 replacement edits that were previously classified as OTHER. Many of these are real-word spelling errors (e.g. _their_ <-> _there_), but there are also some morphological errors (e.g. _health_ -> _healthy_) and POS-based errors (e.g. _transport_ -> _travel_). Note that these rules are a little complex and depend on both the similarity score and the length of the original and corrected strings. For example, _form_ -> _from_ (R:SPELL) and _eventually_ -> _finally_ (R:ADV) both have the same similarity score of 0.5 yet are differentiated as different error types based on their string lengths. 

2. Various minor updates:  
    * `out_m2` in `parallel_to_m2.py` and `m2_to_m2.py` is now opened and closed properly. [#20](https://github.com/chrisjbryant/errant/pull/20)
    * Fixed a bracketing error that deleted a valid edit in rare circumstances. [#26](https://github.com/chrisjbryant/errant/issues/26) [#28](https://github.com/chrisjbryant/errant/issues/28)
    * Updated the English wordlist.
    * Minor changes to the readme.
    * Tidied up some code comments.

## v2.2.3 (12-02-21)

1. Changed the dependency version requirements in `setup.py` since ERRANT v2.2.x is not compatible with spaCy 3. 

## v2.2.2 (14-08-20)

1. Added a copy of the NLTK Lancaster stemmer to `errant.en.lancaster` and removed the NLTK dependency. It was overkill to require the entire NLTK package just for this stemmer so we now bundle it with ERRANT. 

2. Replaced the deprecated `tokens_from_list` function from spaCy v1 with the `Doc` function from spaCy v2 in `Annotator.parse`.

## v2.2.1 (17-05-20)

Fixed key error in the classifier for rare spaCy 2 POS tags: _SP, BES, HVS.

## v2.2.0 (06-05-20)

1. ERRANT now works with spaCy v2.2. It is 4x slower, but this change was necessary to make it work on Python 3.7.  

2. SpaCy 2 uses slightly different POS tags to spaCy 1 (e.g. auxiliary verbs are now tagged AUX rather than VERB) so I updated some of the merging rules to maintain performance.

## v2.1.0 (09-01-20)

1. The character level cost in the sentence alignment function is now computed by the much faster [python-Levenshtein](https://pypi.org/project/python-Levenshtein/) library instead of python's native `difflib.SequenceMatcher`. This makes ERRANT 3x faster!

2. Various minor updates:  
    * Updated the English wordlist.
    * Fixed a broken rule for classifying contraction errors.
    * Changed a condition in the calculation of transposition errors to be more intuitive.
    * Partially updated the ERRANT POS tag map to match the updated [Universal POS tag map](https://universaldependencies.org/tagset-conversion/en-penn-uposf.html). Specifically, EX now maps to PRON rather than ADV, LS maps to X rather than PUNCT, and CONJ has been renamed CCONJ. I did not change the mapping of RP from PART to ADP yet because this breaks several rules involving phrasal verbs.
    * Added an `errant.__version__` attribute.
    * Added a warning about using ERRANT with spaCy 2.
    * Tidied some code in the classifier.

## v2.0.0 (10-12-19)

1. ERRANT has been significantly refactored to accommodate a new API (see README). It should now also be much easier to extend to other languages.

2. Added a `setup.py` script to make ERRANT `pip` installable.

3. The Damerau-Levenshtein alignment code has been rewritten in a much cleaner Python implementation. This also makes ERRANT ~20% faster. 

Note: All these changes do **not** affect system output compared with the previous version. For the first `pip` release, we wanted to make sure v2.0.0 was fully compatible with the [BEA-2019 shared task](https://www.cl.cam.ac.uk/research/nl/bea2019st/) on Grammatical Error Correction.

Thanks to [@sai-prasanna](https://github.com/sai-prasanna) for inspiring some of these changes!

## v1.4 (16-11-18)

1. The `compare_m2.py` evaluation script was refactored to make it easier to use.

2. We tweaked the alignment code and merging rules to not only make ERRANT ~700% faster, but also slightly more accurate.

Specifically, we simplified the lemma cost to not repeatedly call the lemmatiser for different parts-of-speech, and also replaced the character cost with python's native `difflib.SequenceMatcher` instead of a character based Damerau-Levenshtein alignment. 

This significantly increased the speed, but also slightly decreased performance (~0.5 F1 worse), so we additionally revisited the merging rules. The new implementation now processes the largest combinations of adjacent non-matches first, instead of processing one alignment at a time, and now also features some new or slightly modified rules (see `scripts/align_text.py` for more information). 

The differences between the old and new version are summarised in the following table.

| Dataset      | Sents |    Setting |              P |              R |                 F1 |  Time<br>(secs) |
|--------------|------:|-----------:|---------------:|---------------:|-------------------:|----------------:|
| FCE Dev      |  2371 | Old<br>New | 82.77<br>84.00 | 85.22<br>85.52 | 83.98<br>**84.75** |   260<br>**40** |
| FCE Test     |  2805 | Old<br>New | 83.88<br>85.17 | 85.84<br>85.93 | 84.85<br>**85.55** |   300<br>**45** |
| FCE Train    | 30200 | Old<br>New | 82.69<br>84.06 | 85.12<br>85.38 | 83.89<br>**84.72** | 2965<br>**340** |
| CoNLL-2013   |  1381 | Old<br>New | 82.64<br>83.27 | 82.45<br>82.24 | 82.54<br>**82.75** |   315<br>**45** |
| CoNLL-2014.0 |  1312 | Old<br>New | 78.48<br>79.02 | 80.38<br>80.18 | 79.42<br>**79.59** |   350<br>**45** |
| CoNLL-2014.1 |  1312 | Old<br>New | 82.50<br>84.04 | 82.73<br>82.85 | 82.61<br>**83.44** |   385<br>**50** |
| NUCLE        | 57151 | Old<br>New | 70.14<br>73.20 | 80.27<br>81.16 | 71.95<br>**76.97** | 7565<br>**725** |

## v1.3 (23-08-18)

Fix arbitrary reordering of edits with the same start and end span; e.g.  
S I am happy .  
A 2 2|||M:ADV|||really|||REQUIRED|||-NONE-|||0  
A 2 2|||M:ADV|||very|||REQUIRED|||-NONE-|||0  

VS.  

S I am happy .  
A 2 2|||M:ADV|||very|||REQUIRED|||-NONE-|||0  
A 2 2|||M:ADV|||really|||REQUIRED|||-NONE-|||0  

## v1.2 (10-08-18)

Added support for multiple annotators in `parallel_to_m2.py`.  
Before: `python3 parallel_to_m2.py -orig <orig_file> -cor <cor_file> -out <out_file>`  
After: `python3 parallel_to_m2.py -orig <orig_file> -cor <cor_file1> [<cor_file2> ...] -out <out_file>`  
This is helpful if you have multiple annotations for the same orig file.  

## News (17-12-17)

In November, spaCy changed significantly when it became version 2.0.0. Although we have not tested ERRANT with this new version, the main change seemed to be a slight increase in performance (pos tagging and parsing etc.) at a significant cost to speed. Consequently, we still recommend spaCy 1.9.0 for use with ERRANT.

## v1.1 (22-11-17)

ERRANT would sometimes run into memory problems if sentences were long and very different. We hence changed the default alignment from breadth-first to depth-first. This bypassed the memory problems, made ERRANT faster and barely affected results.

## v1.0 (10-05-17)

ERRANT v1.0 released.
