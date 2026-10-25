# H3: performance references on our own ComfyUI GPU

Version 2026.10.26. Target: MiniMax H3 Ref2VA on the existing rented GPU, including H200.
This route addresses stiff acting and weak emotion. It does not require Hypit or its hosted providers.
It does not claim that adding a reference guarantees natural results.

## What is connected

`scripts/h3_performance.py` prepares one pilot using the existing `h3-r2v` graph and model files:

- `<Picture 1>`: selected character/wardrobe/setting image.
- `<Video 1>`: a 2–15 second authorized performance clip, trimmed and normalized to **24 fps**.
  Its soundtrack is removed, and only its frames connect to `ref_videos.ref_video_0`.
- Optional `<Audio 1>`: a separately authorized 2–15 second voice sample, connected to
  `ref_audios.ref_audio_0`. A missing voice is omitted completely, including its prompt instruction.
- Full 20-step baseline; no Turbo LoRA. Existing `h3-i2v` and `h3-r2v` remain unchanged.

The runner uses `LoadVideo → GetVideoComponents → MiniMaxH3ReferenceToVideo` and optional `LoadAudio`.
The existing image and audio VAEs remain connected. It generates picture and sound jointly; do not send
this pilot through the LTX audio-first batch by accident. Reference voice conditioning is not guaranteed
word-for-word dubbing. Verify the generated dialogue and lips.

The reference is not a starting frame. If exact entrance/exit states matter, inspect them and select a
compatible pilot; this route does not invent a first/last-frame input for Ref2VA.

## Before preparing a pilot

1. Confirm that H3 is the requested engine and resolve the existing H3 deployment/license prerequisites.
   Reading local templates is not proof of weights loaded on the server.
2. Analyze the inspiration video locally. Its `reference/private` content remains analysis-only.
   Record a separate performance reference yourself, use an owned synthetic take, or obtain permission
   for the actual clip and its server upload. Do not extract a real person's voice or identity from an
   inspiration link. The runner rejects `reference/private` paths, including resolved symlinks.
3. Choose a short single shot with visible eyes, hands and a complete emotional beat, without overlays,
   jump cuts or unrelated motion. Use a reaction and a change of intention, not constant smiling.
4. Write what the person wants, the subtext, the change of emotion, delivery, one motivated gesture,
   listening response, START/ACTION/END/HOLD and camera behavior in the shot file. Copy the template;
   replace the dialogue, language and acting directions with the approved scene. No English-only default.
5. Record provenance/permission for each actual asset. Source permission is a human assertion, not a
   legal or identity check performed by the script. Keep all real pilot files outside the public skill repo.

## Prepare and inspect, without GPU work

```sh
SK=/path/to/.agents/skills/yesopen-higgsfield-skits
cp "$SK/templates/h3-performance-shot.json" /path/to/film/shot.json
# Edit shot.json and supply your authorized media. Paths are relative to shot.json.
python3 "$SK/scripts/h3_performance.py" prepare /path/to/film/shot.json --out /path/to/film/pilot-01
```

Requires local FFmpeg/FFprobe for bounded reference preparation. Run the same command on the server if
your placement policy requires all media processing there. The script does not transfer files until execution.
It refuses an existing output directory, leaving every earlier attempt intact.

Inspect `prompt.txt`, `workflow.json`, `manifest.json`, the normalized reference, and `checkpoint.json`.
The manifest records source and prepared hashes, permission, seed and full-step settings. Check that the
reference actually carries the intended acting. H3 rounds generated duration onto its 17k+5 frame grid at
24 fps; requested seconds are not an exact export duration. Allow time for both dialogue and reaction.
The upper 15-second request can round to 362 frames (~15.08 seconds); plan the edit from actual media.
ComfyUI also caps reference frames to the generated length and rounds the reference **down** to 17k+5.
The manifest reports effective reference frames and the unused tail. Keep the important action before
that boundary (reserve a settling beat), or choose a different interval/duration. Do not assume the final
frame of the supplied reference reaches conditioning.

