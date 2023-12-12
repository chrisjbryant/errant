import argparse
from contextlib import ExitStack
import errant
from multiprocessing import Pool
from tqdm import tqdm

print("Loading resources...")
# Load Errant
annotator = errant.load("en")

def main():
    print("Processing parallel files...")
    # Process an arbitrary number of files line by line simultaneously. Python 3.3+
    # See https://tinyurl.com/y4cj4gth . Also opens the output m2 file.
    with ExitStack() as stack, open(args.out, "w") as out_m2:
        in_files = [stack.enter_context(open(i)) for i in [args.orig]+args.cor]
        # Process each line of all input files
        with Pool(args.worker) as pool:
            for res in pool.imap(extract_edits, tqdm(zip(*in_files)), chunksize=512):
                if res:
                    out_m2.write(res)

# Parse command line args
def parse_args():
    parser=argparse.ArgumentParser(
        description="Align parallel text files and extract and classify the edits.\n",
        formatter_class=argparse.RawTextHelpFormatter,
        usage="%(prog)s [-h] [options] -orig ORIG -cor COR [COR ...] -out OUT")
    parser.add_argument(
        "-orig",
        help="The path to the original text file.",
        required=True)
    parser.add_argument(
        "-cor",
        help="The paths to >= 1 corrected text files.",
        nargs="+",
        default=[],
        required=True)
    parser.add_argument(
        "-out", 
        help="The output filepath.",
        required=True)
    parser.add_argument(
        "-tok", 
        help="Word tokenise the text using spacy (default: False).",
        action="store_true")
    parser.add_argument(
        "-lev",
        help="Align using standard Levenshtein (default: False).",
        action="store_true")
    parser.add_argument(
        "-merge",
        help="Choose a merging strategy for automatic alignment.\n"
            "rules: Use a rule-based merging strategy (default)\n"
            "all-split: Merge nothing: MSSDI -> M, S, S, D, I\n"
            "all-merge: Merge adjacent non-matches: MSSDI -> M, SSDI\n"
            "all-equal: Merge adjacent same-type non-matches: MSSDI -> M, SS, D, I",
        choices=["rules", "all-split", "all-merge", "all-equal"],
        default="rules")
    parser.add_argument(
        "-worker",
        help="The number of multi-processing workers.",
        type=int,
        default=16,
        )
    args=parser.parse_args()
    return args

# Parse command line args
args = parse_args()

def extract_edits(line):
    res = ""
    # Get the original and all the corrected texts
    orig = line[0].strip()
    cors = line[1:]
    # Skip the line if orig is empty
    if not orig: return ""
    # Parse orig with spacy
    orig = annotator.parse(orig, args.tok)
    # Write orig to the output m2 file
    res += " ".join(["S"]+[token.text for token in orig])+"\n"
    # Loop through the corrected texts
    for cor_id, cor in enumerate(cors):
        cor = cor.strip()
        # If the texts are the same, write a noop edit
        if orig.text.strip() == cor:
            res += noop_edit(cor_id)+"\n"
        # Otherwise, do extra processing
        else:
            # Parse cor with spacy
            cor = annotator.parse(cor, args.tok)
            # Align the texts and extract and classify the edits
            edits = annotator.annotate(orig, cor, args.lev, args.merge)
            # Loop through the edits
            for edit in edits:
                # Write the edit to the output m2 file
                res += edit.to_m2(cor_id)+"\n"
    # Write a newline when we have processed all corrections for each line
    res += "\n"
    return res

# Input: A coder id
# Output: A noop edit; i.e. text contains no edits
def noop_edit(id=0):
    return "A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||"+str(id)
