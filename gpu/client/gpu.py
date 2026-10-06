#!/usr/bin/env python3
"""gpu: run the YesOpen skit workflows on your own ComfyUI GPU server, from your computer.

Part of the skit skill (this file is <skill>/gpu/client/gpu.py). Talks to the plain ComfyUI API through an SSH
tunnel (the server listens on 127.0.0.1 only), or straight to a ComfyUI on this machine. Every job is one
official ComfyUI template in API format (workflows/api/<template>.json) plus a small map of the inputs we change
(workflows/params/<template>.json). Results land in the project folder with a jobs.jsonl line each, like the
Higgsfield engine.

  gpu.py start [--yes]                      connect to the machine if there is one; with --yes make it if there
                                            is none (billing starts); install the stack if needed, open the tunnel
  gpu.py stop [--yes]                       end the session: close the tunnel, delete the machine, keep the disk
  gpu.py templates                          list the templates and their parameters
  gpu.py health [--templates talk,tts]      is the server up, are the nodes and model files there
  gpu.py run talk -s image=stills/owner.png -s audio=voice/line-03.flac -s prompt="..." -s seconds=3.2 -o takes
  gpu.py batch takes/shots.json             run a list of jobs, skipping the ones already done
  gpu.py tunnel | tunnel --close            SSH tunnel to the server's ComfyUI on localhost:8188
  gpu.py up [--first] | down | status       create / delete the Verda machine (asks before anything is billed)
  gpu.py verda-check                        is the Verda CLI set up here (installed, logged in, key ids); what to do
  gpu.py use ADDRESS | use --clear          a machine made by hand (Verda console, another provider): its address
  gpu.py bootstrap                          install the stack on a fresh machine and start the model download
  gpu.py fetch h3-talk,h3-i2v --variant-b   download the models of an option or of MiniMax H3 on the server
  gpu.py push DIR | pull DIR                copy a project folder to / from the server
  gpu.py edit DIR [--remote] -- SCRIPT ARGS run a skit edit script in the editor container (here or on the server)

Settings and machine state live outside the skill, in $YESOPEN_GPU_HOME (default ~/.config/yesopen-gpu):
config.json (start from client/config.example.json) and state.json (written by up and down).
"""
import argparse
import hashlib
import json
import math
import os
import random
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from pathlib import Path

STACK = Path(__file__).resolve().parent.parent
API_DIR = STACK / "workflows" / "api"
PARAMS_DIR = STACK / "workflows" / "params"
MANIFEST = STACK / "server" / "manifest.json"
# your settings and the machine's address stay outside the skill, so updating or re-cloning it keeps them
HOME = Path(os.environ.get("YESOPEN_GPU_HOME", "~/.config/yesopen-gpu")).expanduser()
CONFIG = HOME / "config.json"
EXAMPLE_CONFIG = STACK / "client" / "config.example.json"
STATE = HOME / "state.json"
KNOWN_HOSTS = Path("~/.ssh/known_hosts_yesopen_gpu").expanduser()  # our machines only, renewed on every up
TUNNEL_SOCKET = Path("~/.ssh/yesopen-gpu-tunnel.sock").expanduser()
REMOTE_ROOT = "/srv/yesopen"
FILE_TYPES = {"image", "audio", "video", "mask"}
SEED_MAX = 2**31 - 1  # every seed input we use accepts at least this range


# ---------------------------------------------------------------- configuration


def load_config() -> dict:
    path = CONFIG if CONFIG.exists() else EXAMPLE_CONFIG
    config = json.loads(path.read_text())
    config["comfy_url"] = os.environ.get("GPU_COMFY_URL", config.get("comfy_url", "http://127.0.0.1:8188"))
    state = load_state()
    config["host"] = os.environ.get("GPU_HOST") or config.get("host") or state.get("ip")
    return config


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def skill_dir(config) -> Path:
    """The skit skill whose scripts the editor runs: skill_dir in the config, else the folder this stack sits in."""
    skill = Path(config.get("skill_dir") or STACK.parent).expanduser().resolve()
    if not (skill / "scripts" / "assemble.py").exists():
        raise SystemExit(f"no skit skill at {skill}: set skill_dir in {CONFIG}")
    return skill


# ---------------------------------------------------------------- building a prompt from a template


def load_template(name: str) -> tuple:
    api, params = API_DIR / f"{name}.json", PARAMS_DIR / f"{name}.json"
    if not api.exists() or not params.exists():
        known = sorted(p.stem for p in PARAMS_DIR.glob("*.json"))
        raise SystemExit(f"unknown template {name!r}; known: {', '.join(known)}")
    return json.loads(api.read_text()), json.loads(params.read_text())


def coerce(kind: str, raw):
    """Turn a command-line string (or a JSON value from a batch file) into the parameter's type."""
    if kind in ("int", "seed"):
        return int(raw)
    if kind == "float":
        return float(raw)
    if kind == "bool":
        if isinstance(raw, bool):
            return raw
        if str(raw).lower() in ("1", "true", "yes", "on"):
            return True
        if str(raw).lower() in ("0", "false", "no", "off"):
            return False
        raise ValueError(f"not a boolean: {raw}")
    return raw if isinstance(raw, str) else str(raw)


def resolve_values(spec: dict, given: dict, rng: random.Random) -> dict:
    """Template defaults < our defaults < given values; random seeds unless given. Checks required ones."""
    values = {}
    unknown = set(given) - set(spec["params"])
    if unknown:
        raise SystemExit(f"{spec['template']}: unknown parameter(s) {sorted(unknown)}; "
                         f"known: {sorted(spec['params'])}")
    for name, param in spec["params"].items():
        if name in given:
            values[name] = coerce(param["type"], given[name])
        elif "default" in param:
            values[name] = param["default"]
        elif param["type"] == "seed":
            values[name] = rng.randint(0, SEED_MAX)
        elif param.get("required"):
            raise SystemExit(f"{spec['template']}: parameter {name!r} is required ({param.get('doc', param['type'])})")
    return values


H3_FPS = 24


def frame_grid(spec: dict, values: dict) -> dict:
    """The frame count a video model makes for the asked seconds, and the seconds the audio is padded to."""
    rules = spec.get("rules") or {}
    if "h3_frames" in rules:
        return h3_frames(rules["h3_frames"], values)
    return ltx_frames(spec, values)


