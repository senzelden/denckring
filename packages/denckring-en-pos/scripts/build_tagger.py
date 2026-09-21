"""Train the shipped tagger from UD English-EWT and write `data/tagger.json.gz`.

Run from this package's directory:

    uv run python scripts/build_tagger.py

Two choices here are measurements, not preferences, and both are recorded in
ADR 0045 with the numbers this script printed when they were made:

**Punctuation is dropped from the training stream.** denckring tags what
`word_spans` yields, which is letters and internal apostrophes — never a comma or
a full stop. Training on a stream carrying punctuation would fit a model to
context that inference never supplies, and every accuracy figure measured that
way would be an overstatement of what the shipped tagger does. It also makes the
reported accuracy *lower* than the published figures for this feature set, which
are measured over a stream where roughly one token in eight is a punctuation mark
the tagger cannot get wrong.

**Iterations and the pruning threshold were chosen on `dev` and reported on
`test`, once.** Choosing on the test split and reporting the same number is the
way a held-out figure stops being held out.
"""

from __future__ import annotations

import gzip
import json
import random
import sys
import urllib.request
from collections import defaultdict
from collections.abc import Iterator
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from _download_integrity import verify_or_record
from denckring_en_pos.perceptron import START, Tagger, features

#: `features` is re-exported deliberately, not incidentally. `test_en_pos_build.py`
#: asserts `build_tagger.features is perceptron.features` — identity, because two
#: copies that agree on the cases a test happens to try are exactly the drift this
#: module layout exists to prevent — and `mypy --strict` forbids an implicit
#: re-export, so the name has to be declared public here for that check to be
#: expressible at all.
__all__ = ["AveragedPerceptron", "build_tagdict", "features", "main", "read_conllu", "train"]

BASE = "https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/master/"

#: UD English-EWT v2.18, released 2026-05-15. Pinned by digest: a build that
#: fetches an upstream dataset and never checks what it got is not reproducible
#: from repository state alone, and `master` is a moving branch.
DIGESTS = {
    "train": "d68e06122a702464c613076523d56740f047e5bbe89dd90ec32737e04d952143",
    "dev": "39239e0a60db3ae68f4b7036189f11b6692741d10ff8240dd91f74f2760d90f8",
    "test": "fa024f43dc5da3c5ac02563bc9bd0e974f46cbb1560823976a8f342a37dc494a",
}
TREEBANK_VERSION = "UD English-EWT v2.18 (2026-05-15)"

#: Both selected on `dev`. See the module docstring.
ITERATIONS = 12
PRUNE_BELOW = 0.5
SEED = 7

#: UD's tags for material `word_spans` never yields. Dropping them from training
#: is what matches the model to its input; see the module docstring.
PUNCT_UPOS = frozenset({"PUNCT", "SYM"})

OUT = Path(__file__).resolve().parent.parent / "src" / "denckring_en_pos" / "data"

Sentence = tuple[list[str], list[str]]


def fetch(split: str) -> str:
    url = f"{BASE}en_ewt-ud-{split}.conllu"
    data: bytes = urllib.request.urlopen(url, timeout=300).read()
    verify_or_record(data, source=url, expected_sha256=DIGESTS[split])
    return data.decode("utf-8")


def read_conllu(text: str) -> Iterator[Sentence]:
    """Yield one `(words, labels)` pair per sentence, label `"UPOS|VerbForm"`."""
    words: list[str] = []
    labels: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            if words:
                yield words, labels
            words, labels = [], []
            continue
        if line.startswith("#"):
            continue
        cols = line.split("\t")
        # Multiword-token ranges ("7-8") and empty nodes ("7.1") are not tokens
        # in their own right; taking them would double-count the words they span.
        if "-" in cols[0] or "." in cols[0]:
            continue
        upos, feats = cols[3], cols[5]
        if upos in PUNCT_UPOS:
            continue
        verb_form = "-"
        if feats != "_":
            for feat in feats.split("|"):
                key, _, value = feat.partition("=")
                if key == "VerbForm":
                    verb_form = value
        words.append(cols[1])
        labels.append(f"{upos}|{verb_form}")
    if words:
        yield words, labels


class AveragedPerceptron:
    """Trains the weights `perceptron.Tagger` reads. Training only.

    Averaging is the whole reason for the bookkeeping: a plain perceptron's final
    weights are whatever the last few sentences pushed them to, and averaging
    over every update is what makes the model stable enough that a rebuild from
    the same data and seed produces the same verdicts.
    """

    def __init__(self) -> None:
        self.weights: dict[str, dict[str, float]] = {}
        self.classes: set[str] = set()
        self._totals: dict[tuple[str, str], float] = defaultdict(float)
        self._stamps: dict[tuple[str, str], int] = defaultdict(int)
        self.updates = 0

    def predict(self, feats: list[str]) -> str:
        scores: dict[str, float] = {}
        for feat in feats:
            row = self.weights.get(feat)
            if row is None:
                continue
            for label, weight in row.items():
                scores[label] = scores.get(label, 0.0) + weight
        return max(sorted(self.classes), key=lambda label: (scores.get(label, 0.0), label))

    def update(self, truth: str, guess: str, feats: list[str]) -> None:
        self.updates += 1
        if truth == guess:
            return
        for feat in feats:
            row = self.weights.setdefault(feat, {})
            for label, delta in ((truth, 1.0), (guess, -1.0)):
                key = (feat, label)
                weight = row.get(label, 0.0)
                self._totals[key] += (self.updates - self._stamps[key]) * weight
                self._stamps[key] = self.updates
                row[label] = weight + delta

    def average(self) -> None:
        for feat, row in self.weights.items():
            for label in list(row):
                key = (feat, label)
                total = self._totals[key] + (self.updates - self._stamps[key]) * row[label]
                # Three places: the weights are a shipped table, and full float
                # repr would roughly double the file for digits no verdict turns on.
                row[label] = round(total / self.updates, 3)


