FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install --production

# Copy source code
COPY . .

# Create cache directory for transformers
RUN mkdir -p /app/.cache

ENV NODE_ENV=production
ENV TRANSFORMERS_CACHE=/app/.cache

EXPOSE 8801

# Start HTTP server
CMD ["node", "http-server.mjs"]
