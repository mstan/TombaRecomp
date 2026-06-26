# Tomba! Recompiled — v0.6.2-alpha

A **diagnostics** release. There are no gameplay changes here — the focus is on capturing far better information when the game freezes, so the rare hangs that are hard to reproduce can actually be tracked down.

## 🩺 Better freeze reports

Some freezes (notably the intermittent hang when talking to the small dwarf child in the Dwarf Village — issue #1) are **rare and hard to reproduce**, which makes them hard to fix from a single report. This release makes every freeze report dramatically more useful:

- **The small `psx_freeze_heartbeat.json` now captures the decisive state.** It records the CPU register file and the console's 1 KB scratchpad — the fast working memory where the game keeps its per-frame logic — at the moment of the hang. Previously that detail only lived in a 50+ MB dump that's too big to attach to a GitHub issue; now it's in the small file you *can* upload.
- **A new "logical hang" detector.** A whole class of freeze — where the picture and audio keep running but the *game* is stuck in a loop — slipped past the old freeze detection entirely. These are now identified and labelled (`spin_freeze`) in the report.

## 🙏 If you hit a freeze

Please open (or comment on) a GitHub issue and attach **`psx_freeze_heartbeat.json`** and **`psx_last_run_report.json`** from the game folder, along with a note on **where** in the game it happened. With this build, those two small files are usually enough to pinpoint the cause — no giant uploads needed.

## 📝 Notes
- This is purely an observability change; it ships in the normal (production) build at negligible cost — one background thread writing one small file that's overwritten in place (no log growth).
- As always, **bring your own** PlayStation BIOS and Tomba! (USA, SCUS-94236) disc image — the launcher asks for each.
- Options live in the launcher's **Settings** and are remembered between launches.
- Widescreen remains **opt-in and experimental**.
- The overlay cache grows as you play; please keep `overlay_captures.json` private — it contains game code read from your disc (see README).
