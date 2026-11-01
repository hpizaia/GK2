"""The modules of scripts/build.py, one per subject (build.py is the entry point and re-exports every name):

    common    paths, constants, validate.py, names layers, input helpers, --lang, file writing
    notes     recipe notes: pt translation and perk bonus shapes
    builder   class Builder: raw items / recipes -> the dataset (data/gk2.json)
    grades    quality grades and perk bonuses
    reports   data/report-l10n.md, data/report-build.md
    payload   the JSON embedded in the page (sprite, techs, days, facts)
    page      the page from src/, the data block, the Artifact and preview variants
    versions  VERSION, changelog, game version, meta.built

Imported as `build_parts`, with scripts/ on sys.path (build.py puts it there). Python 3 stdlib only."""
