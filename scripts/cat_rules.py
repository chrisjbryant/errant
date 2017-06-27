from difflib import SequenceMatcher
from string import punctuation
import spacy.parts_of_speech as spos

# Contractions
conts = {"'d", "'ll", "'m", "n't", "'re", "'s", "'ve"}
# Rare POS tags that make uninformative error categories
rare_tags = {"INTJ", "NUM", "SYM", "X"}
# Special auxiliaries in contractions.
special_aux1 = ({"ca", "can"}, {"sha", "shall"}, {"wo", "will"})
special_aux2 = {"ca", "sha", "wo"}
# Open class spacy POS tag objects
open_pos = (spos.ADJ, spos.ADV, spos.NOUN, spos.VERB)
# Open class POS tags
open_tags = {"ADJ", "ADV", "NOUN", "VERB"}
# Some dep labels that map to pos tags. 
dep_map = { "acomp": "ADJ",
			"amod": "ADJ",
			"advmod": "ADV", 
			"det": "DET", 
			"prep": "PREP", 
			"prt": "PART",
			"punct": "PUNCT" }

# Input 1: An edit list. [orig_start, orig_end, cat, cor, cor_start, cor_end]
# Input 2: An original SpaCy sentence.
# Input 3: A corrected SpaCy sentence.
# Input 4: A set of valid GB English words.
# Input 5: A dictionary to map PTB tags to Stanford Universal Dependency tags.
# Input 6: A preloaded spacy processing object.
# Input 7: The Lancaster stemmer in NLTK.
# Output: The input edit with new error tag, in M2 edit format.
def autoTypeEdit(edit, orig_sent, cor_sent, gb_spell, tag_map, nlp, stemmer):
	# Get the tokens in the edit.
	orig_toks = orig_sent[edit[0]:edit[1]]
	cor_toks = cor_sent[edit[4]:edit[5]]
	# Nothing to nothing is a detected, but not corrected edit.
	if not orig_toks and not cor_toks:
		return "UNK"
	# Missing
	elif not orig_toks and cor_toks:
		op = "M:"
		cat = getOneSidedType(cor_toks, tag_map)
	# Unnecessary
	elif orig_toks and not cor_toks:
		op = "U:"
		cat = getOneSidedType(orig_toks, tag_map)
	# Replacement and special cases
	else:
		# Same to same is a detected, but not corrected edit.
		if orig_toks.text == cor_toks.text:
			return "UNK"
		# Special: Orthographic errors at the end of multi-token edits are ignored.
		# E.g. [Doctor -> The doctor], [The doctor -> Dcotor], [, since -> . Since]
		# Classify the edit as if the last token weren't there.
		elif orig_toks[-1].lower_ == cor_toks[-1].lower_ and \
			(len(orig_toks) > 1 or len(cor_toks) > 1):
			min_edit = edit[:]
			min_edit[1] -= 1
			min_edit[5] -= 1
			return autoTypeEdit(min_edit, orig_sent, cor_sent, gb_spell, tag_map, nlp, stemmer)
		# Replacement
		else:
			op = "R:"
			cat = getTwoSidedType(orig_toks, cor_toks, gb_spell, tag_map, nlp, stemmer)
	return op+cat

# Input 1: Spacy tokens
# Input 2: A map dict from PTB to universal dependency pos tags.
# Output: A list of token, pos and dep tag strings.
def getEditInfo(toks, tag_map):
	str = []
	pos = []
	dep = []
	for tok in toks:
		str.append(tok.text)
		pos.append(tag_map[tok.tag_])
		dep.append(tok.dep_)
	return str, pos, dep

# Input 1: Spacy tokens.
# Input 2: A map dict from PTB to universal dependency pos tags.
# Output: An error type string.
# When one side of the edit is null, we can only use the other side.
def getOneSidedType(toks, tag_map):
	# Extract strings, pos tags and parse info from the toks.
	str_list, pos_list, dep_list = getEditInfo(toks, tag_map)
	
	# Special cases.
	if len(toks) == 1:
		# Possessive noun suffixes; e.g. ' -> 's
		if toks[0].tag_ == "POS":
			return "NOUN:POSS"
		# Contraction. Rule must come after possessive.
		if toks[0].lower_ in conts:
			return "CONTR"			
		# Infinitival "to" is treated as part of a verb form.
		if toks[0].lower_ == "to" and toks[0].pos_ == "PART" and toks[0].dep_ != "prep":
			return "VERB:FORM"
	# Auxiliary verbs.
	if set(dep_list).issubset({"aux", "auxpass"}):
		return "VERB:TENSE"	
	# POS-based tags. Ignores rare, uninformative categories.
	if len(set(pos_list)) == 1 and pos_list[0] not in rare_tags:
		return pos_list[0]
	# More POS-based tags using special dependency labels.
	if len(set(dep_list)) == 1 and dep_list[0] in dep_map.keys():
		return dep_map[dep_list[0]]
	# To-infinitives and phrasal verbs.
	if set(pos_list) == {"PART", "VERB"}:
		return "VERB"
	# Tricky cases
	else:
		return "OTHER"		

