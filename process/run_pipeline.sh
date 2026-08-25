#!/bin/bash
cd "$(dirname "$0")"  # Go to process/ dir
podman-compose up --abort-on-container-exit
