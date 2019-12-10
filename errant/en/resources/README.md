# Resources

## en-ptb_map

en-ptb_map is a mapping file that converts spacy Penn Treebank (PTB) style part-of-speech (POS) tags to Universal Dependency (UD) tags.

This file is necessary because spacy is inconsistent in how it maps fine-grained tags to coarse-grained tags and does not always follow UD guidelines. For example, spacy maps the fine-grained WDT tag (denoting a Wh-determiner such as "_which_ book") to PRON (pronoun) even though it is a determiner by definition. 

The original UD mapping file was obtained [here](http://universaldependencies.org/tagset-conversion/en-penn-uposf.html). I note that some of the mappings have changed since I originally downloaded the file (namely EX, LS and RP), and so I may update this in the future.

Spacy also includes some custom POS tags that are not part of the original PTB tagset, so I used the recommended mapping (available [here](https://github.com/explosion/spaCy/blob/master/spacy/lang/en/tag_map.py)) in these cases. It is also worth mentioning that spacy occasionally updates the mapping, but this only applies that later version of spacy and not spacy 1.9 on which ERRANT currently depends. 

## en_GB-large.txt 

en_GB-large.txt is a list of valid British English words according to the latest Hunspell dictionary.  

It was obtained [here](https://sourceforge.net/projects/wordlist/files/speller/2017.08.24/). 

The specific file bundled with this release is: wordlist-en_GB-large-2017.08.24.zip.

