# -------- Build stage --------
FROM node:22-alpine AS build

WORKDIR /app

# Enable Corepack so the Yarn version pinned in package.json is used
RUN corepack enable

# Copy manifests first for better layer caching
COPY package.json yarn.lock .yarnrc.yml ./

RUN yarn install --immutable

# Copy source and config needed by the Vite build
COPY index.html ./
COPY tsconfig.json ./
COPY vite.config.ts ./
COPY public/ public/
COPY src/ src/

ARG environment=dev
COPY ../environments/actions.env.${environment} .env

# X_PUBLIC_PATH is baked into the bundle at build time (Vite `base`),
# so it must be set here rather than at runtime.
# Its value is read from APP_PATH in the copied .env file.
RUN export X_PUBLIC_PATH=$(grep '^APP_PATH=' .env | cut -d'=' -f2-) && \
    X_PUBLIC_PATH=${X_PUBLIC_PATH:-/} && \
    yarn build

# -------- Production stage --------
FROM nginx:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