def build_tagdict(sentences: list[Sentence]) -> dict[str, str]:
    """Frequent words with one near-universal tag, answered by lookup.

    Not an optimisation only: it keeps the perceptron from spending capacity on
    words that never vary, and it makes `the` and `of` immune to a surrounding
    sentence the model has misread.
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for words, labels in sentences:
        for word, label in zip(words, labels, strict=True):
            counts[word.lower()][label] += 1
    return {
        word: max(sorted(by_label), key=lambda label: by_label[label])
        for word, by_label in counts.items()
        if sum(by_label.values()) >= 20 and max(by_label.values()) / sum(by_label.values()) >= 0.97
    }


def train(sentences: list[Sentence], tagdict: dict[str, str]) -> AveragedPerceptron:
    model = AveragedPerceptron()
    for _, labels in sentences:
        model.classes.update(labels)
    rng = random.Random(SEED)
    data = list(sentences)
    for _ in range(ITERATIONS):
        rng.shuffle(data)
        for words, labels in data:
            prev, prev2 = START, START
            context = [word.lower() for word in words]
            for index, (word, truth) in enumerate(zip(words, labels, strict=True)):
                guess = tagdict.get(context[index])
                if guess is None:
                    feats = features(index, word, context, prev, prev2)
                    guess = model.predict(feats)
                    model.update(truth, guess, feats)
                prev2, prev = prev, guess
    model.average()
    return model


def score(tagger: Tagger, sentences: list[Sentence], name: str) -> dict[str, float]:
    """Joint accuracy, UPOS accuracy, and the finite-verb figures.

    The finite-verb triple is reported separately because it is the number
    `verbless_prose` actually rests on: a row that bars finite verbs is wrong in
    proportion to how often the tagger calls a finite verb something else, and an
    aggregate accuracy hides that inside twenty other labels.
    """
    total = joint = upos = 0
    true_positive = false_positive = false_negative = 0
    for words, labels in sentences:
        for truth, guess in zip(labels, tagger.tag(words), strict=True):
            total += 1
            joint += truth == guess
            upos += truth.split("|")[0] == guess.split("|")[0]
            truth_finite, guess_finite = truth.endswith("|Fin"), guess.endswith("|Fin")
            true_positive += truth_finite and guess_finite
            false_positive += guess_finite and not truth_finite
            false_negative += truth_finite and not guess_finite
    precision = true_positive / (true_positive + false_positive)
    recall = true_positive / (true_positive + false_negative)
    result = {
        "tokens": total,
        "joint_accuracy": round(joint / total, 4),
        "upos_accuracy": round(upos / total, 4),
        "finite_precision": round(precision, 4),
        "finite_recall": round(recall, 4),
        "finite_f1": round(2 * precision * recall / (precision + recall), 4),
    }
    print(f"{name}: " + "  ".join(f"{key}={value}" for key, value in result.items()))
    return result


def main() -> None:
    splits = {name: list(read_conllu(fetch(name))) for name in DIGESTS}
    train_data = splits["train"]
    counted = ", ".join(f"{split} {len(rows):,} sentences" for split, rows in splits.items())
    print(f"{TREEBANK_VERSION}: {counted}")

    tagdict = build_tagdict(train_data)
    model = train(train_data, tagdict)
    vocabulary = sorted({word.lower() for words, _ in train_data for word in words})

    weights = {
        feat: kept
        for feat, row in model.weights.items()
        if (kept := {lab: w for lab, w in row.items() if abs(w) > PRUNE_BELOW})
    }
    tagger = Tagger(weights, tagdict, sorted(model.classes), frozenset(vocabulary))
    print(
        f"classes {len(model.classes)}  tagdict {len(tagdict):,}  "
        f"features {len(weights):,}  vocabulary {len(vocabulary):,}"
    )
    dev = score(tagger, splits["dev"], "dev ")
    test = score(tagger, splits["test"], "test")

    blob = json.dumps(
        {
            "weights": weights,
            "tagdict": tagdict,
            "classes": sorted(model.classes),
            "vocabulary": vocabulary,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    # mtime=0, so a rebuild from the same inputs is byte-identical and a diff of
    # the shipped file means the model changed.
    packed = gzip.compress(blob, 9, mtime=0)
    (OUT / "tagger.json.gz").write_bytes(packed)
    (OUT / "metadata.json").write_text(
        json.dumps(
            {
                "generated": date.today().isoformat(),
                "source": (
                    f"{TREEBANK_VERSION}, https://creativecommons.org/licenses/by-sa/4.0 "
                    "- see LICENSE-UD and scripts/build_tagger.py"
                ),
                "training": {
                    "iterations": ITERATIONS,
                    "prune_below": PRUNE_BELOW,
                    "seed": SEED,
                    "punctuation": "dropped, to match denckring's word_spans stream",
                },
                "accuracy": {"dev": dev, "test": test},
                "counts": {
                    "tagger.json.gz": len(weights),
                    "tagdict": len(tagdict),
                    "vocabulary": len(vocabulary),
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT / 'tagger.json.gz'} ({len(packed):,} bytes)")


if __name__ == "__main__":
    main()
