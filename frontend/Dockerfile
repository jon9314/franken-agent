### STAGE 1: Build The React Application ###
# Use an official Node.js Long Term Support (LTS) version on Alpine Linux for a smaller build image.
# Using a specific version like '20-alpine' is better than 'latest' for reproducibility.
FROM node:20-alpine AS build

# Set the working directory inside the container for the build process.
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock) first.
# This step is crucial for leveraging Docker's layer caching. If these files haven't changed,
# Docker can reuse the layer from a previous build that contains all the installed node_modules,
# significantly speeding up subsequent builds.
COPY package*.json ./
# If using yarn instead of npm:
# COPY yarn.lock ./

# Install project dependencies using 'npm ci' which is generally faster and safer for builds
# as it installs directly from the lockfile.
RUN npm ci
# If using yarn:
# RUN yarn install --frozen-lockfile

# Copy the rest of the application source code into the /app directory in the container.
COPY . .

# Build the React application for production.
# This command must match the "build" script defined in your package.json.
# It will typically create a 'dist' or 'build' folder in /app containing the optimized static assets.
RUN npm run build


### STAGE 2: Serve The Application with Nginx ###
# Use an official Nginx image based on Alpine Linux for a very lightweight production server.
FROM nginx:1.25-alpine

# Remove the default Nginx welcome page and its configuration file.
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom Nginx configuration file from the project's frontend directory.
# This file tells Nginx how to serve our Single Page Application.
# It must be named nginx.conf and be in the same directory as this Dockerfile.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the static build output from the 'build' stage (the /app/dist folder)
# into Nginx's default web root directory (/usr/share/nginx/html).
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx listens on port 80 by default inside the container. We expose this port.
# The actual mapping of this port to a port on the host machine will be done in docker-compose.yml.
EXPOSE 80

# The default command for the Nginx image is `nginx -g 'daemon off;'` which keeps Nginx
# running in the foreground. This is the standard and correct way to run Nginx in a Docker
# container, so we do not need to override the CMD.