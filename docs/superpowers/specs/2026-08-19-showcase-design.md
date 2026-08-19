# The Stage — Design

**Status:** approved, awaiting implementation plan
**Date:** 2026-08-19
**Branch point:** `3ebfc5d` (152 catalogued · 126 implementable · 117 implemented · 117 validated)
**Where it lives:** `apps/explorer`, which is `Private :: Do Not Upload` and stays that way.
Nothing here enters the published distributions; the `[tool.hatch.build.targets.sdist]`
exclude added in `a8b289a` is what keeps it out.

## Goal

Two things the project cannot currently do, both of which need a browser.

**See that everything works.** `denckring eval` runs 344 golden cases across 117
procedures and prints a scoreboard. That is the right shape for CI and the wrong shape
for a person who wants to look at the thing and find the one row that is unhappy.

**Show what these procedures are.** The catalogue's value is that these are real
machines with real provenance, and prose does not carry that. Five scenes, recorded as
short loops, do — a reader watching Harsdörffer's rings turn understands the Denckring in
four seconds and no paragraph achieves that.

The two share a stack and nothing else. The board wants coverage; the scenes want to be
worth watching.

## Non-goals

- **Not public.** No hosting, no deployment, no abuse surface. The GIFs are the artefact
  that travels; the application stays local.
- **No build step.** FastAPI, Jinja2, htmx and CSS, as the explorer already is. The day
  this needs npm it becomes a separate repository — that boundary is the decision, not
  the framework.
- **No scene engine up front.** See *Approach* below.
- **No new library capability.** Every scene drives `check`, `apply` and the existing
  pack methods through the public API. A scene that needed core to change would be a
  scene making a claim the library cannot support, which is the one thing this must not
  do.

## Approach

**Bespoke scenes, shared shell only for chrome.** The five scenes move in genuinely
different ways: rings rotate, slips fall, a tablet lights, nouns slide down a dictionary,
refrains recur in place. A `Scene` protocol defined before any of them exists would be
structure invented at the desk — the mistake this repository has a documented practice
against. `form_report` was extracted from real sonnets after three of them were written;
the gloss comparison was chosen by running it against real gloss text. So: build the
rings and Ideenwürfeln concretely, and extract shared machinery when a third scene proves
it needs the same thing.

**Live calls, never pre-baked.** Every scene calls the library through htmx and renders
what comes back. A scene rendering a stored result would be a mockup, and a mockup
recorded as a demonstration is a lie about the software.

**Interactive, driven by hand.** Scenes do not autoplay. The recording is a person using
the thing.

## Routes

| Route | What it is |
| --- | --- |
| `/board` | Every procedure, live from `harness.run()`, green or red, each tile linking to its bench page |
| `/stage` | Index of the five scenes |
| `/stage/denckring` | Scene 1 |
| `/stage/ideenwuerfeln` | Scene 2 (takes `?corpus=` to switch register) |
| `/stage/arca` | Scene 3 |
| `/stage/n_plus_7` | Scene 4 |
| `/stage/ghazal` | Scene 5 |

Each scene posts to its own `…/act` endpoint returning an htmx fragment, following the
bench's existing `/p/{id}/check` shape.

`stage.html` is a second base template beside `base.html`: full-bleed, no bench
navigation, a fixed 1280×720 stage area so every recording is the same size, and a
caption strip. `?chrome=off` removes the caption and controls for a clean capture.

## The board

`harness.run()` already returns every golden case with its procedure, name and outcome,
and `harness.status()` returns the scoreboard. The board renders them as a grid: one tile
per procedure, green when all its cases pass, red naming the first failing case, grey for
a catalogued row with no implementation. The scoreboard line sits above it, the same
string `denckring status` prints.

This is deliberately thin. It is `denckring eval` with a body, and its whole reason to
exist is that a grid of 117 tiles is scannable and 344 lines of terminal output is not.

## The five scenes

### 1 · Der Denckring

Five concentric SVG rings carrying the transcribed parts from
`src/denckring/data/devices/harsdoerffer_1651.yaml` — 49 prefixes, 60 initials, 12
medials, 120 finals, 23 suffixes, as Cramer's transcription actually has them rather than
as Harsdörffer's own text announces them. Turning a ring by click or drag realigns it;
the aligned parts read inward to outward and form a candidate word; `check("denckring",
word)` runs on release and the verdict lands as a stamp. `apply()` drives a *turn it for
me* control.

