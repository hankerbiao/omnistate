FROM node:20-alpine AS build

ARG HTTP_PROXY=http://10.2.48.65:7897
ARG HTTPS_PROXY=http://10.2.48.65:7897
ARG NO_PROXY=localhost,127.0.0.1,host.docker.internal,::1
ARG ALL_PROXY=socks5://10.2.48.65:7897
ARG VITE_OPEN_PLATFORM_API_BASE_URL=
ARG VITE_OPEN_PLATFORM_CONSOLE_TOKEN=dev-console-token
ARG VITE_OPEN_PLATFORM_USE_MOCK=false

ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    ALL_PROXY=${ALL_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY} \
    all_proxy=${ALL_PROXY} \
    VITE_OPEN_PLATFORM_API_BASE_URL=${VITE_OPEN_PLATFORM_API_BASE_URL} \
    VITE_OPEN_PLATFORM_CONSOLE_TOKEN=${VITE_OPEN_PLATFORM_CONSOLE_TOKEN} \
    VITE_OPEN_PLATFORM_USE_MOCK=${VITE_OPEN_PLATFORM_USE_MOCK}

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
