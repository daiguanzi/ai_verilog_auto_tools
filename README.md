# FPGA Agent

AI-driven FPGA development toolkit with automated simulation → feedback → iteration loop.

## What this agent does

You give it reference code or requirements, it generates a complete FPGA project:
- SystemVerilog RTL (`src/`)
- Python testbench with cocotb (`tb/`)
- Runs Verilator simulation automatically
- Reads simulation results, identifies bugs, fixes code
- Loop: modify → simulate → analyze → repeat until all tests pass

## Where to put things

| Directory | Put here... | Who writes |
|-----------|------------|------------|
| `reference/` | Specs, existing code, protocol docs | **You** (human) |
| `outputs/` | Generated projects appear here | **Agent** |
| `examples/` | Working demo projects | Pre-existing |

## Supported reference file formats

| Format | Notes |
|--------|-------|
| `.v` `.sv` `.svh` `.vh` | SystemVerilog/Verilog sources |
| `.py` | Python testbench or scripts |
| `.md` `.txt` | Markdown or plain text docs |
| `.pdf` | Needs `pdftotext` tool (`sudo apt install poppler-utils`) |
| `.docx` | Needs `python-docx` (`pip install python-docx`) |
| `.pptx` | Not supported |

## Quick Start

```bash
# 1. Enter WSL2 Ubuntu
wsl

# 2. Activate Python environment
cd your-project
source .venv/bin/activate   # if using venv

# 3. Run an example
python agent_tools/fpga_tools.py run examples/01_adder
# Expected: TESTS=2 PASS=2 ✓
```

## Prerequisites

- Windows 10/11 + WSL2 (Ubuntu 24.04+)
- Verilator 5.036+ (`/usr/local/bin/verilator`)
- cocotb 2.0.1 (`pip install cocotb`)
- Icarus Verilog 12.0 (fallback simulator)
- GTKWave 3.3 (waveform viewer, optional)

## Tell the agent what to do

Just open the project folder in your AI coding tool and say:

> "Look at the reference files in reference/, generate a UART transmitter in outputs/uart_tx/"

The agent reads `AGENTS.md`, understands the conventions, and starts working.

## License

MIT
