FROM node:20-alpine

WORKDIR /app

# Copy only the HTTP server (uses only built-in Node modules)
COPY http-server.mjs .

# Create data directory for reminders.json
RUN mkdir -p /app/data

EXPOSE 8802

CMD ["node", "http-server.mjs"]
