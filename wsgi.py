import os
import sys

# Import the Flask `app` from the application's module.
from app import app

# Startup banner to make Render logs unambiguous about the file and PID
try:
    banner = f"=== STARTUP BANNER (wsgi): app file={os.path.abspath('app.py')} PID={os.getpid()} ===\n"
    sys.stderr.write(banner)
    sys.stderr.flush()
except Exception:
    pass

# Expose `app` for gunicorn
__all__ = ["app"]
