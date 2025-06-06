# Final stage: Official Python runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV NODE_VERSION 20.14.0

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git curl build-essential ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm using nvm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
ENV NVM_DIR /root/.nvm
RUN . "$NVM_DIR/nvm.sh" && nvm install ${NODE_VERSION} && nvm alias default ${NODE_VERSION} && nvm use default
ENV PATH $NVM_DIR/versions/node/v${NODE_VERSION}/bin:$PATH

# Set a persistent working directory for the application
WORKDIR /app

# Copy and install Python requirements
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# --- SIMPLIFIED COPY ---
# We will copy the app structure into the WORKDIR so that Python can find modules
# But the live code for development will come from the volume mount.
# The WORKDIR will be /app and the code will be mounted at /frankie_codebase
# So to run the app, we need to add the codebase to the PYTHONPATH.
ENV PYTHONPATH "${PYTHONPATH}:/frankie_codebase/backend"

# Expose the port
EXPOSE 8000

# Command to run the application using Uvicorn
# It now looks for the app inside the mounted /frankie_codebase directory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/frankie_codebase/backend/app", "--reload-dir", "/frankie_codebase/config"]