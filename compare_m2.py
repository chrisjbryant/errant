import argparse
from os.path import isfile

# Input: A path to an m2 file.
# Output: A list of sentence+edits in that file.
def loadM2(path):
	if isfile(path):
		return open(path).read().strip().split("\n\n")
	else:
		print("Error: "+path+" is not a file.")
		exit()

# Input 1: An m2 format sentence with edits.
# Input 2: Command line options.
# Output: A dictionary where key is coder and value is edit dict.
# Each subdict might be for detection, correction, or token based detection.
def extractEdits(sent, args):
	coder_dict = {}
	edits = sent.split("\n")[1:]
	# If there are no edits, pretend there was an explicit noop
	if not edits: edits = ["A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||0"]
	for edit in edits:
		# Preprocessing
		edit = edit[2:].split("|||") # Ignore "A " then split.
		span = [int(i) for i in edit[0].split()]
		start = span[0]
		end = span[1]
		cat = edit[1]
		cor = edit[2]
		cor_len = len(cor.split())
		coder = int(edit[-1])
		# Save coder in dict
		if coder not in coder_dict.keys(): coder_dict[coder] = {}
		
		# Some filters based on args.
		# Exclude uncorrected errors (UNK) in correction evaluation. Gold edits.
		if not args.det_tok and not args.det_span and cat == "UNK": continue
		# Only evaluate edits with more than one token on at least one side.
		if args.multi and end-start < 2 and cor_len < 2: continue
		
		# Token Based Detection
		if args.det_tok:
			# Keep noop edits as they are.
			if start == -1:
				if (start, start) in coder_dict[coder].keys():
					coder_dict[coder][(start, start)].append(cat)
				else:
					coder_dict[coder][(start, start)] = [cat]			
			# Insertions defined as affecting the token on the right
			elif start == end and start >= 0:
				if (start, start+1) in coder_dict[coder].keys():
					coder_dict[coder][(start, start+1)].append(cat)
				else:
					coder_dict[coder][(start, start+1)] = [cat]
			# Edit spans are split for each token in the range.
			else:
				for tok_id in range(start, end):
					if (tok_id, tok_id+1) in coder_dict[coder].keys():
						coder_dict[coder][(tok_id, tok_id+1)].append(cat)
					else:
						coder_dict[coder][(tok_id, tok_id+1)] = [cat]			

		# Span Based Detection
		elif args.det_span:
			if (start, end) in coder_dict[coder].keys():
				coder_dict[coder][(start, end)].append(cat)
			else:
				coder_dict[coder][(start, end)] = [cat]		
		
		# Span Based Correction
		else:
			# With error type classification
			if args.cor_span_err:
				if (start, end, cat, cor) in coder_dict[coder].keys():
					coder_dict[coder][(start, end, cat, cor)].append(cat)
				else:
					coder_dict[coder][(start, end, cat, cor)] = [cat]
			# Without error type classification
			else:
				if (start, end, cor) in coder_dict[coder].keys():
					coder_dict[coder][(start, end, cor)].append(cat)
				else:
					coder_dict[coder][(start, end, cor)] = [cat]
	return coder_dict

# Input 1: A dictionary of hypothesis edits.
# Input 2: A dictionary of reference edits for a single annotator.
# Output 1-3: The TP, FP and FN for the hyp vs the given ref annotator.
# Output 4: A dictionary of the error type scores.
def compareEdits(hyp_edits, ref_edits):	
	tp = 0	# True Positives
	fp = 0	# False Positives
	fn = 0	# False Negatives
	cat_dict = {} # {cat: [tp, fp, fn], ...} 

	for h_edit, h_cats in hyp_edits.items():
		# noop hyp edits cannot be TP or FP
		if h_cats[0] == "noop": continue
		# TRUE POSITIVES
		if h_edit in ref_edits.keys():
			# On occasion, multiple tokens at same span.
			for h_cat in ref_edits[h_edit]: # Use ref dict for TP
				tp += 1
				# Each dict value [TP, FP, FN]
				if h_cat in cat_dict.keys():
					cat_dict[h_cat][0] += 1
				else:
					cat_dict[h_cat] = [1, 0, 0]
		# FALSE POSITIVES
		else:
			# On occasion, multiple tokens at same span.
			for h_cat in h_cats:
				fp += 1
				# Each dict value [TP, FP, FN]
				if h_cat in cat_dict.keys():
					cat_dict[h_cat][1] += 1
				else:
					cat_dict[h_cat] = [0, 1, 0]
	for r_edit, r_cats in ref_edits.items():
		# noop ref edits cannot be FN
		if r_cats[0] == "noop": continue
		# FALSE NEGATIVES
		if r_edit not in hyp_edits.keys():
			# On occasion, multiple tokens at same span.
			for r_cat in r_cats:
				fn += 1
				# Each dict value [TP, FP, FN]
				if r_cat in cat_dict.keys():
					cat_dict[r_cat][2] += 1
				else:
					cat_dict[r_cat] = [0, 0, 1]
	return tp, fp, fn, cat_dict
	
