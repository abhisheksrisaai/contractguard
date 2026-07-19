# ── ContractGuard Frontend (Development) ─────────────────────────
# Node 18-alpine for lightweight local dev via docker-compose
FROM node:18-alpine

WORKDIR /app

# Install dependencies first (layer caching)
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start dev server with host binding
CMD ["npm", "run", "dev", "--", "--host"]