def h3_frames(rule: dict, values: dict) -> dict:
    """MiniMax H3 makes 17k+5 frames at 24 fps (the graph rounds up to that itself). Pad the audio to exactly that
    length: the whole soundtrack is then anchored, and the model adds no sound of its own after the line."""
    seconds = float(values[rule["seconds"]])
    frames = max(5, math.ceil(round(seconds * H3_FPS, 6)))  # up, never shorter than asked: the line must fit
    frames += (5 - frames % 17) % 17
    values[rule["seconds"]] = frames / H3_FPS
    return {"frames": frames, "seconds": frames / H3_FPS, "pad_audio": rule.get("pad_audio", [])}


def ltx_frames(spec: dict, values: dict) -> dict:
    """LTX generates 8n+1 frames. Round the shot up to whole groups of 8 frames, so the video, the trimmed audio and
    the latent length agree, and nudge the float a hair up because the graph truncates seconds*fps to an int."""
    rule = (spec.get("rules") or {}).get("ltx_frames")
    if not rule:
        return {}
    seconds, fps = float(values[rule["seconds"]]), int(values[rule["fps"]])
    frames = math.ceil(round(seconds * fps, 6) / 8) * 8
    exact = frames / fps
    kind = spec["params"][rule["seconds"]]["type"]
    if kind == "int":
        if frames % fps:
            raise SystemExit(f"{spec['template']}: {seconds} s at {fps} fps is not a whole number of 8-frame groups; "
                             f"use 24 fps or a length like {exact:.3f} s")
        values[rule["seconds"]] = frames // fps
    else:
        values[rule["seconds"]] = exact + 1e-6
    return {"frames": frames + 1, "seconds": exact, "pad_audio": rule.get("pad_audio", [])}


def set_targets(prompt: dict, param: dict, value) -> None:
    for node, name in param["targets"]:
        if node not in prompt or name not in prompt[node]["inputs"]:
            raise SystemExit(f"workflow has no input {node}.{name}")
        prompt[node]["inputs"][name] = value


def check_enum(param: dict, value, object_info: dict | None, prompt: dict) -> None:
    if param["type"] != "enum" or not object_info:
        return
    node, name = param["targets"][0]
    spec = object_info.get(prompt[node]["class_type"], {}).get("input", {})
    entry = {**spec.get("required", {}), **spec.get("optional", {})}.get(name)
    if not entry:
        return
    options = entry[0] if isinstance(entry[0], list) else (entry[1] if len(entry) > 1 else {}).get("options")
    if options and value not in options:
        raise SystemExit(f"{name}: {value!r} is not one of {options}")


# ---------------------------------------------------------------- media helpers


def png_rgba(width: int, height: int, alpha_of) -> bytes:
    """A white RGBA PNG whose alpha is alpha_of(x, y) in 0..255. Small and dependency-free (used for masks)."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows += bytes((255, 255, 255, alpha_of(x, y)))
    chunk = lambda tag, data: (struct.pack(">I", len(data)) + tag + data
                               + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b"")


def mask_file(value: str, workdir: Path) -> Path:
    """'left' / 'right' -> a half-frame mask; anything else is a path to an RGBA PNG. The Painter node scales it."""
    if value in ("left", "right"):
        width, height = 64, 64
        path = workdir / f"mask-{value}.png"
        path.write_bytes(png_rgba(width, height, lambda x, y: 255 if (x < width // 2) == (value == "left") else 0))
        return path
    return Path(value)


def pad_audio(source: Path, seconds: float, workdir: Path) -> Path:
    """Exactly `seconds` long: silence added at the end or the tail cut, as 48 kHz 24-bit WAV (lossless)."""
    target = workdir / f"{source.stem}-{seconds:.4f}s.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-af", f"apad=whole_dur={seconds:.6f}",
                    "-t", f"{seconds:.6f}", "-ar", "48000", "-c:a", "pcm_s24le", str(target)], check=True)
    return target


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# ---------------------------------------------------------------- ComfyUI HTTP API


class Comfy:
    def __init__(self, url: str, timeout: float = 60):
        self.url, self.timeout = url.rstrip("/"), timeout
        self.client_id = str(uuid.uuid4())

    def _open(self, request):
        try:
            return urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors="replace")
            raise ComfyError(error.code, body) from None
        except urllib.error.URLError as error:
            raise SystemExit(f"cannot reach ComfyUI at {self.url} ({error.reason}); is the tunnel open? "
                             f"run: gpu.py tunnel") from None

    def get(self, path: str):
        with self._open(urllib.request.Request(self.url + path)) as response:
            return json.loads(response.read())

    def get_bytes(self, path: str) -> bytes:
        with self._open(urllib.request.Request(self.url + path)) as response:
            return response.read()

    def post(self, path: str, payload=None):
        data = json.dumps(payload if payload is not None else {}).encode()
        request = urllib.request.Request(self.url + path, data=data, headers={"Content-Type": "application/json"})
        with self._open(request) as response:
            body = response.read()
            return json.loads(body) if body.strip() else None

    def upload(self, path: Path) -> str:
        """Upload into ComfyUI's input folder under a content-addressed name, so re-runs do not upload twice."""
        name = f"{sha256(path)[:16]}-{path.name}"
        boundary = uuid.uuid4().hex
        parts = []
        for field, value in (("type", "input"), ("overwrite", "true")):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                     f"Content-Type: application/octet-stream\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        request = urllib.request.Request(self.url + "/upload/image", data=b"".join(parts),
                                         headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with self._open(request) as response:
            info = json.loads(response.read())
        return f"{info['subfolder']}/{info['name']}" if info.get("subfolder") else info["name"]

    def queue(self, prompt: dict) -> str:
        try:
            return self.post("/prompt", {"prompt": prompt, "client_id": self.client_id})["prompt_id"]
        except ComfyError as error:
            raise SystemExit("ComfyUI rejected the workflow:\n" + describe_rejection(error.body)) from None

    def cancel(self, prompt_id: str, timeout: float = 60) -> None:
        """Remove a job from the queue, or stop it if it already started, and wait until it is gone. On an idle
        server a job starts as soon as it is accepted, so a very short one may finish before the stop arrives."""
        self.post("/queue", {"delete": [prompt_id]})
        deadline = time.time() + timeout
        while time.time() < deadline:
            queue = self.get("/queue")
            if prompt_id not in [item[1] for item in queue.get("queue_running", []) + queue.get("queue_pending", [])]:
                return
            self.post("/interrupt", {"prompt_id": prompt_id})
            time.sleep(0.5)
        raise SystemExit(f"could not stop job {prompt_id}")

    def wait(self, prompt_id: str, timeout: float, poll: float = 2.0, say=print) -> dict:
        start, last = time.time(), None
        while time.time() - start < timeout:
            history = self.get(f"/history/{prompt_id}").get(prompt_id)
            if history and history.get("status", {}).get("completed") is not None:
                status = history["status"]
                if status.get("status_str") == "error" or not status.get("completed"):
                    raise SystemExit("job failed:\n" + describe_failure(status))
                return history
            queue = self.get("/queue")
            running = [item[1] for item in queue.get("queue_running", [])]
            pending = [item[1] for item in sorted(queue.get("queue_pending", []))]
            note = "running" if prompt_id in running else (
                f"waiting, {pending.index(prompt_id) + 1} in line" if prompt_id in pending else "finishing")
            if note != last:
                say(f"  {note} ({time.time() - start:.0f} s)")
                last = note
            time.sleep(poll)
        raise SystemExit(f"timed out after {timeout:.0f} s; the job keeps running on the server: {prompt_id}")


