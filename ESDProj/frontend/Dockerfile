FROM node:20-alpine
WORKDIR /app
# Phase 2 will add package.json and Vue app source
# Phase 1 placeholder: serve a simple index.html
RUN echo '<!DOCTYPE html><html><body><h1>ESD Rental Car - Phase 1 Placeholder</h1></body></html>' > index.html
EXPOSE 8080
CMD ["npx", "--yes", "serve", "-s", ".", "-l", "8080"]
