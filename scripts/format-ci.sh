#!/bin/bash
echo "Running isort..."
isort --check .

echo "Running black..."
black --check .

echo "Running pylint..."
changed_files=`git diff HEAD^ --name-only --diff-filter=d | grep -E '.py$' | tr '\n' ' '`
echo $changed_files | xargs pylint -j 0 --recursive=y

echo "Running mypy..."
mypy .
