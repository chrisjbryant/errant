import argparse
import os
import spacy
from nltk.stem.lancaster import LancasterStemmer
import scripts.align_text as align_text
import scripts.cat_rules as cat_rules
import scripts.toolbox as toolbox

def main(args):
	# Get base working directory.
	basename = os.path.dirname(os.path.realpath(__file__))
	print("Loading resources...")
	# Load Tokenizer and other resources
	nlp = spacy.load("en")
	# Lancaster Stemmer
	stemmer = LancasterStemmer()
	# GB English word list (inc -ise and -ize)
	gb_spell = toolbox.loadDictionary(basename+"/resources/en_GB-large.txt")
	# Part of speech map file
	tag_map = toolbox.loadTagMap(basename+"/resources/en-ptb_map")	
	# Setup output m2 file
	out_m2 = open(args.out, "w")

	print("Processing files...")
	# Open the m2 file and split into sentence+edit chunks.
	m2_file = open(args.m2).read().strip().split("\n\n")
	for info in m2_file:
		# Get the original and corrected sentence + edits for each annotator.
		orig_sent, coder_dict = toolbox.processM2(info)
		# Write the orig_sent to the output m2 file.
		out_m2.write("S "+" ".join(orig_sent)+"\n")
		# Only process sentences with edits.
		if coder_dict:
			# Save marked up original sentence here, if required.
			proc_orig = ""
			# Loop through the annotators
			for coder, coder_info in sorted(coder_dict.items()):
				cor_sent = coder_info[0]
				gold_edits = coder_info[1]
				# If there is only 1 edit and it is noop, just write it.
				if gold_edits[0][2] == "noop":
					out_m2.write(toolbox.formatEdit(gold_edits[0], coder)+"\n")				
					continue
				# Markup the orig and cor sentence with spacy (assume tokenized)
				# Orig is marked up only once for the first coder that needs it.
				proc_orig = toolbox.applySpacy(orig_sent, nlp) if not proc_orig else proc_orig
				proc_cor = toolbox.applySpacy(cor_sent, nlp)
				# Loop through gold edits.
				for gold_edit in gold_edits:
					# Um and UNK edits (uncorrected errors) are always preserved.
					if gold_edit[2] in {"Um", "UNK"}:
						# Um should get changed to UNK unless using old categories.
						if gold_edit[2] == "Um" and not args.old_cats: gold_edit[2] = "UNK"
						out_m2.write(toolbox.formatEdit(gold_edit, coder)+"\n")				
					# Gold edits
					elif args.gold:
						# Minimise the edit; e.g. [has eaten -> was eaten] = [has -> was]
						if not args.max_edits:
							gold_edit = toolbox.minimiseEdit(gold_edit, proc_orig, proc_cor)
							# If minimised to nothing, the edit disappears.
							if not gold_edit: continue
						# Give the edit an automatic error type.
						if not args.old_cats:
							cat = cat_rules.autoTypeEdit(gold_edit, proc_orig, proc_cor, gb_spell, tag_map, nlp, stemmer)
							gold_edit[2] = cat
						# Write the edit to the output m2 file.
						out_m2.write(toolbox.formatEdit(gold_edit, coder)+"\n")
				# Auto edits
				if args.auto:
					# Auto align the parallel sentences and extract the edits.
					auto_edits = align_text.getAutoAlignedEdits(proc_orig, proc_cor, args)				
					# Loop through the edits.
					for auto_edit in auto_edits:
						# Give each edit an automatic error type.
						cat = cat_rules.autoTypeEdit(auto_edit, proc_orig, proc_cor, gb_spell, tag_map, nlp, stemmer)
						auto_edit[2] = cat
						# Write the edit to the output m2 file.
						out_m2.write(toolbox.formatEdit(auto_edit, coder)+"\n")
		# Write a newline when there are no more coders.
		out_m2.write("\n")

if __name__ == "__main__":
	# Define and parse program input
	parser = argparse.ArgumentParser(description="Automatically extract and/or type edits in an m2 file.",
								formatter_class=argparse.RawTextHelpFormatter,
								usage="%(prog)s [-h] (-auto | -gold) [options] m2 -out OUT")
	parser.add_argument("m2", help="A path to an m2 file.")
	type_group = parser.add_mutually_exclusive_group(required=True)
	type_group.add_argument("-auto", help="Extract edits automatically.", action="store_true")
	type_group.add_argument("-gold", help="Use existing edit alignments.",	action="store_true")
	parser.add_argument("-out",	help="The output filepath.", required=True)		
	parser.add_argument("-max_edits", help="Do not minimise edit spans. (gold only)", action="store_true")
	parser.add_argument("-old_cats", help="Do not reclassify the edits. (gold only)", action="store_true")
	parser.add_argument("-lev",	help="Use standard Levenshtein to align sentences.", action="store_true")
	parser.add_argument("-merge", choices=["rules", "all-split", "all-merge", "all-equal"], default="rules",
						help="Choose a merging strategy for automatic alignment.\n"
								"rules: Use a rule-based merging strategy (default)\n"
								"all-split: Merge nothing; e.g. MSSDI -> M, S, S, D, I\n"
								"all-merge: Merge adjacent non-matches; e.g. MSSDI -> M, SSDI\n"
								"all-equal: Merge adjacent same-type non-matches; e.g. MSSDI -> M, SS, D, I")
	args = parser.parse_args()
	main(args)