#!/usr/bin/env bash
# Wrapper to invoke the Python build CLI
exec .venv/bin/python src/build.py "$@"
