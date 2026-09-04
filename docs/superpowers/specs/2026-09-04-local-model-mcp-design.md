# denckring — a local model driving the MCP server

Date: 2026-09-04
Status: approved, not implemented

## Purpose

Give the explorer a page where a **local** model uses denckring's own MCP tools to
check and generate constrained text, and show the tool calls as they happen.

Two things make this worth building beyond the demonstration. The MCP server has
never had a consumer inside this repository — it is written, tested against its own
tool functions, and swept by hand, but nothing here has ever spoken the protocol to
it. And the explorer's two model-driven surfaces (`witz.py`, `ars.py`) both call the
Anthropic API directly, with `anthropic.Anthropic()` instantiated inline in each, so
there is no seam at which a second provider could be added.

## The measurements that chose the design

All measured 2026-09-04 on this machine.

### Only one local model can call tools

| model | tools | note |
|---|---|---|
| `gemma4:e4b-it-q4_K_M` | **yes** | correct call, first try, at temperature 0 |
| `sauerkraut-nemo-12b` | no | Ollama: `does not support tools` |
| `teuken-7b` | no | same |
| `apertus-8b` | no | same |

The three that refuse are exactly the German and European multilingual models that
would otherwise suit this project. The refusal is Ollama's, from the model's template,
and arrives as HTTP 400 rather than as a soft failure — so it can be reported
precisely rather than guessed at.

### The whole loop already works

A spike drove `denckring-mcp` over stdio with the `mcp` SDK, handed its four tools to
gemma4, and got back a correct call and a correct answer:

```
CALL   check_text {"lang":"de","params":{"digits":"7353"},"procedure":"calculator_word","text":"Esel"}
RESULT {"procedure":"calculator_word","satisfied":true,"score":1.0,...}
FINAL  The German word 'Esel' is a calculator word for the digits 7353.
```

### Spawning the server per request is cheap enough

| | spawn + initialize | first tool call | second |
|---|---|---|---|
| run 1 | 0.37 s | 0.19 s | 0.11 s |
| run 2 | 0.37 s | 0.16 s | 0.11 s |
| run 3 | 0.36 s | 0.18 s | 0.12 s |

370 ms against a model turn measured in seconds. A persistent session would save an
invisible fraction and buy a lifecycle to get wrong — a subprocess to reap, a
reconnect path, and a server that keeps whatever it imported at start-up, which is the
staleness CLAUDE.md already warns about for the hand-driven server.

## Decisions

### D1. A real MCP client, over stdio, spawned per request

`mcp.client.stdio.stdio_client` against `denckring-mcp`, one session per request,
closed when the turn ends. Importing the tool functions directly would be simpler and
would not be what the page claims: the point is that the protocol works, and a page
that says "via MCP" while calling Python functions in-process would be the same class
of untruth as a definition promising what its checker cannot do.

Cost: the explorer gains `mcp[cli]>=2` as a dependency, and the page cannot run unless
`denckring-mcp` is on `PATH`. Both are stated on the page when absent rather than
raised.

### D2. gemma4 only, and the other three are named with Ollama's own reason

The page lists all four installed models. The three that cannot call tools are shown
disabled, with the reason quoted from Ollama rather than paraphrased. Hiding them
would leave a German-focused project silently offering only its one English-first
model, and a reader would not learn why.

Cost: the most fitting models for this project's languages are the ones it cannot use,
and the page says so plainly instead of hiding it.

### D3. A provider seam, not a rewrite of `witz.py` and `ars.py`

A new `explorer/models.py` holds the Ollama client. `witz.py` and `ars.py` are left
alone: they stream, they use Anthropic's thinking blocks, and rewriting two working
surfaces to share an abstraction with one new one would be refactoring beyond what
this needs. The seam is that a second provider now exists and is separate.

Cost: there are now two model paths in the app with no common interface. That is
honest — they do different things — but a third provider should prompt the
generalisation this one deliberately skips.

### D4. The transcript is the artefact

The page shows each tool call, its arguments, and the raw JSON that came back, then
the model's closing sentence. Not a chat window: the interesting content is that a
7-billion-parameter model on this machine produced a well-formed call against a schema
it was handed at runtime, and that denckring answered it.

## Components

### L1. `explorer/models.py` — the Ollama provider

`available() -> list[LocalModel]` reading `/api/tags`, each with `name`, `tools: bool`
and `reason: str`. Tool support is asked of Ollama by attempting a one-shot call with
a trivial tool array and reading the error, because `/api/tags` does not report it;
the result is cached for the process, since installing a model mid-session is not a
case worth a cache invalidation path.

`chat(model, messages, tools) -> dict` posting to `/api/chat` with
`stream: false, temperature: 0`. Failures return a problem string rather than raising,
the rule `witz.py` states: this sits beside a verdict and a stopped daemon should not
take the page down.

### L2. `explorer/agent.py` — the MCP client and the turn loop

`run(question, model, max_turns=4) -> Transcript`. Opens a stdio session against
`denckring-mcp`, lists tools, converts each to Ollama's function shape, and loops:
ask, execute any tool calls, feed results back, stop at a text answer or at
`max_turns`.

**The SDK's attribute is `input_schema`, not `inputSchema`.** The wire format uses the
camel-case name and the Python object does not; the spike failed on exactly this. A
comment records it, because the error — `'Tool' object has no attribute 'inputSchema'`
— arrives at the line that builds the tool list, far from anything that looks like a
protocol concern.

`Transcript` carries `steps: list[Step]` (name, arguments, result) and either an
`answer` or a `problem`.

### L3. The page

`GET /agent` and `POST /agent/ask`, following the stage routes' shape: prepare in
`agent.py`, render from a template, swap a fragment on the POST. Preset questions as
buttons so the page can be driven on camera without typing, one of which exercises
`check_text` and one `apply_procedure` — the two halves the GIF needs to show.

## Testing

- **The tool-support probe is pinned against a fake Ollama**, not the live daemon:
  the suite must pass on a machine with no models installed. One test asserts that a
  model Ollama rejects is reported with its reason rather than dropped.
- **The turn loop is tested against a fake session and a fake model**, so a tool call,
  a tool result and a closing answer are exercised with no subprocess and no daemon.
- **One test asserts the page renders with the daemon absent**, showing the reason.
- **`input_schema` is pinned by a test** that would fail if the conversion reached for
  the camel-case name, since that is the one error this design already made once.
- Live integration is deliberately **not** in the suite: it needs a 9.6 GB model and a
  running daemon, and CI has neither.

## Out of scope

- Rewriting `witz.py` or `ars.py` onto the new seam (D3).
- A non-tool-calling path for the three German models (D2). It would need prompted
  JSON and a parser, and small models emit malformed JSON often enough that the page
  would spend most of its surface on error display.
- Streaming. The transcript is the artefact and it is short.
- Any change to the MCP server itself.

## ADR

No ADR. This adds a consumer and a provider; it changes no rule about what the
catalogue means, no capability, and no verdict. ADR 0033's D5 test — does this bind
future work — is answered no.
