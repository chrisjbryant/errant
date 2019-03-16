import argparse
import os

from errant import Errant, toolbox
from errant.alignment import (
    ALL_EQUAL_MERGE,
    ALL_MERGE_MERGE,
    ALL_SPLIT_MERGE,
    RULES_MERGE,
)
from errant.commands.subcommand import Subcommand
from errant.edit import ErrorType


class M2ToM2(Subcommand):
    def add_subparser(
        self, name: str, parser: argparse._SubParsersAction
    ) -> argparse.ArgumentParser:
        # pylint: disable=protected-access

        description = "Automatically extract and/or type edits in an m2 file."

        subparser = parser.add_parser(name, description=description, help=description)
        subparser.add_argument("m2", help="A path to an m2 file.")
        type_group = subparser.add_mutually_exclusive_group(required=True)
        type_group.add_argument(
            "-auto", help="Extract edits automatically.", action="store_true"
        )
        type_group.add_argument(
            "-gold", help="Use existing edit alignments.", action="store_true"
        )
        subparser.add_argument("-out", help="The output filepath.", required=True)
        subparser.add_argument(
            "-max_edits",
            help="Do not minimise edit spans. (gold only)",
            action="store_true",
        )
        subparser.add_argument(
            "-old_cats",
            help="Do not reclassify the edits. (gold only)",
            action="store_true",
        )
        subparser.add_argument(
            "-lev",
            help="Use standard Levenshtein to align sentences.",
            action="store_true",
        )
        subparser.add_argument(
            "-merge",
            choices=[RULES_MERGE, ALL_SPLIT_MERGE, ALL_MERGE_MERGE, ALL_EQUAL_MERGE],
            default=RULES_MERGE,
            help="Choose a merging strategy for automatic alignment.\n"
            "rules: Use a rule-based merging strategy (default)\n"
            "all-split: Merge nothing; e.g. MSSDI -> M, S, S, D, I\n"
            "all-merge: Merge adjacent non-matches; e.g. MSSDI -> M, SSDI\n"
            "all-equal: Merge adjacent same-type non-matches; e.g. MSSDI -> M, SS, D, I",
        )
        subparser.set_defaults(func=m2_to_m2_with_args)
        return subparser


# Input: Command line args
def m2_to_m2_with_args(args: argparse.Namespace) -> None:

    print("Loading resources...")
    # Load Errant Annotator
    errant = Errant()
    # Setup output m2 file
    out_m2 = open(args.out, "w")

    print("Processing files...")
    # Open the m2 file and split into sentence+edit chunks.
    m2_file = open(args.m2).read().strip().split("\n\n")
    for info in m2_file:
        # Get the original and corrected sentence + edits for each annotator.
        orig_sent, coder_dict = toolbox.process_m2(info)
        # Write the orig_sent to the output m2 file.
        out_m2.write("S " + " ".join(orig_sent) + "\n")

        # Only process sentences with edits.
        if coder_dict:
            # Save marked up original sentence here, if required.
            proc_orig = None
            # Loop through the annotators
            for coder, coder_info in sorted(coder_dict.items()):
                cor_sent = coder_info[0]
                gold_edits = coder_info[1]
                # If there is only 1 edit and it is noop, just write it.
                if str(gold_edits[0].error_type) == "noop":
                    out_m2.write(toolbox.format_edit(gold_edits[0], coder) + "\n")
                    continue
                # Markup the orig and cor sentence with spacy (assume tokenized)
                # Orig is marked up only once for the first coder that needs it.
                if not proc_orig:
                    proc_orig = errant.parse(" ".join(orig_sent), tokenize=False)

                proc_cor = errant.parse(" ".join(cor_sent), tokenize=False)
                # Loop through gold edits.
                for gold_edit in gold_edits:
                    # Um and UNK edits (uncorrected errors) are always preserved.
                    if str(gold_edit.error_type) in {"Um", "UNK"}:
                        # Um should get changed to UNK unless using old categories.
                        if str(gold_edit.error_type) and not args.old_cats:
                            gold_edit.error_type = ErrorType(
                                ErrorType.UNKNOWN_OP, "UNK"
                            )
                        out_m2.write(toolbox.format_edit(gold_edit, coder) + "\n")
                    # Gold edits
                    elif args.gold:
                        # Minimise the edit; e.g. [has eaten -> was eaten] = [has -> was]
                        if not args.max_edits:
                            minimized_gold_edit = toolbox.minimise_edit(
                                gold_edit, proc_orig, proc_cor
                            )
                            # If minimised to nothing, the edit disappears.
                            if not minimized_gold_edit:
                                continue
                            else:
                                gold_edit = minimized_gold_edit
                        # Give the edit an automatic error type.
                        if not args.old_cats:
                            error_type = errant.find_error_type(
                                gold_edit, proc_orig, proc_cor
                            )
                            gold_edit.error_type = error_type
                        # Write the edit to the output m2 file.
                        out_m2.write(toolbox.format_edit(gold_edit, coder) + "\n")
                # Auto edits
                if args.auto:
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
                        out_m2.write(toolbox.format_edit(auto_edit, coder) + "\n")
        # Write a newline when there are no more coders.
        out_m2.write("\n")
