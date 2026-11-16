# Preloaded Tomba mods

These packages describe features whose trusted native implementations are
compiled into TombaRecomp. Seamless Loading is enabled by default; the other
features are opt-in. An explicit player choice to disable a feature is preserved.
Package archives do not contain or load native code.

Tomba keeps its original frame rate. The retired Temporal Frame Blending
package and its controls are no longer included.

Fast Loading is hidden while Seamless Loading covers loads; it still appears
for a player who already enabled it, so it can be turned off. The framework's
CD Speed and host-paced Fast Loading packages are not staged for Tomba
(`EXCLUDE_BUILTIN_MODS` in `CMakeLists.txt`); every other framework mod is.

Seamless Loading retains its original `tomba.experimental.seamless` package ID
and `resident-assets` feature ID so existing player selections still apply.
