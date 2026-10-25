"""Offline real-media preparation and controlled submission/recovery regressions (no model calls)."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import h3_performance as h3


class PerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        (cls.base / "identity.png").write_bytes(h3.gpu.png_rgba(64, 96, lambda x, y: 255))
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=96x64:rate=30:duration=3",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:v", "libx264", "-c:a", "aac",
                        str(cls.base / "motion.mp4")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=3",
                        str(cls.base / "voice.wav")], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def shot(self, voice=True):
        value = json.loads((ROOT / "templates/h3-performance-shot.json").read_text())
        for key, file in [("identity", "identity.png"), ("performance", "motion.mp4"), ("voice", "voice.wav")]:
            value[key] = {"file": file, "permission": "Owned synthetic test fixture; authorized local use"}
            if key != "identity":
                value[key].update(start=0, seconds=2)
        if not voice:
            del value["voice"]
        return value

    def prepare(self, voice=True):
        shot = self.base / f"{self._testMethodName}.json"
        shot.write_text(json.dumps(self.shot(voice)))
        out = self.base / self._testMethodName
        h3.prepare(shot, out)
        return out

    def test_media_and_real_graph_wiring(self):
        out = self.prepare()
        graph = json.loads((out / "workflow.json").read_text())
        inputs = graph["136"]["inputs"]
        self.assertEqual(inputs["ref_videos.ref_video_0"], ["151", 0])
        self.assertEqual(inputs["ref_audios.ref_audio_0"], ["152", 0])
        self.assertNotIn("ref_images.ref_image_1", inputs)
        self.assertNotIn("ref_video_audios.ref_video_audio_0", inputs)
        streams = h3.probe(out / "performance.mp4")["streams"]
        self.assertEqual([s["codec_type"] for s in streams], ["video"])
        self.assertEqual(streams[0]["avg_frame_rate"], "24/1")
        self.assertEqual(int(streams[0]["nb_frames"]), 48)
        self.assertFalse(any(n["class_type"] == "LoraLoaderModelOnly" for n in graph.values()))
        self.assertEqual(graph["143"]["inputs"]["value"], 20)
        prompt = (out / "prompt.txt").read_text()
        self.assertIn("<Video 1>", prompt)
        self.assertIn("<Audio 1>", prompt)
        self.assertIn("SUBTEXT:", prompt)

    def test_optional_voice_has_no_dangling_reference(self):
        out = self.prepare(voice=False)
        graph = json.loads((out / "workflow.json").read_text())
        self.assertNotIn("152", graph)
        self.assertNotIn("ref_audios.ref_audio_0", graph["136"]["inputs"])
        self.assertNotIn("<Audio", (out / "prompt.txt").read_text())

    def test_duration_and_source_bounds(self):
        for seconds in [1, 16, float("nan")]:
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                h3.asset({"file": "motion.mp4", "permission": "owned", "seconds": seconds}, self.base, "performance")
        with self.assertRaisesRegex(ValueError, "exceeds"):
            h3.asset({"file": "motion.mp4", "permission": "owned", "start": 2, "seconds": 2}, self.base, "performance")

    def test_private_reference_and_symlink_rejected(self):
        private = self.base / "reference/private"
        private.mkdir(parents=True, exist_ok=True)
        (private / "actor.png").write_bytes((self.base / "identity.png").read_bytes())
        link = self.base / "borrowed.png"
        link.symlink_to(private / "actor.png")
        with self.assertRaisesRegex(ValueError, "analysis-only"):
            h3.asset({"file": str(link), "permission": "claimed"}, self.base, "identity")

    def test_missing_acting_and_permission_rejected(self):
        value = self.shot()
        del value["acting"]["subtext"]
        with self.assertRaisesRegex(ValueError, "acting"):
            h3.direction(value, True)
        with self.assertRaisesRegex(ValueError, "permission"):
            h3.asset({"file": "identity.png"}, self.base, "identity")

    def test_old_workflows_remain_image_only(self):
        graph, spec = h3.gpu.load_template("h3-r2v")
        self.assertIn("ref_2", spec["params"])
        self.assertFalse(any(k.startswith("ref_videos") for k in graph["136"]["inputs"]))

    def test_preflight_rejects_missing_reference_schema_and_model(self):
        graph = {"136": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {"ref_videos.ref_video_0": ["151", 0]}}}
        info = {"MiniMaxH3ReferenceToVideo": {"input": {"optional": {"ref_images": ["AUTOGROW"]}}}}
        with self.assertRaisesRegex(ValueError, "ref_videos"):
            h3.preflight(graph, info)
        info["MiniMaxH3ReferenceToVideo"]["input"]["optional"]["ref_videos"] = ["AUTOGROW"]
        h3.preflight(graph, info)
        with self.assertRaisesRegex(ValueError, "unavailable"):
            h3.preflight({"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "h3.safetensors"}}},
                         {"UNETLoader": {"input": {"required": {"unet_name": [["other.safetensors"]]}}}})

    def test_read_only_preflight_does_not_upload(self):
        out = self.prepare()
        with patch.object(h3.gpu, "Comfy") as client, patch.object(h3, "preflight"), patch.object(h3.gpu, "load_config", return_value={"comfy_url": "http://test"}):
            h3.run(out, False, False, 1)
            client.return_value.upload.assert_not_called()
            client.return_value.queue.assert_not_called()

    def test_timeout_resumes_same_job_without_resubmitting(self):
        out = self.prepare()
        with patch.object(h3.gpu, "Comfy") as client, patch.object(h3, "preflight"), patch.object(h3.gpu, "load_config", return_value={"comfy_url": "http://test"}):
            remote = client.return_value
            remote.get.return_value = {"queue_running": [], "queue_pending": []}
            remote.upload.return_value = "uploaded.mp4"
            remote.queue.return_value = "test-prompt-id"
            remote.wait.side_effect = SystemExit("timeout")
            with self.assertRaises(SystemExit):
                h3.run(out, True, False, 1)
            state = json.loads((out / "checkpoint.json").read_text())
            self.assertEqual(state["prompt_id"], "test-prompt-id")
            remote.wait.side_effect = None
            remote.wait.return_value = {"outputs": {"92": {"images": [{"filename": "take.mp4", "type": "output"}]}}}
            remote.get_bytes.return_value = b"controlled transport fixture, not real generation"
            h3.run(out, True, True, 1)
            remote.queue.assert_called_once()
            self.assertEqual(remote.upload.call_count, 3)
            self.assertEqual(json.loads((out / "checkpoint.json").read_text())["status"], "completed")

    def test_ambiguous_post_is_not_retried(self):
        out = self.prepare()
        with patch.object(h3.gpu, "Comfy") as client, patch.object(h3, "preflight"), patch.object(h3.gpu, "load_config", return_value={"comfy_url": "http://test"}):
            remote = client.return_value
            remote.get.return_value = {}
            remote.upload.return_value = "uploaded"
            remote.queue.side_effect = OSError("lost response")
            with self.assertRaises(OSError):
                h3.run(out, True, False, 1)
            with self.assertRaisesRegex(ValueError, "unknown"):
                h3.run(out, True, False, 1)
            remote.queue.assert_called_once()

    def test_shared_and_busy_sessions_rejected(self):
        out = self.prepare()
        with patch.object(h3.gpu, "load_config", return_value={"shared": True}):
            with self.assertRaisesRegex(ValueError, "shared"):
                h3.run(out, True, False, 1)
        with patch.object(h3.gpu, "Comfy") as client, patch.object(h3, "preflight"), patch.object(h3.gpu, "load_config", return_value={"comfy_url": "http://test"}):
            client.return_value.get.return_value = {"queue_running": [[1, "someone-else"]]}
            with self.assertRaisesRegex(ValueError, "busy"):
                h3.run(out, True, False, 1)
            client.return_value.upload.assert_not_called()

    def test_changed_media_blocked_before_network(self):
        out = self.prepare()
        (out / "identity.png").write_bytes(b"changed")
        with patch.object(h3.gpu, "Comfy") as client:
            with self.assertRaisesRegex(ValueError, "reference changed"):
                h3.run(out, True, False, 1)
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
