import argparse
import json
import sys
import time
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("script", type=Path)
parser.add_argument("--engine", default="C:/Program Files/Epic Games/UE_5.8")
arguments = parser.parse_args()
sys.path.insert(0, str(Path(arguments.engine) / "Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python"))
import remote_execution

session = remote_execution.RemoteExecution()
session.start()
try:
    project = str(Path(__file__).resolve().parents[1]).replace("\\", "/").lower()
    matching = []
    for attempt in range(10):
        matching = [node for node in session.remote_nodes if str(node.get("project_root", "")).replace("\\", "/").rstrip("/").lower() == project]
        if matching:
            break
        time.sleep(1)
    if len(matching) != 1:
        raise RuntimeError("Expected one Unreal Editor for this project; found " + str(len(matching)))
    session.open_command_connection(matching[0]["node_id"])
    result = session.run_command(arguments.script.resolve().read_text(encoding="utf-8"), raise_on_failure=False)
    print(json.dumps({key: value for key, value in result.items() if key != "command"}, ensure_ascii=True))
    if not result["success"]:
        sys.exit(1)
finally:
    session.stop()
