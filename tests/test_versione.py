"""La versione nel codice coincide con l'ultima di CHANGELOG.md."""

import re

import tracker


def test_versione_uguale_al_changelog():
    changelog = (tracker.BASE / "CHANGELOG.md").read_text(encoding="utf-8")
    versioni = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, flags=re.M)
    assert versioni and versioni[0] == tracker.VERSIONE
    assert "## [Unreleased]" in changelog
