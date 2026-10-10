"""Exercise M2 block boundaries through the conversion command."""

import sys

import pytest
import spacy

import errant
from errant.commands import m2_to_m2


FIRST = "S I has a cat .\nA 1 2|||R:VERB:SVA|||have|||REQUIRED|||-NONE-|||0"
SECOND = "S They have cats .\nA -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||0"


@pytest.fixture
def annotator(monkeypatch):
    # Boundary handling does not need downloaded tagging or parsing models.
    configured = errant.load("en", nlp=spacy.blank("en"))
    monkeypatch.setattr(errant, "load", lambda language: configured)
    return configured


@pytest.mark.parametrize("ending", ["", "\n", "\n\n", "\n\n\n"])
@pytest.mark.parametrize("separator", ["\n\n", "\n\n\n", "\n \n\n"])
def test_conversion_preserves_all_blocks(tmp_path, monkeypatch, annotator, ending, separator):
    source = tmp_path / "source.m2"
    output = tmp_path / "output.m2"
    source.write_text(FIRST + separator + SECOND + ending)
    monkeypatch.setattr(sys, "argv", [
        "errant_m2", "-gold", "-old_cats", str(source), "-out", str(output),
    ])

    m2_to_m2.main()

    assert output.read_text() == FIRST + "\n\n" + SECOND + "\n\n"


@pytest.mark.parametrize("text", ["", "\n", "\n\n", " \n\n"])
def test_empty_input_has_no_blocks(tmp_path, monkeypatch, annotator, text):
    source = tmp_path / "source.m2"
    output = tmp_path / "output.m2"
    source.write_text(text)
    monkeypatch.setattr(sys, "argv", [
        "errant_m2", "-gold", str(source), "-out", str(output),
    ])

    m2_to_m2.main()

    assert output.read_text() == ""
