from ..configurator import MapDecoder, MapEncoder
import json
from pathlib import Path

raw_data = {
    "project": {
        "build": {"type": "Debug"},
        "dependecies": {
            "jsonschema": None,
            "libnacl": "^1.7.2",
            "python": False,
            "pytomlpp": True,
        },
        "generator": {"exclude": [".git", "assets"]},
        "name": "Devutils config test",
        "path": "~/proj/devtools/utils",
    }
}


def test_json_loads():
    converted = json.loads(json.dumps(raw_data), cls=MapDecoder)
    proj = converted["project"]
    assert proj.build.type == "Debug"
    proj.build.update(type="Release")
    assert proj.build.type == "Release"


def test_encoder():
    decoded = json.loads(json.dumps(raw_data), cls=MapDecoder)
    encoded = json.dumps(decoded, cls=MapEncoder)
    assert encoded == json.dumps(decoded)
