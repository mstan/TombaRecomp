Hybrid Controller

By mstan

This default-disabled feature switches Tomba's controller presentation mode
according to the player's most recent movement input:

- Touching the D-pad presents a digital PlayStation controller, preserving
  Tomba's original D-pad movement sensitivity.
- Moving the left stick presents an analog DualShock and sends its variable
  stick position.
- The most recently engaged control wins, without adding Hybrid back to the
  generic controller settings.

The implementation is trusted code compiled into TombaRecomp. This package
contains only metadata selecting the stable tomba.hybrid-controller plugin id.
