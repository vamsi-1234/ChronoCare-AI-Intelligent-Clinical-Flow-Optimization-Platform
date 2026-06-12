#!/bin/sh
set -e
# Substitute ONLY ${NGINX_API_URL} — all other nginx $vars are left for nginx to handle
envsubst '${NGINX_API_URL}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf
exec "$@"
