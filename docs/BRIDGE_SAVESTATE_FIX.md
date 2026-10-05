# Dog bridge and quick-save softlocks (v0.15.2)

The custom renderer widened 80022E44's draw admission, which also sets actor
byte +1. Both story interpreters (return PCs 8003D8B8 and 8003E828) call this
routine to query visibility. The dog script uses that answer to advance its
jumps. With wider bounds it continued past the bridge and fell indefinitely,
leaving player input locked. The guarded query adapter keeps the original draw
queue effects but supplies the retail unsigned-halfword visibility predicate to
scripts. It applies to both interpreters, independent of Seamless Loading.

Seamless Loading's register-preserving guest adapter used the scene tick's own
epilogue, 8001AD0C, as its nested return contract. Existing quick-saves captured
that return on the guest stack without the host continuation. Restoring them
could execute the epilogue twice and pop the caller's frame. Guarded recovery
resumes the verified retail caller at 8001A9C0. Host adapter scopes now defer
snapshots; scheduler escapes release abandoned scopes.

Cold restores also need the game-start handoff latch and mod hooks installed
before redispatch. The runtime serializes the latch in an optional section,
infers old states from the loaded entry bytes, and invokes enabled plugins'
restore callbacks without activation or a gameplay tick. Tomba shares one
dispatch chain owner so independently selected plugins cannot recursively wrap
each other.

Validation used copied user saves on OpenBIOS/OpenGL: the failing wide cutscene
completed, input unlocked, and walking continued across the bridge. Startup and
warm restores of the existing bridge state and a new save/load round trip
returned to playable gameplay. Focused tests cover visibility edges, nested
snapshot scopes, scheduler escape reset, restored handoff side effects, and mod
restore callback ordering. No user saves were overwritten.

The release retains the validated framework lineage plus this fix, preserving
the v0.15.0/v0.15.1 codegen key and cache compatibility. The generic runtime fix
is also integrated into framework master; unrelated framework upgrades are not
part of this release.
