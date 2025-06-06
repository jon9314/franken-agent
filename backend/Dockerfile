# Stage 1: Build stage (if any build steps were needed for Python, e.g., compiling wheels)
# For this project, Python dependencies are installed directly.

# Final stage: Official Python runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1  # Prevents Python from writing .pyc files to disc (good for containers)
ENV PYTHONUNBUFFERED 1       # Force stdin, stdout, and stderr to be totally unbuffered

# Set Node.js version for NVM
ENV NODE_VERSION 20.14.0

# Install system dependencies:
# - git: Required by GitPython for agent's Git operations.
# - curl: Used by the NVM (Node Version Manager) installer script.
# - build-essential: May be needed for some Python packages that might compile C extensions during pip install.
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

# Copy requirements first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the backend application's code into the /app directory.
# This is what runs if no volume is mounted.
COPY ./alembic.ini /app/alembic.ini
COPY ./alembic /app/alembic
COPY ./app /app/app # The Python application code

# The directory /frankie_codebase will be created by the docker-compose volume mount.

# Expose the port the app runs on
EXPOSE 8000

# --- CORRECTED COMMAND ---
# We remove the `--reload-dir /app/app` because that path doesn't exist at runtime with our volumes.
# The application code itself is located at `/frankie_codebase/backend/app`.
# We also remove the reload watch on `/app/app` which was redundant.
# The entrypoint "app.main:app" still works because the WORKDIR is /app.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/frankie_codebase/backend/app", "--reload-dir", "/frankie_codebase/config"]