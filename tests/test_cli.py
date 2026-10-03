"""End to end through the actual entry point a reviewer would run."""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import tempfile
import unittest

from brandkit import cli
from tests.support import ROOT, SOURCE_NAMES


class TestCli(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(ROOT)

    def tearDown(self):
        os.chdir(self._cwd)

    def test_verify_exits_zero_on_every_source(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    code = cli.main(["verify", f"examples/{name}"])
                self.assertEqual(0, code)
                self.assertIn("identical", buf.getvalue())

    def test_build_writes_every_artefact(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "build"
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(
                    ["build", "examples/source-acme.html", "--out", str(out)]
                )
            self.assertEqual(0, code)
            for artefact in ("kit.json", "kit.css", "tokens.csv"):
                self.assertTrue((out / artefact).is_file(), artefact)
            for skeleton in ("01-host-landing", "02-saas", "03-product-pdp"):
                self.assertTrue((out / skeleton / "index.html").is_file(), skeleton)
                self.assertTrue((out / skeleton / "DESIGN.md").is_file(), skeleton)

    def test_build_is_reproducible_across_models(self):
        """Same source, different model, byte identical tokens."""
        outputs = {}
        for style in ("terse", "verbose"):
            with tempfile.TemporaryDirectory() as tmp:
                out = pathlib.Path(tmp) / "build"
                with contextlib.redirect_stdout(io.StringIO()):
                    cli.main([
                        "build", "examples/source-acme.html",
                        "--out", str(out), "--model", style,
                    ])
                outputs[style] = (out / "kit.css").read_text(encoding="utf-8")
        self.assertEqual(outputs["terse"], outputs["verbose"])

    def test_an_unreadable_source_fails_loudly(self):
        with self.assertRaises(OSError):
            cli.main(["verify", "examples/does-not-exist.html"])


if __name__ == "__main__":
    unittest.main()
