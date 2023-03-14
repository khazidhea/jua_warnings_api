#!/bin/bash
set -e
set -x
echo "Running isort..."
isort .

echo "Running black..."
black .

echo "Running pylint..."
changed_files=`git diff HEAD^ --name-only --diff-filter=d | grep -E '.py$' | tr '\n' ' '`
echo $changed_files | xargs pylint -j 0 --recursive=y

echo "Running mypy..."
mypy .
