#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def _ensure_env():
    """Ensure utf-8 console output and auto-delegate to local .venv if django is missing."""
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    current_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = (
        os.path.join(current_dir, ".venv", "Scripts", "python.exe")
        if os.name == "nt"
        else os.path.join(current_dir, ".venv", "bin", "python")
    )

    try:
        import django  # noqa: F401
    except ImportError:
        if os.path.exists(venv_python) and os.path.abspath(sys.executable).lower() != os.path.abspath(venv_python).lower():
            import subprocess
            res = subprocess.run([venv_python, *sys.argv])
            sys.exit(res.returncode)


def main():
    """Run administrative tasks."""
    _ensure_env()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

