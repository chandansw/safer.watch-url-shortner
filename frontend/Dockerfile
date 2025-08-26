# Use official Node.js image
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install react-scripts@5.0.1
COPY . .
RUN npm install && npm run build
EXPOSE 3000
CMD ["npm", "start"]
