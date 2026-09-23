"""One-command executor launcher."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11+ required.')
result = subprocess.run([sys.executable, str(ROOT / 'api_only.py'), *sys.argv[1:]], cwd=ROOT)
raise SystemExit(result.returncode)
