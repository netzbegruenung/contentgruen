#!/bin/sh
# Replace placeholder values in Angular's built JavaScript files with environment variables

for file in /usr/share/nginx/html/*.js; do
  sed -i "s|\${PRODUCTION}|${PRODUCTION}|g" $file
  sed -i "s|\${API_BASE_URL}|${API_BASE_URL}|g" $file
  sed -i "s|\${USE_KEYCLOAK}|${USE_KEYCLOAK}|g" $file
done
