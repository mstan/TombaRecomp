# Widescreen scene transitions

Mixed 3D scenes can place scrolling finite artwork behind terrain. The renderer
now requires sustained world-scale geometry plus natural overhang before letting
that terrain override the finite-backdrop 4:3 classification. Sparse props alone
do not widen a room. The existing narrow Villa policy is retained.

Event-title glyphs are UI even when they project through GTE. The title observes
the existing regional event-object pool and retains the preceding aspect until
the actual display flip, including the animation tail. It preserves both wide
worlds and deliberate 4:3 rooms; widescreen OFF remains unchanged. It does not
modify quests, camera scripts, animation duration, sounds or saved games.

EU1, EU2 original/Rev1 and Japan keep their independent checked MAIN/overlay
maps and live identity guards. USA uses the common native map. Source/byte checks
are not visual acceptance of every region, layout or campaign area. The title
change requires the matching shared renderer recovery correction.
