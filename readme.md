# ERRANT

This repository contains the grammatical ERRor ANnotation Toolkit (ERRANT) described in:

> Christopher Bryant, Mariano Felice, and Ted Briscoe. 2017. [**Automatic annotation and evaluation of Error Types for Grammatical Error Correction**](http://aclweb.org/anthology/P/P17/P17-1074.pdf). In Proceedings of the 55th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers). Vancouver, Canada.

> Mariano Felice, Christopher Bryant, and Ted Briscoe. 2016. [**Automatic extraction of learner errors in esl sentences using linguistically enhanced alignments**](http://aclweb.org/anthology/C/C16/C16-1079.pdf). In Proceedings of COLING 2016, the 26th International Conference on Computational Linguistics: Technical Papers. Osaka, Japan.

If you make use of this code, please cite the above papers.

# Overview

The main aim of ERRANT is to automatically annotate parallel English sentences with error type information. Specifically, given an original and corrected sentence pair, ERRANT will extract the edits that transform the former to the latter and then classify them according to a rule-based error type framework. This can be used to standardise parallel datasets or facilitate detailed error type evaluation. The annotated output file is in M2 format and an evaluation script is provided.

### Example:  
**Original**: This are gramamtical sentence .  
**Corrected**: This is a grammatical sentence .  
**Output M2**:  
S This are gramamtical sentence .  
A 1 2|||R:VERB:SVA|||is|||REQUIRED|||-NONE-|||0  
A 2 2|||M:DET|||a|||REQUIRED|||-NONE-|||0  
A 2 3|||R:SPELL|||grammatical|||REQUIRED|||-NONE-|||0  
A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||1

In M2 format, a line preceded by S denotes an original sentence while a line preceded by A indicates an edit annotation. Each edit line consists of the start and end token offset of the edit, the error type, and the tokenized correction string. The next two fields are included for historical reasons (see the CoNLL-2014 shared task) while the last field is the annotator id.  

A "noop" edit is a special kind of edit that explicitly indicates an annotator/system made no changes to the original sentence. If there is only one annotator, noop edits are optional, otherwise a noop edit should be included whenever at least 1 out of n annotators considered the original sentence to be correct. This is something to be aware of when combining individual m2 files, as missing noops can affect results. 

# Pre-requisites

We only support Python 3. It is safest to install everything in a clean [virtualenv](https://docs.python-guide.org/dev/virtualenvs/#lower-level-virtualenv).

## spaCy

spaCy is a natural language processing (NLP) toolkit available here: https://spacy.io/.

It can be installed for Python 3 as follows:  
```
pip3 install -U spacy==1.9.0
python3 -m spacy download en  
```
This installs both spaCy itself and the default English language model. We do not recommend spaCy 2.0 at this time because it is slower and less compatible with ERRANT. More information on how to install spaCy can be found on its website. We used spaCy 1.7.3 in our original paper. 

## NLTK

NLTK is another well-known NLP library: http://www.nltk.org/. We use it only for the Lancaster Stemmer.  

It can be installed for Python 3 as follows:
```
pip3 install -U nltk  
```

# Usage

Three main scripts are provided with ERRANT: `parallel_to_m2.py`, `m2_to_m2.py` and `compare_m2.py`.  

1. `parallel_to_m2.py`  

     Extract and classify edits from parallel sentences automatically. This is the simplest annotation script, which requires an original text file, at least one corrected text file, and an output filename. The original and corrected text files must have one sentence per line and be word tokenized.  
	 Example:
	 ```
	 python3 parallel_to_m2.py -orig <orig_file> -cor <cor_file1> [<cor_file2> ...] -out <out_m2>
	 ```

2. `m2_to_m2.py`  

     This is a more sophisticated version of `parallel_to_m2.py` that operates on an m2 file instead of parallel text files. This makes it easier to process multiple sets of corrections simultaneously. In addition to an input m2 file, you must also specify whether you want to use gold or auto edits: `-gold` will only classify the existing edits, while `-auto` will extract and classify edits automatically. In both settings, uncorrected edits and noops are preserved in the original input file.  
     Example:
	 ```
	 python3 m2_to_m2.py {-auto|-gold} m2_file -out <out_m2>
	 ```

3. `compare_m2.py`  

     This is the script to evaluate a hypothesis m2 file against a reference m2 file. The default behaviour evaluates the hypothesis overall in terms of correction. The `-cat {1,2,3}` flag is used to evaluate error types at increasing levels of granularity while the `-ds` or `-dt` flag is used to evaluate in terms of span-based or token-based detection (i.e. ignoring the correction). All scores are presented in terms of Precision, Recall and F-score (default: F0.5), and counts for True Positives (TP), False Positives (FP) and False Negatives (FN) are also shown.  
	 Examples:
	 ```
     python3 compare_m2.py -hyp <hyp_m2> -ref <ref_m2> 
     python3 compare_m2.py -hyp <hyp_m2> -ref <ref_m2> -cat {1,2,3}
     python3 compare_m2.py -hyp <hyp_m2> -ref <ref_m2> -ds
     python3 compare_m2.py -hyp <hyp_m2> -ref <ref_m2> -ds -cat {1,2,3}
	 ```	

All these scripts also have additional advanced command line options which can be displayed using the `-h` flag.  

#### Runtime

In terms of speed, ERRANT processes ~70 sents/sec in the fully automatic edit extraction and classification setting, but ~350 sents/sec in the classification setting alone. These figures were calculated on an Intel Xeon E5-2630 v4 @ 2.20GHz machine, but results will vary depending on how different the original and corrected sentences are.  

# Edit Extraction

For more information about the edit extraction phase of annotation, we refer the reader to the following paper:

> Mariano Felice, Christopher Bryant, and Ted Briscoe. 2016. [**Automatic extraction of learner errors in esl sentences using linguistically enhanced alignments**](http://aclweb.org/anthology/C/C16/C16-1079.pdf). In Proceedings of COLING 2016, the 26th International Conference on Computational Linguistics: Technical Papers. Osaka, Japan.

Note that ERRANT has been updated since the release of this paper and that the alignment cost and merging rules have also changed slightly. See `scripts/align_text.py` for more information.  

# Error Type Classification

A brief description of some of the rules used to classify error types is described in Section 3.1 of the ERRANT paper. In this section, we describe all the rules in more detail. Although we present the rules for each error type individually, the reader should be aware that some rules interract and there are several constraints on rule order. Rule order is discussed at the end of this section.

## Operation Tier

All edits are minimally classified in terms of edit operation, i.e. Missing, Replacement or Unnecessary, depending on whether tokens are inserted, substituted or deleted respectively.

| Type        | Form
|-------------|--------
| Missing     | Ø -> B
| Replacement | A -> B
| Unnecessary | A -> Ø

A special case concerns edits such as [Man -> The man] or [The man -> Man]. While these look like substitution edits, the main intention of the edit is actually to insert or delete a word. We hence treat them as such and ignore the case change. They are detected by the following rule:  

* The number of tokens on each side of the edit is not equal, the lower cased form of the last token is the same, and removing the last token on both sides results in an empty string on one side.

Finally, any gold edit that changes A -> A or Ø -> Ø is labelled Unknown (UNK), since it ultimately has no effect on the text. These are normally gold edits that humans detected, but were unable or unsure how to correct. UNK edits are analogous to *Um* (Unclear Meaning) edits in the NUCLE framework.

## Token Tier

### Part-Of-Speech

POS-based error types are assigned based primarily on the POS tags of the edited tokens according to the [Stanford Universal Dependency](http://universaldependencies.org/tagset-conversion/en-penn-uposf.html) framework. These tags are sometimes too detailed for error annotation however, so we do not use: interjections (INTJ), numerals (NUM), symbols (SYM) or other (X). We also renamed adpositions (ADP) to prepositions (PREP) and treat proper nouns (PROPN) as regular nouns (NOUN). 

In the majority of cases, an edit may be assigned a POS error category if it meets the following condition:

* All tokens on both sides of the edit have the same POS tag and do not meet the criteria for a more specific type.

This is not always sufficient however, and so we also make use of other information to determine certain POS-based edits. For example, there are several dependency parse labels that map to specific parts-of-speech. 

| Dep Label | POS   |
|-----------|-------|
| acomp     | ADJ   |
| amod      | ADJ   |
| advmod    | ADV   |
| det       | DET   |
| prep      | PREP  |
| prt       | PART  |
| punct     | PUNCT |

* The tokens on both sides of the edit may have different POS tags but they all have the same dep label which appears in the above table.  

Finally, there are also several special cases of POS error types:  

#### VERB
* All tokens on both sides of the edit are either PART or VERB and the last token on each side has a different lemma; e.g. [*to eat* -> Ø], [*consuming* -> *to eat*], [*look at* -> *see*]  

#### PART
* There is exactly one token on both sides of the edit and the combined set of POS tags is PREP and PART or the combined set of dep labels is *prep* and *prt*; e.g. [(look) *at* -> (look) *for*].

#### DET/PRON
* There is exactly one token on both sides of the edit and the combined set of POS tags is DET and PRON. If the corrected token dep label is *poss*, this is a possessive determiner which means the edit is DET. If the corrected dep label is *nsubj*, *nsubjpass*, *dobj* or *pobj* however, the edit is PRON because determiners cannot be subjects or objects.  

#### PUNCT
* The lower cased form of the last token on both sides of the edit is the same and all remaining tokens are punctuation; e.g. [*. Because* -> *, because*]

### Contractions: CONTR

* At least one side of the edit is a contraction (*'d*, *'ll*, *'m*, *n't*, *'re*, *'s*, or *'ve*), there is not more than one token on both sides of the edit and all tokens have the same POS. 

During auto alignment, contractions may get separated from the word they depend on; e.g. [*did n't* -> *did not*] becomes [*n't* -> *not*]. *ca n't*, *wo n't* and *sha n't* are special cases where *can*, *will* and *shall* are shortened to *ca*, *wo* and *sha*. To prevent them being flagged as spelling errors, they are handled by a separate rule:

* There is exactly one token on both sides of the edit and they are *ca* and *can*, *wo* and *will*, or *sha* and *shall*.  

### Morphology: MORPH

* There is exactly one token on both sides of the edit and the tokens have the same lemma or stem, but nothing else in common.  

The morphology category captures derivational morphology errors, e.g. [*quick* (ADJ) -> *quickly* (ADV)], and cases where the POS tagger makes a mistake; e.g. [*catch* (NOUN) -> *catching* (VERB)]

### Other: OTHER

Edits that are not captured by any rules are classified as OTHER. They are typically edits such as [*at* (PREP) -> *the* (DET)], which have perhaps been improperly aligned, or else multi-token edits such as [*at his best* -> *well*] which are much more semantic in nature. 

### Orthography: ORTH

* The lower cased form of both sides of the edit with all whitespace removed results in the same string; e.g. [*firstly* -> *Firstly*], [*bestfriend* -> *best friend*].

Although the definition of orthography can be quite broad, we use it here to refer only to edits that involve case and/or whitespace changes.

### Spelling: SPELL

We use the latest [British English Hunspell dictionary word list](https://sourceforge.net/projects/wordlist/files/speller/2017.01.22/) to identify spelling errors. Alternative English dictionaries can also be used. It is assumed humans did not misspell their corrections. 

Spelling edits must meet the following conditions:

1. There is exactly one token on both sides of the edit.
2. The original token is entirely alphabetical (no numbers or punctuation).
3. The original token is not in the dictionary.
4. The lower cased original token is not in the dictionary.
5. The original and corrected tokens do not have the same lemma.
6. The original and corrected tokens share at least 50% of the same characters in the same relative order. 

We check the dictionary twice because casing produces false positives. For example *Cat* is not in the dictionary but *cat* is; we do not want to call *Cat* a spelling error however if the correction is [*Cat* -> *Cats*]. It's also worth noting some words require upper case to be valid; e.g. *iPhone*.

The character comparison condition is an approximation. In general, spelling errors involve tokens that have very similar original and corrected forms. This is not always the case however, and there are also edits such as [*greatful* -> *pleased*]. While *greatful* is a misspelling of *grateful*, the correction ultimately replaces it entirely with a synonym. It hence seems more appropriate to call this a replacement adjective error rather than a spelling error:

* The original token meets criteria 1-5, but not 6. If both sides of the edit have the same POS tag, use that as the error type, otherwise OTHER.

### Word Order: WO

* Alphabetically sorted lists of lower cased tokens on both sides of the edit are identical; e.g. [*house white* -> *white house*]

Sorted lists are used instead of sets as sets do not allow duplicates. We also investigated relaxing the exact-match constraint to allow majority-matches, e.g. [*I saw the man* -> *The man saw me*], but ultimately preferred exact matches.

## Morphology Tier

### Adjective Form: ADJ:FORM

* There is exactly one token on both sides of the edit and both tokens have the same lemma. The tokens themselves are either both ADJ or parsed as *acomp* or *amod*; e.g. [*big* -> *biggest*].

A second rule captures multi-token adjective form errors: 

* There are no more than two tokens on both sides of the edit, the first token on either side is *more* or *most* and the last token on both sides has the same lemma; e.g. [*more big* -> *bigger*].

### Noun Inflection: NOUN:INFL

Noun inflection errors are usually count-mass noun errors, e.g. [*advices* -> *advice*], but also include cases such as [*countrys* -> *countries*] and [*childs* -> *children*]. They are a special kind of non-word error that must meet the following criteria:

1. There is exactly one token on both sides of the edit.
2. The original token is entirely alphabetical (no numbers or punctuation).
3. The original token is not in the dictionary.
4. The lower cased original token is not in the dictionary.
5. The original and corrected tokens have the same lemma.
6. The original and corrected tokens are both NOUN.

### Noun Number: NOUN:NUM

* There is exactly one token on both sides of the edit, both tokens have the same lemma and both tokens are NOUN; e.g. [*cat* -> *cats*].

A fairly common POS tagger error concerns nouns that look like adjectives; e.g. [*musical* -> *musicals*]. These are handled by a separate rule that also makes use of fine PTB-style POS tags. 

* There is exactly one token on both sides of the edit, both tokens have the same lemma, the original token is ADJ and the corrected token is a plural noun (NNS).

This second rule was only found to be effective in the singular to plural direction and not the other way around.

### Noun Possessive: NOUN:POSS

* There is not more than one token on both sides of the edit and at least one side is given the fine PTB tag POS. In this instance, POS indicates possessive rather than part-of-speech. 

Since possessive suffixes are separated from their dependent nouns, edits such as [*teacher* -> *teacher 's*] are minimised to [Ø -> *'s*]. Multi-token possessive edits are handled by a separate rule.

* Either the original tokens or the corrected tokens consist of the POS sequence NOUN PART and the first token on both sides has the same lemma; e.g. [*friends* -> *friend 's*].

### Verb Form: VERB:FORM

Verb form errors typically involve bare infinitive, *to*-infinitive, gerund and participle forms. To give an example, any edit between members of the following set would likely be considered a verb form error: {*eat*, *to eat*, *eating*, *eaten*}. To make things more complicated, *eat* is also a non-3rd-person present tense form (e.g. *I eat food*), which is usually not a verb form error. In light of this ambiguity, we use fine PTB-style POS tags, rather than coarse Universal Dependency tags, to classify verb form errors. A verb form error must meet one of the following criteria.

&ensp;&ensp;A. The edit is a missing or unnecessary *to*, it is tagged PART and is not parsed *prep*.  
&ensp;&ensp;B. There is exactly one token on both sides of the edit, they both have the same lemma, are both VERB and are both preceded by a dependent auxiliary verb.  
&ensp;&ensp;C. There is exactly one token on both sides of the edit, they both have the same lemma, are both VERB and at least one is a gerund (VBG) or past participle (VBN).  
&ensp;&ensp;D. There is exactly one token on both sides of the edit, they both have the same lemma, do not have the same POS tag, but the corrected token is a gerund (VBG) or past participle (VBN).  
&ensp;&ensp;E. All the tokens on both sides of the edit are PART or VERB and the last tokens have the same lemma.

#### Explanation

&ensp;&ensp;A. We treat infinitival *to* as part of a verb form; e.g. [Ø -> *to*].  
&ensp;&ensp;B. In a verb phrase, tense and agreement fall on the first auxiliary, if any. Consequently, if both edited verbs are preceded by auxiliaries, they can only be form errors; e.g. [(has) *eating* -> (has) *eaten*], [(have) *be* (sleeping) -> (have) *been* (sleeping)].  
&ensp;&ensp;C. In general, we found that edits with a VBG or VBN on one side were form errors.  
&ensp;&ensp;D. If the POS tags are different, we rely only on the corrected POS tag.  
&ensp;&ensp;E. Multi-token form errors typically involve infinitival *to*; e.g. [*to eat* -> *eating*].  

### Verb Inflection: VERB:INFL

Verb inflection errors are classified in a similar manner to noun inflection errors. Examples include [*getted* -> *got*], [*danceing* -> *dancing*] and [*fliped* -> *flipped*].

1. There is exactly one token on both sides of the edit.  
2. The original token is entirely alphabetical (no numbers or punctuation).  
3. The original token is not in the dictionary.  
4. The lower cased original token is not in the dictionary.  
5. The original and corrected tokens have the same lemma.  
6. The original and corrected tokens are both VERB.  

### Subject-Verb Agreement: VERB:SVA

SVA errors must meet one of the following criteria:  

&ensp;&ensp;A. There is exactly one token on both sides of the edit and they are *was* and *were*.  
&ensp;&ensp;B. There is exactly one token on both sides of the edit, they both have the same lemma, are both VERB and at least one side is a 3rd-person verb form (VBZ).  
&ensp;&ensp;C. There is exactly one token on both sides of the edit, they both have the same lemma, do not have the same POS tag, but the corrected token is a 3rd-person verb form (VBZ).  

#### Explanation

&ensp;&ensp;A. *was* and *were* are the only past tense forms that have agreement morphology.  
&ensp;&ensp;B. In general, we found that edits with VBZ on one side were form errors.  
&ensp;&ensp;C. If the POS tags are different, we rely only on the corrected POS tag.  

### Tense: VERB:TENSE

Tense errors are complicated. The simplest tense errors are inflectional, e.g. [*eat* -> *ate*], but tense can also be expressed periphrastically by means of auxiliary verbs; e.g. [*eat* -> *has eaten*]. This does not mean we can label all auxiliary verbs tense errors however, as auxiliary verbs can also be form or agreement errors; e.g. [(is) *be* (eaten) -> (is) *being* (eaten)] and [(it) *are* (eaten) -> (it) *is* (eaten)]. Consequently, errors involving auxilliary verbs are only considered tense errors if they are not already classified as form or agreement errors. They must also meet one of the following criteria: 

&ensp;&ensp;A. All tokens are parsed as missing or unnecessary auxiliary verbs (*aux*/*auxpass*); e.g. [Ø (eaten) -> *has* (eaten)].  
&ensp;&ensp;B. There is exactly one token on both sides of the edit. If one side is *ca*, the other side is not *can*; if one side is *wo*, the other side is not *will*; or if one side is *sha*, the other side is not *shall*. E.g. [*ca* (n't) -> *could* (n't)].  
&ensp;&ensp;C. There is exactly one token on both sides of the edit, they both have the same lemma, are both VERB and at least one side is a past tense verb form (VBD).  
&ensp;&ensp;D. There is exactly one token on both sides of the edit, they both have the same lemma, are both VERB, and are both parsed *aux* or *auxpass*.  
&ensp;&ensp;E. There is exactly one token on both sides of the edit, they both have the same lemma, do not have the same POS tag, but the corrected token is a past tense verb form (VBD).  
&ensp;&ensp;F. There is exactly one token on both sides of the edit, they do not have the same lemma, but are both parsed *aux* or *auxpass*; e.g. [*was* (eaten) -> *has* (eaten)].  
&ensp;&ensp;G. All tokens on both side of the edit are parsed *aux* or *auxpass*; e.g. [*has been* (eaten) -> *is* (eaten)].  
&ensp;&ensp;H. All tokens on both sides of the edit are VERB and the last token on both sides has the same lemma; e.g. [*has eaten* -> *was eating*].  

#### Explanation

&ensp;&ensp;A. A missing or unnecessary auxilliary verb cannot be a form or agreement error so must be tense.  
&ensp;&ensp;B. As mentioned previously, certain contractions require a special rule.  
&ensp;&ensp;C. In general, we found that edits with VBD on one side were tense errors.  
&ensp;&ensp;D. In some situations, auxiliaries might be tagged as infinitives (VB) or non-3rd-person forms (VBP). Nevertheless, if they are auxiliaries, they are likely to be tense errors.  
&ensp;&ensp;E. If the POS tags are different, we rely only on the corrected POS tag.  
&ensp;&ensp;F. Auxiliary verbs with different lemmas are all likely to be tense errors.  
&ensp;&ensp;G. Sequences of auxiliaries on both sides of the edit are likely to be tense errors.  
&ensp;&ensp;H. Multi-token edits with the same VERB lemma are likely to be inflectional-to-periphrastic tense errors or vice versa.  

It is worth mentioning that although auxiliaries can be further subdivided in terms of tense, aspect, mood or voice, this distinction seems too narrow for the purposes of error type classification.  

## Rule Order

As mentioned at the start of this section, the above rules have been described in isolation when in fact they sometimes interact and may be carefully ordered. The most complex example of this is verb morphology errors: while errors involving gerunds (VBG) or participles (VBN) are usually considered FORM, and errors involving past tense forms (VBD) are usually considered TENSE, edits such as VBG -> VBD, or vice versa, are more ambiguous (FORM or TENSE?). Similarly, SVA errors normally involve a 3rd-person form (VBZ), but there are also cases of VBZ -> VBN (SVA or FORM?). Although such cases are normally the result of a POS tagging error, we ultimately resolved this issue by manually inspecting the data to determine an order of precedence. Specifically, ambiguous errors were first considered FORM if one side was VBG or VBN, second considered SVA if one side was VBP or VBZ, and third considered TENSE if one side was VBD. In our experiments, this order seemed to produce the most reliable results, but it must still be recognised as an approximation. 

Ultimately, since the interactions between our rules are very difficult to describe in words, we refer the reader to the code for more information concerning rule order. Specifically, look at `getOneSidedType` and `getTwoSidedType` in `scripts/cat_rules.py`. In general, the rules presented in this section mirror the order they occur in these functions.

# MIT License

Copyright (c) 2017 Christopher Bryant, Mariano Felice

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# Contact

If you have any questions, suggestions or bug reports, you can contact the authors at:  
christopher d0t bryant at cl.cam.ac.uk  
mariano d0t felice at cl.cam.ac.uk  