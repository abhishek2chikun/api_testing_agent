#!/bin/bash
# optional helper to run tests in docker locally
# usage: ./docker-runner.sh <branch>
BRANCH="$1"
if [ -z "$BRANCH" ]; then
  echo "provide branch"
  exit 1
fi
TMPDIR=$(mktemp -d)
GITURL="https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO_FULL_NAME}.git"
git clone "$GITURL" "$TMPDIR"
cd "$TMPDIR" || exit
git checkout "$BRANCH"
# run pytest inside python image
docker run --rm -v "$TMPDIR":/repo -w /repo python:3.11 bash -lc "pip install -r requirements.txt && pytest -q --maxfail=1 --junitxml=results.xml || true"


