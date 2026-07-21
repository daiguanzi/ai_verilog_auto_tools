"""Agent tools configuration loader. Provides fallback defaults if config.json missing."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

_defaults = {
    "paths": {
        "vivado": r"C:\Xilinx\Vivado\2018.2\bin\vivado.bat",
        "modelsim": r"C:\modeltech64_10.4\win64",
        "wsl": "wsl",
        "python_venv": ".venv/bin/python",
    },
    "defaults": {
        "device": "xc7a200t-fbg484-2L",
        "clk_freq_mhz": 100,
        "simulator": "modelsim",
        "timeout_minutes": 60,
    },
}


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    # merge with defaults
    result = dict(_defaults)
    result["paths"].update(cfg.get("paths", {}))
    result["defaults"].update(cfg.get("defaults", {}))
    return result


def get_path(key: str) -> str:
    return load_config()["paths"].get(key, _defaults["paths"].get(key, ""))


def get_default(key: str):
    return load_config()["defaults"].get(key, _defaults["defaults"].get(key))
