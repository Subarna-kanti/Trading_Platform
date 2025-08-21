# Stage 1: Build the frontend
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy Vite config and source code
COPY index.html ./
COPY vite.config.js ./
COPY src ./src
COPY public ./public

# Build the production bundle
RUN npm run build

# Stage 2: Serve the frontend with a lightweight server
FROM nginx:alpine

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx config if needed (optional)
# COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
