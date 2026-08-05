Tomba CD Speed
==============

Makes the emulated CD drive deliver data faster. Loads get shorter, but the
game keeps running at its normal speed -- nothing moves faster than it should.

This is the mod to use if you want quicker loads without the game speeding up
during them. The separate "Fast Loading (host pacing)" mod does speed the game
up while loading, which is safer for the emulator but disturbs routes that
depend on real-time behaviour during a load.

Settings
--------
CD speed multiplier   1 is authentic 1x. Higher divides the sector delay, so
                      4 means sectors arrive four times sooner. 2-32 is the
                      useful range; any positive value is accepted so you can
                      find the highest speed this game tolerates.

Instant               Ignores the multiplier and uses the bounded instant
                      scheduler instead. Fastest and riskiest.

Instant sectors/frame Only used with Instant. Caps how many sectors may be
                      delivered per frame; lower is gentler.

Notes
-----
Raising CD speed changes WHEN the game receives CD interrupts. Most of the
game does not care, but a load that stalls or a cutscene that misbehaves means
you have gone past this game's limit -- lower the value or turn the mod off.

FMV and CD audio always play at authentic timing regardless of this setting,
so movies and music are never sped up or pitch-shifted.
