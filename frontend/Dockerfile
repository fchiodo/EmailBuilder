FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application (disable SSL verification for Google Fonts)
RUN NODE_TLS_REJECT_UNAUTHORIZED=0 npm run build

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]