# Maintained application snapshot

This is a source-only copy of the CPU portable implementation, with complete frontend, backend, companion, scene compiler, NSGA-II and governed EAG-APR source. Runtime algorithms have not been rewritten. Historical unused dataset utility code and desktop-specific launch configurations were excluded. The staged integrity manifest is regenerated for these deliberate exclusions.

Windows x64: Python 3.12 and Node 22 on PATH. Run `./setup.ps1`, then `./start.ps1`; stop with `./stop.ps1`. Setup downloads pinned dependencies and creates ignored environments/build/state directories. No environments, datasets or model weights are committed. See `../docs/SETUP_AND_CAPABILITY_LIMITS.md` before using the app.

This source review snapshot is not a complete real-venue deployment. The static controlled Twin registration fixture contains stale desktop paths; KNOX compiler image/source admission and fresh inference output relocation have unresolved defects. The verified positive flow is the controlled Scene compiler sidecar, SQLite CRUD and separate EAG-APR controlled lifecycle. Sidecar results do not become canonical backend approved layouts automatically.