# Input 1-3: True positives, false positives, false negatives
# Input 4: Value of beta in F-score.
# Output 1-3: Precision, Recall and F-score rounded to 4dp.
def computeFScore(tp, fp, fn, beta):
	p = float(tp)/(tp+fp) if fp else 1.0
	r = float(tp)/(tp+fn) if fn else 1.0
	f = float((1+(beta**2))*p*r)/(((beta**2)*p)+r) if p+r else 0.0
	return round(p, 4), round(r, 4), round(f, 4)

# Input 1-2: Two error category dicts. Key is cat, value is list of TP, FP, FN.
# Output: The dictionaries combined with cumulative TP, FP, FN.
def mergeDict(dict1, dict2):
	for cat, stats in dict2.items():
		if cat in dict1.keys():
			dict1[cat] = [x+y for x, y in zip(dict1[cat], stats)]
		else:
			dict1[cat] = stats
	return dict1
	
# Input 1: A dictionary of category TP, FP and FN per category.
# Input 2: Numerical setting on level of detail to process categories.
# 1: M, R, U, UNK only.  2: Everything without M, R, U.  3: Everything.
# Output: A dictionary of category TP, FP and FN based on Input 2.
def processCategories(cat_dict, setting):
	# Otherwise, do some processing.
	proc_cat_dict = {}
	for cat, cnt in cat_dict.items():
		if cat == "UNK":
			proc_cat_dict[cat] = cnt
			continue
		# M, U, R or UNK combined only.
		if setting == 1:
			if cat[0] in proc_cat_dict.keys():
				proc_cat_dict[cat[0]] = [x+y for x, y in zip(proc_cat_dict[cat[0]], cnt)]
			else:
				proc_cat_dict[cat[0]] = cnt
		# Everything without M, U or R.		
		elif setting == 2:
			if cat[2:] in proc_cat_dict.keys():
				proc_cat_dict[cat[2:]] = [x+y for x, y in zip(proc_cat_dict[cat[2:]], cnt)]
			else:
				proc_cat_dict[cat[2:]] = cnt
		# All error category combinations
		else:
			return cat_dict
	return proc_cat_dict

	
