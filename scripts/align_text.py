from itertools import groupby
import spacy.parts_of_speech as POS
import scripts.rdlextra as DL
import string

# Some global variables
NLP = None
CONTENT_POS = [POS.ADJ, POS.ADV, POS.NOUN, POS.VERB]

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

def check_split(source, target, edits):
	s = []
	t = []
	# Collect the tokens
	for e in edits:
		if e[1] < e[2]:
			s_tok = source[e[1]:e[2]].orth_.replace("'", "")
			if len(s_tok) >= 1:
				s.append(s_tok)
		if e[3] < e[4]:
			t_tok = target[e[3]:e[4]].orth_.replace("'", "")
			if len(t_tok) >= 1:
				t.append(t_tok)

	
	if len(s) == len(t):
		return False
	elif len(s) == 1 and len(t) > 1:
		string = s[0]
		tokens = t
	elif len(t) == 1 and len(s) > 1:
		string = t[0]
		tokens = s
	else:
		return False
	# Check split
	if string.startswith(tokens[0]): # Matches beginning
		string = string[len(tokens[0]):]
		if string.endswith(tokens[-1]): # Matches end
			string = string[:-len(tokens[-1])]
			# Matches all tokens in the middle (in order)
			match = True
			for t in tokens[1:-1]:
				try:
					i = string.index(t)
					string = string[i+len(t):]
				except:
					# Token not found
					return False
			# All tokens found
			return True
	# Any other case is False
	return False

# Input 1: Spacy source sentence
# Input 2: Spacy target sentence
# Input 3: The alignmen between the 2; [e.g. M, M, S ,S M]
# Function that decide whether to merge, or keep separate, adjacent edits of various types
# Processes 1 alignment at a time
def get_edits(source, target, edits):
	if len(edits) < 1:
		return edits
	elif edits[0][0] == "M":
#		print("RULE 1")
		return get_edits(source, target, edits[1:])
	elif edits[-1][0] == "M":
#		print("RULE 1")
		return get_edits(source, target, edits[:-1])
	else:
		VP = [POS.VERB, POS.PART]
		merge = False
		pos_seq = False
		old_op = None
		old_pos_s = set()
		old_pos_t = set()
		i = -1 # Edit index in group
		for e in edits:
			i += 1
			op = e[0]
			if op == "M": # M in the middle => split
#				print("RULE 1")
				return get_edits(source, target, edits[:i]) + get_edits(source, target, edits[i+1:])
			# Get the affected tokens
			s = source[e[1]:e[2]][0] if len(source[e[1]:e[2]]) >= 1 else None
			t = target[e[3]:e[4]][0] if len(target[e[3]:e[4]]) >= 1 else None
			# Get the next affected tokens
			j = i+1
			if len(edits) > j:
				s_ = source[edits[j][1]:edits[j][2]][0] if len(source[edits[j][1]:edits[j][2]]) >= 1 else None
				t_ = target[edits[j][3]:edits[j][4]][0] if len(target[edits[j][3]:edits[j][4]]) >= 1 else None
			else:
				s_ = None
				t_ = None
			# Merge consecutive tokens with equal POS tags, e.g. 'because of' > 'for'
			equal_pos = len(old_pos_s.union(old_pos_t, {s.pos} if s else {}, {t.pos} if t else {})) == 1
			# Merge puctuation edits followed by a change in case, e.g. ", we" -> ". We", "Computer" -> "The computer"
			# Next token: same word, different capitalisation
			if ((s and (ispunct(s) or s.orth_[0].isupper())) or (t and (ispunct(t) or t.orth_[0].isupper()))) and \
			   s_ and t_ and s_.lower_ == t_.lower_ and s_.orth_[0] != t_.orth_[0]: 
#				print("RULE 2")
				return get_edits(source, target, edits[:i]) + merge_edits(edits[i:j+1]) + get_edits(source, target, edits[j+1:])
			# Keep all T separate.
			elif op.startswith("T"):
