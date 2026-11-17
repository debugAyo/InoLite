import json
import os
import subprocess
from typing import Dict, List, Tuple

class ArduinoCLIWrapper:
    """Backend engine interfacing with the local arduino-cli executable."""
    def __init__ (self, cli_path: str= ".\\arduino-cli.exe"):
        self.cli_path = os.path.abspath(cli_path)
        if not os.path.exists(self.cli_path):
            raise FileNotFoundError(
                f"Arduino CLI binary not found at: {self.cli_path}"
                )

    def get_version(self) -> str:
        """Returns the version string of the local arduino-cli binary."""
        res = subprocess.run(
            [self.cli_path, "version"], capture_output=True, text=True
        )
        return (
            res.stdout.strip()
            if res.returncode ==0
            else f"Error: {res.stderr.strip()}"
        )
    def detect_boards(self) -> List[Dict[str, str]]:
        """Scans USB ports and returns a list of detected board with port and FQBN."""
        cmd = [self.cli_path, "board", "list", "--format", "json"]
        res = subprocess.run(cmd, capture_output=True, text=True)

        boards = []
        if res.returncode != 0 or not res.stdout.strip():
            return boards
        try:
            data = json.loads(res.stdout)
            detected_ports = data.get("detected_ports", [])

            if isinstance(detected_ports, list):
                for entry in detected_ports:
                    port_info = entry.get("port", {})
                    port_addr = port_info.get("address", [])
                    matching = entry.get("matching_boards", [])

                    if matching and isinstance(matching, list):
                        board_name = matching[0].get("name", "Unknown Board")
                        fqbn = matching[0].get("fqbn", "")
                    else:
                        board_name ="Generic/Unknown Device"
                        fqbn = ""

                    boards.append(
                        {"name": board_name, "port": port_addr, "fqbn": fqbn}
                    )
        except Exception as e:
            print(f"[Debug] JSON parse issue: {e}")
        return boards


    def compile(
        self, sketch_path: str, fqbn: str
    ) -> Tuple[bool, str]:
        """Compiles an Arduino sketch directory for a target board FQBN."""
        cmd = [self.cli_path, "compile", "--fqbn", fqbn, sketch_path]
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode == 0:
            return True, res.stdout
        else:
            return False, res.stderr or res.stdout

    def upload(
        self, sketch_path: str, fqbn: str, port: str
    ) -> Tuple[bool, str]:
        """Uploads the compiled sketch to the specified port."""
        cmd = [
            self.cli_path,
            "upload",
            "-p",
            port,
            "--fqbn",
            fqbn,
            sketch_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode == 0:
            return True, res.stdout
        else:
            return False, res.stderr or res.stdout
            



