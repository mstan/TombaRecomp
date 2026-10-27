# Shared PS1 memory-card manager

Tomba opts into the optional psxrecomp/recomp-ui card editor with
`PSX_MEMORY_CARD_MANAGER` (default ON here, overridable OFF). The implementation
and UI live entirely in those dependencies; Tomba adds no parser or editor copy.
Existing official dependency pins still build but do not show the editor until
the engine and UI capability changes are merged and officially pinned.

The pre-boot Memory Cards panel opens two side-by-side card drafts. Open and
Refresh only read. Copy/drag/import/delete edit drafts; Save explicitly confirms
a validated update with verified backups; Save As requires a new file. Existing
game card assignments remain unchanged. Close other games/editors first.
The initial writable implementation is Windows/local-NTFS only and needs two
backup folders on distinct volumes, selectable in the manager. It is unavailable
from an active game's in-session launcher. See the dependency documentation for
formats, safeguards and tests.

This opt-in applies to the common build inherited by regional targets. It changes
no US/EU/JP game code, mod catalog, personal defaults or release files. The private
UI3 predecessor was user-tested in EU1; no new campaign/regional playthrough is
claimed for this dependency-only integration. Merge after the engine/UI PRs and
choose official dependency pins, without relying on unmerged fork commits.
