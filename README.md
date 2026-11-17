# Arduino Alternative IDE

A snappy, lightweight desktop IDE for Arduino boards built with Python and PyQt6.

Standard IDEs can feel sluggish to launch and heavy on memory just to write code, compile, and read serial telemetry. This project strips out the unnecessary bloat while keeping the workflow deterministic and fast: direct CLI orchestration, non-blocking USB detection, and a built-in serial monitor.

## Current State

- **Backend Engine:** Lightweight subprocess wrapper around `arduino-cli` using clean JSON parsing to detect boards, compile sketches, and flash targets.
- **Non-blocking Threading:** Async worker threads (`QThread`) handling compilation, uploads, and USB polling so the GUI remains responsive at all times.
- **Serial Monitor:** Integrated serial viewport built on `pyserial` with baud rate selection, live data streaming, and automatic port disconnects during flash routines.
- **Code Editor:** Custom editor with live line numbers, active line highlighting, and full C++/Arduino syntax highlighting.

## Project Structure

```
├── arduino_backend.py      # Core engine wrapping arduino-cli
├── code_editor.py          # Custom QPlainTextEdit with line numbers and gutters
├── syntax_highlighter.py   # Regex-based syntax highlighter for Arduino/C++
├── main_gui.py             # Main PyQt6 interface, worker threads, serial pipeline
├── BlinkTest/              # Test sketch folder
└── .gitignore
```

## Getting Started

1. **Install dependencies:**
   ```cmd
   pip install PyQt6 pyserial
   ```

2. **Ensure `arduino-cli.exe` and AVR core are present:**
   ```cmd
   arduino-cli core install arduino:avr
   ```

3. **Run the IDE:**
   ```cmd
   python main_gui.py
   ```

## Next Milestones

- Multi-tab document support for working across multiple sketches
- Real-time numeric Serial Plotter
- AI-assisted compiler diagnostic analyzer
