import json
import subprocess

cmd = ['.\\arduino-cli.exe', 'board', 'list', '--format', 'json']
result = subprocess.run(cmd, capture_output=True, text=True)

try:
    data = json.loads(result.stdout)
    detected_ports = data.get("detected_ports", [])

    if not detected_ports:
        print("No boards currently detected. Check your USB connection.")
    else:
        for entry in detected_ports:
            port_info = entry.get("port", {})
            port_address = port_info.get("address", "Unknown Port")
            
            matching_boards = entry.get("matching_boards", [])
            if matching_boards:
                board_name = matching_boards[0].get("name", "Unknown Board")
                fqbn = matching_boards[0].get("fqbn", "Unknown FQBN")
                print(f"[FOUND] {board_name} on {port_address} (FQBN: {fqbn})")
            else:
                print(f"[FOUND] Unidentified device on {port_address}")

except json.JSONDecodeError:
    print("Failed to decode JSON from arduino-cli output.")