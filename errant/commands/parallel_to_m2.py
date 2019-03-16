import argparse
import os
from contextlib import ExitStack

from errant import Errant, toolbox
from errant.commands.subcommand import Subcommand


class ParallelToM2(Subcommand):
    def add_subparser(
        self, name: str, parser: argparse._SubParsersAction
    ) -> argparse.ArgumentParser:
        # pylint: disable=protected-access
        description = """Convert parallel original and corrected text files (1 sentence per line) into M2 format.
                         The default uses Damerau-Levenshtein and merging rules and assumes tokenized text."""
        subparser = parser.add_parser(name, description=description, help=description)

        subparser.add_argument(
            "-orig", help="The path to the original text file.", required=True
        )
        subparser.add_argument(
            "-cor",
            help="The paths to >= 1 corrected text files.",
            nargs="+",
            default=[],
            required=True,
        )
        subparser.add_argument("-out", help="The output filepath.", required=True)
        subparser.add_argument(
            "-lev",
            help="Use standard Levenshtein to align sentences.",
            action="store_true",
        )
        subparser.add_argument(
            "-merge",
            choices=["rules", "all-split", "all-merge", "all-equal"],
            default="rules",
            help="Choose a merging strategy for automatic alignment.\n"
            "rules: Use a rule-based merging strategy (default)\n"
            "all-split: Merge nothing; e.g. MSSDI -> M, S, S, D, I\n"
            "all-merge: Merge adjacent non-matches; e.g. MSSDI -> M, SSDI\n"
            "all-equal: Merge adjacent same-type non-matches; e.g. MSSDI -> M, SS, D, I",
        )

        subparser.set_defaults(func=parallel_to_m2_with_args)
        return subparser


# Input: Command line args
def parallel_to_m2_with_args(args: argparse.Namespace) -> None:

    # Get base working directory.
    print("Loading resources...")
    # Load Tokenizer and other resources

    errant = Errant()

    # Setup output m2 file
    out_m2 = open(args.out, "w")

    # ExitStack lets us process an arbitrary number of files line by line simultaneously.
    # See https://stackoverflow.com/questions/24108769/how-to-read-and-process-multiple-files-simultaneously-in-python
    print("Processing files...")
    with ExitStack() as stack:
        in_files = [stack.enter_context(open(i)) for i in [args.orig] + args.cor]
        # Process each line of all input files.
        for line_id, line in enumerate(zip(*in_files)):
            orig_sent = line[0].strip()
            cor_sents = line[1:]
            # If orig sent is empty, skip the line
            if not orig_sent:
                continue
            # Write the original sentence to the output m2 file.
            out_m2.write("S " + orig_sent + "\n")
            # Markup the original sentence with spacy (assume tokenized)
            proc_orig = errant.parse(orig_sent, tokenize=False)
            # Loop through the corrected sentences
            for cor_id, cor_sent in enumerate(cor_sents):
                cor_sent = cor_sent.strip()
                # Identical sentences have no edits, so just write noop.
                if orig_sent == cor_sent:
                    out_m2.write(
                        "A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||"
                        + str(cor_id)
                        + "\n"
                    )
                # Otherwise, do extra processing.
                else:
                    # Markup the corrected sentence with spacy (assume tokenized)
                    proc_cor = errant.parse(cor_sent.strip(), tokenize=False)
                    # Auto align the parallel sentences and extract the edits.
                    auto_edits = errant.get_typed_edits(
                        proc_orig,
                        proc_cor,
                        levenshtien_costs=args.lev,
                        merge_type=args.merge,
                    )

                    # Loop through the edits.
                    for auto_edit in auto_edits:
                        # Write the edit to the output m2 file.
                        out_m2.write(toolbox.format_edit(auto_edit, str(cor_id)) + "\n")
            # Write a newline when we have processed all corrections for a given sentence.
            out_m2.write("\n")