#				print("RULE 3")
				return get_edits(source, target, edits[:i]) + [e] + get_edits(source, target, edits[i+1:])
			# Merge some possessives.
			elif ((s and s.tag_ == "POS") or (t and t.tag_ == "POS")):
#				print("RULE 4")
				return merge_edits(edits[:i+1]) + get_edits(source, target, edits[i+1:])
			# Merge things like sub way -> subway. Some more possessives.
			elif (s_ or t_) and check_split(source, target, edits[i:j+1]):
#				print("RULE 5")
				return get_edits(source, target, edits[:i]) + merge_edits(edits[i:j+1]) + get_edits(source, target, edits[j+1:])
			# Adjacent subsittution rules.
			elif op == "S":
				# If tokens are very similar => split (spelling errors)			
				if char_cost(s.orth_, t.orth_) < 0.3 and not (equal_pos and i > 0):
#					print("RULE 6")
					return get_edits(source, target, edits[:i]) + [e] + get_edits(source, target, edits[i+1:])
				# Consecutive substitutions are split.
				elif old_op == "S": 
#					print("RULE 7")
					return get_edits(source, target, edits[:i]) + [e] + get_edits(source, target, edits[i+1:])
				# Merge if at least one content word		
				else:
#					print("RULE 8")
					merge = merge or is_content(s) or is_content(t)
			# Merge if at least one content word					
			elif op == "D":
#				print("RULE 8")
				merge = merge or is_content(s)
			# Merge if at least one content word				
			elif op == "I":
#				print("RULE 8")
				merge = merge or is_content(t)
			# Save operation
			old_op = e[0]
			# Save old POS
			if s: old_pos_s.add(s.pos)
			if t: old_pos_t.add(t.pos)
		
		# End of changes/group
		#if equal_pos: print "RULE 9"
		merge = merge or equal_pos
		# DET at the end => split
		if (op == "D" and s.pos == POS.DET) or (op == "I" and t.pos == POS.DET) or \
		   (op == "S" and (s.pos == POS.DET or t.pos == POS.DET)):
#			print("RULE 10")
			return merge_edits(edits[:i]) + [e]
		elif merge:
			return merge_edits(edits)
		else:
			return edits

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

# Get all possible lemmas for current token. By checking all POS, we increase
# the chance that there will be a match.
def get_lemmas(token):
	return set([
	NLP.vocab.morphology.lemmatize(POS.ADJ, token.orth, NLP.vocab.morphology.tag_map),
	NLP.vocab.morphology.lemmatize(POS.ADV, token.orth, NLP.vocab.morphology.tag_map),
	NLP.vocab.morphology.lemmatize(POS.NOUN, token.orth, NLP.vocab.morphology.tag_map),
	NLP.vocab.morphology.lemmatize(POS.VERB, token.orth, NLP.vocab.morphology.tag_map)])

def lemma_cost(A, B):
	# Use 0.499 instead of 0.5 to prefer alignments having substitutions
	# instead of unintuitive transpositions. This also avoids having an
	# upperbound of 2 for substitutions, which is good. Now S is in [0, 5)
	return 0.499 * get_lemmas(A).isdisjoint(get_lemmas(B))

# Is the token a content word?
def is_content(A):
	return A.pos in CONTENT_POS	

# Check whether token is punctuation
def ispunct(token):
	return token.pos == POS.PUNCT or token.orth_ in string.punctuation
	
# If POS is the same, cost is 0. If diff POS but both content words, 0.25 
# otherwise cost is 0.5. Content words more likely to align to other content words.
def pos_cost(A, B):
	if A.pos == B.pos:
		return 0
	elif is_content(A) and is_content(B):
		return 0.25
	else:
		return 0.5

# Calculate the cost of character alignment; i.e. char similarity
def char_cost(A, B):
	alignments = DL.WagnerFischer(A, B)
	alignment = next(alignments.alignments(True))	# True uses Depth-first search.
	return alignments.cost / float(len(alignment)) 

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
