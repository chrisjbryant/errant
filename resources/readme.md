# Resources

## en-ptb_map

en-ptb_map is a mapping file that converts spacy Penn Treebank (PTB) style part of speech tags to stanford universal dependency tags.  

The mapping file was obtained [here](http://universaldependencies.org/tagset-conversion/en-penn-uposf.html).  

Spacy includes some custom POS tags that were not part of the original PTB tagset. The authors of spacy suggested the following mapping for these tags:

| PTB-Style | Universal
|-----------|--------
| ""        | PUNCT
| ADD       | X
| GW        | X
| NFP       | X
| SP        | SPACE
| XX        | X

## en_GB-large.txt 

en_GB-large.txt is a list of valid British English words according to the latest Hunspell dictionary.  

It was obtained [here](https://sourceforge.net/projects/wordlist/files/speller/2017.08.24/). 

The specific file bundled with this release is: wordlist-en_GB-large-2017.08.24.zip.

