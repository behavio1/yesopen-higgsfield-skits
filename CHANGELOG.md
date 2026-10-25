# Releases

## 2026.10.26-rc.1 — H3 performance references

Adds an optional H3/ComfyUI route for naturalness work: identity image + 24 fps performance video +
optional authorized voice. Structured direction covers intention, subtext, emotion, delivery, gesture,
listening, continuity and reaction hold. Full 20-step baseline; existing workflows remain unchanged.

Offline preparation records source/prepared hashes, permissions, actual reference-frame consumption and
workflow settings. Read-only preflight checks nodes/models; explicit submission persists the prompt ID.
Ambiguous submissions stop for reconciliation; timeout recovery reuses the original job. Shared coordinator
sessions are explicitly unsupported by this runner. No Hypit code or hosted API dependency is included.

Validation on macOS, Python 3.11.12, ComfyUI 0.35.0 in CPU mode, PyTorch 2.14.1:

- 69 tests passed, including 12 new H3 tests and 6 existing live ComfyUI transport tests; none skipped in
  the final clean-release run.
- Both H3 graph variants accepted by real ComfyUI validation using placeholder model filenames; queued
  validation was cancelled, with no model inference. This is structural proof only.
- Real media upload, video/audio load, demux, mux, export and download passed for both reference variants.
- FFmpeg preparation verified 24 fps, bounded length and removal of the performance video's soundtrack.
- Existing rendering scripts and examples are unchanged by this release.

**Pending:** H200 model inference, actual deployed-server compatibility, naturalness/lip-sync/voice
acceptance, and comparison against an image-only control. No GPU was rented or paid generation started.
This is a release candidate, not a claim of improved video quality. The installed production server has not
been changed. Based on committed `feat/shared-server-pipeline` cd514b9; unrelated local edits were excluded.

Start at [H3 performance references](references/h3-performance.md).
