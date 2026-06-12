FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 3000
# nginx official image runs /docker-entrypoint.d/ which calls envsubst on *.template files
# NGINX_API_URL defaults to local docker-compose service; override for Render/prod
ENV NGINX_API_URL=http://api:8000
CMD ["nginx", "-g", "daemon off;"]
