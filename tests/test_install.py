# SPDX-License-Identifier: Apache-2.0
"""Protect ownership boundaries for user runtime installation and removal."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fians_install", ROOT / "packaging/install.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
BUILD_SPEC = importlib.util.spec_from_file_location("fians_release", ROOT / "packaging/build_release.py")
release = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(release)


class InstallOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.prefix = self.root / "runtime"
        self.launcher = self.root / "bin/fians"
        self.args = ["--prefix", str(self.prefix), "--bin-dir", str(self.launcher.parent)]
        self.environment = patch.dict(os.environ, {"FIANS_HOME": str(self.root / "data")})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def managed(self):
        self.prefix.mkdir()
        self.launcher.parent.mkdir()
        self.launcher.write_text("managed launcher")
        marker = {"schema": 1, "prefix": str(self.prefix), "launcher": str(self.launcher),
                  "token": "a" * 32, "state": "ready",
                  "launcher_sha256": installer.digest(self.launcher)}
        installer.save_marker(self.prefix, marker)

    def test_unmanaged_directory_is_preserved(self):
        self.prefix.mkdir()
        sentinel = self.prefix / "keep"
        sentinel.write_text("unrelated data")
        with self.assertRaisesRegex(ValueError, "not empty"):
            installer.main(self.args)
        self.assertEqual(sentinel.read_text(), "unrelated data")

    def test_changed_launcher_prevents_uninstall(self):
        self.managed()
        self.launcher.write_text("replacement from another application")
        with self.assertRaisesRegex(ValueError, "launcher was changed"):
            installer.main(self.args + ["--uninstall"])
        self.assertTrue(self.prefix.exists())
        self.assertEqual(self.launcher.read_text(), "replacement from another application")

    def test_uninstall_stops_worker_and_retains_data(self):
        self.managed()
        selected = self.root / "chosen-data"
        selected.mkdir(mode=0o700)
        marker = installer.read_marker(self.prefix)
        marker["data"] = str(selected)
        installer.save_marker(self.prefix, marker)
        data = selected / "voice-model.bin"
        data.write_bytes(b"model")
        with patch.dict(os.environ):
            os.environ.pop("FIANS_HOME", None)
            with patch.object(installer, "run") as run:
                self.assertEqual(installer.main(self.args + ["--uninstall"]), 0)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], [self.prefix / "bin/fians", "stop"])
        self.assertEqual(run.call_args.kwargs["env"]["FIANS_HOME"], str(selected))
        self.assertFalse(self.prefix.exists())
        self.assertFalse(self.launcher.exists())
        self.assertEqual(data.read_bytes(), b"model")

    def test_symlink_prefix_is_preserved(self):
        real = self.root / "unrelated"
        real.mkdir()
        self.prefix.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            installer.main(self.args + ["--uninstall"])
        self.assertTrue(real.exists())
        self.assertTrue(self.prefix.is_symlink())

    def test_concurrent_installation_is_rejected(self):
        with installer.installation_lock(self.prefix):
            with self.assertRaisesRegex(ValueError, "Another FIANS installation"):
                installer.main(self.args)
        self.assertFalse(self.prefix.exists())

    def test_default_layout_creates_private_data_before_runtime(self):
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(self.root / "share")}):
            os.environ.pop("FIANS_HOME", None)
            data = self.root / "share/fians"
            with patch.object(installer, "install_runtime", return_value=0) as install:
                installer.main(["--bin-dir", str(self.launcher.parent)])
            self.assertEqual(data.stat().st_mode & 0o777, 0o700)
            self.assertEqual(install.call_args.args[1], data / "runtime")

    def test_update_preserves_selected_data_home_without_environment(self):
        self.managed()
        selected = self.root / "chosen-data"
        marker = installer.read_marker(self.prefix)
        marker["data"] = str(selected)
        installer.save_marker(self.prefix, marker)
        with patch.dict(os.environ):
            os.environ.pop("FIANS_HOME", None)
            with patch.object(installer, "install_runtime", return_value=0) as install:
                installer.main(self.args + ["--update"])
            self.assertEqual(install.call_args.args[3], selected)
        self.assertEqual(selected.stat().st_mode & 0o777, 0o700)

    def test_release_excludes_local_state_and_model_files(self):
        for relative in ["src/fians/__init__.py", "models/manifest.json", "models/weights.pt",
                         "local-config.json", ".env", "venv/secret", "src/fians/__pycache__/x.pyc"]:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture")
        included = {str(relative) for _, relative in release.source_files(self.root)}
        self.assertEqual(included, {"src/fians/__init__.py", "models/manifest.json"})

    def test_release_rejects_symlinks(self):
        target = self.root / "secret"
        target.write_text("private data")
        (self.root / "src").mkdir()
        (self.root / "src/leak.py").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            list(release.source_files(self.root))


if __name__ == "__main__":
    unittest.main()
