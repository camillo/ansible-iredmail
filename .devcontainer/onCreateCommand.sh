#!/bin/env bash

git config --global init.defaultBranch main
echo "Set git default branch to main"

python -m venv .venv
.venv/bin/pip install -r .devcontainer/requirements.txt

gopass setup --storage fs

echo "source /workspaces/ansible-iredmail/.venv/bin/activate" >> ~/.zshrc
echo "Activated .venv"
mkdir -p ~/.oh-my-zsh/completions
