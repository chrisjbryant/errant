# Changelog

This document contains descriptions of all the significant changes made to ERRANT since its release.

## 16-11-18

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

## 23-08-18

Fix arbitrary reordering of edits with the same start and end span; e.g.  
S I am happy .  
A 2 2|||M:ADV|||really|||REQUIRED|||-NONE-|||0  
A 2 2|||M:ADV|||very|||REQUIRED|||-NONE-|||0  

VS.  

S I am happy .  
A 2 2|||M:ADV|||very|||REQUIRED|||-NONE-|||0  
A 2 2|||M:ADV|||really|||REQUIRED|||-NONE-|||0  

## 10-08-18

Added support for multiple annotators in `parallel_to_m2.py`.  
Before: `python3 parallel_to_m2.py -orig <orig_file> -cor <cor_file> -out <out_file>`  
After: `python3 parallel_to_m2.py -orig <orig_file> -cor <cor_file1> [<cor_file2> ...] -out <out_file>`  
This is helpful if you have multiple annotations for the same orig file.  

## 17-12-17

In November, spaCy changed significantly when it became version 2.0.0. Although we have not tested ERRANT with this new version, the main change seemed to be a slight increase in performance (pos tagging and parsing etc.) at a significant cost to speed. Consequently, we still recommend spaCy 1.9.0 for use with ERRANT.

## 22-11-17

ERRANT would sometimes run into memory problems if sentences were long and very different. We hence changed the default alignment from breadth-first to depth-first. This bypassed the memory problems, made ERRANT faster and barely affected results.

## 10-05-17 

ERRANT v1.0 released.