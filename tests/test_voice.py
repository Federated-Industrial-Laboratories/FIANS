# SPDX-License-Identifier: Apache-2.0
"""Exercise text preservation and output safety without loading model weights."""
from pathlib import Path
import fcntl
import tempfile
import threading
import unittest
from unittest.mock import patch

from fians.common import chunks
from fians.cli import lifecycle, write_audio


class VoiceContracts(unittest.TestCase):
    def test_stop_serializes_with_launch_before_worker_lock_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checked = threading.Event()
            result = []
            def missing(request, timeout):
                checked.set()
                raise FileNotFoundError
            with (root / 'start.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                with patch('fians.cli.state_dir', return_value=root), \
                     patch('fians.cli.exchange', side_effect=missing):
                    thread = threading.Thread(target=lambda: result.append(lifecycle('stop')))
                    thread.start()
                    try:
                        self.assertFalse(checked.wait(0.2), 'Stop checked state before startup finished')
                    finally:
                        fcntl.flock(lock, fcntl.LOCK_UN)
                        thread.join(2)
                    self.assertFalse(thread.is_alive())
                    self.assertEqual(result, [{'ok': True, 'state': 'stopped'}])

    def test_status_sees_worker_loading_before_socket_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / 'worker.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                with patch('fians.cli.state_dir', return_value=root), \
                     patch('fians.cli.exchange', side_effect=FileNotFoundError):
                    self.assertEqual(lifecycle('status')['state'], 'starting')

    def test_stop_waits_for_loading_worker_to_become_reachable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / 'worker.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                calls = []
                def reply(request, timeout):
                    calls.append(request['op'])
                    if len(calls) == 1:
                        raise FileNotFoundError
                    fcntl.flock(lock, fcntl.LOCK_UN)
                    return {'ok': True, 'state': 'stopping'}
                with patch('fians.cli.state_dir', return_value=root), \
                     patch('fians.cli.exchange', side_effect=reply), \
                     patch('fians.cli.time.sleep'):
                    self.assertEqual(lifecycle('stop')['state'], 'stopped')
                self.assertEqual(calls, ['stop', 'stop'])

    def test_long_text_preserves_words_and_punctuation(self):
        text = ('Signal clear. We can proceed with the next operation; all channels are ready. ' * 9).strip()
        parts = chunks(text)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(part) <= 240 for part in parts))
        self.assertEqual(' '.join(parts), text)

    def test_text_is_data(self):
        text = 'Report "ready"; $(touch /tmp/should-not-exist) and `commands` stay text.'
        self.assertEqual(chunks(text), [text])

    def test_empty_and_oversized_text_rejected(self):
        for text in ('  \n', 'a' * 2001, 'a' * 241):
            with self.assertRaises(ValueError):
                chunks(text)

    def test_output_preserved_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'voice.wav'
            path.write_bytes(b'original')
            with self.assertRaises(FileExistsError):
                write_audio(path, b'replacement', False)
            self.assertEqual(path.read_bytes(), b'original')
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_force_replaces_link_not_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target, link = Path(directory) / 'target', Path(directory) / 'voice.wav'
            target.write_bytes(b'original')
            link.symlink_to(target)
            write_audio(link, b'replacement', True)
            self.assertFalse(link.is_symlink())
            self.assertEqual(target.read_bytes(), b'original')
            self.assertEqual(link.read_bytes(), b'replacement')


if __name__ == '__main__':
    unittest.main()
