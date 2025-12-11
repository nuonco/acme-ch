import os

# Bind to PORT env var
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Logging - send everything to stdout/stderr
accesslog = "-"
errorlog = "-"
capture_output = True
loglevel = "info"

# Workers
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
