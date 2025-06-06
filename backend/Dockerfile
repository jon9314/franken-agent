# Stage 1: Build stage (if any build steps were needed for Python, e.g., compiling wheels)
# For this project, Python dependencies are installed directly.

# Final stage: Official Python runtime
FROM python:3.11

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1  # Prevents Python from writing .pyc files to disc (good for containers)
ENV PYTHONUNBUFFERED 1       # Force stdin, stdout, and stderr to be totally unbuffered

# Set Node.js version for NVM
ENV NODE_VERSION 20.14.0

# Install system dependencies:
# - git: Required by GitPython for agent's Git operations.
# - curl: Used by the NVM (Node Version Manager) installer script.
# - build-essential: May be needed for some Python packages that compile C extensions during pip install.
# - ca-certificates: For HTTPS requests made by curl/other tools.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Install Node.js and npm using Node Version Manager (nvm) ---
# This is primarily for the CodeModifierPlugin to run Prettier via `npx prettier`.
# Note: This adds to the image size. For a highly optimized production image where
# these tools are not run directly by the production Python process, consider
# using a multi-stage build or a separate "tools" container.
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
ENV NVM_DIR /root/.nvm
# The following RUN command executes in a new shell, so nvm needs to be sourced again.
RUN . "$NVM_DIR/nvm.sh" && \
    nvm install ${NODE_VERSION} && \
    nvm alias default ${NODE_VERSION} && \
    nvm use default

# Add nvm's Node.js and npm to the PATH for subsequent commands and the final container environment.
ENV PATH $NVM_DIR/versions/node/v${NODE_VERSION}/bin:$PATH

# Verify Node.js and npm installation (optional, good for debugging Dockerfile)
RUN node --version
RUN npm --version
RUN npx --version # Verify npx is available

# Set the working directory for the application inside the container
WORKDIR /app

# Copy only requirements.txt first to leverage Docker's layer caching.
# If requirements.txt hasn't changed, Docker can reuse the layer from a previous build.
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the backend application's code into the /app directory.
# This includes alembic.ini, the alembic/ directory, and the app/ directory.
# Note: For development, docker-compose.yml mounts the host's ./backend/app
# to /frankie_codebase/backend/app and ./config to /app/config.
# The application code itself runs from /app as defined by WORKDIR.
COPY ./alembic.ini /app/alembic.ini
COPY ./alembic /app/alembic
# This is the Python application code
COPY ./app /app

# The directory /frankie_codebase (project root) will be created and populated by the
# docker-compose volume mount: `- ./:/frankie_codebase`

# Expose the port the Uvicorn server will run on inside the container
EXPOSE 8000

# Command to run the application using Uvicorn.
# --host 0.0.0.0: Makes the server accessible from outside the container.
# --port 8000: The port Uvicorn listens on inside the container.
# --reload: Enables auto-reloading when code changes are detected. Good for development.
# --reload-dir: Specifies directories to watch for changes.
#   - Watches the application code copied into /app/app.
#   - Watches /frankie_codebase/backend/app for changes made by the agent or local dev.
#   - Watches /frankie_codebase/config for changes to config.yml (though app only reads on startup).
# For production, you would typically remove --reload and --reload-dir for stability and performance.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app", "--reload-dir", "/frankie_codebase/backend/app", "--reload-dir", "/frankie_codebase/config"]