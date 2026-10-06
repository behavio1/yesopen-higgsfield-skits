---
name: yesopen-higgsfield-skits
description: Make short, funny YesOpen video skits for TikTok, Reels and Shorts on your own GPU server with open models (ComfyUI: Chatterbox voices, LTX lip sync, Z-Image, ACE-Step music) or with Higgsfield. Take a reference video's comedy mechanics, write a skit where YesOpen is only the punchline, cast it, record every line and film it to that sound, cut it with scripted ffmpeg (captions, notification banners, end card, music on the beat) and deliver 9:16, 4:5, 1:1 and 16:9. Its client finds, connects to or orders the GPU machine and sets it up. Use whenever the user shares a YouTube, TikTok or Instagram link and asks for "taką scenkę", "coś takiego dla YesOpen", a funny video, short, reel, skit, filmik or ad for YesOpen or local businesses (gyms, restaurants, salons, shops), wants it "na naszym serwerze", "lokalnie", "na GPU" or with Higgsfield, or wants to re-cut, reformat or continue the gym breakup skit ("It's not you. It's your invoices."). Not for product demos, screen recordings or feature explainers.
---

## GPU retirement and API-first operation

Standing user instruction: after use, DELETE the idle GPU instance and PRESERVE ALL disks, including OS and detached volumes. This supersedes earlier stop-only and leave-running instructions. Verify real shared workloads; pending review is not compute. Use CLI/API first. Follow [Verda operations](references/verda-operations.md) and [retirement checks](gpu/SHUTDOWN.md).


# YesOpen skits on your own GPU server or Higgsfield

This skill turns "make something like this for YesOpen" plus a link into a finished, funny vertical video and its
other formats. Two engines make the pictures and the voices:

- **GPU, the default** (`"engine": "gpu"`): your own GPU server with ComfyUI and open models. Every line is
  recorded first (Chatterbox, a voice cloned from a sample), checked word by word, and the take is then filmed to
  that sound (LTX-2.3 lip sync). You pay for the machine's hours, not per job: the gym skit needed 10 minutes of
  GPU time and its whole first session cost $4.86. Everything the server needs is in `gpu/`;
  `references/gpu-engine.md` is the guide.
- **Higgsfield** (`"engine": "higgsfield"`): Soul stills and Seedance 2.5 takes through the Higgsfield API, paid
  per second of video (the gym skit: $49). No server.

Phases 0–2 and 5–8 are the same for both. The first skit, "It's not you. It's your invoices.", exists in both: a
gym owner breaks up with his marketing agency, every "I don't know" is answered by a YesOpen notification on his
phone, and YesOpen only appears as the punchline and the end card. `examples/gym-breakup/` is the Higgsfield
original (2026-10-01; the full story in `references/case-study-gym-breakup.md`), `examples/gym-breakup-gpu/` the
same script made on one rented H200 (2026-10-02). Each keeps every prompt, parameter, job log, take, the edit and
the finals. Read the case study before your first skit.

`SK` below is this skill's folder (for example `~/.agents/skills/yesopen-higgsfield-skits`) and `G` the GPU client:
`G="python3 $SK/gpu/client/gpu.py"`. Talk to the user in their language; the dialogue of the video is English
unless they ask otherwise.

On Windows the tools are not installed: run every command of this skill through `scripts\skill.ps1` (it starts it in
a Docker container where `SK` is `/skill`), for example `scripts\skill.ps1 gpu status`. See `docs/docker-client.md`.

## Production procedure and runtime boundaries

Read [references/production-procedure.md](references/production-procedure.md) before paid work or resuming
an interrupted film. Its pilot, language, timing, recovery and retirement checks apply to both engines and
supersede the older timing estimates and automatic shutdown shortcuts below. Follow
[gpu/SHUTDOWN.md](gpu/SHUTDOWN.md) for shared-host shutdown. Do not assume that local uncommitted shared
pipeline features exist in the published release; verify the installed version and commands first.

## Voice quality: mandatory validation

Apply [the integrated Chatterbox practices](references/chatterbox-practice.md), adapted from the reviewed
Demoforge voice-cloning skill and checked against the model documentation.

