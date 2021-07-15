# Resources

## en-ptb_map

en-ptb_map is a mapping file that converts spacy Penn Treebank (PTB) style part-of-speech (POS) tags to Universal Dependency (UD) tags.

This file is necessary because spacy used to be inconsistent in how it mapped fine-grained tags to coarse-grained tags and did not always follow UD guidelines. For example, some versions of spacy mapped the fine-grained WDT tag (denoting a Wh-determiner such as "_which_ book") to PRON (pronoun) even though it is a determiner by definition. 

The original UD mapping file was obtained [here](http://universaldependencies.org/tagset-conversion/en-penn-uposf.html). I note that some of the mappings have changed since the original release of ERRANT.

## en_GB-large.txt 

en_GB-large.txt is a list of valid British English words according to the latest Hunspell dictionary.  

It was obtained [here](https://sourceforge.net/projects/wordlist/files/speller/2020.12.07/). 

The specific file bundled with this release is: wordlist-en_GB-large-2020.12.07.zip.

