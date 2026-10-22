"""SOURCES.yaml is the provenance claim; a claim nothing checks is empty.

Each country keeps a manifest naming every CSV it commits, who publishes
it and how it is refreshed. The pages print that manifest, so a manifest
that drifts from the data does not fail quietly — it publishes a wrong
attribution under a real number.

An earlier version of one of these manifests broke silently: two unquoted
scalars containing ': ' folded a key into the line above, and nothing read
the file at build time, so nothing noticed for days.
"""
from __future__ import annotations

import re

import yaml

from core import sitebuild


def manifest(country) -> dict:
    path = country.dir / "SOURCES.yaml"
    assert path.exists(), f"{country.slug}: no SOURCES.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_it_parses(country):
    assert manifest(country), f"{country.slug}: manifest is empty"


def test_every_listed_file_exists(country):
    missing = [d["file"] for d in sitebuild.datasets_for(country)
               if not d["present"]]
    assert not missing, (f"{country.slug}: {len(missing)} listed file(s) "
                         f"are gone: {missing[:6]}")


# A fetcher never overwrites a curated number. It writes what it pulled to
# a sidecar beside the file instead, so a bad upstream day shows up as a
# diff a person reads rather than as a plate that quietly changed. Two
# naming conventions for the same thing grew up in the five projects and
# both are still in use: `<name>_check.csv` and `<name>_from_<source>.csv`.
# Sidecars are working files, not published data, so they are not expected
# in the manifest and are not drawn from.
SIDECAR = re.compile(r"_check$|_from_[a-z0-9]+$")


def test_every_committed_csv_is_listed(country):
    """A CSV nobody declared is a number with no stated source."""
    listed = {d["file"] for d in sitebuild.datasets_for(country)}
    on_disk = {
        str(p.relative_to(country.data_dir))
        for p in country.data_dir.rglob("*.csv")
        if not SIDECAR.search(p.stem)
    }
    undeclared = sorted(on_disk - listed)
    assert not undeclared, (f"{country.slug}: {len(undeclared)} CSV(s) not in "
                            f"SOURCES.yaml: {undeclared[:6]}")


def test_every_entry_names_who_publishes_it(country):
    nameless = [d["file"] for d in sitebuild.datasets_for(country)
                if not d["publisher"].strip()]
    assert not nameless, (f"{country.slug}: no publisher named for "
                          f"{nameless[:6]}")


def test_coverage_is_read_off_the_file_not_the_manifest(country):
    """The years a file covers are a fact about the file.

    Stated in the manifest they go stale the first time a fetcher adds a
    year, and the page then prints a span the CSV does not contain.
    """
    for d in sitebuild.datasets_for(country):
        if d["coverage"] == "—":
            continue
        first, last = (int(x) for x in d["coverage"].split("-"))
        table = country.table(d["file"])
        years = sorted(y for y in (table or {}).get("year", []) if y)
        assert (first, last) == (years[0], years[-1]), \
            f"{country.slug}/{d['file']}: printed {d['coverage']}"


def test_every_plate_cites_files_the_manifest_declares(country):
    """What a plate was watched reading must be a declared dataset.

    core.provenance records the reads; SOURCES.yaml states the provenance.
    If a plate reads a file the manifest does not mention, the page cites
    a source for it that nobody wrote down.
    """
    import json

    listed = {d["file"] for d in sitebuild.datasets_for(country)}
    recorded = json.loads(
        (country.dir / "provenance.json").read_text(encoding="utf-8"))
    stray = sorted({f for files in recorded.values() for f in files} - listed)
    assert not stray, (f"{country.slug}: plates read undeclared file(s): "
                       f"{stray[:6]}")


def test_no_plate_is_drawn_from_a_sidecar(country):
    """A sidecar is what a fetcher pulled, not what anyone reviewed.

    The curated file is the published number; drawing from its sidecar
    would publish whatever the upstream API said this morning, which is
    the single thing this whole arrangement exists to prevent.
    """
    import json

    recorded = json.loads(
        (country.dir / "provenance.json").read_text(encoding="utf-8"))
    bad = sorted({f for files in recorded.values() for f in files
                  if SIDECAR.search(f[:-4] if f.endswith(".csv") else f)})
    assert not bad, f"{country.slug}: plates read sidecar file(s): {bad}"


def test_a_dataset_that_is_not_official_says_so(country):
    """The pages print an Official column, so the flag must be deliberate.

    A dataset is official unless the manifest says otherwise. That default
    is only safe if no entry's own prose contradicts it — a note reading
    "NOT AN OFFICIAL STATISTIC" beside a row labelled Official is the
    page telling the reader something untrue.
    """
    disclaimer = re.compile(
        r"not an official statistic|is not an official|non[- ]official|"
        r"unofficial|no es una estad[íi]stica oficial|"
        r"n'est pas une statistique officielle|"
        r"n[ãa]o (?:é|e) uma estat[íi]stica oficial", re.I)
    contradictions = []
    for d in sitebuild.datasets_for(country):
        blob = f"{d['title']} {d['publisher']}"
        if disclaimer.search(blob) and d["official"]:
            contradictions.append(d["file"])
    assert not contradictions, (
        f"{country.slug}: labelled official but their notes deny it: "
        f"{contradictions}")