Read [references/voice-validation.md](references/voice-validation.md) before any dialogue batch or voice/language/model
change. Use [templates/voice-validation.md](templates/voice-validation.md) for sample selection, per-line listening
and final-film acceptance. ASR pass alone is not voice-quality approval. Missing listening evidence stays
`needs_review`; do not claim that it passed. Use [references/multilingual.md](references/multilingual.md) for
Chatterbox Multilingual V3 setup and supported language codes.

## Production hardening from the Polish salon film

Read [references/production-hardening.md](references/production-hardening.md) when resuming shared production,
selecting voice sources, diagnosing talk shots or preparing delivery. It covers explicit user-deferred listening,
source verification before generation, corrected first-stage CFG, readable typography and WhatsApp delivery.
Do not turn a user's temporary inability to listen into repeated approval requests or invented listening evidence.

## Non-negotiables

1. **A comedy skit, not a product presentation.** From the first brief: "to nie jest prezentacja produktu".
   People share a joke, not a feature tour. The product is the reason for the laugh (a notification, one honest
   line), and the brand closes the video on the end card. If YesOpen could be cut out without losing a joke, it is
   an ad.
2. **Nothing paid before an explicit yes to the script.** GPU: obtain authorization for the script and paid session before provisioning.
   Record the authorized retirement operation and protected resources. Verify provider billing semantics;
   Stop and Delete differ, and retained disks may continue to incur charges. Follow the production procedure
   after completion or failure; the standing YesOpen instruction explicitly authorizes instance deletion with all disks retained. Higgsfield: stills cost cents and may be made while the
   script is discussed; takes cost dollars and wait for the yes.
3. **Only true claims.** Every product punchline must point to the product copy in
   `business-card/messages/en/*.json` (file and line) of the Localesto checkout, or come from the user. Unknown
   features stay out.
4. **Mechanics from the reference, never its content.** Reuse form, rhythm and editing. Never reuse its lines,
   names, characters or signature jokes. Its frames and transcript stay in the project's `reference/private/` on
   your computer: never commit, publish or upload them (also not to the GPU server), never paste them, and never
   retell its dialogue, even in other words.
5. **Only voices and faces we may use.** Clone only synthetic voices (our own generated takes, Chatterbox's own
   voices) or a person who agreed in writing; never a real person's voice or face from the reference. The LTX-2
   licence asks that content made with it is marked as AI-generated: use the platform's label when posting.
6. **Keys stay in the Keychain.** The Higgsfield key (service `higgsfield`, account `api-key`) and the Hugging Face
   token (service `huggingface`, account `token`) are read by the scripts and never printed. Never write a key into
   args, logs, scripts, commits, memory or chat. If a key is pasted into a chat, store it with
   `security add-generic-password -U -s <service> -a <account> -w` and tell the owner to rotate it.
7. **No generated text on screen.** Banners, captions and the end card are drawn in the edit, so the text is
   exact and on brand. Take prompts end with "no text on screen".
8. **Nothing is posted anywhere without an explicit request for that post.** Deliver files; links to the local
   files come first.

## Shot continuity: required before stills and takes

Every script shot must specify **START → ACTION / DIALOGUE → END → HOLD → NEXT**.
A starting still and an action description alone are incomplete. Read
`references/scriptwriting.md`, section 8, and fill the continuity table in `templates/script.md`.

- START: framing, character position, pose, gaze, expression, hands and prop locations.
- ACTION / DIALOGUE: ordered speech and movement, with enough time to finish both.
- END: observable completed event and exact final pose, gaze, expression and prop state.
- HOLD: a planned readable settling/listening beat after completion, included in generation duration
  and retained in the edit; no new gesture, speech, zoom or fade during it.
- NEXT: next shot ID and its matching entry state, or an explicit reverse shot / motivated transition.
  Track off-screen characters and props too: a reverse shot must not reset their state.

Before generating, copy these directions into the actual model prompt, not just the script document.
Use existing GPU `prompt` / `action` fields and timing controls; do not invent unsupported API fields.
A different pose/prop state requires a matching starting image. Reuse the actual accepted final frame
when the next clip continues the same view; for reverse angles use a matching reference, not the wrong angle.
Use an end-frame input only when the selected model and wrapper actually support it. A written END is
still mandatory and must be verified visually; a prompt is not proof.

Validate continuity at Gates 2, 3, 4 and 5. Missing completion requires correction of the take, not a cutaway
that hides the missing event. After regeneration, review and select the edit boundaries again.

