from copy import deepcopy
from pathlib import Path
from time import perf_counter

from .types import EXTRA_KEYS, DocumentData, SaveResults, SpartitionData, SubsetData


def initialize():
    import itaxotools

    itaxotools.progress_handler("Initializing...")
    import itaxotools.taxi2.sequences  # noqa
    import itaxotools.spart_parser  # noqa


def open_spart(path: Path) -> DocumentData:
    from itaxotools.spart_parser import Spart

    spart = Spart.fromXML(path)

    spartitions = []
    for original in spart.spartDict["spartitions"].values():
        label = original["label"]
        subsets = [
            SubsetData(subset, spart.getSubsetIndividuals(label, subset))
            for subset in spart.getSpartitionSubsets(label)
        ]
        spartitions.append(SpartitionData(label, subsets, original, False))

    extras = {key: spart.spartDict[key] for key in EXTRA_KEYS if key in spart.spartDict}

    return DocumentData(spart.getIndividuals(), spartitions, extras)


def import_individuals(path: Path) -> list[str]:
    """Read individual names from either a FASTA or a SPART XML file."""
    from itaxotools.spart_parser import Spart
    from itaxotools.taxi2.sequences import SequenceHandler, Sequences

    with open(path) as file:
        head = file.read(1024).lstrip()

    if head.startswith("<"):
        return Spart.fromXML(path).getIndividuals()
    if head.startswith(">"):
        sequences = Sequences.fromPath(path, SequenceHandler.Fasta)
        return [sequence.id for sequence in sequences]
    raise Exception(f"Not a FASTA or SPART XML file: {path.name}")


def save_spart(path: Path, document: DocumentData) -> SaveResults:
    """Write the document as SPART XML.

    Spartitions that were not edited are written back as they were read.
    Edited ones are rebuilt from their subsets, which drops their scores and
    concordances, since those no longer describe them.
    """
    from itaxotools.spart_parser import Spart

    ts = perf_counter()

    spart = Spart()
    for key in EXTRA_KEYS:
        if key in document.extras:
            spart.spartDict[key] = deepcopy(document.extras[key])

    known = spart.spartDict["individuals"]
    spart.spartDict["individuals"] = {
        individual: known.get(individual, {"types": {}})
        for individual in document.individuals
    }

    for number, spartition in enumerate(document.spartitions, start=1):
        original = spartition.original or {}

        if original and not spartition.dirty:
            data = deepcopy(original)
            data["label"] = spartition.label
        else:
            original_subsets = original.get("subsets", {})
            subsets = {}
            for subset in spartition.subsets:
                # Subset attributes such as the taxon name survive an edit,
                # but scores do not.
                kept = {
                    key: value
                    for key, value in original_subsets.get(subset.label, {}).items()
                    if key not in ("individuals", "score")
                }
                subsets[subset.label] = {
                    **deepcopy(kept),
                    "individuals": {
                        individual: {} for individual in subset.individuals
                    },
                }
            data = {
                "label": spartition.label,
                "remarks": original.get("remarks", None),
                "subsets": subsets,
                "concordances": {},
            }

        spart.spartDict["spartitions"][str(number)] = data

    spart.toXML(path)

    tf = perf_counter()

    return SaveResults(path, len(document.spartitions), tf - ts)
