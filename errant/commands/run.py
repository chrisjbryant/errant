#!/usr/bin/env python
import argparse
import logging
import os
import sys
from typing import Dict

from errant import __version__
from errant.commands.compare_m2 import CompareM2
from errant.commands.m2_to_m2 import M2ToM2
from errant.commands.parallel_to_m2 import ParallelToM2

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def main() -> None:
    prog = "errant"
    parser = argparse.ArgumentParser(
        description="Run ErrAnnT", usage="%(prog)s", prog=prog
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )

    subparsers = parser.add_subparsers(title="Commands", metavar="")

    subcommands = {
        "compare_m2": CompareM2(),
        "parallel_to_m2": ParallelToM2(),
        "m2_to_m2": M2ToM2(),
    }

    for name, subcommand in subcommands.items():
        subparser = subcommand.add_subparser(
            name, subparsers
        )  # pylint: disable=unused-variable

    args = parser.parse_args()

    # If a subparser is triggered, it adds its work as `args.func`.
    # So if no such attribute has been added, no subparser was triggered,
    # so give the user some help.
    if "func" in dir(args):
        args.func(args)
    else:
        parser.print_help()


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        level=logging.INFO,
    )


def run() -> None:
    setup_logging()
    main()
