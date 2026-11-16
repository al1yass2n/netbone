"""Command-line entry point for `python -m netbone.webapp`."""

from netbone.webapp.server import main

if __name__ == "__main__":
    raise SystemExit(main())
