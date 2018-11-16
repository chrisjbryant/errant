from difflib import SequenceMatcher
from itertools import combinations, groupby
from string import punctuation
import re
import spacy.parts_of_speech as POS
import scripts.rdlextra as DL

# Some global variables
NLP = None
CONTENT_POS = {POS.ADJ, POS.ADV, POS.NOUN, POS.VERB}

### FUNCTIONS ###

def get_opcodes(alignment):
	s_start = 0
	s_end   = 0
	t_start = 0
	t_end   = 0
	opcodes = []
	for op in alignment:
		if op[0] == "D": # Deletion
			s_end += 1
		elif op[0] == "I": # Insertion
			t_end += 1
		elif op[0].startswith("T"): # Transposition
			# Extract number of elements involved (default is 2)
			k = int(op[1:] or 2)
			s_end += k
			t_end += k
		else: # Match or substitution
			s_end += 1
			t_end += 1
		# Save
		opcodes.append((op, s_start, s_end, t_start, t_end))
		# Start from here
		s_start = s_end
		t_start = t_end
	return opcodes

def merge_edits(edits):
	if edits:
		return [("X", edits[0][1], edits[-1][2], edits[0][3], edits[-1][4])]
	else:
		return edits

# Input 1: Spacy source sentence
# Input 2: Spacy target sentence
# Input 3: The alignment between the 2; [e.g. M, M, S ,S M]
# Output: A list of processed edits that have been merged or split.
def get_edits(source, target, edits):
	out_edits = []
	# Start: Split alignment intro groups of M, T and rest. T has a number after it.
	for op, group in groupby(edits, lambda x: x[0][0] if x[0][0] in {"M", "T"} else False):
		# Convert the generator to a list
		group = list(group)
		# Ignore M
		if op == "M": continue
		# Do not merge T
		elif op == "T": out_edits.extend(group)
		# Further processing required
		else: out_edits.extend(process_edits(source, target, group))
	return out_edits

# Input 1: Spacy source sentence
# Input 2: Spacy target sentence
# Input 3: A list of non-matching alignments: D, I and/or S
# Output: A list of processed edits that have been merged or split.
def process_edits(source, target, edits):
	# Return single alignments
	if len(edits) <= 1: return edits
	# Get the ops for the whole edit sequence
	ops = [op[0] for op in edits]
	# Merge ops that are all D xor I. (95% of human multi-token edits contain S).
	if set(ops) == {"D"} or set(ops) == {"I"}: return merge_edits(edits)
	
	content = False # True if edit includes a content word
	# Get indices of all combinations of start and end ranges in the edits: 012 -> 01, 02, 12
	combos = list(combinations(range(0, len(edits)), 2))
	# Sort them starting with largest spans first
	combos.sort(key = lambda x: x[1]-x[0], reverse=True)
	# Loop through combos
	for start, end in combos:
		# Ignore ranges that do NOT contain a substitution.
		if "S" not in ops[start:end+1]: continue
		# Get the tokens in orig and cor. They will never be empty due to above rule.
		s = source[edits[start][1]:edits[end][2]]
		t = target[edits[start][3]:edits[end][4]]
		# Possessive suffixes merged with previous token: [friends -> friend 's]
		if s[-1].tag_ == "POS" or t[-1].tag_ == "POS":
			return process_edits(source, target, edits[:end-1]) + merge_edits(edits[end-1:end+1]) + process_edits(source, target, edits[end+1:])
		# Case changes
		if s[-1].lower_ == t[-1].lower_:
			# Merge first token I or D of arbitrary length: [Cat -> The big cat]
			if start == 0 and ((len(s) == 1 and t[0].text[0].isupper()) or (len(t) == 1 and s[0].text[0].isupper())):
				return merge_edits(edits[start:end+1]) + process_edits(source, target, edits[end+1:])
			# Merge with previous punctuation: [, we -> . We], [we -> . We]
			if (len(s) > 1 and is_punct(s[-2])) or (len(t) > 1 and is_punct(t[-2])):
				return process_edits(source, target, edits[:end-1]) + merge_edits(edits[end-1:end+1]) + process_edits(source, target, edits[end+1:])
		# Whitespace/hyphens: [bestfriend -> best friend], [sub - way -> subway]
		s_str = re.sub("['-]", "", "".join([tok.lower_ for tok in s]))
		t_str = re.sub("['-]", "", "".join([tok.lower_ for tok in t]))
		if s_str == t_str:
			return process_edits(source, target, edits[:start]) + merge_edits(edits[start:end+1]) + process_edits(source, target, edits[end+1:])
		# POS-based merging: Same POS or infinitive/phrasal verbs: [to eat -> eating], [watch -> look at]
		pos_set = set([tok.pos for tok in s]+[tok.pos for tok in t])
		if (len(pos_set) == 1 and len(s) != len(t)) or pos_set == {POS.PART, POS.VERB}:
			return process_edits(source, target, edits[:start]) + merge_edits(edits[start:end+1]) + process_edits(source, target, edits[end+1:])
		# Split rules take effect when we get to smallest chunks
		if end-start < 2:
			# Split adjacent substitutions
			if len(s) == len(t) == 2:
				return process_edits(source, target, edits[:start+1]) + process_edits(source, target, edits[start+1:])
			# Similar substitutions at start or end
			if (ops[start] == "S" and char_cost(s[0].text, t[0].text) < 0.25) or \
				(ops[end] == "S" and char_cost(s[-1].text, t[-1].text) < 0.25):
				return process_edits(source, target, edits[:start+1]) + process_edits(source, target, edits[start+1:])	
			# Split final determiners
			if end == len(edits)-1 and ((ops[-1] in {"D", "S"} and s[-1].pos == POS.DET) or \
				(ops[-1] in {"I", "S"} and t[-1].pos == POS.DET)):
				return process_edits(source, target, edits[:-1]) + [edits[-1]]
		# Set content word flag
		if not pos_set.isdisjoint(CONTENT_POS): content = True
	# If all else fails, merge edits that contain content words
	if content: return merge_edits(edits)
	else: return edits

