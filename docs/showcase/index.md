# The whole thing, in forty seconds

The catalogue, every machine on the stage **being driven**, and a local model
checking and generating through this package's own MCP server.

![denckring: the catalogue, the stage, and a local model over MCP](denckring-overview.gif)

Recorded against a real Chromium and a real server by
`apps/explorer/tests/browser/overview-gif.mjs`, and assembled by
`scripts/build_overview_gif.py`. Nothing in it is staged: the verdicts are the
library's own, and the two tool calls at the end were made by
`gemma4:e4b-it-q4_K_M` running on the machine that recorded it, against
`denckring-mcp` over stdio.

The three parts:

**The board.** All 156 catalogued rows, with the golden cases each one carries
and — in red — what an unimplemented row is waiting for.

**The stage.** Nine machines, each 1280×720, and each one actually turned rather
than photographed: the rings spin and stagger inward, the blades cut, the 426
flaps clatter, the ladder's rungs arrive one by one, and the calculator turns
over. Ideenwürfeln throws three excerpts filed under *control* from three
distinct fields — fluid dynamics, soft matter, and the epidemiology of rabies —
which is the collision the procedure exists for. The machines are: Harsdörffer's
*Denckring*, Jean Paul's excerpt boxes, N+7, Queneau's *Cent mille milliards*,
Carroll's Doublets, the cut-up, a Llullian figure, Enzensberger's
*Poesie-Automat*, and a pocket calculator turned upside down.

**Over MCP.** `check_text` on a German calculator word, then `apply_procedure`
on an English anagram, with the raw JSON the server sent back.
