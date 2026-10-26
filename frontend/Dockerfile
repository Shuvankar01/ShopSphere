# Build stage
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
# The SSR bundle keeps react / @tanstack/* as external imports, so the runtime
# dependencies have to ship with it. Dev-only tooling is not needed at runtime.
RUN npm prune --omit=dev

# Production stage
FROM node:22-alpine AS production
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000
# package.json is required so Node treats dist/server/server.js as ESM.
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/server.mjs ./server.mjs
EXPOSE 3000
CMD ["node", "server.mjs"]
