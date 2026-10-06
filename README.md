# YesOpen skits on your own GPU server or Higgsfield

An agent skill that turns "make something like this for YesOpen" plus a link to a short video into a finished,
funny skit, delivered in 9:16, 4:5, 1:1 and 16:9. The cast stills, the voices and the talking, lip-synced takes
come from your own GPU server with open models (ComfyUI with Z-Image, Chatterbox, LTX-2.3 and ACE-Step), or from
Higgsfield (Soul 2 and Seedance 2.5). The edit (cuts, punch-ins, captions, YesOpen notification banners, end card,
an optional music bed on the beat, loudness) is a scripted ffmpeg pipeline driven by one JSON file.

<p>
  <img src="examples/gym-breakup-gpu/final/web/its-not-you-its-your-invoices-gpu-9x16-poster.jpg" height="240" alt="GPU, 9:16">
  <img src="examples/gym-breakup/final/web/its-not-you-its-your-invoices-9x16-poster.jpg" height="240" alt="Higgsfield, 9:16">
  <img src="examples/gym-breakup/final/web/its-not-you-its-your-invoices-16x9-poster.jpg" height="240" alt="Higgsfield, 16:9">
</p>

The first skit, **"It's not you. It's your invoices."**: a gym owner breaks up with his marketing agency, and
every "I don't know" is answered by a YesOpen notification on his phone. It was made twice from the same script:

- on one rented H200 with open models:
  [9:16](examples/gym-breakup-gpu/final/web/its-not-you-its-your-invoices-gpu-9x16.mp4) ·
  [how it was made](examples/gym-breakup-gpu/README.md)
- with Higgsfield: [9:16](examples/gym-breakup/final/web/its-not-you-its-your-invoices-9x16.mp4) ·
  [4:5](examples/gym-breakup/final/web/its-not-you-its-your-invoices-4x5.mp4) ·
  [1:1](examples/gym-breakup/final/web/its-not-you-its-your-invoices-1x1.mp4) ·
  [16:9](examples/gym-breakup/final/web/its-not-you-its-your-invoices-16x9.mp4) ·
  [how it was made](references/case-study-gym-breakup.md)

## Po polsku

Skill dla agenta (Claude Code, Codex i inne czytające `SKILL.md`), który robi śmieszne scenki wideo dla
YesOpen. Pokazujesz filmik, który ci się podoba, a agent wykonuje kolejne kroki:

1. Analizuje mechanikę wzoru.
2. Pisze scenariusz, w którym YesOpen jest tylko puentą, nie prezentacją produktu, i czeka na akceptację.
3. Na twoim serwerze GPU z otwartymi modelami nagrywa każdą kwestię, sprawdza ją słowo po słowie i dopiero do tego
   dźwięku generuje ujęcie z ruchem ust. Zamiast serwera może użyć Higgsfield.
4. Składa montaż w czterech formatach, opcjonalnie z muzyką zsynchronizowaną z beatem.

Klient GPU sam sprawdza, czy maszyna istnieje. Jeśli tak, łączy się z nią. Jeśli nie, zamawia ją, ale dopiero po
twoim „tak”, bo maszyna jest płatna za godzinę. Potem instaluje, co trzeba, a na koniec usuwa maszynę i zostawia
dysk z modelami na następny raz. Pierwsza scenka powstała na obu silnikach: w Higgsfield za 49 USD, a na jednej
karcie H200 w 10 minut pracy GPU (cała pierwsza sesja z instalacją kosztowała 4,86 USD). Instrukcja instalacji
jest niżej.

## What is inside

```text
SKILL.md                    the workflow the agent follows: rules, phases 0–8, commands, gates, costs
references/                 how-to for each phase, the GPU engine, the Higgsfield API, the edit pipeline, QA, the case study
scripts/                    project setup, reference capture, GPU batches and line fitting, Higgsfield jobs, take inspection, edit, music, QA, delivery
gpu/                        the GPU server: client, server setup, editor container, 15 ComfyUI workflows, tests
templates/                  project.json, lines.json, cuts.json, script and analysis documents, Higgsfield request templates
assets/brand/               YesOpen icon (PNG, SVG), wordmarks and lockups, palette, Manrope font
assets/overlays/            ready notification banners, end cards and caption samples for all four formats
assets/sfx/                 the notification ding
assets/cast/                the cast of the first skit: stills with their Soul prompts and voice samples, ready for sequels
assets/broll/               20 reaction shots cut from the first skit's takes
assets/graphics/            YesOpen product illustrations
assets/product-clips/       four short YesOpen product clips
examples/gym-breakup-gpu/   the first skit made on the GPU server: lines, every voice take, line fits, takes, edit
examples/gym-breakup/       the first skit made with Higgsfield, complete
agents/openai.yaml          display metadata for agents that read it
```

