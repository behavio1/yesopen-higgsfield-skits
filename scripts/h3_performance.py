#!/usr/bin/env python3
"""Prepare, submit or resume one H3 performance-reference pilot on an existing ComfyUI.

prepare is offline; run requires --execute and never provisions a server. See references/h3-performance.md.
"""
import argparse
import fcntl
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gpu" / "client"))
import gpu

VERSION = "2026.10.26"
ACTING = ("objective", "subtext", "emotion_start", "emotion_end", "delivery", "gesture",
          "listener", "start", "action", "end", "hold", "camera")


def save(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label}: expected a number in {low}..{high}")
    return value


def asset(spec, base, kind):
    if not isinstance(spec, dict) or set(spec) - {"file", "permission", "start", "seconds"}:
        raise ValueError(f"{kind}: expected file, permission, and optional start/seconds")
    if (not isinstance(spec.get("permission"), str) or not spec["permission"].strip()
            or spec["permission"].startswith("Replace with")):
        raise ValueError(f"{kind}: record the ownership/consent and permission to upload")
    path = (base / spec["file"]).resolve()
    if not path.is_file():
        raise ValueError(f"{kind}: missing file {path}")
    if any(a == "reference" and b == "private" for a, b in zip(path.parts, path.parts[1:])):
        raise ValueError("reference/private is analysis-only; use a separately authorized performance asset")
    info = probe(path)
    stream_type = "audio" if kind == "voice" else "video"
    streams = [s for s in info["streams"] if s["codec_type"] == stream_type]
    if not streams:
        raise ValueError(f"{kind}: missing {stream_type} stream")
    result = {"path": path, "sha256": gpu.sha256(path), "permission": spec["permission"]}
    if kind != "identity":
        start = number(spec.get("start", 0), f"{kind}.start", 0, 86400)
        seconds = number(spec.get("seconds"), f"{kind}.seconds", 2, 15)
        duration = float(streams[0].get("duration") or info["format"]["duration"])
        if start + seconds > duration + 0.025:
            raise ValueError(f"{kind}: selected interval exceeds source duration")
        result.update(start=start, seconds=seconds)
    return result


def direction(shot, with_voice):
    acting = shot.get("acting", {})
    if set(acting) != set(ACTING) or any(not isinstance(acting[k], str) or not acting[k].strip() for k in ACTING):
        raise ValueError("acting must supply non-empty fields: " + ", ".join(ACTING))
    for key in ("language", "dialogue"):
        if not isinstance(shot.get(key), str) or not shot[key].strip():
            raise ValueError(f"{key}: required (use '[silent]' for a silent shot)")
    return "\n".join([
        "Use <Picture 1> for the character's identity, wardrobe and setting.",
        "Use <Video 1> only for performance timing, gaze, expression and body motion; do not copy its identity, setting or words.",
        ("Use <Audio 1> for the authorized voice and expressive delivery; speak only the dialogue below."
         if with_voice else "Generate natural expressive speech matching the character; no reference voice is supplied."),
        f"Language: {shot['language']}. Dialogue: {shot['dialogue']}",
        *[f"{key.upper()}: {acting[key]}" for key in ACTING],
        "Keep gestures motivated by the thought. Preserve breathing, listening and the change of emotion; avoid a frozen face or constant exaggerated motion.",
        "Natural skin texture and lighting. Keep identity, hands and props coherent. No captions, logos, music or text on screen.",
    ])


