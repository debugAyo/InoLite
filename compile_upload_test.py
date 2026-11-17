import subprocess

cli = '.\\arduino-cli.exe'
sketch_path ='.\\BlinkTest'
fqbn = 'arduino:avr:uno'
port = 'COM6'

print("1. Compiling the sketch...")
compile_cmd = [cli, 'compile', '--fqbn', fqbn, sketch_path]
compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)

if compile_result.returncode !=0:
    print("Compilation failed:")
    print(compile_result.stderr)
else:
    print("Compilation Successful!")
    print("2. Uploading to board... ")
    upload_cmd = [cli, 'upload', '-p', port, '--fqbn', fqbn, sketch_path]
    upload_result = subprocess.run(upload_cmd, capture_output=True, text=True)

    if upload_result.returncode !=0:
        print("Upload failed:")
        print(upload_result.stderr)
    else:
        print("Upload complete! Check the LEd on your Uno.")

    