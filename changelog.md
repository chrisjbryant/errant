# Changelog

This document contains descriptions of all the significant changes made to ERRANT since its release.

## 16-11-18

The `compare_m2.py` evaluation script was refactored to make it easier to use.


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