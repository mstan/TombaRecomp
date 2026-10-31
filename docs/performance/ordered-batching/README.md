# Existing ordered OpenGL batching adoption

Fresh enhanced Tomba builds select the engine's existing `HLE` textured
batching tier. It keeps painter order while grouping compatible opaque and
semi-transparent primitives; subtractive blending and mask checks retain
isolation. No renderer implementation changes here.

Use the normal supported build/regeneration flow. Pass
`-DPSX_GL_BATCH_IMPL=LLE` for the original tier. Fresh
`-DPSX_EXECUTION_PROFILE=REFERENCE` configurations default to LLE; explicitly
pass both flags for a reference recipe. Use separate build directories for
profiles/tiers: existing cache selections, including explicit LLE overrides,
are preserved.

The production LLE/HLE/HLE/LLE village/AP field block used the same half-core
CPU budget, PGXP off, 5x resolution, bilinear filtering and default 4:3 settings.
Its result is **neutral/inconclusive in magnitude, with positive paired
support**. CPU and cycle ranges overlap and host CPU means vary from 21.05% to
54.72%. Both adjacent CPU comparisons favor HLE; the block does not establish
a proven percentage gain. Both choices maintain approximately 60 Hz, with zero
timed audio bridge underruns/overflow and no reproduced regression here.
Original host gates pass. No further timing block is needed to chase magnitude.

[tomba.json](tomba.json) contains all four individual results, the original
selected CPU/host/frame/feature samples, seven-field NVML samples, audio and
mechanism counters, source/binary/fixture identities and raw-file hashes.
Complete original observations remain retained by the campaign; this public
sample subset does not replace or rewrite them.

Existing source-owned real-GL checks pass 331 checks at scale 1 and 340 at scale
4, including exact supersampled HLE/LLE equality for tested filter/mask cases
and draw-to-sample feedback. A separate LLE blend oracle passes 22 checks against
software/formulas. These are bounded renderer contracts.

Both actual production choices pass two current-build eight-boundary warm
restore/resimulation windows and resume field progress. All 19 serialized
sections match byte for byte between LLE/HLE at boundaries 900 and 1060,
including GPU, native VRAM and MDEC. Both retain identical RAM restore drift
(8/8 then 1/8); this shared caveat has no causal attribution or netplay waiver.
Native output equality does not establish every high-resolution presentation
pixel. Final combined regression, rewind, rollback, common-profile checks and
owner playcheck remain pending. No merge or release is implied.