# Is the token a content word?
def is_content(A):
	return A.pos in CONTENT_POS

# Check whether token is punctuation
def is_punct(token):
	return token.pos == POS.PUNCT or token.text in punctuation

# all-split: No edits are ever merged. Everything is 1:1, 1:0 or 0:1 only.
def get_edits_split(edits):
	new_edits = []
	for edit in edits:
		op = edit[0]
		if op != "M":
			 new_edits.append(edit)
	return new_edits

# all-merge: Merge all adjacent edits of any operation type, except M.
def get_edits_group_all(edits):
	new_edits = []
	for op, group in groupby(edits, lambda x: True if x[0] == "M" else False):
		if not op:
			 new_edits.extend(merge_edits(list(group)))
	return new_edits

# all-equal: Merge all edits of the same operation type.
def get_edits_group_type(edits):
	new_edits = []
	for op, group in groupby(edits, lambda x: x[0]):
		if op != "M":
			 new_edits.extend(merge_edits(list(group)))
	return new_edits

# Cost is 0 if lemmas are the same, otherwise 0.499. Maximum S cost is 1.999.
# This prevents unintuitive transpositions.
def lemma_cost(A, B):
	if A.lemma == B.lemma:
		return 0
	else: 
		return 0.499

# Cost is 0 if POS are the same, else 0.25 if both are content, else 0.5.
# Content words more likely to align to other content words.
def pos_cost(A, B):
	if A.pos == B.pos:
		return 0
	elif is_content(A) and is_content(B):
		return 0.25
	else:
		return 0.5

# Calculate the cost of character alignment; i.e. char similarity
def char_cost(A, B):
	return 1-SequenceMatcher(None, A, B).ratio()

# If there is a substitution, calculate the more informative cost.
def token_substitution(A, B, A_extra, B_extra):
	# If lower case strings are the same, don't bother checking pos etc.
	# This helps catch case marking substitution errors.
	if A.lower() == B.lower():
		return 0
	cost = lemma_cost(A_extra, B_extra) + pos_cost(A_extra, B_extra) + char_cost(A, B)
	return cost	

# Change cost of Transpositions to be the same as Levenshtein.
def levTransposition(a,b,c,d):
	return float("inf")

# Change cost of Substitution to be the same as Levenshtein.
def levSubstitution(a,b,c,d):
	return 1

# Input 1: A Spacy annotated original sentence.
# Input 2: A Spacy annotated corrected sentence.
# Input 3: A preloaded Spacy processing object.
# Input 4: Command line args.
# Output: A list of lists. Each sublist is an edit of the form:
# edit = [orig_start, orig_end, cat, cor, cor_start, cor_end]
def getAutoAlignedEdits(orig, cor, spacy, args):
	# Save the spacy object globally.
	global NLP
	NLP = spacy
	# Get a list of strings from the spacy objects.
	orig_toks = [tok.text for tok in orig]
	cor_toks = [tok.text for tok in cor]
	# Align using Levenshtein.
	if args.lev: alignments = DL.WagnerFischer(orig_toks, cor_toks, orig, cor, substitution=levSubstitution, transposition=levTransposition)
	# Otherwise, use linguistically enhanced Damerau-Levenshtein
	else: alignments = DL.WagnerFischer(orig_toks, cor_toks, orig, cor, substitution=token_substitution)
	# Get the alignment with the highest score. There is usually only 1 best in DL due to custom costs.
	alignment = next(alignments.alignments(True)) # True uses Depth-first search.
	# Convert the alignment into edits; choose merge strategy
	if args.merge == "rules": edits = get_edits(orig, cor, get_opcodes(alignment))
	elif args.merge == "all-split": edits = get_edits_split(get_opcodes(alignment))
	elif args.merge == "all-merge": edits = get_edits_group_all(get_opcodes(alignment))
	elif args.merge == "all-equal": edits = get_edits_group_type(get_opcodes(alignment))
	proc_edits = []
	for edit in edits:
		orig_start = edit[1]
		orig_end = edit[2]
		cat = "NA" # Auto edits do not have human types.
		cor_start = edit[3]
		cor_end = edit[4]
		cor_str = " ".join(cor_toks[cor_start:cor_end])
		proc_edits.append([orig_start, orig_end, cat, cor_str, cor_start, cor_end])
	return proc_edits