A combination counter shows the true product of the ring sizes beside the 97,209,600 the
literature repeats. The catalogue row already records that the famous figure cannot be a
product of rings of 12 and 120 at all; putting the real number next to it, on a device
the viewer is turning with their own hand, is the argument made visible.

**Register:** Baroque. This is the scene that sets the visual language.

### 2 · Ideenwürfeln

Excerpt slips drawn from a corpus under one shared `domain`, falling onto a table where
the collision is the point. The Witzbox is the explorer's existing `witz` route: a model
reads the collision and says what the excerpts share, labelled on screen as a reading and
not a verdict. `ideenwuerfeln`'s own docstring and its catalogue row both say the Witz is
the step no program performs, and the scene must not blur that — it is the one place
where looking impressive and being honest could pull apart.

The scene runs against both corpora, which already carry the marker that switches it:

- `jean-paul-exzerpte.json` — `style: jean_paul`, 89,166 entries, Würzburg digital
  edition, private copy. Paper and copperplate register.
- `arxiv-exzerpte.json` — `style: modern`, 51,219 entries, each carrying `domain`,
  `source` and `headwords`. Clean card register.

One scene, two centuries, and the same procedure underneath both. Neither corpus is in
this repository and neither ever will be (ADR 0020); both are read from
`DENCKRING_CORPORA`, and the scene degrades to an explanatory placeholder when the
directory is empty.

### 3 · Arca musarithmica

A phrase is typed, measured in syllables, and the tablet for that length lights up; a
column is drawn from it and `check` confirms the pattern is one that tablet offers.

The scene states on screen that the columns stay opaque. ADR 0021 decided to implement
Kircher's indexing and leave his music alone, and the scene demonstrates exactly that —
the machine that measures and looks up, with the contents left where Kircher put them.
The restraint is the content, not an omission to cover.

### 4 · N+7

The source sentence above, each noun dropping down a scrolling column of the noun list
exactly seven entries and landing on its replacement, the result assembling below.
`apply()` produces it and `check()` proves it, both visible.

Caption: *cat → catacomb*, and that it was *catafalque* until the Open English WordNet
migration. A procedure is only as stable as the dictionary underneath it, and this is the
scene where that is a feature of the demonstration rather than a footnote.

### 5 · Ghazal

Couplets with radif and qafia lighting up as they recur, and a couplet that breaks the
scheme marked inline through the bench's existing violation highlighting. Deliberately
the quiet, typographic scene after four mechanical ones.

## Testing

Visual appearance is not tested. The claims underneath it are.

- **Route smoke tests.** Each scene renders, contains its stage element, and survives
  `?chrome=off`. The board renders with the scoreboard string in it.
- **One claim test per scene.** The word the rings scene builds satisfies `denckring`;
  the N+7 output satisfies `n_plus_7` against its source; the arca phrase's pattern is
  one the tablet for its length offers; the ghazal example fails on the couplet it is
  meant to fail on. A scene that dramatises a result the library does not produce is the
  failure mode that matters, and it is cheap to catch.
- **Corpus-absent path.** Scene 2 renders its placeholder when `DENCKRING_CORPORA` is
  empty or unset, since that is the state every machine except this one is in.

These live in `apps/explorer/tests`, which raises the thing to fix while we are here:
**the explorer has 957 lines and a test file CI has never run.** A `explorer` job is
added to `ci.yml` — `uv sync --project apps/explorer` and `pytest` — as part of this
work. It is cheap and it is the difference between a tested app and an aspiration.

## Risks

**The visual register is the part that can miss.** Baroque spans restrained letterpress
to full copperplate pastiche, and the wrong end reads as kitsch. Mitigation: scene 1 is
built first, in two or three concrete looks, and reviewed before the other four commit to
a language.

**Scene 2 depends on private corpora.** They exist on the author's machine and cannot be
committed. Anyone else running the explorer sees a placeholder. This is a property of
ADR 0020 rather than a defect, but it means scene 2 cannot be verified by CI, only by
the person who holds the files.

**The Witzbox is the honesty risk.** A model's reading rendered next to five verdicts
invites the viewer to read it as a sixth. Labelling is the mitigation, and it is a
requirement of the scene rather than a nicety.