# Input 1: Original text spacy tokens.
# Input 2: Corrected text spacy tokens.
# Input 3: A set of valid GB English words.
# Input 4: A map from PTB to universal dependency pos tags.
# Input 5: A preloaded spacy processing object.
# Input 6: The Lancaster stemmer in NLTK.
# Output: An error type string.
def getTwoSidedType(orig_toks, cor_toks, gb_spell, tag_map, nlp, stemmer):
	# Extract strings, pos tags and parse info from the toks.
	orig_str, orig_pos, orig_dep = getEditInfo(orig_toks, tag_map)
	cor_str, cor_pos, cor_dep = getEditInfo(cor_toks, tag_map)

	# Orthography; i.e. whitespace and/or case errors.
	if onlyOrthChange(orig_str, cor_str):
		return "ORTH"
	# Word Order; only matches exact reordering.
	if exactReordering(orig_str, cor_str):
		return "WO"
		
	# 1:1 replacements (very common)
	if len(orig_str) == len(cor_str) == 1:
		# 1. SPECIAL CASES
		# Possessive noun suffixes; e.g. ' -> 's
		if orig_toks[0].tag_ == "POS" or cor_toks[0].tag_ == "POS":
			return "NOUN:POSS"
		# Contraction. Rule must come after possessive.
		if (orig_str[0].lower() in conts or cor_str[0].lower() in conts) and orig_pos == cor_pos:
			return "CONTR"
		# Special auxiliaries in contractions (1); e.g. ca -> can
		if set(orig_str[0].lower()+cor_str[0].lower()) in special_aux1:
			return "CONTR"
		# Special auxiliaries in contractions (2); e.g. ca -> could
		if orig_str[0].lower() in special_aux2 or cor_str[0].lower() in special_aux2:
			return "VERB:TENSE"
		# Special: "was" and "were" are the only past tense SVA.
		if {orig_str[0].lower(), cor_str[0].lower()} == {"was", "were"}:
			return "VERB:SVA"
			
		# 2. SPELLING AND INFLECTION
		# Only check alphabetical strings on the original side.
		# Spelling errors take precendece over POS errors so this rule is ordered.
		if orig_str[0].isalpha():
			# Check a GB English dict for both orig and lower case.
			# "cat" is in the dict, but "Cat" is not.
			if orig_str[0] not in gb_spell and orig_str[0].lower() not in gb_spell:
				# Check if both sides have a common lemma
				if sameLemma(orig_toks[0], cor_toks[0], nlp):
					# Inflection; Usually count vs mass nouns or e.g. got vs getted
					if orig_pos == cor_pos and orig_pos[0] in {"NOUN", "VERB"}:
						return orig_pos[0]+":INFL"
					# Unknown morphology; i.e. we cannot be more specific.
					else:
						return "MORPH"
				# Use string similarity to detect true spelling errors.
				else:
					char_ratio = SequenceMatcher(None, orig_str[0], cor_str[0]).ratio()
					# Ratio > 0.5 means both side share at least half the same chars.
					# WARNING: THIS IS AN APPROXIMATION.
					if char_ratio > 0.5:
						return "SPELL"
					# If ratio is <= 0.5, this may be a spelling+other error; e.g. tolk -> say
					else:
						# If POS is the same, this takes precedence over spelling.
						if orig_pos == cor_pos and orig_pos[0] not in rare_tags:
							return orig_pos[0]
						# Tricky cases.
						else:
							return "OTHER"					
		
		# 3. MORPHOLOGY
		# Only ADJ, ADV, NOUN and VERB with same lemma can have inflectional changes.
		if sameLemma(orig_toks[0], cor_toks[0], nlp) and \
			orig_pos[0] in open_tags and cor_pos[0] in open_tags:
			# Same POS on both sides
			if orig_pos == cor_pos:
				# Adjective form; e.g. comparatives
				if orig_pos[0] == "ADJ":
					return "ADJ:FORM"
				# Noun number
				if orig_pos[0] == "NOUN":
					return "NOUN:NUM"
				# Verbs - various types
				if orig_pos[0] == "VERB":
					# NOTE: These rules are carefully ordered.
					# Use the dep parse to find some form errors.
					# Main verbs preceded by aux cannot be tense or SVA.
					if precededByAux(orig_toks, cor_toks):
						return "VERB:FORM"
					# Use fine PTB tags to find various errors.
					# FORM errors normally involve VBG or VBN.
					if orig_toks[0].tag_ in {"VBG", "VBN"} or cor_toks[0].tag_ in {"VBG", "VBN"}:
						return "VERB:FORM"
					# Of what's left, TENSE errors normally involved VBD.
					if orig_toks[0].tag_ == "VBD" or cor_toks[0].tag_ == "VBD":
						return "VERB:TENSE"
					# Of what's left, SVA errors normally involve VBZ.
					if orig_toks[0].tag_ == "VBZ" or cor_toks[0].tag_ == "VBZ":
						return "VERB:SVA"
					# Any remaining aux verbs are called TENSE.
					if orig_dep[0].startswith("aux") and cor_dep[0].startswith("aux"):
						return "VERB:TENSE"
			# Use dep labels to find some more ADJ:FORM
			if set(orig_dep+cor_dep).issubset({"acomp", "amod"}):
				return "ADJ:FORM"
			# Adj to plural noun is usually a noun number error; e.g. musical -> musicals.
			if orig_pos[0] == "ADJ" and cor_toks[0].tag_ == "NNS":
				return "NOUN:NUM"
			# For remaining verb errors (rare), rely on cor_pos
			if cor_toks[0].tag_ in {"VBG", "VBN"}:
				return "VERB:FORM"
			# Cor VBD = TENSE
			if cor_toks[0].tag_ == "VBD":
				return "VERB:TENSE"
			# Cor VBZ = SVA
			if cor_toks[0].tag_ == "VBZ":
				return "VERB:SVA"
			# Tricky cases that all have the same lemma.
			else:
				return "MORPH"
		# Derivational morphology.
		if stemmer.stem(orig_str[0]) == stemmer.stem(cor_str[0]) and \
			orig_pos[0] in open_tags and cor_pos[0] in open_tags:
			return "MORPH"

		# 4. GENERAL
		# Auxiliaries with different lemmas
		if orig_dep[0].startswith("aux") and cor_dep[0].startswith("aux"):
			return "VERB:TENSE"
		# POS-based tags. Some of these are context sensitive mispellings.
		if orig_pos == cor_pos and orig_pos[0] not in rare_tags:
			return orig_pos[0]
		# Some dep labels map to POS-based tags.
		if orig_dep == cor_dep and orig_dep[0] in dep_map.keys():
			return dep_map[orig_dep[0]]
		# Phrasal verb particles.
		if set(orig_pos+cor_pos) == {"PART", "PREP"} or set(orig_dep+cor_dep) == {"prt", "prep"}:
			return "PART"
		# Can use dep labels to resolve DET + PRON combinations.
		if set(orig_pos+cor_pos) == {"DET", "PRON"}:
			# DET cannot be a subject or object.
			if cor_dep[0] in {"nsubj", "nsubjpass", "dobj", "pobj"}:
				return "PRON"
			# "poss" indicates possessive determiner
			if cor_dep[0] == "poss":
				return "DET"
		# Tricky cases.
		else:
			return "OTHER"
	
	# Multi-token replacements (uncommon)
	# All auxiliaries
	if set(orig_dep+cor_dep).issubset({"aux", "auxpass"}):
		return "VERB:TENSE"		
	# All same POS
	if len(set(orig_pos+cor_pos)) == 1:
		# Final verbs with the same lemma are tense; e.g. eat -> has eaten 
		if orig_pos[0] == "VERB" and sameLemma(orig_toks[-1], cor_toks[-1], nlp):
			return "VERB:TENSE"
		# POS-based tags. 
		elif orig_pos[0] not in rare_tags:
			return orig_pos[0]
	# All same special dep labels.
	if len(set(orig_dep+cor_dep)) == 1 and orig_dep[0] in dep_map.keys():
		return dep_map[orig_dep[0]]			
	# Infinitives, gerunds, phrasal verbs.
	if set(orig_pos+cor_pos) == {"PART", "VERB"}:
		# Final verbs with the same lemma are form; e.g. to eat -> eating
		if sameLemma(orig_toks[-1], cor_toks[-1], nlp):
			return "VERB:FORM"
		# Remaining edits are often verb; e.g. to eat -> consuming, look at -> see
		else:
			return "VERB"
	# Possessive nouns; e.g. friends -> friend 's
	if (orig_pos == ["NOUN", "PART"] or cor_pos == ["NOUN", "PART"]) and \
		sameLemma(orig_toks[0], cor_toks[0], nlp):
		return "NOUN:POSS"	
	# Adjective forms with "most" and "more"; e.g. more free -> freer
	if (orig_str[0].lower() in {"most", "more"} or cor_str[0].lower() in {"most", "more"}) and \
		sameLemma(orig_toks[-1], cor_toks[-1], nlp) and len(orig_str) <= 2 and len(cor_str) <= 2:
		return "ADJ:FORM"		
		
	# Tricky cases.
	else:
		return "OTHER"
		
