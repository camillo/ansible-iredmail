FROM mcr.microsoft.com/devcontainers/base:bookworm

RUN apt-get --yes update
RUN apt-get --yes upgrade
RUN apt-get install --yes \
    git neovim curl wget syslog-ng-core \
    rng-tools gnupg \
    iputils-ping iputils-tracepath \
    python3 python3-venv python-is-python3 \
    sshpass
