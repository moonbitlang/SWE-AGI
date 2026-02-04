# Base image for spec-test agents
# Includes MoonBit CLI and communication tools for Unix socket interaction

FROM ubuntu:24.04

# Avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Use USTC mirror to avoid network issues
RUN sed -i 's|http://archive.ubuntu.com|http://mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/ubuntu.sources && \
  sed -i 's|http://security.ubuntu.com|http://mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/ubuntu.sources

# Install system dependencies
RUN apt-get update && apt-get install -y \
  curl \
  git \
  socat \
  netcat-openbsd \
  jq \
  ca-certificates \
  gnupg \
  unzip \
  sudo \
  wget \
  gosu \
  python3 \
  python3-pip \
  && rm -rf /var/lib/apt/lists/*

# Install yq (YAML processor)
RUN wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq && \
  chmod +x /usr/local/bin/yq

# Install Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y nodejs \
  && rm -rf /var/lib/apt/lists/*

# Create non-root user for running agents with host UID/GID
# macOS typically uses UID 501 for first user
RUN useradd -m -u 501 -g 0 -s /bin/bash moonbit

# Create workspace directory with proper permissions
RUN mkdir -p /workspace && chown moonbit:0 /workspace

# Set up working directory
WORKDIR /workspace

# Switch to moonbit user
USER moonbit
ENV HOME="/home/moonbit"
ENV PATH="/home/moonbit/.moon/bin:/home/moonbit/.npm-global/bin:/home/moonbit/.local/bin:$PATH"

# Install MoonBit CLI for the user
RUN curl -fsSL https://cli.moonbitlang.com/install/unix.sh | bash && \
  /home/moonbit/.moon/bin/moon update && \
  /home/moonbit/.moon/bin/moon version

# Configure npm to use per-user global directory
RUN mkdir -p ~/.npm-global && \
  npm config set prefix ~/.npm-global

# Install Claude Code (Anthropic CLI)
RUN npm install -g @anthropic-ai/claude-code

# Install Codex (OpenAI CLI)
RUN npm install -g @openai/codex

# Install Gemini CLI (Google)
RUN npm install -g @google/gemini-cli

# Install Kimi Code
RUN curl -LsSf https://code.kimi.com/install.sh | bash

# Default command
CMD ["/bin/bash"]