# Input 1: A list of original token strings
# Input 2: A list of corrected token strings
# Output: Boolean; the difference between the inputs is only whitespace or case.
def onlyOrthChange(orig_str, cor_str):
	orig_join = "".join(orig_str).lower()
	cor_join = "".join(cor_str).lower()
	if orig_join == cor_join:
		return True
	return False

# Input 1: A list of original token strings
# Input 2: A list of corrected token strings
# Output: Boolean; the tokens are exactly the same but in a different order.
def exactReordering(orig_str, cor_str):
	# Sorting lets us keep duplicates.
	orig_set = sorted([tok.lower() for tok in orig_str])
	cor_set = sorted([tok.lower() for tok in cor_str])
	if orig_set == cor_set:
		return True
	return False

# Input 1: An original text spacy token. 
# Input 2: A corrected text spacy token.
# Input 3: A spaCy processing object.
# Output: Boolean; the tokens have the same lemma.
# Spacy only finds lemma for its predicted POS tag. Sometimes these are wrong,
# so we also consider alternative POS tags to improve chance of a match.
def sameLemma(orig_tok, cor_tok, nlp):
	orig_lemmas = []
	cor_lemmas = []
	for pos in open_pos:
		# Pass the lower cased form of the word for lemmatization; improves accuracy.
		orig_lemmas.append(nlp.vocab.morphology.lemmatize(pos, orig_tok.lower, nlp.vocab.morphology.tag_map))
		cor_lemmas.append(nlp.vocab.morphology.lemmatize(pos, cor_tok.lower, nlp.vocab.morphology.tag_map))
	if set(orig_lemmas).intersection(set(cor_lemmas)):
		return True
	return False

