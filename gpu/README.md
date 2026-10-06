# The GPU server

Your own GPU server for the YesOpen skits: ComfyUI with the official ComfyUI workflow templates and open models,
a client that runs it from your computer, and an editor container. It is the `gpu` engine of this skill. The skill
leads from the reference link to the finished files; this server makes the cast stills, the voices, the
lip-synced takes, silent shots, the music bed and, if you want, the edit. How to use it in a skit:
[`../references/gpu-engine.md`](../references/gpu-engine.md).

Nothing secret is stored here. The Hugging Face token stays in your Keychain (or `HF_TOKEN`) and reaches the
server through SSH stdin, into a file only root can read. Your settings and the machine's address live outside the
skill, in `~/.config/yesopen-gpu/` (`YESOPEN_GPU_HOME`), so updating the skill keeps them.

## Quick start

```bash
SK=~/.agents/skills/yesopen-higgsfield-skits
G="python3 $SK/gpu/client/gpu.py"
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_yesopen_gpu -C yesopen-gpu
mkdir -p ~/.config/yesopen-gpu && cp $SK/gpu/client/config.example.json ~/.config/yesopen-gpu/config.json
$G verda-check          # Verda: is the Verda CLI set up here? it prints the steps when not (required)
$G use 203.0.113.10      # only with "provider": "other" (a machine made elsewhere); at Verda start finds or orders it
$G start                 # is there a machine? connect to it. none: show what would be ordered
$G start --yes           # order it if there is none (billing starts), install what is missing, open the tunnel
$G health                # every template: nodes and model files
$G stop --yes            # close the tunnel, delete the machine, keep the disk
```

`start` skips every step that is already done: it waits for SSH, installs the stack when the server has none or
an older one (the server keeps a stamp of the server files), otherwise only starts ComfyUI, then opens the tunnel
and checks the core templates. A new disk takes about 11 minutes before ComfyUI starts; the rest of the models
download in the background.

## What the machine needs

- One NVIDIA GPU with 80 GB or more (Hopper or Blackwell: H100, H200, B200). Measured on an H200: peaks of
  13–49 GiB per job, with models from earlier jobs still loaded.
- A VM, not a container: Ubuntu 24.04, the NVIDIA driver, Docker with the compose plugin and the NVIDIA Container
  Toolkit (`docker run --gpus all` must work), root login by SSH key with your public key.
- 300 GB of disk for variant A with every optional file (192 GB) plus the system and the Docker images.
- Outbound access to ghcr.io, docker.io, github.com and huggingface.co.
- The install turns on the firewall (`ufw`, only SSH comes in) and turns off SSH passwords, and it does not run
  `apt upgrade` or reboot, so the NVIDIA driver stays as it is. Give it a machine of its own.

