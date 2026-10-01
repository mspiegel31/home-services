#!/bin/bash
set -eu
if ! command -v skillgrade-omp-grader >/dev/null 2>&1; then
  echo '{"score": 0, "details": "grader error: skillgrade-omp-grader not on PATH"}'
  exit 0
fi
exec skillgrade-omp-grader