class ComfyError(Exception):
    def __init__(self, code: int, body: str):
        super().__init__(f"HTTP {code}: {body[:300]}")
        self.code, self.body = code, body


def describe_rejection(body: str) -> str:
    try:
        data = json.loads(body)
    except ValueError:
        return body[:2000]
    lines = [f"  {data.get('error', {}).get('message', '')} {data.get('error', {}).get('details', '')}".rstrip()]
    for node, info in (data.get("node_errors") or {}).items():
        for err in info.get("errors", []):
            lines.append(f"  node {node} ({info.get('class_type')}): {err.get('message')} {err.get('details', '')}")
    return "\n".join(lines)


def describe_failure(status: dict) -> str:
    for event, data in status.get("messages", []):
        if event == "execution_error":
            return (f"  node {data.get('node_id')} ({data.get('node_type')}): {data.get('exception_type')}: "
                    f"{data.get('exception_message', '').strip()[:1500]}")
        if event == "execution_interrupted":
            return "  interrupted"
    return json.dumps(status)[:1500]


def output_files(history: dict, node: str) -> list:
    """File records ({filename, subfolder, type}) and texts a node produced."""
    found = []
    for key, items in (history.get("outputs", {}).get(node) or {}).items():
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and item.get("filename"):
                found.append(item)
            elif key == "text" and isinstance(item, str):
                found.append({"text": item})
    return found


# ---------------------------------------------------------------- one job


def prepare_job(template: str, given: dict, rng: random.Random, workdir: Path, object_info=None) -> dict:
    prompt, spec = load_template(template)
    spec.setdefault("template", template)
    values = resolve_values(spec, given, rng)
    frames = frame_grid(spec, values)
    files = {}
    for name, param in spec["params"].items():
        if name not in values:
            continue
        value = values[name]
        if param["type"] in FILE_TYPES:
            path = mask_file(value, workdir) if param["type"] == "mask" else Path(value).expanduser()
            if not path.exists():
                raise SystemExit(f"{name}: file not found: {path}")
            if name in frames.get("pad_audio", []):
                path = pad_audio(path, frames["seconds"], workdir)
            files[name] = path
        else:
            check_enum(param, value, object_info, prompt)
            set_targets(prompt, param, value)
    return {"template": template, "prompt": prompt, "spec": spec, "values": values, "files": files, "frames": frames}


def run_job(comfy: Comfy, job: dict, out_dir: Path, name: str, timeout: float, validate_only=False, say=print) -> dict:
    prompt, spec = job["prompt"], job["spec"]
    uploads = {}
    for param_name, path in job["files"].items():
        uploads[param_name] = comfy.upload(path)
        set_targets(prompt, spec["params"][param_name], uploads[param_name])
    started = time.time()
    prompt_id = comfy.queue(prompt)
    if validate_only:
        comfy.cancel(prompt_id)
        return {"template": job["template"], "prompt_id": prompt_id, "validated": True}
    say(f"{name}: queued {job['template']} as {prompt_id}")
    history = comfy.wait(prompt_id, timeout, say=say)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = {}
    for label, node in spec["outputs"].items():
        for index, item in enumerate(output_files(history, node)):
            suffix = f"-{index}" if index else ""
            if "text" in item:
                target = out_dir / f"{name}.{label}{suffix}.txt"
                target.write_text(item["text"])
            else:
                query = urllib.parse.urlencode({k: item.get(k, "") for k in ("filename", "subfolder", "type")})
                target = out_dir / f"{name}.{label}{suffix}{Path(item['filename']).suffix}"
                target.write_bytes(comfy.get_bytes(f"/view?{query}"))
            saved.setdefault(label, []).append(str(target))
    if not any(label in saved for label in spec["outputs"] if label != "final_prompt"):
        raise SystemExit(f"{name}: the job finished but produced no output files")
    record = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "engine": "gpu", "name": name, "template": job["template"],
        "prompt_id": prompt_id, "seconds": round(time.time() - started, 1),
        "values": {k: (str(v) if k in job["files"] else v) for k, v in job["values"].items()},
        "inputs": {k: {"file": str(p), "sha256": sha256(p)} for k, p in job["files"].items()},
        "outputs": saved, "frames": job["frames"] or None,
    }
    with open(out_dir / "jobs.jsonl", "a") as log:
        log.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def parse_sets(pairs: list) -> dict:
    given = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--set needs key=value, got {pair!r}")
        key, value = pair.split("=", 1)
        given[key.strip()] = value
    return given


# ---------------------------------------------------------------- commands


def cmd_templates(args, config):
    for path in sorted(PARAMS_DIR.glob("*.json")):
        spec = json.loads(path.read_text())
        print(f"{path.stem}: {spec['doc']}")
        for name, param in spec["params"].items():
            flags = " required" if param.get("required") else (f" = {param['default']!r}" if "default" in param else "")
            doc = f"  {param['doc']}" if param.get("doc") else ""
            print(f"    {name:18} {param['type']:6}{flags}{doc}")
        print(f"    -> outputs: {', '.join(spec['outputs'])}")


def cmd_health(args, config):
    comfy = Comfy(config["comfy_url"])
    stats = comfy.get("/system_stats")
    system = stats.get("system", {})
    print(f"ComfyUI {system.get('comfyui_version')} (python {system.get('python_version', '').split()[0]})")
    for device in stats.get("devices", []):
        print(f"  {device.get('name')}: {device.get('vram_free', 0) / 2**30:.0f} of "
              f"{device.get('vram_total', 0) / 2**30:.0f} GiB free")
    wanted = args.templates.split(",") if args.templates else sorted(p.stem for p in PARAMS_DIR.glob("*.json"))
    object_info = comfy.get("/object_info")
    manifest = json.loads(MANIFEST.read_text())
    listings, problems = {}, 0
    for template in wanted:
        prompt, _ = load_template(template)
        missing_nodes = sorted({n["class_type"] for n in prompt.values()} - set(object_info))
        missing_files = []
        for entry in manifest["files"]:
            if template not in entry["templates"] or entry["directory"].startswith("chatterbox/"):
                continue  # the Chatterbox weights live outside ComfyUI's model folders; fetch_models.py checks them
            folder = entry["directory"]
            if folder not in listings:
                try:
                    listings[folder] = set(comfy.get(f"/models/{urllib.parse.quote(folder)}"))
                except ComfyError:
                    listings[folder] = set()
            if entry["name"] not in listings[folder]:
                missing_files.append(f"{folder}/{entry['name']}")
        ok = not missing_nodes and not missing_files
        problems += not ok
        print(f"  {'ok ' if ok else 'NO '} {template:12}"
              + (f" missing nodes: {', '.join(missing_nodes)}" if missing_nodes else "")
              + (f" missing files: {', '.join(missing_files)}" if missing_files else ""))
    return 1 if problems else 0