**Verda from this computer** (tested; the default `provider`, and the Verda CLI is required for it).
`brew install verda-cloud/tap/verda-cli` (v1.8.2 tested). The account holder makes API credentials in the Verda
console and saves them with `verda auth login` in their own terminal (never through a chat or an agent), or they
reach the CLI as `VERDA_CLIENT_ID` and `VERDA_CLIENT_SECRET` in the environment (the team vault's way,
`../scripts/verda-vault.py`; never on a command line), then `verda ssh-key add --name yesopen-gpu --public-key "$(cat ~/.ssh/id_ed25519_yesopen_gpu.pub)"`. In
`config.json` → `verda` set `instance_type` (`1H200.141S.44V` tested, `1B200.30V` planned; a list orders the first type with a free card in the kept disk's location, and `up --yes` waits for one for 120 minutes, `--wait-card <min>`), `ssh_key_id`
(`verda ssh-key list`) and `location` (one with a free card: `verda availability --type <type>`).
`gpu.py verda-check` checks all of it; until it passes, `start`, `stop`, `up`, `down` and `status` stop with the
setup steps (an outage of Verda's API only warns). `start --yes`
then orders the machine named `verda.hostname` with the image "Ubuntu 24.04 + CUDA 13.0 Open + Docker", or boots
the disk kept from the last session; `stop --yes` deletes the machine and keeps the disk. `up`, `down` and
`status` are the single steps. An order that ends as `no_capacity` must be removed with `down --yes` before the
next try. A team in one Verda project lists every member's key id in `ssh_key_id`, so whoever orders the machine
lets the others connect to it; `../references/gpu-engine.md`, section 2, has the details.

**A machine made elsewhere** (another provider, your own server, or a Verda machine a teammate starts for you):
`"provider": "other"` in `config.json`, `gpu.py use <address>`, then `start`. At the end `gpu.py stop`, delete the machine at the provider (keep its disk
if the provider allows it, so the 162 GB of models need not download again) and `gpu.py use --clear`.

## Status on 2 October 2026

Checked without a GPU, on a Mac and in the server image running locally:

| What | Result |
| --- | --- |
| 15 workflows in API format | all accepted by ComfyUI 0.35.0, locally and in the server image (amd64, CPU mode) |
| Tests (`tests/`) | 109 tests, 103 run without a GPU: the client, `start` / `stop` / `up` / `down` / `use` against a stand-in Verda CLI (also a deleted machine, an order without a free card, a hand-made machine, a lost connection), `verda-check` (not installed, not logged in, credentials in the environment, key ids missing, an API outage, another provider), the MiniMax H3 frame grid and file swap, H3 takes without the LTX-only settings, the voice, language and shutdown checks, the model download with its free-space check, and real jobs in ComfyUI on the core nodes. Without a local ComfyUI the 6 end-to-end tests are skipped |
| Verda commands in `client/gpu.py` | match the source of Verda CLI v1.8.2: the `vm create` flags, the `vm list` JSON fields; `vm action delete` without `--with-volumes` keeps the disk with the models |
| Polish voice | `tts` with a voice cloned from one of our own Seedance takes; Whisper read the text without differences |
| Two-character dialogue | `tts-dialog`, 3 lines: voices at 113 Hz and 208 Hz as in the samples (121 and 206 Hz), the speakers' tracks do not overlap, the mix is exactly their sum, Whisper word for word |
| Smoother motion | `interpolate`: 24 → 48 fps, 24 → 47 frames |
| Model download | real downloads from Hugging Face with SHA-256 checks, resume after an interruption, finished files skipped, a lock against two downloads at once |
| `server/bootstrap.sh` | shellcheck clean; two dry runs in a clean Ubuntu 24.04 with stand-ins for the GPU, Docker and the firewall |
| Editor container | the gym skit as rendered on the Mac: the same frames, PSNR 47.9 dB, SSIM 0.990, −14.2 LUFS |
| Edit with music in the container | downbeat 0.3 ms from the cut to the end card, −14.4 LUFS, −1.8 dBTP |

Fixed before the first server day: torchaudio 2.9+ writes files only through TorchCodec, and the base image had
neither TorchCodec nor the FFmpeg libraries, so `tts-dialog` passed validation but would have failed when run.
The image now has FFmpeg 6.1 and TorchCodec 0.17.0, and the build checks writing and reading audio.

First day on a server, 2 October 2026: 1× H200 at Verda (no B200 was free anywhere that day). Times are GPU time
from ComfyUI's own history, without queueing or transfers. Peak memory includes models that ComfyUI still held
from earlier jobs.

| Workflow | First job, with the model load | Later jobs | Peak GPU memory |
| --- | --- | --- | --- |
| `still`, Z-Image 1088×1920 | 9.6 s | 2.8 s | 13–18 GiB |
| `still-edit`, Qwen, 4 steps | 15.7 s | about 5 s | 33 GiB |
| `still-edit`, 40 steps | 36.2 s | | 29 GiB |
| `tts`, one line | 10.8 s | 2.6–5 s (8.6–15.6 s before the keep-loaded fix) | 15 GiB |
| `tts-dialog`, 5 lines, 13.8 s of sound | 14.5 s | | 15 GiB |
| `talk`, LTX-2.3, a 3–5 s take | 35.4 s | 10.8–14 s, 13.4 s on average over 21 takes | 44–49 GiB |
| `talk-voice`, a 3.5 s take | 65.7 s | | 45 GiB |
| `music`, 45 s | 17.8 s | | 38 GiB |
| `upscale`, a 4.4 s take to 1056×1920 | 63.2 s | | 49 GiB |
| `interpolate`, a 4.4 s take to 48 fps | 10.2 s | | 20 GiB |

The first install on a fresh machine took 10 min 40 s; the longest part was the 29 GB LTX-2.3 file (one stream,
about 50–70 MB/s). What the first day taught about each model (lip sync, push-ins, the voice model talking on, the
framing of Z-Image stills, phone screens, ACE-Step's tempo) is in `../references/gpu-engine.md`, section 10.

The pilot skit, "It's not you. It's your invoices.", was made from the same script and edit as the Higgsfield
version: [`../examples/gym-breakup-gpu/`](../examples/gym-breakup-gpu/). 21 lines and 21 takes, 58.8 s of
dialogue and a 2.6 s end card; 10.4 min of GPU time (voices 5.2 min, still before the keep-loaded fix; takes
4.7 min; still edits 0.6 min); QA: frames exact, −14.9 LUFS, Whisper hears exactly the caption text. The whole
session (install, a test of every template, the skit) took about 1 h and cost $4.86. Not measured yet: the B200,
and LTX-2.5, which waits for a Hugging Face token.

## Workflows

The official templates from `Comfy-Org/workflow_templates`, commit `0bfbbbfa260e` of 30 September 2026. The graphs
are as Comfy-Org publishes them, except for the patches in `workflows/patches.json`: voice and music are saved
losslessly as FLAC, the dialogue is not trimmed and also saves each speaker's track, the voice model stays in
GPU memory between jobs, and MiniMax H3 uses the 8-bit text encoder and, in `h3-talk`, our recorded line.

| Id | Template | Licence | Download | When | For |
| --- | --- | --- | --- | --- | --- |
| `still` | `image_z_image_turbo_int8` | Apache 2.0 | 12.2 GB | before start | 9:16 character stills |
| `still-edit` | `image_qwen_image_edit_2511_int8` | Apache 2.0 | 31.0 GB | background | the same character in another pose, expression or framing |
| `tts` | `audio-chatterbox_tts_multilingual` | MIT | 3.2 GB | before start | one line in 23 languages, voice cloned from a sample |
| `tts-dialog` | `audio-chatterbox_tts_dialog` | MIT | 3.2 GB | before start | a whole English conversation and each speaker's track |
| `talk` | `video_ltx2_3_ia2v` | LTX-2 Community | 43.0 GB | before start | a still and a recorded line make a lip-synced take |
| `talk-voice` | `video_ltx2_3_id_lora` | LTX-2 Community | 43.5 GB | background | voice and lips in one pass, like Seedance |
| `action` | `video_ltx2_5_i2v` | LTX-2.x Community, licence accepted on Hugging Face | 44.9 GB | background | silent reactions and B-roll from a still |
| `action-t2v` | `video_ltx2_5_t2v` | as above | 44.9 GB | background | a shot from text alone |
| `action-flf` | `video_ltx2_5_flf2v` | as above | 43.9 GB | background | a move from a first to a last frame |
| `music` | `audio_ace_step1_5_xl_turbo` | Apache 2.0 (Comfy-Org files) | 19.9 GB | background | a bed of a set length, tempo and key |
| `upscale` | `utility_seedvr2_3b_int8_upscale_video` | Apache 2.0 | 4.0 GB | background | 704×1280 → 1056×1920 |
| `interpolate` | `utility_video_frame_interpolation` | MIT and Apache 2.0 | 0.1 GB | background | extra frames |
| `two-shot` | `video_wan2_1_infinitetalk` | Apache 2.0 and MIT; the Kijai files state no licence | 29.7 GB | on request | two people talking in one frame |
| `h3-talk` | `video_minimax_h3_i2v` | MiniMax H3 Community | 53.5 GB | on request, only with MiniMax's consent | variant B: a still and a recorded line make a lip-synced take, per film instead of `talk` |
| `h3-i2v`, `h3-r2v` | `video_minimax_h3_*` | as above | 53.5 GB each | as above | variant B: a shot with the model's own sound |

Sizes count shared files in every row. Without repeats: 61.5 GB before ComfyUI starts, 101 GB in the background
(variant A automatic: 162.5 GB), 106.1 GB on request (`two-shot` 29.7 GB, MiniMax H3 76.4 GB). The 300 GB disk
holds variant A and MiniMax H3 plus the system and the Docker images; with `two-shot` as well it gets tight, and
`gpu.py fetch` refuses a download that would leave less than 15 GB free. Verda disks can only grow.

MiniMax H3 (`h3-*`) needs MiniMax's written consent: its standard licence excludes the EU, the UK, the US and
South Korea, asks for a separate authorization above $20 million of yearly revenue, and requires published videos
made with it to be marked clearly as machine-generated. With the consent, download it once onto the kept disk:
`gpu.py fetch h3-talk,h3-i2v,h3-r2v --variant-b`. Our changes to its templates: the 8-bit text encoder instead of
the 4-bit one (the H200 has no FP4 cores), 768×1344 instead of the template's 480×864, and in `h3-talk` our
recorded line anchored as the soundtrack (`workflows/patches.json`).

The LTX-2.x Community License is free for a company whose yearly revenue, with its affiliates, is under
$10 million; it forbids deepfakes of real people without their consent and asks that content made with it is
marked as generated. Check that your company qualifies before using `talk`, `talk-voice` or `action*`.

## From link to file

| Phase | What happens | Where | Who decides |
| --- | --- | --- | --- |
| 0–1. Start and reference | the link in `project.json`; Ego Browser saves the reference's frames and transcript in `reference/private/` | your computer | the agent |
| 2. Script | the joke's mechanics, the lines, the shot and sound plan, the cost | your computer | **the user says yes** |
| 3. Cast | `still`: 4 candidates per character, variants with `still-edit` | GPU | the agent |
| 4a. Voice | `tts` for every line, checked with Whisper | GPU | the agent |
| 4b. Takes | `talk` to the finished line, `action` for silent reactions | GPU | the agent |
| 4c. Music | `music` of the edit's length at a set tempo | GPU | the agent |
| 5. Edit | `cuts.json` → `edl.json` → `assemble.py`; a downbeat on the end card, the music ducked under speech | your computer or the server | the agent |
| 6. Formats and QA | 9:16, 4:5, 1:1, 16:9; −14 LUFS, true peak, frames, Whisper | your computer or the server | the agent |
| 7. Delivery | links to the files, the 9:16 to watch | your computer | **the user watches** |

Sound first: each line is made as audio, and the video is generated to it, so the lips match the sound. The
reference stays on your computer: its frames and transcript never go to the server.

## Editing: your computer or the server

The skill's scripts run in three places: directly on your computer, in the `yesopen-editor` container on your
computer (`docker build -t yesopen-editor:latest gpu/editor`), and in the same container on the server. The
container has Python 3.12, Pillow, numpy, Whisper and a static ffmpeg 8.1.

- **Your computer:** the control render of the gym skit is bit for bit the approved master (MD5 `095ffdca…`) with
  ffmpeg 8 on macOS.
- **The server:** 30 cores on the B200 for `--format all` (the H200 has 44). Neither the B200 nor the H200 has a
  hardware video encoder (NVENC), so encoding is libx264 on the CPU anyway; the GPU stays with the models.
- **Music** (`project.json` → `music`): the script finds the track's tempo and downbeat, puts a downbeat on the cut
  to the end card, ducks the bed 12 dB under every line with a 0.15 s lead, fades it out and brings the mix to
  −14 LUFS with a fixed gain and an oversampled limiter. Details and measurements:
  `../references/edit-pipeline.md`, section 8.

## Commands

```bash
G="python3 gpu/client/gpu.py"
$G templates                       # the workflows and their parameters
$G start                           # connect to the machine, or show what would be ordered
$G start --yes                     # order it if there is none (billed from now on), install, tunnel, health
$G use 203.0.113.10                # a machine made by hand; use --clear after deleting it
$G health                          # version, GPU memory, nodes and model files for every workflow
$G run tts -s text="Dzień dobry." -s language="Polish (pl)" -s voice=voices/owner.wav -o voice --name line-01
$G batch takes/batch.json          # a list of jobs; finished ones are skipped
$G fetch h3-talk,h3-i2v,h3-r2v --variant-b   # once per disk: MiniMax H3 (only with MiniMax's consent)
$G edit <project> --remote -- assemble.py --format all   # edit on the server, the result comes back
$G stop --yes                      # close the tunnel, delete the machine, keep the disk
$G up | down | status | bootstrap | tunnel [--close]     # the single steps
```

Every job writes a line to `jobs.jsonl` next to its outputs: the workflow, the ComfyUI prompt id, every value, the
input files with SHA-256, the outputs and the time.

## Choosing the card

1× B200 (180 GB) should compute about twice as fast as an H200: its Tensor cores are 2–2.5 times faster and it
runs the INT8 and NVFP4 files of the manifest natively. It holds both variants, also H3 in INT8. The B300 is a
poor fit: 0.15 POPS of INT8 instead of 4.5, and LTX-2.5 and H3 are INT8 here. The server image (PyTorch 2.13,
CUDA 13.0) supports Blackwell; the speed of the INT8 kernels on a B200 is not measured yet.

Verda prices on 2 October 2026 (price list and public API): 1× B200 (`1B200.30V`, 30 vCPU, 170 GB RAM) $6.99 an
hour on demand or $3.49 as spot, which Verda can stop at any time; 1× H200 (`1H200.141S.44V`) $4.78, spot $2.39. A
kept 300 GB disk costs $60 a month ($0.20 per GB) until you delete it. Check the prices before starting.

## Security

- ComfyUI listens on 127.0.0.1 only and has no login. It is reached only through the SSH tunnel.
- The firewall lets only SSH in. SSH accepts keys only: `01-yesopen.conf` is read before cloud-init's settings,
  and the script checks the settings after the reload.
- No `apt upgrade` and no reboot, so the NVIDIA driver is left alone.
- The Hugging Face token goes only to huggingface.co, never to the file server a download redirects to. It is
  never printed or passed as an argument.
- The server's host key is kept in a separate `~/.ssh/known_hosts_yesopen_gpu`; `up` and `use` remove an old entry
  for the address.
- Voices are cloned only from our own generated takes, from Chatterbox's voices or with the person's written
  consent. Never from the reference.

## Layout

```text
client/gpu.py            the client (only the Python 3.11+ standard library)
client/config.example.json
server/Dockerfile        ComfyUI 0.35.0, PyTorch 2.13, CUDA 13.0, the Chatterbox nodes, FFmpeg, TorchCodec
server/compose.yaml      comfyui (127.0.0.1:8188) and editor (profile edit)
server/bootstrap.sh      prepares the machine in 6 steps, safe to run again
server/fetch_models.py   downloads the models in the manifest
server/manifest.json     every model file: URL pinned to a commit, size, SHA-256, licence, stage
editor/Dockerfile        the editor container
workflows/ui/            the templates from the pinned commit, unchanged (MIT, LICENSE.txt)
workflows/api/           the same graphs in API format (api/raw: before the patches)
workflows/params/        each workflow's parameter map: node, field, type, default
workflows/patches.json   the audio-saving and voice-model patches
tools/                   fetching templates, UI → API conversion, the manifest, validation in a local ComfyUI
tests/                   tests of the client and the download
```

## Updating the templates

```bash
cd gpu
python3 tools/fetch_templates.py            # after changing the commit in workflows/templates.json
python3 tools/convert_templates.py          # conversion in a local ComfyUI 0.35 through Ego Browser (or --print-snippet)
python3 tools/build_manifest.py             # new URLs, sizes, SHA-256 and licences from Hugging Face
python3 tools/validate_local.py --comfy-dir <a local ComfyUI>
cd tests && python3 -m unittest discover -s .
```

Validation checks the graph, the nodes, the types, the options and the model file names. It does not catch errors
that only appear when a job runs, like the missing TorchCodec, so a new node from outside the core must be run
once for real.

A local ComfyUI for validation and the end-to-end tests, without a GPU (the server image in CPU mode):

```bash
docker build --platform linux/amd64 -t yesopen-comfyui:0.35.0 gpu/server
mkdir -p /tmp/comfy-test/models /tmp/comfy-test/input /tmp/comfy-test/output
docker run -d --name yesopen-comfy-test --platform linux/amd64 -p 127.0.0.1:8188:8188 \
  -v /tmp/comfy-test/models:/opt/ComfyUI/models -v /tmp/comfy-test/input:/opt/ComfyUI/input \
  -v /tmp/comfy-test/output:/opt/ComfyUI/output \
  yesopen-comfyui:0.35.0 python main.py --listen 0.0.0.0 --port 8188 --cpu --disable-auto-launch
python3 gpu/tools/validate_local.py --comfy-dir /tmp/comfy-test
```

## Nebius

For manual Nebius operations with your own service account, see [Nebius access and disk preparation](../references/nebius-operations.md). Each operator supplies their own local configuration and vault entry. Automatic provider fallback is not implemented.
