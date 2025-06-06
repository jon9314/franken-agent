# Final stage: Official Python runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1  # Prevents Python from writing .pyc files to disc (good for containers)
ENV PYTHONUNBUFFERED 1       # Force stdin, stdout, and stderr to be totally unbuffered

# Set Node.js version for NVM
ENV NODE_VERSION 20.14.0

# Install system dependencies:
# - git: Required by GitPython for agent operations.
# - curl: Used by the NVM (Node Version Manager) installer script.
# - build-essential: May be needed for some Python packages that might compile C extensions.
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

# --- CORRECTED COPY INSTRUCTION ---
# Copy requirements.txt from the build context (which is ./backend) into the container's /app directory.
COPY requirements.txt /app/requirements.txt

# Install Python dependencies specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# --- SIMPLIFIED COPY FOR APPLICATION CODE ---
# Since docker-compose mounts the code for development, we only need to copy
# the code into the image as a fallback for creating a standalone production image.
# We also set the PYTHONPATH so the application can find modules within the mounted volume structure.
COPY app /app/app

# Set the PYTHONPATH to include the location of our application code within the mounted volume.
# This allows `uvicorn app.main:app` to work correctly.
ENV PYTHONPATH "${PYTHONPATH}:/frankie_codebase/backend"

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn.
# It now correctly looks for the app and reloads directories inside the mounted /frankie_codebase volume.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/frankie_codebase/backend/app", "--reload-dir", "/frankie_codebase/config"]