def prepare(shot_path, out):
    shot_path = shot_path.resolve()
    shot = json.loads(shot_path.read_text())
    allowed = {"seconds", "seed", "aspect", "identity", "performance", "voice", "language", "dialogue", "acting"}
    if set(shot) - allowed:
        raise ValueError(f"unknown shot fields: {sorted(set(shot) - allowed)}")
    seconds = number(shot.get("seconds"), "seconds", 4, 15)
    seed = shot.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= gpu.SEED_MAX:
        raise ValueError(f"seed: required integer 0..{gpu.SEED_MAX}")
    prompt_text = direction(shot, "voice" in shot)
    sources = {key: asset(shot[key], shot_path.parent, key) for key in ("identity", "performance")}
    if "voice" in shot:
        sources["voice"] = asset(shot["voice"], shot_path.parent, "voice")
    out.mkdir(parents=True, exist_ok=False)
    state = {"version": VERSION, "status": "preparing", "source_shot_sha256": gpu.sha256(shot_path)}
    save(out / "checkpoint.json", state)
    try:
        image = out / "identity.png"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(sources["identity"]["path"]),
                        "-frames:v", "1", str(image)], check=True)
        motion = out / "performance.mp4"
        ref = sources["performance"]
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ref["start"]), "-i", str(ref["path"]),
                        "-t", str(ref["seconds"]), "-map", "0:v:0", "-an", "-vf",
                        "fps=24,scale=w='min(1280,iw)':h='min(1280,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(motion)], check=True)
        stream = next(s for s in probe(motion)["streams"] if s["codec_type"] == "video")
        if Fraction(stream["avg_frame_rate"]) != 24 or not 2 <= float(stream["duration"]) <= 15:
            raise ValueError("normalized reference must be 2–15 seconds at 24 fps")
        generated_frames = round(seconds * 24)
        generated_frames += (5 - generated_frames % 17) % 17
        reference_frames = int(stream["nb_frames"])
        consumed_frames = min(reference_frames, generated_frames)
        consumed_frames -= (consumed_frames - 5) % 17
        job = gpu.prepare_job("h3-r2v", {"ref_1": str(image), "ref_2": str(image), "prompt": prompt_text,
            "seconds": seconds, "seed": seed, "fast": False,
            "aspect": shot.get("aspect", "9:16 (Portrait Widescreen)")}, random.Random(seed), out)
        graph = job["prompt"]
        # v0.35 uses nested format.codec, not the old top-level codec field.
        graph["92"]["inputs"].pop("codec", None)
        del graph["139"]
        del graph["136"]["inputs"]["ref_images.ref_image_1"]
        graph["150"] = {"class_type": "LoadVideo", "inputs": {"file": "performance.mp4"}}
        graph["151"] = {"class_type": "GetVideoComponents", "inputs": {"video": ["150", 0]}}
        graph["136"]["inputs"]["ref_videos.ref_video_0"] = ["151", 0]
        # Performance video is intentionally silent. Only explicit authorized voice enters the audio conditioning.
        inputs = {"identity": {"file": image.name, "target": ["137", "image"]},
                  "performance": {"file": motion.name, "target": ["150", "file"]}}
        if "voice" in sources:
            voice = out / "voice.wav"
            ref = sources["voice"]
            subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ref["start"]), "-i", str(ref["path"]),
                            "-t", str(ref["seconds"]), "-vn", "-ar", "32000", "-ac", "1", str(voice)], check=True)
            graph["152"] = {"class_type": "LoadAudio", "inputs": {"audio": voice.name}}
            graph["136"]["inputs"]["ref_audios.ref_audio_0"] = ["152", 0]
            inputs["voice"] = {"file": voice.name, "target": ["152", "audio"]}
        # Full-quality baseline: no unused Turbo LoRA dependency, even on servers with eager validation.
        graph["126"]["inputs"]["model"] = ["127", 0]
        graph["124"]["inputs"]["steps"] = ["143", 0]
        for node in ("141", "142", "144", "145", "146"):
            del graph[node]
        for key, item in inputs.items():
            item["sha256"] = gpu.sha256(out / item["file"])
            item["source"] = {k: str(v) if isinstance(v, Path) else v for k, v in sources[key].items()}
        save(out / "workflow.json", graph)
        (out / "prompt.txt").write_text(prompt_text + "\n")
        save(out / "manifest.json", {"version": VERSION, "inputs": inputs, "workflow_sha256": gpu.sha256(out / "workflow.json"),
            "seed": seed, "requested_seconds": seconds, "fast": False, "steps": 20,
            "generated_frames": generated_frames, "reference_frames": reference_frames,
            "effective_reference_frames": consumed_frames,
            "reference_tail_not_consumed_seconds": (reference_frames - consumed_frames) / 24,
            "visual_acceptance": "needs_review", "voice_acceptance": "needs_review"})
        state["status"] = "prepared"
        save(out / "checkpoint.json", state)
        print(f"prepared {out}; no server contacted; run only after script/session approval", flush=True)
        if consumed_frames < reference_frames:
            print(f"H3 will consume {consumed_frames}/{reference_frames} reference frames; inspect the effective ending in manifest.json", flush=True)
    except BaseException:
        state["status"] = "prepare_failed"
        save(out / "checkpoint.json", state)
        raise


