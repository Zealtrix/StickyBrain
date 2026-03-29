# Contributing

Thanks for contributing to Sticky Brain.

## Development setup

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Before opening a pull request

```powershell
python -m compileall .
```

## Scope

- Keep the app local-first
- Avoid cloud dependencies for core note capture and search
- Prefer lightweight models and low resource usage
- Treat user secrets carefully and avoid logging sensitive note content
