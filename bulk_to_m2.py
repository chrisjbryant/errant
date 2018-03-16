# 500676

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

    print("Processing files...")
    for dir in os.listdir(args.dir):
        if dir == ".DS_Store":
            continue
        if int(float(dir)) < 500676:
            continue
        print("Processing dir... " + dir)
        orig = open(os.path.join(args.dir, dir, "orig.txt"))
        cor = open(os.path.join(args.dir, dir, "cor.txt"))
        out_m2 = open(os.path.join(args.dir, dir, "out.m2"), "w")

        for orig_sent, cor_sent in zip(orig, cor):
            # Write the original sentence to the output m2 file.
            out_m2.write("S "+ orig_sent)
            # Identical sentences have no edits, so just write noop.
            if orig_sent.strip() == cor_sent.strip():
                out_m2.write("A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||0\n")
                # Otherwise, do extra processing.
            else:
                # Markup the parallel sentences with spacy (assume tokenized)
                proc_orig = toolbox.applySpacy(orig_sent.strip().split(), nlp)
                proc_cor = toolbox.applySpacy(cor_sent.strip().split(), nlp)
                # Auto align the parallel sentences and extract the edits.
                auto_edits = align_text.getAutoAlignedEdits(proc_orig, proc_cor, nlp, args)
                # Loop through the edits.
                for auto_edit in auto_edits:
                    # Give each edit an automatic error type.
                    cat = cat_rules.autoTypeEdit(auto_edit, proc_orig, proc_cor, gb_spell, tag_map, nlp, stemmer)
                    auto_edit[2] = cat
                    # Write the edit to the output m2 file.
                    out_m2.write(toolbox.formatEdit(auto_edit)+"\n")
                    # Write a newline when there are no more edits.
                    out_m2.write("\n")

if __name__ == "__main__":
    # Define and parse program input
    parser = argparse.ArgumentParser(description="Convert parallel original and corrected text files (1 sentence per line) into M2 format.\nThe default uses Damerau-Levenshtein and merging rules and assumes tokenized text.",
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     usage="%(prog)s [-h] [options] -orig ORIG -cor COR -out OUT")
    parser.add_argument("-dir", help="The path to the folder containing subdirectories.", required=True)
    parser.add_argument("-lev", help="Use standard Levenshtein to align sentences.", action="store_true")
    parser.add_argument("-merge", choices=["rules", "all-split", "all-merge", "all-equal"], default="rules",
                        help="Choose a merging strategy for automatic alignment.\n"
                        "rules: Use a rule-based merging strategy (default)\n"
                        "all-split: Merge nothing; e.g. MSSDI -> M, S, S, D, I\n"
                        "all-merge: Merge adjacent non-matches; e.g. MSSDI -> M, SSDI\n"
                        "all-equal: Merge adjacent same-type non-matches; e.g. MSSDI -> M, SS, D, I")
    args = parser.parse_args()
    # Run the program.
    main(args)
