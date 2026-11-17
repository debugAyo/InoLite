import subprocess

cmd = ['.\\arduino-cli.exe', 'board', 'list', '--format', 'json']
result = subprocess.run(cmd, capture_output=True, text=True)

print("--- RAW OUTPUT ---")
print(result.stdout)
print("------------------")