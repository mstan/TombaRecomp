# Tomba! Recompiled — v0.4.0-alpha

The **movies-and-loading** release: skip *any* FMV — even the ones you couldn't before — and choose how loading screens sound.

## ✨ What's new

### Skip every movie (improved FMV skip)
"Skip FMVs" now ends a video the **game's own way** — by telling the movie player it has reached its final frame — so it works on **every** movie, including the ones the game never let you skip with a button: the Whoopee Camp logo, the opening, and in-game cutscene movies. Turn it on in the launcher (**Settings → Skip FMVs**); it's off by default.

### Turbo loads is now a toggle — and off by default
Loading screens used to always run in "turbo": the game fast-forwarded through them, which briefly **muted the audio**. That's now a launcher option (**Settings → Turbo loads**), and it's **off by default** — so music and sound **play continuously through loading screens**, with no cut or fade. Loads stay quick because disc reads are already instant. Prefer the old behavior? Switch **Turbo loads** on to fast-forward them at the cost of a brief audio mute.

## 📝 Notes
- As always, **bring your own** PlayStation BIOS and Tomba! (USA, SCUS-94236) disc image — the launcher asks for each.
- Both new options live in the launcher's **Settings** and are remembered between launches.
- Widescreen remains **opt-in and experimental**.
- The overlay cache grows as you play; please keep `overlay_captures.json` private — it contains game code read from your disc (see README).