# Input 1: An original text spacy token. 
# Input 2: A corrected text spacy token.
# Output: Boolean; both tokens have a dependant auxiliary verb.
def precededByAux(orig_tok, cor_tok):
	# If the toks are aux, we need to check if they are the first aux.
	if orig_tok[0].dep_.startswith("aux") and cor_tok[0].dep_.startswith("aux"):
		# Find the parent verb
		orig_head = orig_tok[0].head
		cor_head = cor_tok[0].head
		# Find the children of the parent
		orig_children = orig_head.children
		cor_children = cor_head.children
		# Check the orig children.
		for orig_child in orig_children:
			# Look at the first aux...
			if orig_child.dep_.startswith("aux"):
				# Check if the string matches orig_tok
				if orig_child.text != orig_tok[0].text:
					# If it doesn't, orig_tok is not the first aux so check the cor children
					for cor_child in cor_children:
						# Find the first aux in cor...
						if cor_child.dep_.startswith("aux"):
							# If that doesn't match cor_tok, there cor_tok also isnt first aux.
							if cor_child.text != cor_tok[0].text:
								# Therefore, both orig and cor are not first aux.
								return True
							# Break after the first cor aux
							break
				# Break after the first orig aux.
				break
	# Otherwise, the toks are main verbs so we need to look for any aux.
	else:
		orig_deps = [orig_dep.dep_ for orig_dep in orig_tok[0].children]
		cor_deps = [cor_dep.dep_ for cor_dep in cor_tok[0].children]
		if "aux" in orig_deps or "auxpass" in orig_deps:
			if "aux" in cor_deps or "auxpass" in cor_deps:
				return True
	return False