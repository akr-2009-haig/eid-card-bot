import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_render_python_version():
    render_config = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    match = re.search(r"^\s*-\s*key:\s*PYTHON_VERSION\s*$\n^\s*value:\s*([^\s]+)\s*$", render_config, re.MULTILINE)
    if not match:
        raise AssertionError("render.yaml is missing the PYTHON_VERSION env var")
    return match.group(1)


class RenderPythonVersionTests(unittest.TestCase):
    def test_render_yaml_matches_python_version_file(self):
        python_version = (REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip()
        self.assertEqual(read_render_python_version(), python_version)

    def test_runtime_txt_matches_python_version_file(self):
        python_version = (REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip()
        runtime_version = (REPO_ROOT / "runtime.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(runtime_version, f"python-{python_version}")


if __name__ == "__main__":
    unittest.main()