if __name__ == "__main__":
	# Define and parse program input
	parser = argparse.ArgumentParser(description="Calculate F-scores for error detection and/or correction "
						"between HYP and REF M2 files.\nDefault behaviour evaluates "
						"just correction in terms of spans.\nFlags let you evaluate "
						"both span and token based detection etc.",
						formatter_class=argparse.RawTextHelpFormatter,
						usage="%(prog)s [options] -hyp HYP -ref REF")
	parser.add_argument("-hyp", help="The hypothesis M2 file", required=True)
	parser.add_argument("-ref", help="The reference M2 file", required=True)
	parser.add_argument("-v", "--verbose", help="Print verbose output.", action="store_true", required=False)
	parser.add_argument("-b", "--beta", help="Value of beta in F-score. (default: 0.5)",
						default=0.5, type=float, required=False)
	parser.add_argument("-multi", help="Only evaluate edits with >1 tokens on at least one side.",
						action="store_true", required=False)						
	parser.add_argument("-cat",	help="Show error category scores.\n"
						"1: Only show overall first level category scores; e.g. R.\n"
						"2: Only show overall non-first level category scores; e.g. NOUN.\n"
						"3: Show all combinations of category scores; e.g. R:NOUN.",
						choices=[1, 2, 3], type=int, required=False)
	type_group = parser.add_mutually_exclusive_group(required=False)
	type_group.add_argument("-dt", "--det_tok",	help="Evaluate Token-level Detection only.", 
						action="store_true")
	type_group.add_argument("-ds", "--det_span", help="Evaluate Span-level Detection only.", 
						action="store_true")
	type_group.add_argument("-cse", "--cor_span_err",
						help="Evaluate Span-level Correction including error types.", action="store_true")
	args = parser.parse_args()

	# Load input files.
	hyp_m2 = loadM2(args.hyp)
	ref_m2 = loadM2(args.ref)
	# Make sure they have the same number of sentences
	assert len(hyp_m2) == len(ref_m2)

	# Variables storing global TP, FP, FN and cat dicts
	best_tp, best_fp, best_fn = 0, 0, 0
	best_cat_dict = {}
	
	# Process each sentence
	sents = zip(hyp_m2, ref_m2)
	for sent_id, sent in enumerate(sents):
		# Process the edits according to input args.
		hyp_dict = extractEdits(sent[0], args)
		ref_dict = extractEdits(sent[1], args)
		# Compare the hyp against each ref and keep track of best so far.
		best_coder = 0
		tmp_f = -1
		tmp_tp, tmp_fp, tmp_fn = 0, 0, 0
		tmp_cat_dict = {}
		for coder, ref_edits in ref_dict.items():
			# Raw counts for a single annotator.
			tp, fp, fn, cat_dict = compareEdits(hyp_dict[0], ref_edits)
			# Score these cumulatively with previous global results.
			p, r, f = computeFScore(tp+best_tp, fp+best_fp, fn+best_fn, args.beta)
			# 1. Save sentence with highest F-score.
			# 2. If both have same F-score, save largest TP.
			# 3. If both have same F-score and TP, save lowest FP.
			# 4. If both have same F-score, TP and FP, save lowest FN.
			if (f > tmp_f) or (f == tmp_f and tp > tmp_tp) or \
				(f == tmp_f and tp == tmp_tp and fp < tmp_fp) or \
				(f == tmp_f and tp == tmp_tp and fp == tmp_fp and fn < tmp_fn):
				best_coder = coder
				tmp_f = f
				tmp_tp, tmp_fp, tmp_fn = tp, fp, fn
				tmp_cat_dict = cat_dict
			# Verbose output
			if args.verbose:
				# Prepare verbose output edits.
				hyp_verb = list(sorted(hyp_dict[0].keys()))
				ref_verb = list(sorted(ref_edits.keys()))
				if not hyp_verb or hyp_verb[0][0] == -1: hyp_verb = []
				if not ref_verb or ref_verb[0][0] == -1: ref_verb = []
				# Print verbose info
				print('{:-^40}'.format(""))
				print("ANNOTATOR "+str(coder))
				print("HYPOTHESIS EDITS :", hyp_verb)
				print("REFERENCE EDITS  :", ref_verb)
				print("Local TP/FP/FN   :", str(tp), str(fp), str(fn))
				print("Global TP/FP/FN  :", str(tp+best_tp), str(fp+best_fp), str(fn+best_fn))
				print("Global P/R/F"+str(args.beta)+"  :", str(p), str(r), str(f))
		# Having processed all ref, save the best tp, fp, fn etc.
		best_tp += tmp_tp
		best_fp += tmp_fp
		best_fn += tmp_fn
		best_cat_dict = mergeDict(best_cat_dict, tmp_cat_dict)
		# Verbose output
		if args.verbose:
			print('{:-^40}'.format(""))
			print("^^ Annotator "+str(best_coder)+" chosen for sentence "+str(sent_id))

	# Prepare output title.
	if args.det_tok: title = " Token-Based Detection "
	elif args.det_span: title = " Span-Based Detection "
	elif args.cor_span_err: title = " Span-Based Correction + Classification "
	else: title = " Span-Based Correction "			

	# Category Scores
	if args.cat:
		best_cat_dict = processCategories(best_cat_dict, args.cat)
		print("")
		print('{:=^66}'.format(title))
		print("Category".ljust(14), "TP".ljust(8), "FP".ljust(8), "FN".ljust(8), "P".ljust(8), "R".ljust(8), "F"+str(args.beta))
		for cat, cnts in sorted(best_cat_dict.items()):
			if cnts[0] + cnts[2] == 0: continue # Ignore hyp file placeholder error type.
			cat_p, cat_r, cat_f = computeFScore(cnts[0], cnts[1], cnts[2], args.beta)
			print(cat.ljust(14), str(cnts[0]).ljust(8), str(cnts[1]).ljust(8), str(cnts[2]).ljust(8), str(cat_p).ljust(8), str(cat_r).ljust(8), cat_f)

	# Print the overall results.
	print("")
	print('{:=^46}'.format(title))
	print("\t".join(["TP", "FP", "FN", "Prec", "Rec", "F"+str(args.beta)]))
	print("\t".join(map(str, [best_tp, best_fp, best_fn]+list(computeFScore(best_tp, best_fp, best_fn, args.beta)))))
	print('{:=^46}'.format(""))
	print("")