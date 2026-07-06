# Stage 1: Build the Angular application

FROM node:22@sha256:3218f0d1b9e4b63def322e9ae362d581fbeac1ef21b51fc502ef91386667ce92 AS build

# Accept build configuration as an argument (defaults to production)
ARG BUILD_CONFIGURATION=production

WORKDIR /app
COPY ["package.json", "package-lock.json*", "./"]
RUN npm install
COPY . .

# Create environment.ts from appropriate source based on build configuration
RUN if [ "$BUILD_CONFIGURATION" = "development" ] || [ "$BUILD_CONFIGURATION" = "docker" ]; then \
      echo "Using Docker environment configuration"; \
      cp src/environments/environment.docker.ts src/environments/environment.ts; \
    elif [ -f "src/environments/environment.ts.template" ]; then \
      echo "Using environment template"; \
      cp src/environments/environment.ts.template src/environments/environment.ts; \
    else \
      echo "Using production environment configuration"; \
      cp src/environments/environment.prod.ts src/environments/environment.ts; \
    fi

# Build with the specified configuration
RUN npx ng build contentgruen-frontend --configuration ${BUILD_CONFIGURATION}


# Stage 2: Serve the application with Nginx

FROM nginx:alpine@sha256:d67ea0d64d518b1bb04acde3b00f722ac3e9764b3209a9b0a98924ba35e4b779

# Accept build arg for nginx config file
ARG NGINX_CONF=nginx.conf

# Copy the appropriate Nginx configuration file
COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf

# Note that due to Angular Universal the path since a while needs to be set to the browser subfolder
COPY --from=build /app/dist/contentgruen-frontend/browser /usr/share/nginx/html

# Add script to replace environment variables at runtime
COPY replace-env.sh /usr/share/nginx/html/
# Remove Windows line endings from the script
RUN sed -i 's/\r$//' /usr/share/nginx/html/replace-env.sh
RUN chmod +x /usr/share/nginx/html/replace-env.sh

EXPOSE 80

# Run the environment variable replacement script before starting Nginx
CMD ["/bin/sh", "-c", "/usr/share/nginx/html/replace-env.sh && nginx -g 'daemon off;'"]
