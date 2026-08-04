Tomba Fast Loading
==================

This feature is disabled by default.

The Host pacing choices are recommended. They run complete loading frames
faster in wall-clock time while preserving guest-visible CD timing, callbacks,
interrupts, and game logic. Acceleration stops on the first frame after the
sustained load ends.

The CD timing choices are experimental. They deliver emulated CD events sooner,
which can expose timing assumptions in the game. Start with 2x, and disable the
feature if a load, audio stream, or speedrun setup behaves differently.

Because these are values in one dropdown, host turbo and CD timing cannot be
enabled at the same time.
