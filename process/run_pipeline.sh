#!/bin/bash
cd "$(dirname "$0")"  # Go to process/ dir
docker-compose up --abort-on-container-exit