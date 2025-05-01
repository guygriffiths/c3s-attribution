#!/bin/sh
set -e

exec micromamba run -n c3s-pyenv -- "$@"
