import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "app-wireframe" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def run_script(name, *args, check=True):
    return subprocess.run([sys.executable, SCRIPTS / name, *map(str, args)],
                          capture_output=True, text=True, check=check)


@pytest.fixture
def make_run(tmp_path):
    """A run folder with screenshots and a selection.json, initialised with `wireframes.py init`."""
    def make(sizes=((1179, 2556), (1290, 2796))):
        run = tmp_path / "Demo"
        shots = run / "screenshots"
        shots.mkdir(parents=True)
        selection = {"app_name": "Demo", "screens": []}
        for i, size in enumerate(sizes):
            name = f"{i + 1:02d} - Screen {i} - abcdef0{i}.png"
            Image.new("RGB", size, "white").save(shots / name)
            selection["screens"].append({"file": name, "label": f"Screen {i}",
                                         "mobbin_url": f"https://mobbin.com/screens/0000000{i}"})
        (shots / "selection.json").write_text(json.dumps(selection))
        run_script("wireframes.py", "init", run)
        return run
    return make
