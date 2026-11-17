from arduino_backend import ArduinoCLIWrapper
engine = ArduinoCLIWrapper(".\\arduino-cli.exe")
print(f"Engine active: {engine.get_version()}\n")

print("Scanning connected microcontrollers...")
boards = engine.detect_boards()
target_board = None
for b in boards:
    print(f"-> Found {b['name']} on {b['port']} (FQBN: {b['fqbn']})")
    if "uno" in b["fqbn"].lower():
        target_board = b
if target_board:
    sketch_dir = ".\\BlinkTest"
    print(f"\nTargeting {target_board['name']} on {target_board['port']}...")

    # When Compiling
    success, log = engine.compile(sketch_dir, target_board["fqbn"])
    if not success:
        print(f"Compilation Failed:n\n{log}")
    else:
        print("Compilation Succeeded.")

        up_success, up_log = engine.upload(
            sketch_dir, target_board["fqbn"], target_board["port"]

        )
        if up_success:
            print("Upload Successful! Hardware running.")
        else:
            print(f"Upload Failed:\n{up_log}")
else:
        print("\nNo compatible board detected to test.")


    