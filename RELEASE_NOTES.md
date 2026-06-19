# Tomba! Recompiled — v0.3.0-alpha

The **stability** release: the long-run freeze is fixed, the controls feel snappier, and widescreen looks cleaner.

## ✨ What's new

### No more long-play freeze (major fix)
Earlier builds could **hard-freeze after a long session or extended idle** — a slow internal resource leak that eventually wedged the game. That's **fixed at the root**: the recompiler now uses a continuation-passing call model that keeps the host stack flat no matter how long you play. Leave the game running, or play for hours, without the creeping freeze.

### Snappier controls (lower input lag)
Your input is now read **right before each frame is drawn** instead of up to a frame earlier, so the game responds to the stick and buttons up to **~a frame (≈14 ms) sooner**. This is on automatically. Advanced users can also choose a **vsync mode** (on / immediate / adaptive) in the game config to trade a little tearing for even lower display latency on a fast monitor.

### Cleaner widescreen
The **far-background void** in 16:9 — the missing sky band and flower-field along the screen edges — is now **filled in** properly, on both the OpenGL and software renderers. Widescreen is still experimental, but the most noticeable seam from v0.2.0 is gone.

### More flexible controller handling
New **Hybrid** controller mode (now the default): the game auto-switches between analog and digital based on how you're playing — nudge the stick for variable-speed analog, tap the D-pad for crisp digital — with a **3-way selector per player** (Hybrid / Analog / Digital) in the launcher.

### Under the hood
- The game now compiles itself to fast native code **in the background while you play**, so the brief first-time hitches when entering new areas are smoother.

## 📝 Notes
- As always, **bring your own** PlayStation BIOS and Tomba! (USA, SCUS-94236) disc image — the launcher asks for each.
- Widescreen is **opt-in and experimental**.
- The overlay cache grows as you play; please keep `overlay_captures.json` private — it contains game code read from your disc (see README).
