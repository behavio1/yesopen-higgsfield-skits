# QA checklist, gate by gate

Tick every item. A gate that fails stops the next paid step. Items marked GPU or Higgsfield apply to that
engine only.

## Gate 1: reference analysis

- [ ] `reference/analysis.md` written in our own words: form, beat map, engine, editing grammar.
- [ ] Frames and transcript only in `reference/private/` (git-ignored, never published).
- [ ] "What we take / what we do not take" filled in.

## Gate 2: script (needs the owner's explicit approval)

- [ ] It is a skit, not a product demo: the first 10 seconds contain no feature.
- [ ] One familiar frame, one engine, 3–4 escalation steps, a turn, a button, an end-card line.
- [ ] Every product claim is in the claims table with a file and line in `business-card/messages/en`.
- [ ] No line, name or signature joke copied from the reference.
- [ ] Lines under ~12 words; numbers written as words for the take prompts.
- [ ] Cost estimate given. GPU: `gpu_batches.py estimate` and the session's hours at the machine's price.
      Higgsfield: `hf-job cost` for every take (the price per second depends on the resolution).
- [ ] GPU: `lines.json` written from the line table; every character has a voice sample (5–15 s, one clean
      synthetic voice) and a still or a `look`.
- [ ] Approval recorded in `script.md` (who, date). GPU: the yes covers starting the machine for this session.

## Gate 3: cast stills

- [ ] Four candidates per character on one sheet.
- [ ] Picked still: no logos, no readable text, neutral face with lips closed, prop visible, face large enough
      for a 1.4x punch-in, real local business look, nobody in the background.
- [ ] Higgsfield: `stills/picked.json` and the args saved. GPU: the pick in `lines.json` →
      `characters.<name>.still`; the batch file and `jobs.jsonl` kept; phones with their back to the camera.

## Gate 4: takes

- [ ] Higgsfield: `hf-job` used (jobs.jsonl has every request id).
- [ ] GPU: `fit_lines.py` passed every line before any take was made (`lines/fit.json`); the key lines
      (`key_shots`) listened to: right words, the script's "?" and "!", no mumbling.
- [ ] `inspect_take.py` run on each take: all lines present and in order, right words, one voice.
- [ ] Lip sync holds on every line (sheet), no music, no extra people, no on-screen text.
- [ ] GPU: no zoom or push-in at the end of a take; no phone screen facing the camera.
- [ ] Silent actions happened where the jokes need them.
- [ ] Room tone at least 3 dB under `speech.thr`.
- [ ] GPU: once the takes, the retakes and the music are in, `gpu.py stop --yes` has run and no machine is
      left (`gpu.py status` with Verda, otherwise the provider's console).

## Gate 5: edit

- [ ] Preview of the first 8–10 cuts shown and approved before the full edit when the pacing is new.
- [ ] Every cut has a `note` with the script line.
- [ ] Banners show the exact approved text and appear on the ding; nothing covers a face.
- [ ] Captions: every chunk on the right speaker and shot (`qa-<fmt>-captions.jpg`), spelling and
      punctuation as in the script.
- [ ] End card: right tagline, URL, 2.6 s, ding.

## Gate 6: final, per format

- [ ] `qa_report.py`: frames actual = planned (`frames.ok`), loudness −14 ±1 LUFS, true peak ≤ −1.0 dBTP.
- [ ] `--whisper` on the 9:16 master: word match ≈ 1.0 with the caption words (the gym skit: 1.0, no differences).
- [ ] Watched once from start to end with sound.
- [ ] 4:5, 1:1, 16:9 checked with sheets: faces framed, captions readable, banners clear of faces.

## Gate 7: delivery

- [ ] Clickable local links to the master, share and web files in the reply.
- [ ] Web version sent for preview; Artifact page only if asked.
- [ ] Nothing posted publicly without an explicit request.
- [ ] `script.md` updated with what changed in production and the final files.

## H3 performance-reference route

- [ ] Follow `h3-performance.md`; use separately authorized references, never inspiration-only private media.
- [ ] Prepared reference video is 24 fps, 2–15 seconds, silent; optional voice is explicit and authorized.
- [ ] Actual submitted graph connects video and optional voice to H3; no image-only fallback.
- [ ] Intention, emotional change, delivery, gesture, listening and reaction hold reach the actual prompt.
- [ ] Use `templates/h3-performance-review.md`; view the entire pilot with sound and muted.
- [ ] Naturalness, voice, physical action and continuity accepted before expanding the batch.
- [ ] Keep every attempt, input hashes, prompt ID and result hashes. ASR alone does not pass acting.