def preflight(graph, info):
    """Read-only node/model check; never submit/cancel as a pretend dry-run."""
    for node in graph.values():
        kind = node["class_type"]
        if kind not in info:
            raise ValueError(f"server missing node {kind}")
        fields = info[kind].get("input", {})
        fields = {**fields.get("required", {}), **fields.get("optional", {})}
        for field in node["inputs"]:
            if field.split(".")[0] not in fields and field not in fields:
                raise ValueError(f"server {kind} lacks input {field}; verify ComfyUI v0.35.0 schema")
        for key in ("unet_name", "vae_name", "clip_name", "aspect_ratio", "sampler_name", "scheduler"):
            if key in node["inputs"] and key in fields:
                entry = fields[key]
                options = entry[0] if isinstance(entry[0], list) else (entry[1] if len(entry) > 1 else {}).get("options")
                if options is not None and node["inputs"][key] not in options:
                    raise ValueError(f"server {kind}: unavailable {key}={node['inputs'][key]}")


def run(out, execute, resume, timeout):
    with (out / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("another runner owns this pilot") from None
        return run_locked(out, execute, resume, timeout)


def run_locked(out, execute, resume, timeout):
    out = out.resolve()
    manifest = json.loads((out / "manifest.json").read_text())
    state = json.loads((out / "checkpoint.json").read_text())
    if gpu.sha256(out / "workflow.json") != manifest["workflow_sha256"]:
        raise ValueError("workflow changed; prepare a new pilot directory")
    for item in manifest["inputs"].values():
        if gpu.sha256(out / item["file"]) != item["sha256"]:
            raise ValueError("reference changed; prepare a new pilot directory")
    graph = json.loads((out / "workflow.json").read_text())
    config = gpu.load_config()
    if config.get("shared"):
        raise ValueError("shared coordinator mode: this pilot runner is not integrated; do not bypass its queue")
    print("preflight: existing ComfyUI /object_info; no provisioning or generation", flush=True)
    comfy = gpu.Comfy(config["comfy_url"])
    preflight(graph, comfy.get("/object_info"))
    if not execute:
        print("preflight passed; no upload or queue submission", flush=True)
        return
    if state["status"] == "completed":
        print("already completed; use saved outputs", flush=True)
        return
    if state["status"] in ("submitting", "unknown"):
        raise ValueError("submission outcome unknown; reconcile /queue and /history before another pilot; never blindly resubmit")
    if state.get("prompt_id") and not resume:
        raise ValueError("job already submitted; use --resume --execute")
    if resume and not state.get("prompt_id"):
        raise ValueError("no prompt_id to resume")
    if not state.get("prompt_id"):
        if state["status"] != "prepared":
            raise ValueError(f"cannot submit state {state['status']}")
        queue = comfy.get("/queue")
        if queue.get("queue_running") or queue.get("queue_pending"):
            raise ValueError("ComfyUI busy; do not mix this pilot with other work")
        for key, item in manifest["inputs"].items():
            print(f"upload: {key} sha256={item['sha256'][:12]}", flush=True)
            uploaded = comfy.upload(out / item["file"])
            node, field = item["target"]
            graph[node]["inputs"][field] = uploaded
        save(out / "submitted-workflow.json", graph)
        state.update(status="submitting", submitted_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        save(out / "checkpoint.json", state)
        try:
            state["prompt_id"] = comfy.queue(graph)
        except BaseException:
            state["status"] = "unknown"
            save(out / "checkpoint.json", state)
            raise
        state["status"] = "queued"
        save(out / "checkpoint.json", state)
    print(f"wait: prompt_id={state['prompt_id']}; timeout leaves job running and checkpoint resumable", flush=True)
    history = comfy.wait(state["prompt_id"], timeout)
    save(out / "history.json", history)
    outputs = []
    for i, item in enumerate(gpu.output_files(history, "92")):
        if "filename" not in item:
            continue
        query = gpu.urllib.parse.urlencode({k: item.get(k, "") for k in ("filename", "subfolder", "type")})
        target = out / f"result-{i}{Path(item['filename']).suffix}"
        target.write_bytes(comfy.get_bytes("/view?" + query))
        outputs.append({"file": target.name, "sha256": gpu.sha256(target)})
    if not outputs:
        raise ValueError("job returned no video; inspect history.json")
    state.update(status="completed", outputs=outputs, visual_acceptance="needs_review", voice_acceptance="needs_review")
    save(out / "checkpoint.json", state)
    print("downloaded; technical completion only, naturalness/voice still need review", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("shot", type=Path)
    prep.add_argument("--out", type=Path, required=True)
    execute = commands.add_parser("run")
    execute.add_argument("directory", type=Path)
    execute.add_argument("--execute", action="store_true")
    execute.add_argument("--resume", action="store_true")
    execute.add_argument("--timeout", type=float, default=1800)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.shot, args.out.resolve())
        else:
            number(args.timeout, "timeout", 1, 86400)
            run(args.directory, args.execute, args.resume, args.timeout)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
