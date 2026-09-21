# denckring-en-pos

An English part-of-speech tagger for
[denckring](https://github.com/senzelden/denckring), trained on the
[Universal Dependencies English Web Treebank](https://github.com/UniversalDependencies/UD_English-EWT).

```console
pip install denckring[pos]
```

It supplies one capability, `pos`: a reading of each token **in its sentence**,
as a universal part-of-speech tag and, for verbs, UD's `VerbForm` feature. Two
rows need it and could not be built without it — `verbless_prose`, which bars
finite verbs while living on participles, and `homosyntaxism`, which keeps a
source's word classes and replaces its words.

Every other English capability here answers about a word on its own. This one
cannot: `walks` is a noun in *the evening walks were long* and a finite verb
in *she walks home*, and no lookup decides between them.

It registers no entry point. `denckring-en-data` owns the `en` language and its
`pack()` factory composes this distribution in when it is importable, because
`denckring` refuses two packs claiming one language (ADR 0013, ADR 0045).

## What it is, and what that costs

An averaged perceptron over the feature set Honnibal published for
`textblob-aptagger` — the standard cheap tagger. Pure Python at inference time
and no model download, which is why, unlike the usual tagger, it can sit in
denckring's test matrix including the free-threaded build.

**It is a model, so its answers are estimates.** There is no exact tier behind it
the way `syllables.dictionary` stands behind `syllables.heuristic`, so the
honesty is carried per token instead: `PosTag.known` says whether the form
appeared in the training data at all, and a procedure that reports a violation on
a word where it did not says so in the violation.

Measured on the treebank's held-out **test** split (hyperparameters were chosen
on `dev` and the test split read once):

| | |
|---|---|
| tokens | 21,885 |
| joint accuracy (UPOS + VerbForm) | 0.9269 |
| UPOS accuracy | 0.9342 |
| finite verb — precision | 0.9482 |
| finite verb — recall | 0.9498 |
| finite verb — F1 | 0.9490 |

The finite-verb row is reported separately because it is the number
`verbless_prose` actually rests on, and an aggregate accuracy hides it among
nineteen other labels.

These figures are **lower** than the published ones for this feature set, and
deliberately so: the model is trained and scored on a punctuation-free token
stream, because that is what denckring's `word_spans` hands it. Scoring over a
stream where roughly one token in eight is a punctuation mark that cannot be got
wrong would be measuring something the shipped tagger never does.

## Why a separate distribution

The treebank is CC BY-SA 4.0, where `denckring-en-data` carries a different mix.
ADR 0013 quarantines a data licence in its own distribution. The shipped weights
are treated as an adapted work under share-alike — see `NOTICE`, which records
why, and that the question is one on which readings differ.

## Rebuilding the model

```console
cd packages/denckring-en-pos && uv run python scripts/build_tagger.py
```

Fetches the three splits, verifies each against a pinned SHA-256, trains, and
writes `tagger.json.gz` and `metadata.json`. About twenty seconds. The archive is
written with `mtime=0`, so a rebuild from the same inputs is byte-identical and a
diff of the shipped file means the model genuinely changed.

See ADR 0045 for the decision and the costs it accepts.
