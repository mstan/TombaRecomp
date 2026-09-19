Tomba Fast Loading
==================

This feature is disabled by default.

When enabled, it accelerates the host wall-clock pacing only while Tomba is in
a sustained non-movie data load. Every guest frame, CD deadline, interrupt,
callback, and game-logic step still runs. Acceleration stops immediately when
the load predicate clears so it does not intentionally spill into gameplay.

Choose 2x, 4x, 8x, or 16x for a bounded rate, or Uncapped for the fastest rate
the host computer can sustain.
