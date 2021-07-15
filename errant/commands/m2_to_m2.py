import argparse
import errant

def main():
    # Parse command line args
    args = parse_args()
    print("Loading resources...")
    # Load Errant
    annotator = errant.load("en")

    print("Processing M2 file...")
    # Open the m2 file and split it into text+edits blocks. Also open out_m2.
    with open(args.m2_file) as m2, open(args.out, "w") as out_m2:
        # Store the current m2_block here
        m2_block = []
        # Loop through m2 lines
        for line in m2:
            line = line.strip()
            # If the line isn't empty, add it to the m2_block
            if line: m2_block.append(line)
            # Otherwise, process the complete blocks
            else:
                # Write the original text to the output M2 file
                out_m2.write(m2_block[0]+"\n")
                # Parse orig with spacy
                orig = annotator.parse(m2_block[0][2:])
                # Simplify the edits and sort by coder id
                edit_dict = simplify_edits(m2_block[1:])
                # Loop through coder ids
                for id, raw_edits in sorted(edit_dict.items()):
                    # If the first edit is a noop
                    if raw_edits[0][2] == "noop":
                        # Write the noop and continue
                        out_m2.write(noop_edit(id)+"\n")
                        continue
                    # Apply the edits to generate the corrected text
                    # Also redefine the edits as orig and cor token offsets
                    cor, gold_edits = get_cor_and_edits(m2_block[0][2:], raw_edits)
                    # Parse cor with spacy
                    cor = annotator.parse(cor)
                    # Save detection edits here for auto
                    det_edits = []
                    # Loop through the gold edits
                    for gold_edit in gold_edits:
                        # Do not minimise detection edits
                        if gold_edit[-2] in {"Um", "UNK"}:
                            edit = annotator.import_edit(orig, cor, gold_edit[:-1],
                                min=False, old_cat=args.old_cats)
                            # Overwrite the pseudo correction and set it in the edit
                            edit.c_toks = annotator.parse(gold_edit[-1])
                            # Save the edit for auto
                            det_edits.append(edit)
                            # Write the edit for gold
                            if args.gold:
                                # Write the edit
                                out_m2.write(edit.to_m2(id)+"\n")
                        # Gold annotation
                        elif args.gold:
                            edit = annotator.import_edit(orig, cor, gold_edit[:-1],
                                not args.no_min, args.old_cats)
                            # Write the edit
                            out_m2.write(edit.to_m2(id)+"\n")
                    # Auto annotations
                    if args.auto:
                        # Auto edits
                        edits = annotator.annotate(orig, cor, args.lev, args.merge)
                        # Combine detection and auto edits and sort by orig offsets
                        edits = sorted(det_edits+edits, key=lambda e:(e.o_start, e.o_end))
                        # Write the edits to the output M2 file
                        for edit in edits:
                            out_m2.write(edit.to_m2(id)+"\n")
                # Write a newline when there are no more edits
                out_m2.write("\n")
                # Reset the m2 block
                m2_block = []

# Parse command line args
def parse_args():
    parser = argparse.ArgumentParser(
        description = "Automatically extract and/or classify edits in an m2 file.",
        formatter_class = argparse.RawTextHelpFormatter,
        usage = "%(prog)s [-h] (-auto | -gold) [options] m2_file -out OUT")
    parser.add_argument(
        "m2_file",
        help = "The path to an m2 file.")
    type_group = parser.add_mutually_exclusive_group(required = True)
    type_group.add_argument(
        "-auto",
        help = "Extract edits automatically.",
        action = "store_true")
    type_group.add_argument(
        "-gold",
        help = "Use existing edit alignments.",
        action = "store_true")
    parser.add_argument(
        "-out",
        help = "The output filepath.",
        required = True)
    parser.add_argument(
        "-no_min",
        help = "Do not minimise edit spans (gold only).",
        action = "store_true")
    parser.add_argument(
        "-old_cats",
        help = "Preserve old error types (gold only); i.e. turn off the classifier.",
        action = "store_true")
    parser.add_argument(
        "-lev",
        help = "Align using standard Levenshtein.",
        action = "store_true")
    parser.add_argument(
        "-merge",
        help = "Choose a merging strategy for automatic alignment.\n"
            "rules: Use a rule-based merging strategy (default)\n"
            "all-split: Merge nothing: MSSDI -> M, S, S, D, I\n"
            "all-merge: Merge adjacent non-matches: MSSDI -> M, SSDI\n"
            "all-equal: Merge adjacent same-type non-matches: MSSDI -> M, SS, D, I",
        choices = ["rules", "all-split", "all-merge", "all-equal"],
        default = "rules")
    args = parser.parse_args()
    return args

# Input: A list of edit lines from an m2 file
# Output: An edit dictionary; key is coder id, value is a list of edits
def simplify_edits(edits):
    edit_dict = {}
    for edit in edits:
        edit = edit.split("|||")
        span = edit[0][2:].split() # [2:] ignore the leading "A "
        start = int(span[0])
        end = int(span[1])
        cat = edit[1]
        cor = edit[2]
        id = edit[-1]
        # Save the useful info as a list
        proc_edit = [start, end, cat, cor]
        # Save the proc_edit inside the edit_dict using coder id
        if id in edit_dict.keys():
            edit_dict[id].append(proc_edit)
        else:
            edit_dict[id] = [proc_edit]
    return edit_dict

# Input 1: A tokenised original text string
# Input 2: A list of edits; [o_start, o_end, cat, cor]
# Output 1: A tokenised corrected text string
# Output 2: A list of edits; [o_start, o_end, c_start, c_end, cat, cor]
def get_cor_and_edits(orig, edits):
    # Copy orig; we will apply edits to it to make cor
    cor = orig.split()
    new_edits = []
    offset = 0
    # Sort the edits by offsets before processing them
    edits = sorted(edits, key=lambda e:(e[0], e[1]))
    # Loop through edits: [o_start, o_end, cat, cor_str]
    for edit in edits:
        o_start = edit[0]
        o_end = edit[1]
        cat = edit[2]
        cor_toks = edit[3].split()
        # Detection edits
        if cat in {"Um", "UNK"}:
            # Save the pseudo correction
            det_toks = cor_toks[:]
            # But temporarily overwrite it to be the same as orig
            cor_toks = orig.split()[o_start:o_end]
        # Apply the edits
        cor[o_start+offset:o_end+offset] = cor_toks
        # Get the cor token start and end offsets in cor
        c_start = o_start+offset
        c_end = c_start+len(cor_toks)
        # Keep track of how this affects orig edit offsets
        offset = offset-(o_end-o_start)+len(cor_toks)
        # Detection edits: Restore the pseudo correction
        if cat in {"Um", "UNK"}: cor_toks = det_toks
        # Update the edit with cor span and save
        new_edit = [o_start, o_end, c_start, c_end, cat, " ".join(cor_toks)]
        new_edits.append(new_edit)
    return " ".join(cor), new_edits

# Input: A coder id
# Output: A noop edit; i.e. text contains no edits
def noop_edit(id=0):
    return "A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||"+str(id)