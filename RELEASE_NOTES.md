# Tomba! Recompiled — v0.5.0-alpha

The **fast-and-faithful** release: loads are dramatically quicker, sprite layering is fixed, and the menus are smooth.

## ✨ What's new

### Much faster loading — on by default, with sound
Loading is now **blazing fast**. While a load is happening, the whole machine fast-forwards at your PC's full speed, then drops back to normal the instant it's done — so a load that used to take a few seconds finishes almost immediately. Crucially, this preserves all of the game's internal timing, so **audio plays through normally** (no mute, no cut, no glitches) and nothing desyncs.

This is **on by default** now. (In v0.4.0 the fast-forward briefly muted audio, so it shipped off — that mute is gone, so it's simply the better way to play.) You can still turn it off in **Settings → Turbo loads** if you prefer authentic loading times.

### Fixed sprite layering
On the OpenGL renderer, the character could appear **in front of** things he should be **behind** — an item block's "AP" letters, a save post. That's fixed: sprites now layer correctly, matching the original hardware (and the software renderer).

### Smoother menus
The title screen and **file-select / load menu** lag is gone — menus and save browsing are now snappy.

## 🔧 Under the hood
- Reworked the emulated CD timing so it stays authentic (the safe default), with the speed coming from the load fast-forward above instead of from speeding up the disc itself — which is what keeps audio and game logic correct.
- The OpenGL renderer now composites opaque sprites in their true draw order (the cause of the layering bug), with no impact on the scenery batching that keeps framerates high.

## 📝 Notes
- As always, **bring your own** PlayStation BIOS and Tomba! (USA, SCUS-94236) disc image — the launcher asks for each.
- Options live in the launcher's **Settings** and are remembered between launches.
- Widescreen remains **opt-in and experimental**.
- The overlay cache grows as you play; please keep `overlay_captures.json` private — it contains game code read from your disc (see README).
