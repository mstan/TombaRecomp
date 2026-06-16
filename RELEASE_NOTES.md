# Tomba! Recompiled — v0.2.0-alpha

The biggest update yet: **widescreen**, a much better **controller** experience, and the game now **remembers your settings**.

## ✨ What's new

### Widescreen (experimental 16:9)
Play in 16:9 with a genuinely **wider field of view** — you see more of the world to the sides, not a stretched-out picture. Turn it on in the launcher under **Settings → Widescreen** (it works on both the OpenGL and software renderers).

It's experimental, so expect rough edges: some menus/HUD elements and the occasional background seam can look a little off, and ultrawide (21:9) isn't ready yet. Leave it at 4:3 for the most faithful look.

### Better controller support
- **Analog stick and D-pad both work at the same time** — no controller mode to toggle. Push the stick gently to walk and harder to run (true variable speed); the D-pad keeps working too.
- **DualShock / analog is on by default** now (both player slots).
- New **analog stick deadzone** slider in the launcher (**Settings → Controller**) if your stick drifts or feels too touchy.

### Remembers your settings
Your in-game **OPTION** choices — **text speed, sound, vibration, screen adjust** — now **stick between launches**. Set text speed to Auto and turn vibration off once, and that's how it'll be every time you boot. No more re-doing it on every launch.

### Smoother performance
- The OpenGL renderer is more efficient now, clearing up slowdown in busy areas (and in widescreen).
- The game converts more of itself into fast native code as you play **and reuses that work on later launches** — so spots that hitched the first time run smoothly afterward.

### Even better crash reports
Building on the last release's crash safety net: reports now **name the exact function** involved in the rare runaway-recursion crash, and a new guard catches a class of stack-overflow crashes **gracefully** (writing a report) instead of just closing. If you hit the rare Underground Maze / seesaw crash (issue #1), the report now has what's needed to fix it — please attach `psx_last_run_report.json`.

### Launcher polish
- The two **Player cards stay an even 50/50 size** when you pick a controller (they no longer go lopsided).

## 📝 Notes
- As always, **bring your own** PlayStation BIOS and Tomba! (USA, SCUS-94236) disc image — the launcher asks for each.
- Widescreen is **opt-in and experimental**.
- The overlay cache grows as you play; please keep `overlay_captures.json` private — it contains game code read from your disc (see README).
