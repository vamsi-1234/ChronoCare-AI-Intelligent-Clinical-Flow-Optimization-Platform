#!/bin/sh
set -e
# Substitute ONLY these two vars — all other nginx $vars are left intact
envsubst '${NGINX_API_URL} ${NGINX_API_HOST}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf
exec "$@"