## Requirements

- macOS or Linux. On macOS the keys are read from the Keychain; on Linux export `HF_TOKEN` (Hugging Face) and
  `HF_KEY` (Higgsfield) instead.
- `ffmpeg` and `ffprobe` 8.x. No `drawtext` or `libass` is needed.
- Python 3.11 with `pip install pillow numpy openai-whisper`.
- Ego Browser (Ego Lite) with its `ego-browser` command and agent skill, only to capture a reference video.
  Without it, watch the reference yourself and write the analysis by hand.
- **GPU engine:** a GPU server you rent or own: one NVIDIA card with 80 GB or more (H100, H200, B200), an
  Ubuntu 24.04 VM with Docker and the NVIDIA Container Toolkit, root login by SSH key, a 300 GB disk. Tested on
  1× H200 at [Verda](https://verda.com). Optional: the `verda` CLI with API credentials, so the client orders and
  deletes the machine by itself; a Hugging Face read token with the LTX-2.5 licence accepted, for silent action
  shots. Everything that runs on the server is in `gpu/` and installs itself.
- **Higgsfield engine:** a Higgsfield account with credit and an API key. `scripts/hf-job` creates its own
  virtualenv with `higgsfield-client` on first use.

## Install

Clone into your Agent Skills folder (or a project's `.agents/skills/`):

```bash
git clone https://github.com/behavio1/yesopen-higgsfield-skits.git ~/.agents/skills/yesopen-higgsfield-skits
SK=~/.agents/skills/yesopen-higgsfield-skits
```

On Windows, with Docker Desktop and no WSL: the tools come in a Docker image and every command goes through
`scripts\skill.ps1`. Install it as a Claude Code skill and set it up: [docs/docker-client.md](docs/docker-client.md).

GPU engine, once: a key for the server and your settings, which stay outside the skill.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_yesopen_gpu -C yesopen-gpu
mkdir -p ~/.config/yesopen-gpu && cp $SK/gpu/client/config.example.json ~/.config/yesopen-gpu/config.json
```

Then either let the client manage a Verda machine (install the `verda` CLI, `verda auth login`, add the public key
with `verda ssh-key add`, and fill `verda.instance_type`, `verda.ssh_key_id` and `verda.location` in the config),
or make a machine anywhere yourself and give the client its address with `gpu.py use <address>`. Step by step:
[references/gpu-engine.md](references/gpu-engine.md), section 2, and [gpu/README.md](gpu/README.md).

Optional, for silent action shots (LTX-2.5): accept the licence on the Hugging Face page `Lightricks/LTX-2.5`,
create a read token and store it. The command asks for the value and does not echo it:

```bash
security add-generic-password -U -s huggingface -a token -w
```

Higgsfield engine, once: store your key the same way.

```bash
security add-generic-password -U -s higgsfield -a api-key -w
```

Check the setup (free, nothing is sent or ordered):

```bash
python3 -c "import PIL, numpy, whisper; print('python ok')"
python3 $SK/gpu/client/gpu.py templates | head -1
$SK/scripts/hf-job cost bytedance/seedance-2.5/image-to-video $SK/templates/args/take.json
```

## Use it

Ask your agent, for example:

> Zrób taką scenkę dla YesOpen dla właścicieli restauracji, na naszym serwerze: https://youtube.com/shorts/…

The agent captures and analyses the reference, writes the script with a claims table and a cost estimate, and
waits for your yes before it spends money: the GPU machine bills by the hour, Higgsfield by the second of video.
Then it casts, records, films, edits, checks and hands over the files with local links, and ends the GPU session.

By hand, a GPU skit is:

```bash
G="python3 $SK/gpu/client/gpu.py"
cd "$(python3 $SK/scripts/new_project.py my-skit --title "The end-card line")"
# write script.md and lines.json (templates/lines.json shows the fields), add voices/<character>.wav, then:
$G start --yes                                                   # connect, or order and install; opens the tunnel
python3 $SK/scripts/gpu_batches.py stills && $G batch stills/batch.json
python3 $SK/scripts/gpu_batches.py voice && $G batch voice/batch.json
python3 $SK/scripts/fit_lines.py lines.json voice lines
python3 $SK/scripts/gpu_batches.py takes && $G batch takes/batch.json
python3 $SK/scripts/inspect_take.py takes/l01.video.mp4          # every take
$G stop --yes                                                    # delete the machine, keep the disk
python3 $SK/scripts/make_edl.py .
python3 $SK/scripts/assemble.py . --format all
python3 $SK/scripts/qa_report.py . --format 9:16 --whisper
python3 $SK/scripts/encode_variants.py final/<name>-9x16.mp4
```

With Higgsfield, `new_project.py --engine higgsfield` and the takes come from `hf-job`:

```bash
$SK/scripts/hf-job submit still-owner higgsfield-ai/soul/v2/standard args/still-owner.json stills
$SK/scripts/hf-job submit take-owner-1-720p bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json takes
python3 $SK/scripts/inspect_take.py takes/take-owner-1-720p-0.mp4
```

Every step, parameter and decision is explained in [SKILL.md](SKILL.md) and the [references](references/).

## Reproduce the examples

```bash
cd $SK
python3 scripts/assemble.py examples/gym-breakup-gpu --format 9:16
md5 -q examples/gym-breakup-gpu/final/its-not-you-its-your-invoices-gpu-9x16.mp4   # 327f8ffbf16465b95f9651d6aef10d5f
python3 scripts/assemble.py examples/gym-breakup --format 9:16
md5 -q examples/gym-breakup/final/its-not-you-its-your-invoices-9x16.mp4           # 095ffdca450db823b26fd76fa89a1204
```

The byte-identical check holds with the same ffmpeg build (8.x on macOS); another build can differ in bytes but
not in timing.

## The first skit in numbers

| | GPU server (2026-10-02) | Higgsfield (2026-10-01) |
| --- | --- | --- |
| Length | 61.4 s (58.8 s dialogue + 2.6 s end card), 21 lines, 21 cuts | 73.5 s (70.9 s dialogue + 2.6 s end card), 21 lines, 21 cuts |
| Generated | 50 voice takes, 21 lip-synced takes, 3 still edits; the cast stills came from the Higgsfield skit | 5 Soul batches (20 stills), 5 Seedance 2.5 takes (118 s of video) |
| GPU time or credits | 10.4 min on one H200 | $49.01 at list price, matching the account spend |
| Session | about 1 h with the first install and a test of every template: $4.86 | 1 h 25 min from the link to the master, including 30 min waiting for a top-up |
| QA | frames as planned, −14.9 LUFS, true peak −1.3 dBTP, captions match the audio word for word | frames as planned in all four formats, −14.2 LUFS, true peak −1.4 dBTP, captions match the audio word for word |

The GPU cut is 12 s shorter and tighter: each line was trimmed to its words before its take was filmed.

## What is not in this repository

- **No keys of any kind.** Keys and tokens live in each person's Keychain or environment.
- **No account data.** Your GPU settings and the machine's address live in `~/.config/yesopen-gpu/`, outside the
  skill.
- **No model weights.** The server downloads them from Hugging Face on its first start (162.5 GB), each file
  pinned to a commit and checked by SHA-256.
- **No material from the reference video.** Its frames and transcript belong to its authors and were kept
  local; the examples keep only the link and our own analysis.

## Rights

- The scripts and documents were written for YesOpen by Behavio.one with Claude Code. No open-source licence has
  been chosen yet, so ask before reusing them outside YesOpen.
- The YesOpen name, logo, icon, product illustrations, product clips and the example videos belong to YesOpen
  / Behavio.one. Use them for YesOpen content only.
- Manrope is licensed under the SIL Open Font License 1.1 (`assets/brand/fonts/OFL.txt`).
- The ComfyUI workflow templates in `gpu/workflows/ui/` are Comfy-Org's, under the MIT licence
  (`gpu/workflows/ui/LICENSE.txt`); `gpu/workflows/api/` holds the same graphs converted and patched.
- The models are not included and each keeps its own licence (`gpu/README.md`): Apache 2.0 for Z-Image Turbo,
  Qwen-Image-Edit, ACE-Step and SeedVR2, MIT for Chatterbox. LTX-2.3 and LTX-2.5 are under the LTX-2 Community
  License: free for a company under $10 million in yearly revenue, no deepfakes of real people without their
  consent, and content made with it is marked as generated.
- The Higgsfield example's stills and takes were generated with Higgsfield (Soul 2, Seedance 2.5) under the
  account owner's Higgsfield terms. The GPU example's voices were cloned from those takes, and its takes were made
  with LTX-2.3.