def cmd_run(args, config):
    comfy = Comfy(config["comfy_url"])
    with tempfile.TemporaryDirectory(prefix="gpu-job-") as tmp:
        job = prepare_job(args.template, parse_sets(args.set), random.Random(), Path(tmp),
                          comfy.get("/object_info") if args.check_enums else None)
        name = args.name or f"{args.template}-{time.strftime('%Y%m%d-%H%M%S')}"
        record = run_job(comfy, job, Path(args.out), name, args.timeout, args.validate_only)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


def cmd_batch(args, config):
    """A list of jobs: {"jobs": [{"name": "o1", "template": "talk", "set": {...}}]}. Paths are relative to the file."""
    batch_file = Path(args.file).resolve()
    jobs = json.loads(batch_file.read_text())["jobs"]
    out_dir = Path(args.out).resolve() if args.out else batch_file.parent
    done = set()
    if (out_dir / "jobs.jsonl").exists() and not args.force:
        done = {json.loads(line)["name"] for line in (out_dir / "jobs.jsonl").read_text().splitlines() if line.strip()}
    comfy = Comfy(config["comfy_url"])
    failed = 0
    for item in jobs:
        if item["name"] in done:
            print(f"{item['name']}: already done, skipped")
            continue
        _, spec = load_template(item["template"])
        given = {}
        for key, value in item.get("set", {}).items():
            kind = spec["params"].get(key, {}).get("type")
            relative = kind in FILE_TYPES and not (kind == "mask" and value in ("left", "right"))
            given[key] = str((batch_file.parent / value).resolve()) if relative else value
        with tempfile.TemporaryDirectory(prefix="gpu-job-") as tmp:
            try:
                job = prepare_job(item["template"], given, random.Random(), Path(tmp))
                record = run_job(comfy, job, out_dir, item["name"], args.timeout)
                print(f"{item['name']}: done in {record['seconds']} s -> {', '.join(sum(record['outputs'].values(), []))}")
            except SystemExit as error:
                failed += 1
                print(f"{item['name']}: FAILED {error}", file=sys.stderr)
                if not args.keep_going:
                    return 1
    return 1 if failed else 0


def ssh_base(config) -> list:
    if not config.get("host"):
        raise SystemExit(f"no server address: gpu.py start (Verda), gpu.py use ADDRESS (a machine made by hand), "
                         f"host in {CONFIG}, or GPU_HOST")
    key = str(Path(config.get("ssh_key", "~/.ssh/id_ed25519_yesopen_gpu")).expanduser())
    return ["ssh", "-i", key, "-o", "IdentitiesOnly=yes", "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
            "-o", "StrictHostKeyChecking=accept-new", "-o", "ServerAliveInterval=30",
            f"{config.get('ssh_user', 'root')}@{config['host']}"]


def cmd_tunnel(args, config):
    socket = TUNNEL_SOCKET
    if args.close:
        if not socket.exists():
            print("no tunnel open")
            return 0
        # a control command goes to the local master process; it needs no address, also after gpu.py use --clear
        target = f"{config.get('ssh_user', 'root')}@{config['host']}" if config.get("host") else "yesopen-gpu"
        try:
            subprocess.run(["ssh", "-S", str(socket), "-O", "exit", target], check=False, timeout=15)
        except subprocess.TimeoutExpired:
            # the machine is gone and the tunnel's master process no longer answers: stop it here
            subprocess.run(["pkill", "-f", "--", f"-S {socket}"], check=False)
            print("the tunnel did not answer (is the machine gone?); stopped it")
        socket.unlink(missing_ok=True)
        return 0
    base = ssh_base(config)
    port = urllib.parse.urlparse(config["comfy_url"]).port or 8188
    if socket.exists():
        check = subprocess.run(base[:-1] + ["-S", str(socket), "-O", "check", base[-1]], capture_output=True)
        if check.returncode == 0:
            print(f"tunnel already open: {config['comfy_url']}")
            return 0
        socket.unlink()
    subprocess.run(base[:-1] + ["-f", "-N", "-M", "-S", str(socket), "-o", "ExitOnForwardFailure=yes",
                                "-L", f"{port}:127.0.0.1:8188", base[-1]], check=True)
    print(f"tunnel open: {config['comfy_url']} -> {config['host']}:8188 (close with: gpu.py tunnel --close)")
    return 0


def verda(args: list, capture=True):
    if not shutil.which("verda"):
        raise SystemExit("the Verda CLI is missing: brew install verda-cloud/tap/verda-cli, then verda auth login")
    result = subprocess.run(["verda", "--agent", *args], capture_output=capture, text=True)
    if result.returncode != 0:
        raise SystemExit(f"verda {' '.join(args[:3])} failed:\n{(result.stderr or result.stdout)[-2000:]}")
    return json.loads(result.stdout) if capture and result.stdout.strip().startswith(("{", "[")) else result.stdout


GONE = ("discontinued", "deleting", "notfound", "deleted")  # a machine in these states is gone or going


def find_instance(hostname: str):
    for item in verda(["vm", "list", "-o", "json"]) or []:
        if item.get("hostname") == hostname and item.get("status") not in GONE:
            return item
    return None


def describe_instance(item: dict) -> str:
    # print only these fields; the CLI's JSON also carries secrets such as a Jupyter token
    return (f"{item.get('hostname')} {item.get('status')} ip={item.get('ip')} type={item.get('instance_type')} "
            f"${item.get('price_per_hour')}/h os_volume={item.get('os_volume_id')}")


def require_verda(config) -> None:
    """status, up and down drive Verda machines: stop with the setup steps, or say why Verda cannot be used now."""
    if not verda_ready(config):
        raise SystemExit("This command drives Verda machines, and Verda cannot be used now: "
                         + ("provider is not \"verda\" in the config." if config.get("provider", "verda") != "verda"
                            else "its API does not answer (see the warning above); try again later."))