## Existing server: check, submit, resume

Use the existing private `YESOPEN_GPU_HOME` and SSH tunnel. Do not paste the server address or credentials
into public examples. This entry point never starts, rents, upgrades, stops or deletes a server.

```sh
python3 "$SK/scripts/h3_performance.py" run /path/to/film/pilot-01
# Read-only /object_info check: nodes, reference inputs and selected models. No upload or queue submission.

# Only after the script and paid session are authorized:
python3 "$SK/scripts/h3_performance.py" run /path/to/film/pilot-01 --execute

# Following a timeout/disconnect AFTER a prompt_id was saved:
python3 "$SK/scripts/h3_performance.py" run /path/to/film/pilot-01 --execute --resume
```

The runner rejects `shared: true` and a nonempty ComfyUI queue. It does not integrate with the shared
coordinator, acquire a server-wide lease, or protect against another independent producer racing after
the queue check. Use only an explicitly allocated idle session; do not disable shared mode to bypass it.
It locks each pilot directory against simultaneous local submissions.

It saves `submitting` before POST `/prompt`, then the returned `prompt_id` before waiting. An ambiguous
submission stays `unknown` and must be reconciled using the server queue/history. Never retry it blindly.
A timeout leaves the remote job running. Resume fetches the same job; it does not buy another generation.
Use a new pilot directory for an intentional new attempt. There are no automatic generation retries.

ComfyUI acceptance is structural validation, not model execution or visual acceptance. Unsupported nodes,
reference inputs or missing weights stop the run; never silently fall back to image-only conditioning.
Keep `history.json`, `submitted-workflow.json`, result hashes and the review with each attempt.

After actual processing/download finishes, follow the project's existing GPU retirement policy: verify
other work is idle, delete only the instance when authorized, preserve disks. This runner does not retire it.

## Judge naturalness before a batch

Use [the pilot review](../templates/h3-performance-review.md). Watch with sound and then muted, at normal
speed. Reject incorrect meaning, voice/face drift, lip mismatch, broken hands, missing action or continuity.
Judge the emotional change, responsive eyes/face, prosody, listening and motivated gesture separately.
ASR, frame counts, prompt text, successful node execution and added captions cannot pass these criteria.

For a fair comparison, make an image-only control with the same identity, intended dialogue, model files,
duration, seed, steps and equivalent direction (remove dangling Video/Audio instructions). Compare it to
the referenced pilot before music/captions; then assess the edit separately. One result is a pilot, not a
general benchmark. Change one factor at a time and retain rejected attempts and reasons. A 2K upscale
cannot establish improved acting. Do not attribute defects to INT8 or Turbo without an actual comparison.

Use reference roles explicitly in multi-shot work. Preserve identity, set, props, gaze direction and the
emotional state between shots. Preserve the reaction after the last word in the cut. When a reference
does not solve the defect, correct direction/inputs and review a new pilot before scaling.

## Provenance and verification boundary

Implemented against official ComfyUI **v0.35.0** source, with no code copied from Hypit:

- [H3 reference schema and 24 fps frame grid](https://github.com/Comfy-Org/ComfyUI/blob/v0.35.0/comfy_extras/nodes_minimax_h3.py)
- [LoadVideo / GetVideoComponents](https://github.com/Comfy-Org/ComfyUI/blob/v0.35.0/comfy_extras/nodes_video.py)
- [LoadAudio](https://github.com/Comfy-Org/ComfyUI/blob/v0.35.0/comfy_extras/nodes_audio.py)
- [MiniMax H3 local deployment and prompting guidance](https://www.minimax.io/news/minimax-h3-open-source)

This route authors its own structured direction; it does not call H3-Context-IR or the hosted 2K regeneration
service. Seedance-specific kits from Hypit are not assumed to be H3-compatible. Check the release notes for
the actual tested runtime and pending GPU/visual acceptance; local tests do not prove production quality.
