# SPDX-License-Identifier: Apache-2.0
"""Check model integrity, offline reuse and failure-safe downloads without large fixtures."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fians import models
from fians.common import assets, home_dir


class ModelContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.environment = patch.dict(os.environ, {"FIANS_HOME": str(self.root / "home")})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.content = b"model weights"
        self.pin = {"repository": "example/model", "revision": "a" * 40, "files": {
            "weights.safetensors": {"size": len(self.content),
                                    "sha256": hashlib.sha256(self.content).hexdigest()}}}
        self.manifest = patch("fians.models.manifest", return_value=self.pin)
        self.manifest.start()
        self.addCleanup(self.manifest.stop)

    def test_existing_directory_requires_matching_bytes(self):
        path = self.root / "weights.safetensors"
        path.write_bytes(self.content)
        models.install(self.root)
        previous = (home_dir() / "config.json").read_bytes()
        path.write_bytes(b"wrong weights")
        with self.assertRaises(ValueError):
            models.install(self.root)
        self.assertEqual((home_dir() / "config.json").read_bytes(), previous)

    def test_optional_unverified_conditionals_rejected(self):
        (self.root / "weights.safetensors").write_bytes(self.content)
        (self.root / "conds.pt").write_bytes(b"unverified")
        with self.assertRaisesRegex(ValueError, "conds.pt"):
            models.verify(self.root)

    def test_auto_discovered_unverified_tokenizer_rejected(self):
        (self.root / "weights.safetensors").write_bytes(self.content)
        (self.root / "tokenizer.json").write_bytes(b"unverified")
        with self.assertRaisesRegex(ValueError, "tokenizer.json"):
            models.verify(self.root)

    def test_cached_install_does_not_contact_network(self):
        directory = home_dir() / "models" / self.pin["revision"]
        directory.mkdir(parents=True)
        (directory / "weights.safetensors").write_bytes(self.content)
        with patch("fians.models.urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
            self.assertEqual(models.install()["downloaded"], 0)

    def test_corrupt_download_does_not_replace_existing_file(self):
        directory = home_dir() / "models" / self.pin["revision"]
        directory.mkdir(parents=True)
        target = directory / "weights.safetensors"
        target.write_bytes(b"preserved")
        with patch("fians.models.urllib.request.urlopen", return_value=io.BytesIO(b"corrupt")):
            with self.assertRaisesRegex(ValueError, "verification"):
                models.install()
        self.assertEqual(target.read_bytes(), b"preserved")
        self.assertEqual(list(directory.iterdir()), [target])

    def test_download_uses_exact_revision_and_validates_payload(self):
        with patch("fians.models.urllib.request.urlopen", return_value=io.BytesIO(self.content)) as request:
            result = models.install()
        self.assertIn("/resolve/" + self.pin["revision"] + "/", request.call_args.args[0].full_url)
        self.assertEqual(result["downloaded"], 1)
        self.assertEqual(models.verify()["files_verified"], 1)


class VoiceIdentity(unittest.TestCase):
    def test_reference_and_effects_match_profile_manifest(self):
        directory = assets() / "voices/praetor"
        profile = json.loads((directory / "voice.json").read_text())
        self.assertEqual(profile["id"], "praetor")
        for name, digest in profile["assets"].items():
            self.assertEqual(hashlib.sha256((directory / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