def cmd_status(args, config):
    require_verda(config)
    machine = config["verda"]
    item = find_instance(machine["hostname"])
    print(describe_instance(item) if item else f"no machine called {machine['hostname']}; disk: "
          f"{load_state().get('os_volume_id') or 'none recorded'}")
    return 0


def kept_disk(machine: dict, state: dict):
    """The disk with the models: the one in state.json, else the volume called verda.os_volume_name in Verda
    (a fresh state.json on another computer must not lead to a new, empty disk)."""
    volumes = verda(["volume", "list", "-o", "json"]) or []
    by_id = next((v for v in volumes if v.get("id") == state.get("os_volume_id")), None) if state.get("os_volume_id") else None
    # an id in state.json that Verda no longer lists (deleted by hand) falls back to the name, so the location is known
    by_name = next((v for v in volumes if v.get("name") == machine["os_volume_name"]), None)
    return by_id or by_name or ({"id": state["os_volume_id"]} if state.get("os_volume_id") else None)


def free_type(types: list, location: str):
    """The first instance type in the order of the config with a free card in the location, or None when every one
    is reported as not available. An answer without the `available` field (or no answer) is no reason to wait: the
    order is tried and Verda decides."""
    for kind in types:
        info = verda(["availability", "--type", kind, "--location", location, "-o", "json"]) or {}
        if info.get("available", True):
            return kind
    return None


CARD_POLL = 60  # seconds between two looks for a free card
CARD_WAIT = 120  # minutes to wait for a free card before giving up (--wait-card)


def cmd_up(args, config):
    require_verda(config)
    machine, state = config["verda"], load_state()
    existing = find_instance(machine["hostname"])
    if existing:
        raise SystemExit(f"{machine['hostname']} already exists ({existing.get('status')}); gpu.py status, "
                         f"or gpu.py down --yes to remove it")
    for key in ("instance_type", "ssh_key_id"):
        if not machine.get(key):
            raise SystemExit(f"set verda.{key} in {CONFIG} first "
                             f"({'verda instance-types --gpu' if key == 'instance_type' else 'verda ssh-key list'})")
    # one type, or a list in order of preference (B200 first, then H200): the first with a free card is ordered
    types = machine["instance_type"] if isinstance(machine["instance_type"], list) else [machine["instance_type"]]
    disk = None if args.first else kept_disk(machine, state)
    # the kept disk only boots where it is: wait for a card there instead of starting over on a new disk elsewhere
    location = (disk or {}).get("location") or machine["location"]
    kind = free_type(types, location)
    if kind is None and args.yes:
        limit = getattr(args, "wait_card", None)
        limit = CARD_WAIT if limit is None else limit
        print(f"no free card of {', '.join(types)} in {location}; waiting for one, up to {limit} min (Ctrl+C to give up)")
        waited = 0
        while kind is None:
            if waited >= limit * 60:
                print(f"no free card after {limit} min; nothing was ordered. Try again later or with --wait-card <min>.")
                return 1
            time.sleep(CARD_POLL)
            waited += CARD_POLL
            kind = free_type(types, location)
        print(f"free card: {kind} in {location}")
    # one key id, or a list: every key on the team, so whoever runs start later can reach the machine
    keys = machine["ssh_key_id"] if isinstance(machine["ssh_key_id"], list) else [machine["ssh_key_id"]]
    command = ["vm", "create", "--kind", "gpu", "--instance-type", kind or types[0],
               "--location", location, "--hostname", machine["hostname"]]
    for key_id in keys:
        command += ["--ssh-key", key_id]
    command += ["--contract", machine.get("contract", "pay_as_go"), "--wait", "--wait-timeout", "20m", "-o", "json"]
    if disk:
        command += ["--os", disk["id"]]  # boot the kept disk: models and images are already there
    else:
        command += ["--os", machine["os"], "--os-volume-size", str(machine["os_volume_size"]),
                    "--os-volume-name", machine["os_volume_name"]]
    print("verda " + " ".join(shlex.quote(c) for c in command))
    if not args.yes:
        if kind is None:
            print(f"No free card of {', '.join(types)} in {location} right now; with --yes this waits for one.")
        print("This starts billing for the machine. Run again with --yes to create it.")
        return 0
    try:
        verda(command)
    except SystemExit as error:
        raise SystemExit(f"{error}\nThe order may still have made a machine that bills: check gpu.py status "
                         f"and remove it with gpu.py down --yes.") from None
    item = find_instance(machine["hostname"])
    if not item:
        raise SystemExit("the machine was created but does not show in verda vm list yet; check gpu.py status")
    state.update({"instance_id": item["id"], "ip": item.get("ip"), "os_volume_id": item.get("os_volume_id")})
    save_state(state)
    if item.get("ip"):
        # a fresh OS has a new host key and Verda may give us an address we had before: trust the key on first use
        subprocess.run(["ssh-keygen", "-R", item["ip"], "-f", str(KNOWN_HOSTS)], capture_output=True)
    print(describe_instance(item))
    if item.get("status") != "running":
        # --wait stops at any final status; no_capacity and offline end the wait without an error
        print(f"The machine is {item.get('status')}, not running. Remove the order with gpu.py down --yes"
              + (f"; for free capacity see verda availability --type {kind or types[0]}"
                 if item.get("status") == "no_capacity" else "") + ".")
        return 1
    return 0


def cmd_down(args, config):
    require_verda(config)
    machine, state = config["verda"], load_state()
    item = find_instance(machine["hostname"])
    if not item:
        print(f"no machine called {machine['hostname']}")
        return 0
    command = ["vm", "action", "--id", item["id"], "--action", "delete", "--yes"]
    print("verda " + " ".join(command) + "   # without --with-volumes: the disk with the models stays")
    if not args.yes:
        print("Run again with --yes to delete the machine. The disk keeps billing until you delete it in Verda.")
        return 0
    verda(command)
    state.update({"instance_id": None, "ip": None, "os_volume_id": item.get("os_volume_id") or state.get("os_volume_id")})
    save_state(state)
    print(f"deleted {machine['hostname']}; kept disk {state['os_volume_id']}")
    return 0


STAMP = f"{REMOTE_ROOT}/stack-stamp"  # what the server was installed from, written after every bootstrap
CORE_TEMPLATES = "still,tts,talk"  # downloaded before ComfyUI starts; the rest follows in the background