## What you need

| Need | Details |
| --- | --- |
| `ffmpeg`, `ffprobe` | 8.x; no `drawtext` or `libass` needed (all text is drawn with Pillow) |
| Python 3.11 | `pip install pillow numpy openai-whisper` (`large-v3-turbo` downloads on first use) |
| GPU engine | a GPU server: one NVIDIA card with 80 GB or more, an Ubuntu 24.04 VM with Docker and the NVIDIA Container Toolkit, root login by SSH key, a 300 GB disk. Verda, another provider or your own machine: `references/gpu-engine.md`, section 2. Here: `ssh`, `rsync`, an SSH key and the settings in `~/.config/yesopen-gpu/config.json` |
| GPU engine at Verda, required | the `verda` CLI, set up by the user: installed, logged in with API credentials of the Verda project, and `verda.instance_type` and `verda.ssh_key_id` filled in the config. Before the first GPU step run `python3 $SK/gpu/client/gpu.py verda-check`. When it says the CLI is not set up, stop and tell the user plainly that they must set it up first, and give them the steps it prints. The user runs `verda auth login` in their own terminal; never ask for the client secret, never take it in the chat and never read it. The credentials may also reach the CLI from the environment (`VERDA_CLIENT_ID`, `VERDA_CLIENT_SECRET`), the way `scripts/verda-vault.py` passes the team vault entry (`references/verda-operations.md`); `verda-check` tests them with a read-only call. `start`, `stop`, `up`, `down` and `status` refuse to run until the check passes. A server elsewhere, or a machine a teammate starts for you: `"provider": "other"` in the config |
| GPU engine, optional | a Hugging Face token for silent `action` shots (LTX-2.5); Docker here for the editor container |
| Higgsfield engine | an account with credit and an API key `<key-id>:<secret>` in the Keychain (service `higgsfield`, account `api-key`) or `HF_KEY`; `hf-job` finds or creates a venv with `higgsfield-client` |
| Ego Browser | captures the reference (global skill `ego-browser`); without it, save frames and the transcript by hand into `reference/private/` |
| Localesto checkout | optional: product copy for claims and the default project root; `LOCALESTO_ROOT` if it is not a parent folder |
| Manrope | bundled in `assets/brand/fonts/` (SIL OFL); `YESOPEN_FONT` overrides it |

Environment variables: `YESOPEN_SHORTS_ROOT` (where projects go; default `<localesto>/output/yesopen-shorts`,
else `./yesopen-shorts`), `YESOPEN_GPU_HOME` (GPU settings and machine state, default `~/.config/yesopen-gpu`),
`GPU_HOST` (a server address for one command), `HF_TOKEN` (Hugging Face, where there is no Keychain),
`LOCALESTO_ROOT`, `YESOPEN_FONT`, and for Higgsfield `HF_KEY` and `HF_PYTHON`.

Related global skills, if installed: `ego-browser` (capture), `higgsfield-generate` (model catalog and one-shot
`hf-api`), `higgsfield-soul-id` (a recurring character across many videos), `higgsfield-seedance`.

Quick check, free:

```bash
ffmpeg -version | head -1
python3 -c "import PIL, numpy, whisper; print('python ok')"
$G templates | head -1                                   # GPU client
test -f ~/.config/yesopen-gpu/config.json && echo "gpu settings ok"
$SK/scripts/hf-job cost bytedance/seedance-2.5/image-to-video $SK/templates/args/take.json   # Higgsfield
```

## Project layout

```text
<root>/<date>-<slug>/
  project.json             engine, cast, takes, speech threshold, caption style and fixes, banner texts, end card
  script.md                the script document (Polish), dialogue in the video's language
  lines.json               GPU: the lines, voices, stills and take prompts every batch is written from
  reference/analysis.md    our analysis of the reference; reference/private/ is git-ignored
  args/                    Higgsfield: every Soul and Seedance request body, one JSON per request
  stills/                  candidates, sheets, picks, batch files, jobs.jsonl
  voices/                  GPU: one voice sample per character
  voice/                   GPU: every recorded take of every line, batch files, jobs.jsonl
  lines/                   GPU: the fitted lines the takes are filmed to, fit.json
  takes/                   the takes, <take>.words.json, batch files, jobs.jsonl
  music/                   the music bed (optional)
  edit/cuts.json           the edit, one entry per shot
  edit/edl.json            generated by make_edl.py
  edit/assets/<fmt>/       banners, end card, caption sample per format; edit/assets/ding.wav
  edit/frames/             sheets for QA
  final/                   <name>-<fmt>.mp4 masters, -share.mp4, web/ copies and posters
```

