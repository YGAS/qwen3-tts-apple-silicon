```
lsof -ti:8766 | xargs kill -9 2>/dev/null; sleep 1; source .venv/bin/activate && python web_app.py
```