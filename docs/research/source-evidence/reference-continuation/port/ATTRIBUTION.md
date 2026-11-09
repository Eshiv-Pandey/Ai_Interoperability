This is an authored development port of the official `a2aproject/a2a-samples` number-guessing Carol application at commit `6603ba3f2c31a7ef33e70b9d8b5b5f8be42ac9a3`, principally `agent_Carol.py` and `utils/game_logic.py`. The original files remain byte-identical in `../runtime/original-number-game/`; exact hashes are in `../runtime/original-source-manifest.json`.

The upstream repository's Apache-2.0 license is preserved in `../upstream-LICENSE.txt`. The sample's own README also states “Released into the public domain” at line 90; both primary notices are retained. This port is local research work, not an upstream release or an unchanged-source result.

The port uses the already installed official `@a2a-js/sdk 1.1.0` from the pinned AmirK-S checkout. It installs no dependencies and calls no model. The adjacent change map identifies event, wire and representation adaptations. The global history field and nonempty-reference dispatch guard remain application behavior. No referential integrity, receiving-principal authority or protocol-mandated dependency is inferred.

The prospective controls use one source-valid history entry and the identical `Well done!` answer. This avoids shuffle-order variation. JSON serialization and language-specific formatting on other inputs are not asserted byte-identical to Python. No new native or bridge capture has been executed for this port.