Start one with `python3 $SK/scripts/new_project.py <slug> --title "<end-card line>"` (GPU engine; add
`--engine higgsfield` for Higgsfield).

## The workflow

Every phase ends with a gate from `references/qa-checklist.md`. A failed gate stops the next paid step.
Explicit user-deferred listening follows the scoped continuation rule in `references/voice-validation.md`;
known defects and missing voice rights still block the affected work.

### Phase 0: Start

1. Create the project (above). Put the link into `project.json` → `reference.url`.
2. The engine is GPU unless the user asks for Higgsfield or has no GPU server.
3. If the brief is unclear only in ways that change the joke (who the audience is, the language, the length),
   ask once. Otherwise state your assumption and go.

### Phase 1: Reference (about 5 min)

Read `references/reference-analysis.md`.

```bash
$SK/scripts/capture-reference "<link>" reference/private
python3 $SK/scripts/contact_sheet.py reference/private/frames -o reference/private/sheet.jpg --cols 5 --per-sheet 10
```

Fill `reference/analysis.md` in your own words: form, beat structure, the engine of the joke, editing grammar,
what we take and what we do not. Gate 1.

### Phase 2: Script (about 10 min, then the user's yes)

Read `references/scriptwriting.md`. Build the joke in this order:

1. A frame everyone knows (breakup, intervention, job interview, therapy, parent-teacher meeting).
2. The business owner as the straight man; the old way of doing things (agency, nephew, sticky notes) as
   the other side.
3. An engine with a gap between what is said and what is seen, so the audience is ahead of a character.
4. Three or four escalation steps with the same shape, then a turn, one honest product line, a button.
5. The end-card line = the best line of the script.

Check every claim (`rg` in `business-card/messages/en`) and write the claims table. Write `script.md` from the
template. With the GPU engine also write `lines.json` from `templates/lines.json`: the line table in the form the
batches read (who, the text with numbers as words, exaggeration, acting, what we see), and run
`python3 $SK/scripts/gpu_batches.py estimate` for the GPU minutes.

