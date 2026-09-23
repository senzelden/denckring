"""Build strict, single-token relations from OEWN 2024 using wn 1.1.1.

Run from the repository root:
uv run --with wn==1.1.1 python packages/denckring-en-data/scripts/build_relations.py

Same CC BY 4.0 source as the existing glosses; see LICENSE-WORDNET.
No inference, morphology, transitive closure or manual fallback pairs.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import wn

DATA = Path(__file__).resolve().parents[1] / "src/denckring_en_data/data"
SPEC = "oewn:2024"


def main() -> None:
    if wn.__version__ != "1.1.1":
        raise RuntimeError("reproduction requires wn==1.1.1")
    lexicon = wn.Wordnet(SPEC)
    tables: dict[str, dict[str, set[str]]] = {"synonyms": {}, "antonyms": {}}
    for word in lexicon.words():
        lemma = word.lemma().casefold()
        if not lemma.isalpha():
            continue
        for sense in word.senses():
            related = {
                "synonyms": sense.synset().words(),
                "antonyms": [other.word() for other in sense.get_related("antonym")],
            }
            for relation, words in related.items():
                targets = {other.lemma().casefold() for other in words}
                targets = {target for target in targets if target.isalpha() and target != lemma}
                if targets:
                    tables[relation].setdefault(lemma, set()).update(targets)
    metadata_path = DATA / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    for relation, table in tables.items():
        name = f"{relation}.json.gz"
        payload = json.dumps(
            {key: sorted(value) for key, value in sorted(table.items())},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        compressed = gzip.compress(payload, mtime=0)
        (DATA / name).write_bytes(compressed)
        metadata["counts"][name] = len(table)
        metadata.setdefault("relations", {})[relation] = {
            "lexicon": SPEC,
            "builder": "wn-1.1.1-relations-v1",
            "sha256": hashlib.sha256(compressed).hexdigest(),
            "rule": "synset co-membership" if relation == "synonyms" else "direct sense antonym",
        }
        print(relation, len(table), len(compressed))
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