def stack_stamp() -> str:
    """A fingerprint of what the server's installation depends on: images, compose file, setup and model list."""
    digest = hashlib.sha256()
    for name in ("server/Dockerfile", "server/compose.yaml", "server/bootstrap.sh", "server/fetch_models.py",
                 "server/manifest.json", "editor/Dockerfile"):
        digest.update((STACK / name).read_bytes())
    return digest.hexdigest()[:16]


def remote_text(config, command: str, timeout: float = 60):
    """Output of a command on the server, or None when it fails or the machine does not answer."""
    try:
        base = ssh_base(config)
        # key only and a short connect timeout: a machine that is still booting answers "not yet", not a prompt
        result = subprocess.run(base[:-1] + ["-o", "ConnectTimeout=15", "-o", "BatchMode=yes", base[-1], command],
                                capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def wait_for(check, what: str, minutes: float, every: float = 10) -> None:
    deadline = time.time() + minutes * 60
    while not check():
        if time.time() > deadline:
            raise SystemExit(f"{what}: not ready after {minutes:g} min")
        print(f"waiting for {what}...")
        time.sleep(every)


VERDA_SETUP = """\
Machines at Verda are made and deleted with the Verda CLI, and it is not set up on this computer yet. Set it up
before the first session (the person who owns the Verda account does steps 2 and 3, never an agent):
  1. install it: brew install verda-cloud/tap/verda-cli
  2. in the Verda console, in the project that runs your machines: Project management -> Credentials -> create
     API credentials (the secret is shown once)
  3. in your own terminal: verda auth login, then paste the client ID and the secret there. Never paste them into
     a chat or give them to an agent. With several profiles, choose one: verda auth use NAME
  4. check it: verda doctor ("Authentication valid" must be ok), then gpu.py verda-check
The CLI also takes the credentials from VERDA_CLIENT_ID and VERDA_CLIENT_SECRET in the environment (never on a
command line); gpu.py verda-check then checks them with a read-only call. A server at another provider, or a
machine a teammate starts for you, needs none of this: set "provider": "other" in the config and use gpu.py use
ADDRESS."""


def verda_check(config):
    """('ready' | 'unreachable' | 'missing', [what is wrong]) for driving Verda from this computer: the CLI is
    installed and logged in (verda doctor, or credentials in the environment) and the config names the instance
    type and the SSH key ids."""
    if not shutil.which("verda"):
        return "missing", ["the verda command is not installed"]
    try:
        result = subprocess.run(["verda", "doctor", "-o", "json"], capture_output=True, text=True, timeout=120)
        checks = {check.get("name"): check for check in json.loads(result.stdout).get("checks", [])}
    except (subprocess.TimeoutExpired, ValueError, AttributeError):
        return "unreachable", ["verda doctor gave no answer"]
    api = checks.get("API reachable") or {}
    if api.get("status", "ok") != "ok":
        return "unreachable", [f"Verda's API does not answer ({api.get('detail') or api.get('status')}): "
                               f"a maintenance window or the network"]
    if os.environ.get("VERDA_CLIENT_ID") and os.environ.get("VERDA_CLIENT_SECRET"):
        # the CLI uses these before its profile (scripts/verda-vault.py passes them so), but verda doctor only
        # looks at the profile file and then skips the login test, so a read-only call checks them instead
        try:
            probe = subprocess.run(["verda", "--agent", "vm", "list", "-o", "json"], capture_output=True, text=True,
                                   timeout=120, env={**os.environ, "VERDA_DEBUG": "false"})
        except subprocess.TimeoutExpired:
            return "unreachable", ["verda vm list gave no answer"]
        problems = [] if probe.returncode == 0 else [
            "VERDA_CLIENT_ID and VERDA_CLIENT_SECRET in the environment were refused (verda vm list failed); "
            "unset them to use the CLI's own login"]
    else:
        problems = [f"{name}: {(checks.get(name) or {}).get('status', 'no answer')}"
                    + (f" ({checks[name]['detail']})" if (checks.get(name) or {}).get("detail") else "")
                    for name in ("Credentials found", "Authentication valid")
                    if (checks.get(name) or {}).get("status") != "ok"]
    machine = config.get("verda") or {}
    for key, source in (("instance_type", "verda --agent instance-types --gpu -o json"),
                        ("ssh_key_id", "verda --agent ssh-key list -o json")):
        if not machine.get(key):
            problems.append(f"verda.{key} is empty in {CONFIG} (from: {source})")
    return ("missing" if problems else "ready"), problems


def verda_ready(config) -> bool:
    """Can this computer make and delete Verda machines? A Verda setup that is not finished stops here with the
    steps to finish it. Only an API that does not answer (maintenance, network) falls back to the known address,
    and provider "other" in the config skips Verda altogether."""
    if config.get("provider", "verda") != "verda":
        return False
    state, problems = verda_check(config)
    if state == "ready":
        return True
    if state == "unreachable":
        print(f"warning: {problems[0]}; going on with the machine's known address, if there is one")
        return False
    raise SystemExit(VERDA_SETUP + "\nWhat is missing now:\n  - " + "\n  - ".join(problems))


def cmd_verda_check(args, config):
    """Is the Verda CLI ready on this computer? Run it before the first session; it says what to set up."""
    if config.get("provider", "verda") != "verda":
        print(f"provider is {config.get('provider')!r} in the config: this setup does not use the Verda CLI")
        return 0
    state, problems = verda_check(config)
    if state == "ready":
        print("Verda CLI: ready (logged in; instance type and SSH key ids are set)")
        return 0
    if state == "unreachable":
        print(f"Verda CLI: installed, but {problems[0]}. Try again later (verda doctor shows more).")
        return 1
    print(VERDA_SETUP + "\nWhat is missing now:\n  - " + "\n  - ".join(problems))
    return 1


FAILED = ("no_capacity", "offline", "error")  # an order in these states will not start by itself


def cmd_start(args, config):
    """One command for the start of a session: use the machine if there is one, make it if there is none (only
    with --yes, because it bills from that moment), install or start the stack, open the tunnel, check."""
    if verda_ready(config):
        machine = config["verda"]
        item = find_instance(machine["hostname"])
        if item is None:
            if not args.yes:
                print("No machine is running. gpu.py start --yes makes this one; it bills from that moment:")
                cmd_up(argparse.Namespace(first=False, yes=False), config)
                return 2
            if cmd_up(argparse.Namespace(first=False, yes=True, wait_card=getattr(args, "wait_card", None)), config):
                return 1  # the order did not start; cmd_up said why and what to do
            item = find_instance(machine["hostname"])
        elif item.get("status") in FAILED:
            raise SystemExit(f"{describe_instance(item)}\nThat order will not start: remove it with "
                             f"gpu.py down --yes and run gpu.py start --yes again.")
        elif item.get("status") != "running":
            wait_for(lambda: (find_instance(machine["hostname"]) or {}).get("status") == "running",
                     f"{machine['hostname']} ({item.get('status')})", 20, 15)
            item = find_instance(machine["hostname"])
        state = load_state()
        if item.get("ip") and item["ip"] != state.get("ip"):
            state.update({"instance_id": item["id"], "ip": item["ip"], "os_volume_id": item.get("os_volume_id")})
            save_state(state)
        config["host"] = os.environ.get("GPU_HOST") or item.get("ip")
        print(f"machine: {describe_instance(item)}")
    elif config.get("host"):
        print(f"machine: {config['host']} (made by hand; gpu.py use --clear once it is deleted)")
    else:
        raise SystemExit("No machine is known. At Verda, gpu.py start --yes makes one once the Verda CLI is set up "
                         "(gpu.py verda-check; verda auth login); if Verda's API is down, try again later. At "
                         "another provider (\"provider\": \"other\" in the config), make a machine there (Ubuntu "
                         "24.04, NVIDIA driver, Docker, NVIDIA Container Toolkit, root SSH with your key) and run "
                         "gpu.py use ADDRESS.")
    wait_for(lambda: remote_text(config, "true", 40) is not None, f"SSH on {config['host']}", 10)
    stamp = stack_stamp()
    if args.bootstrap or remote_text(config, f"cat {STAMP} 2>/dev/null") != stamp:
        print("installing the stack: on a new disk about 11 min (61.5 GB of models), on a kept disk a few minutes")
        cmd_bootstrap(args, config)
        remote(config, f"echo {stamp} > {STAMP}")
    else:
        remote(config, f"cd {REMOTE_ROOT}/stack/server && docker compose up -d comfyui >/dev/null 2>&1")
        wait_for(lambda: remote_text(config, "curl -fsS -m 5 http://127.0.0.1:8188/system_stats >/dev/null", 30)
                 is not None, "ComfyUI on the server", 10)
    cmd_tunnel(argparse.Namespace(close=False), config)
    code = cmd_health(argparse.Namespace(templates=CORE_TEMPLATES), config)
    print("Ready: stills, voices and takes. Other templates arrive in the background after a first install "
          "(gpu.py health). End the session with gpu.py stop --yes." if code == 0 else
          "The core templates are not ready: see the lines above, or run gpu.py start --bootstrap.")
    return code


def cmd_stop(args, config):
    """End of a session: close the tunnel first (it hangs once the machine is gone), then delete the machine."""
    cmd_tunnel(argparse.Namespace(close=True), config)
    if verda_ready(config):
        return cmd_down(args, config)  # without --yes it only shows the command
    if not config.get("host"):
        print("No machine is known here. If one still runs at your provider, delete it there.")
        return 0
    print(f"Delete the machine at {config['host']} at your provider now (keep its disk: the next start skips the "
          "downloads), then run gpu.py use --clear.")
    return 0


def cmd_use(args, config):
    """Record the address of a machine made by hand, or forget it after the machine is deleted."""
    state = load_state()
    if args.clear:
        state["ip"] = None
        save_state(state)
        print("forgot the machine's address")
        return 0
    if not args.address:
        raise SystemExit("gpu.py use ADDRESS, or gpu.py use --clear")
    state["ip"] = args.address
    save_state(state)
    # a new machine has a new host key, also at an address we used before: trust the key on first use
    subprocess.run(["ssh-keygen", "-R", args.address, "-f", str(KNOWN_HOSTS)], capture_output=True)
    print(f"using {args.address} (state in {STATE}); next: gpu.py start")
    pinned = os.environ.get("GPU_HOST") or (json.loads(CONFIG.read_text()).get("host") if CONFIG.exists() else None)
    if pinned and pinned != args.address:
        where = "GPU_HOST" if os.environ.get("GPU_HOST") else f"host in {CONFIG}"
        print(f"note: {where} ({pinned}) still wins over this address; remove it to use {args.address}")
    return 0


def keychain_secret(service: str, account: str):
    """A secret from the macOS Keychain, or None (no such entry, or no Keychain on this system)."""
    if not shutil.which("security"):
        return None
    result = subprocess.run(["security", "find-generic-password", "-s", service, "-a", account, "-w"],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def rsync(config, sources: list, target: str, excludes=()) -> None:
    ssh = " ".join(shlex.quote(part) for part in ssh_base(config)[:-1])
    command = ["rsync", "-az", "-e", ssh]
    for pattern in excludes:
        command += ["--exclude", pattern]
    subprocess.run(command + sources + [target], check=True)


def remote(config, command: str, stdin: str | None = None) -> None:
    subprocess.run(ssh_base(config) + [command], input=stdin, text=True, check=True)


def cmd_bootstrap(args, config):
    """Copy the stack, hand over the HF token through stdin (never as an argument), run server/bootstrap.sh."""
    host = ssh_base(config)[-1]
    remote(config, f"mkdir -p {REMOTE_ROOT}/stack")
    rsync(config, [f"{STACK}/"], f"{host}:{REMOTE_ROOT}/stack/",
          excludes=[".git", "client/config.json", "client/state.json", "__pycache__", "*.pyc", "tests/out",
                    ".DS_Store"])
    token = os.environ.get("HF_TOKEN") or keychain_secret("huggingface", "token")
    if token:
        remote(config, f"umask 077 && cat > {REMOTE_ROOT}/stack/server/.env", stdin=f"HF_TOKEN={token}\n")
    else:
        print("no Hugging Face token (Keychain service 'huggingface', account 'token'): LTX-2.5 will be skipped")
    remote(config, f"bash {REMOTE_ROOT}/stack/server/bootstrap.sh")
    return 0


def cmd_fetch(args, config):
    """Download the models of templates that no stage fetches by itself: an option (two-shot) or variant B (MiniMax
    H3, --variant-b, only with MiniMax's consent). Runs fetch_models.py on the server, which checks the free disk
    space before the first byte. ComfyUI sees the new files without a restart."""
    templates = [t for t in args.templates.split(",") if t]
    files = json.loads(MANIFEST.read_text())["files"]
    unknown = sorted(set(templates) - {t for entry in files for t in entry["templates"]})
    if unknown:
        raise SystemExit(f"no model files listed for {', '.join(unknown)} (gpu.py templates lists the templates)")
    variant_b = sorted({t for entry in files if entry["variant"] == "B" for t in entry["templates"]} & set(templates))
    if variant_b and not args.variant_b:
        raise SystemExit(f"{', '.join(variant_b)}: MiniMax H3 (variant B), only with MiniMax's consent; "
                         f"add --variant-b once you have it")
    if remote_text(config, f"cat {STAMP} 2>/dev/null") != stack_stamp():
        raise SystemExit("the server runs other stack files than this skill (or does not answer): run gpu.py start, "
                         "which installs them, then fetch again")
    command = (f"cd {REMOTE_ROOT}/stack/server && set -a && {{ [ ! -f .env ] || . ./.env; }} && set +a && "
               f"python3 fetch_models.py --models {REMOTE_ROOT}/models --templates {shlex.quote(','.join(templates))}"
               f"{' --variant-b' if args.variant_b else ''} --jobs 6{' --check' if args.check else ''}")
    return subprocess.run(ssh_base(config) + [command]).returncode


def cmd_push(args, config):
    source = Path(args.dir).resolve()
    host = ssh_base(config)[-1]
    remote(config, f"mkdir -p {REMOTE_ROOT}/projects/{source.name}")
    rsync(config, [f"{source}/"], f"{host}:{REMOTE_ROOT}/projects/{source.name}/", excludes=["edit/work"])
    return 0


def cmd_pull(args, config):
    target = Path(args.dir).resolve()
    host = ssh_base(config)[-1]
    rsync(config, [f"{host}:{REMOTE_ROOT}/projects/{target.name}/"], f"{target}/", excludes=["edit/work"])
    return 0


def cmd_edit(args, config):
    """Run one skit-skill script (assemble.py, qa_report.py, ...) in the editor container, here or on the server."""
    project = Path(args.dir).resolve()
    script, rest = args.script[0], args.script[1:]
    if args.remote:
        cmd_push(argparse.Namespace(dir=str(project)), config)
        skill = skill_dir(config)
        host = ssh_base(config)[-1]
        # the editor needs the scripts and assets only: not the examples, the GPU stack or the skill's Git history
        rsync(config, [f"{skill}/"], f"{host}:{REMOTE_ROOT}/skill/",
              excludes=[".git", "examples", "gpu", ".venv", "__pycache__", "*.pyc"])
        inner = " ".join(shlex.quote(x) for x in ["python3", f"/skill/scripts/{script}", f"/work/{project.name}", *rest])
        remote(config, f"cd {REMOTE_ROOT}/stack/server && docker compose run --rm editor {inner}")
        cmd_pull(argparse.Namespace(dir=str(project)), config)
        return 0
    skill = skill_dir(config)
    command = ["docker", "run", "--rm", "-v", f"{skill}:/skill:ro", "-v", f"{project}:/work/{project.name}",
               "-w", f"/work/{project.name}", config.get("editor_image", "yesopen-editor:latest"),
               "python3", f"/skill/scripts/{script}", f"/work/{project.name}", *rest]
    return subprocess.run(command).returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="gpu.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("templates", help="list templates and parameters").set_defaults(func=cmd_templates)
    p = sub.add_parser("health", help="check server, nodes and model files")
    p.add_argument("--templates", help="comma-separated; default all")
    p.set_defaults(func=cmd_health)
    p = sub.add_parser("run", help="run one template")
    p.add_argument("template")
    p.add_argument("-s", "--set", action="append", metavar="KEY=VALUE")
    p.add_argument("-o", "--out", default=".")
    p.add_argument("--name")
    p.add_argument("--timeout", type=float, default=7200)
    p.add_argument("--validate-only", action="store_true", help="let ComfyUI check the job, then cancel it")
    p.add_argument("--check-enums", action="store_true", help="check option values against the server first")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("batch", help="run a list of jobs")
    p.add_argument("file")
    p.add_argument("-o", "--out")
    p.add_argument("--force", action="store_true", help="also re-run jobs already in jobs.jsonl")
    p.add_argument("--keep-going", action="store_true")
    p.add_argument("--timeout", type=float, default=7200)
    p.set_defaults(func=cmd_batch)
    p = sub.add_parser("tunnel", help="open or close the SSH tunnel")
    p.add_argument("--close", action="store_true")
    p.set_defaults(func=cmd_tunnel)
    sub.add_parser("verda-check", help="is the Verda CLI set up here, and what to do if not").set_defaults(
        func=cmd_verda_check)
    sub.add_parser("status", help="show the Verda machine").set_defaults(func=cmd_status)
    p = sub.add_parser("up", help="create the Verda machine (billing starts)")
    p.add_argument("--first", action="store_true", help="fresh OS image instead of the kept disk")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--wait-card", type=int, metavar="MIN", help=f"with --yes: minutes to wait for a free card (default {CARD_WAIT})")
    p.set_defaults(func=cmd_up)
    p = sub.add_parser("down", help="delete the Verda machine, keep the disk")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_down)
    p = sub.add_parser("start", help="connect to the machine, or make it (--yes), and get ComfyUI ready")
    p.add_argument("--yes", action="store_true", help="make the machine if there is none (billing starts)")
    p.add_argument("--first", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--bootstrap", action="store_true", help="install the stack again even if it is current")
    p.add_argument("--wait-card", type=int, metavar="MIN", help=f"minutes to wait for a free card (default {CARD_WAIT})")
    p.set_defaults(func=cmd_start)
    p = sub.add_parser("stop", help="close the tunnel and delete the machine (--yes); the disk stays")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_stop)
    p = sub.add_parser("use", help="the address of a machine made by hand (Verda console, another provider)")
    p.add_argument("address", nargs="?")
    p.add_argument("--clear", action="store_true", help="forget it, after the machine is deleted")
    p.set_defaults(func=cmd_use)
    sub.add_parser("bootstrap", help="install the stack on the machine").set_defaults(func=cmd_bootstrap)
    p = sub.add_parser("fetch", help="download the models of an option (two-shot) or of MiniMax H3 on the server")
    p.add_argument("templates", help="comma-separated, e.g. h3-talk,h3-i2v,h3-r2v")
    p.add_argument("--variant-b", action="store_true", help="MiniMax H3: only with MiniMax's consent")
    p.add_argument("--check", action="store_true", help="only report what is missing and the free disk space")
    p.set_defaults(func=cmd_fetch)
    for name, func in (("push", cmd_push), ("pull", cmd_pull)):
        p = sub.add_parser(name, help=f"{name} a project folder")
        p.add_argument("dir")
        p.set_defaults(func=func)
    p = sub.add_parser("edit", help="run a skit edit script in the editor container")
    p.add_argument("dir")
    p.add_argument("--remote", action="store_true")
    p.add_argument("script", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_edit)
    args = parser.parse_args(argv)
    if getattr(args, "script", None) and args.script[0] == "--":
        args.script = args.script[1:]
    return args.func(args, load_config()) or 0


if __name__ == "__main__":
    sys.exit(main())