Present it in chat, short and in the user's language: the idea in two sentences, the line table, what is borrowed
(mechanics only), the claims, open decisions each with a recommendation, the cost (GPU: the session's hours at the
machine's price; Higgsfield: `hf-job cost` for each planned take). Wait for an explicit yes, and record it in
`script.md`. With the GPU engine the same message asks for the yes to start the machine. Gate 2.

### Phase 3: Cast (about 5 min)

**GPU engine** (`gpu-engine.md`, sections 3 and 5). Start the session, then four Z-Image candidates for every
character that has no still yet:

```bash
$G start --yes                       # connects to the machine or orders it, installs what is missing, opens the tunnel
python3 $SK/scripts/gpu_batches.py stills
$G batch stills/batch.json
python3 $SK/scripts/contact_sheet.py stills/still-owner-*.image.png -o stills/sheet-owner.jpg --cols 4 --width 400 --label index
```

Write each `look` like a Soul prompt (`references/casting-soul.md`), but open it with the framing: "Vertical
smartphone photo, medium shot from mid-thigh up, eye level, …". A variant of a picked still (another pose, a prop)
comes from `still-edit` with `fast=true`, which keeps the face, the clothes and the set. Phones always show their
back to the camera.

**Higgsfield engine.** Read `references/casting-soul.md`. One `args/still-<character>.json` per character, from
`templates/args/still.json`: point of view, concrete looks, wardrobe without logos, the prop the joke needs, a
plain local set, daylight, eye contact with a neutral face and lips closed, mid-thigh framing, "No text, no logos,
no watermark." Parameters: `aspect_ratio` 9:16, `resolution` 1080p, `batch_size` 4, `enhance_prompt` false.

```bash
$SK/scripts/hf-job submit still-owner higgsfield-ai/soul/v2/standard args/still-owner.json stills
python3 $SK/scripts/contact_sheet.py stills/still-owner-*.png -o stills/sheet-owner.jpg --cols 4 --width 400 --label index
```

**Both.** Reject logos, readable text, broad smiles, hidden props, small faces, chain-store sets. Write the picks
to `lines.json` → `characters.<name>.still` (GPU) or `stills/picked.json` (Higgsfield), and to `project.json` →
`cast`. Returning characters come from `assets/cast/` with their stills and voice samples. Gate 3.

### Phase 4: Takes (historical estimates, not a runtime promise)

Before the full take batch: validate language support, fit and listen to audio, calculate the proposed edit
length, then review representative pilots as specified in `references/production-procedure.md`.
The commands below describe batch mechanics; do not submit the full batch until the pilot check passes.

**GPU engine** (`gpu-engine.md`, section 6): audio first, then one lip-synced take per line.

```bash
python3 $SK/scripts/gpu_batches.py voice && $G batch voice/batch.json      # every line twice
python3 $SK/scripts/fit_lines.py lines.json voice lines                    # check, cut and pick: lines/<id>.wav
python3 $SK/scripts/gpu_batches.py reseed l18 && $G batch voice/batch-l18.json   # only for a line that failed
python3 $SK/scripts/fit_lines.py lines.json voice lines --only l18
python3 $SK/scripts/gpu_batches.py takes && $G batch takes/batch.json      # 13 s per take on an H200
python3 $SK/scripts/inspect_take.py takes/l01.video.mp4                    # words, sheet, boundaries; every take
```

Voice samples: `voices/<character>.wav`, 5–15 s of one clean synthetic voice (`assets/cast/*.voice.wav`, or cut
from our own earlier take). Listen to the lines that carry the joke (`key_shots`) before any picture is made: the
picture follows the sound, so a wrong word, or a question where the script has a full stop, is fixed here for
seconds of GPU time. A silent beat before a line: `silence_before` on that line, with a whole `prompt` that says
what happens first. The takes are LTX-2.3 by default; with MiniMax's consent a film (or one line) can be made on
MiniMax H3 instead: `"model": "h3"` in `lines.json` → `take`, or `gpu_batches.py takes --model h3` (`gpu-engine.md`,
section 6). Make the music bed in the same session if the skit wants one (`gpu-engine.md`, section 7).
After Gate 4, retire resources only when the remaining edit/QA no longer needs that host and the
production procedure permits it. A shared machine may still have CPU/export work.

**Higgsfield engine.** Read `references/takes-seedance.md`. One character per take, all their lines in order with
"Pause" lines between them, 20–30 s, from `templates/args/take.json`: "Single continuous handheld vertical
smartphone shot, no cuts", "stays in place", "talks directly into the camera lens as if to the person filming",
the same voice description in every take of that character, numbered lines each with a short physical direction,
the silent jokes written as actions, and the closing negatives (no music, no other people, no subtitles, no text
on screen). Numbers as words. Model `bytedance/seedance-2.5/image-to-video`, `resolution` 720p,
`generate_audio` true.

```bash
$SK/scripts/hf-job cost bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json
$SK/scripts/hf-job submit take-owner-1-720p bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json takes
python3 $SK/scripts/inspect_take.py takes/take-owner-1-720p-0.mp4
```

Submit the takes as parallel background commands (three at once worked); each takes 4–9 minutes. If the balance
is unknown, send a 4 s 480p probe first. A job that fails within 5 s means a low balance: ask for a top-up, do not
loop. A content-safety block can be random: resubmit the same args once. If a terminal dies, `hf-job resume` the
`request_id` from `jobs.jsonl`; never pay twice.

**Both.** `inspect_take.py` writes the word timestamps and a frame sheet and prints each line, the boundaries
refined against the audio, and the room tone. Check every line, the lip sync, one voice per character, no music
or extra people, no zoom or push-in, no phone screen towards the camera, and the silent actions. Gate 4.

### Phase 5: Edit (about 15 min)

Read `references/edit-pipeline.md`. Fill `project.json` (`takes`, `captions.fixes`, `notifications`, `endcard`)
and write `edit/cuts.json` while looking at the sheets: per shot the take, the first and last word of the line,
`head`/`tail` (or `out`, or `fixed` for silent beats), an optional punch-in (`zoom`, `cy`), events (`ding`,
`banner`, `ding_at`, `cutaway`) and a `note` with the script line. A GPU take holds one line, so a shot is usually
the whole take: `{"take": "l01", "line": ["Hey", "up"], "head": 0.28, "tail": 0.2}`.

```bash
python3 $SK/scripts/build_assets.py . --sheet
python3 $SK/scripts/make_edl.py . --upto 10 --no-endcard -o edit/edl-preview.json
python3 $SK/scripts/assemble.py . --format 9:16 --edl edit/edl-preview.json --out edit/preview/part1.mp4
```

Show the preview (SendUserFile) when the pacing is new, adjust, then build the full edit:

```bash
python3 $SK/scripts/make_edl.py .
python3 $SK/scripts/assemble.py . --format 9:16
```

Rules of thumb: 1–4 s per shot; punch-ins 1.10–1.45 on at most every third shot; `tail` 1.0–1.35 when a silent
joke follows; banner 0.02 s after its ding. `head` 0.6–0.85 keeps a look before a line in a Seedance take; a GPU
take has only 0.3 s before its line, so keep `head` under that. Gate 5.

Music is optional: the first skit had none, because its jokes live in the pauses. When the reference or the skit
wants a bed, add `project.json` → `music` (`edit-pipeline.md`, section 8): `assemble.py` puts a downbeat on the
cut to the end card, ducks the bed 12 dB under every line and masters the mix to −14 LUFS. The same scripts also
run in the editor container, here or on the GPU server (`gpu-engine.md`, section 8).

### Phase 6: Formats and QA (about 5 min)

Read `references/formats-delivery.md`.

```bash
python3 $SK/scripts/assemble.py . --format all
python3 $SK/scripts/qa_report.py . --format 9:16 --whisper
python3 $SK/scripts/qa_report.py . --format 4:5     # and 1:1, 16:9
```

Required: frames actual = planned, −14 ±1 LUFS, true peak ≤ −1.0 dBTP, Whisper word match about 1.0, and the
caption sheets checked (faces framed, captions and banners clear of faces). Watch the 9:16 once with sound. Gate 6.

### Phase 7: Delivery

```bash
python3 $SK/scripts/encode_variants.py final/<name>-9x16.mp4       # -share.mp4 (25 MiB) and web/ (15 MB) + poster
```

1. Reply with clickable links to the local files first: master, share copy, web copies.
2. Show the 9:16 web copy using the current app’s supported local video preview (absolute-path Markdown in Codex).
   Use SendUserFile only when that tool is actually available; never stall delivery looking for a missing tool.
3. A shareable page only on request (a private claude.ai Artifact with the web mp4 and poster).
4. No posting to any platform without an explicit request. Gate 7.

### Phase 8: Wrap-up

- Add "Po produkcji" to `script.md`: what changed from the approved script, the final files, the QA numbers.
- GPU: execute the authorized retirement operation after verifying downloads and actual shared workload.
  Verify provider state, record the evidence and retained resources. Never delete a disk without explicit authorization.
- Keep reusable material: cast stills to `assets/cast/` (with their prompt or Soul args) and voice samples as
  `assets/cast/<name>.voice.wav`, reaction shots to `assets/broll/`
  (`python3 $SK/scripts/extract_clip.py <take> <in> <dur> <out> --native`), new banners with
  `scripts/render_asset_library.py`.
- New lesson or fix? Update this skill and publish it (last section).

## Cost and time

**GPU engine**, measured on 2 October 2026 on one H200 at Verda (`gpu-engine.md`, section 9):

| Item | Price or time | The gym skit |
| --- | --- | --- |
| The machine, billed from creation to deletion | H200 $4.78 an hour, B200 $6.99 (Verda, on demand) | about 1 h with the first install and a test of every template: $4.86 |
| First install on a new disk | about 11 min | once per disk |
| The disk kept between sessions | $0.20 per GB a month ($60 for 300 GB) | |
| Stills, 4 per new character | 3 s each | none: the cast came from the Higgsfield skit |
| Voice, 2 takes per line | 3–5 s each | 50 takes, 5.2 min |
| Talking take, 3–5 s | 13 s each | 21 takes, 4.7 min |
| Music bed, 45 s | 18 s | |
| Edit, all formats, QA | on your computer, as for Higgsfield | |

The skit itself took 10.4 min of GPU time; the hours around it are what costs. Have `lines.json`, the looks and
the voice samples ready before `start`, run approved batches without unnecessary gaps, and follow the retirement checks when host work ends. `gpu_batches.py estimate` prints the GPU minutes of a new skit.

**Higgsfield engine**, list prices on 2026-10-01:

| Step | Price | Time | The first skit |
| --- | --- | --- | --- |
| Soul 2 batch of 4 stills, 1080p | $0.0228 ($0.0057 per image; $0.0032 in 720p) | 1.8–2.6 min | 5 batches, $0.11 |
| Seedance 2.5 take, per second | $0.2056 in 480p, $0.4622 in 720p, $1.1372 in 1080p | 4–9 min per 20–28 s take | 96 s in 720p and 22 s in 480p, $48.90 |
| 4 s 480p probe | $0.82 | a few minutes | refused (no credit), free |
| Edit, all formats, QA | local | about 15 min the first time; 35–56 s per format re-render | |
| Link to finished master | | 1 h 25 min, with 30 min waiting for a top-up | |

The first skit cost $49.01 at list price, which matches the account spend. The price per second depends on the
resolution, so a 1080p take costs about 2.5 times as much as the same take in 720p. `hf-job cost <model>
<args.json>` prints the estimate for any args file from its resolution, duration and batch size. The API
returns no cost and there is no balance endpoint.

## Scripts

| Script | What it does |
| --- | --- |
| `new_project.py` | new project folder from the templates, for either engine |
| `capture-reference` (`capture_reference.mjs`) | Ego Browser: metadata, frames, transcript of a reference into `reference/private/` |
| `contact_sheet.py` | labelled grid of images or frames |
| `gpu/client/gpu.py` | GPU engine: `start` / `stop` a session (finds, connects to or orders the machine, installs the stack, opens the tunnel), `run` and `batch` jobs, `health`, `templates`, `edit`; a `jobs.jsonl` line per job |
| `gpu_batches.py` | GPU engine: the batch files for stills, voices, reseeds and takes from `lines.json`, and the GPU-time estimate |
| `verify_voice_sources.py` | free source preflight: provenance declarations, selected cast paths and SHA-256; not listening approval |
| `fit_lines.py` | GPU engine: checks every recorded take against its line, cuts what the model added, picks the take |
| `hf-job` (`hf_job.py`) | Higgsfield: `submit`, `resume`, `status`, `upload`, `cost`; checkpoints in `jobs.jsonl` |
| `inspect_take.py` | Whisper words, frame sheet, refined line times, room tone of a take |
| `build_assets.py` | ding, banners, end card, caption sample for each format |
| `make_edl.py` | `cuts.json` + transcripts -> `edl.json` (frame-exact segments, events, caption words) |
| `assemble.py` | renders one or all formats from the EDL |
| `music.py` | music bed: beat grid, downbeat on the end card, ducking under speech; prints a track's grid |
| `qa_report.py` | frames, loudness, caption sheet, Whisper diff |
| `qa_sheet.py` | frame sheet of any video |
| `encode_variants.py` | share copy, web copy, poster |
| `extract_clip.py` | cut a B-roll clip from a take, in any format |
| `render_asset_library.py` | brand pack and the reusable banners, end cards and caption samples |
| `brand.py`, `media.py` | shared drawing (YesOpen look) and media helpers |
| `gpu/tools/validate_local.py` | lets a local ComfyUI without GPU or models accept every workflow, after a template change |

## References

| File | Read when |
| --- | --- |
| `references/case-study-gym-breakup.md` | before the first skit, and whenever you need a worked example of any step |
| `references/reference-analysis.md` | Phase 1 |
| `references/scriptwriting.md` | Phase 2: joke structure, verified claims, ideas for the next skits |
| `references/gpu-engine.md` | GPU engine: the server and how to get one, a session, the templates, Phases 3–4 audio first, music, editing on the server, time and cost |
| `examples/gym-breakup-gpu/README.md` | GPU engine: the gym skit made on one H200, with every batch, line fit and take |
| `gpu/README.md` | the server itself: models and their licences, security, updating the ComfyUI templates, tests |
| `references/casting-soul.md` | Phase 3 (the still prompts of both engines) |
| `references/takes-seedance.md` | Phase 4 with Higgsfield |
| `references/higgsfield-api.md` | anything about the Higgsfield key, `hf-job`, models, parameters, prices, failures |
| `references/edit-pipeline.md` | Phase 5: every field of `project.json`, `cuts.json`, `edl.json`, the filters, known traps |
| `references/formats-delivery.md` | Phases 6–7 |
| `references/qa-checklist.md` | the gates |
| `references/voice-validation.md` | required voice audition, pronunciation, listening and final acceptance |
| `references/multilingual.md` | language propagation and V3 setup |
| `references/production-procedure.md` | preflight, pilots, recovery, scheduling and retirement |
| `references/asset-catalog.md` | logo, icon, fonts, banners, end cards, sound, cast and voice samples, B-roll, product graphics |

## Lessons that cost time or money

- v1 copied the reference's premise and had no place for the product; the approved idea made the product the
  engine of the joke.
- 1080p takes failed on balance while 720p went through; 720p is enough for the 1080x1920 master.
- The first take request failed in 5 s for lack of credit; a 4 s probe would have shown it for under a dollar.
- Whisper's word times can be 0.4 s late; the edit refines every line against the audio, with a threshold above
  the take's room tone (−26 dB).
- Rounding each segment separately drifted captions by 0.34 s; lengths are whole frames now.
- Delivery detours cost 25 minutes and the user's patience: links to the files on disk come first.
- GPU: the voice model often talks on after the line or mumbles in a pause, and once said "two AMA"; every line is
  fitted and checked before any picture is made (2 of 21 lines needed new seeds).
- GPU: LTX-2.3 pushes in on the face at the end of a take unless the prompt says the framing stays the same, and
  a phone screen facing the camera gets an invented app on it.
- GPU: the machine is the cost, not the jobs (10 min of GPU time in a 1 h session); prepare everything before
  `start`; retire resources according to the authorized operation and verified workload.

## Updating this skill and the public repository

This folder is its own Git repository, published at https://github.com/behavio1/yesopen-higgsfield-skits
(public, shared with colleagues and partners; the name stays for existing links). The parent Localesto repository
excludes the folder locally (`.git/info/exclude`).

1. Change the skill; run the scripts you touched on both examples. The 9:16 renders must stay byte-identical
   unless you meant to change the edit (`md5 -q`; the expected sums are in each example's README).
2. After a change in `gpu/`: `cd $SK/gpu/tests && python3 -m unittest discover -s .` (the end-to-end tests run
   when a ComfyUI answers on `GPU_TEST_COMFY_URL`, default `http://127.0.0.1:8188`), and after a workflow change
   also `python3 $SK/gpu/tools/validate_local.py --comfy-dir <a local ComfyUI>` (`gpu/README.md`).
3. Scan before every commit; all of these must print nothing:

   ```bash
   cd $SK
   git ls-files -co --exclude-standard | grep -E '(^|/)(\.env|.*\.pem|.*\.key)$|reference/private/|gpu/client/(config|state)\.json$'
   git ls-files -co --exclude-standard -z | xargs -0 grep -I -l -E '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-fA-F]{16,}|HF_KEY=[^"$ []|HF_TOKEN=[^"$ {[]|hf_[0-9A-Za-z]{30,}|(sk|pk|rk)_(live|test)_[0-9A-Za-z]{8,}|gh[pousr]_[0-9A-Za-z]{20,}|postgres(ql)?://'
   K="$(security find-generic-password -s higgsfield -a api-key -w)"; git ls-files -co --exclude-standard -z | xargs -0 grep -I -l -F -e "${K#*:}"; unset K
   T="$(security find-generic-password -s huggingface -a token -w 2>/dev/null)"; [ -z "$T" ] || git ls-files -co --exclude-standard -z | xargs -0 grep -I -l -F -e "$T"; unset T
   ```

4. When remote publication is authorized, commit as `behavio1` and push only the reviewed task changes.
   Inspect the existing dirty work first; never sweep unrelated changes into the commit. The commands below
   require an explicitly reviewed file list, not `git add -A`:

   ```bash
   git -C $SK add -- <reviewed-files>
   git -C $SK commit -m "<what changed and why>"
   git -C $SK push
   ```

The remote is `git@github.com-behavio1:behavio1/yesopen-higgsfield-skits.git` (SSH alias for the behavio1 key).
Never push keys, a reference's frames or transcript, your GPU settings (`~/.config/yesopen-gpu`), `edit/work/` or
`.venv/`.
