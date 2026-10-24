"""Run verification for the currently installed backdrop revision."""
from pathlib import Path
import runpy


if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parent / 'distance-fix' / 'verify.py'),
                   run_name='__main__')
