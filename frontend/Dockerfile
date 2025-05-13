FROM node:18

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# 指定環境變數讓 react-scripts 綁定對外
ENV HOST=0.0.0.0
ENV PORT=3001

EXPOSE 3001

CMD ["npm", "start"]