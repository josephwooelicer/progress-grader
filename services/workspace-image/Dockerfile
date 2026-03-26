FROM gitpod/openvscode-server:latest

USER root

# Install git, Node.js (for building extension), and other dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Configure git defaults for student workspaces
RUN git config --system core.editor "code --wait" && \
    git config --system init.defaultBranch main

# Set workspace directory
ENV OPENVSCODE_SERVER_ROOT=/home/.openvscode-server
ENV HOME=/home/workspace
WORKDIR /home/workspace

# Create workspace dir owned by the openvscode user
RUN mkdir -p /home/workspace && chown -R openvscode-server:openvscode-server /home/workspace

# ── Build and install the VS Code extension ────────────────────────────────────
COPY --chown=openvscode-server:openvscode-server extension /tmp/extension

RUN cd /tmp/extension \
    && npm ci \
    && npm run package \
    && ${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server \
       --install-extension /tmp/extension/progress-grader-*.vsix \
       --without-connection-token \
    && rm -rf /tmp/extension

USER openvscode-server

# Expose the IDE port
EXPOSE 3000

ENTRYPOINT ["/bin/sh", "-c", \
    "exec ${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server \
    --host 0.0.0.0 \
    --port 3000 \
    --without-connection-token \
    --default-folder /home/workspace"]
