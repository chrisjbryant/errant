"""
Base class for subcommands under ``errant.run``.
"""
import argparse


class Subcommand:
    """
    An abstract class representing subcommands for errant.cli.run.
    """

    def add_subparser(
        self, name: str, parser: argparse._SubParsersAction
    ) -> argparse.ArgumentParser:
        # pylint: disable=protected-access
        raise NotImplementedError
