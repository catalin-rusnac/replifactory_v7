FROM node:18.16.1-bullseye

ARG NODE_ENV=production

ENV NODE_ENV $NODE_ENV

WORKDIR /usr/src/app

RUN chown node:node ./

USER node

COPY package.json package-lock.json* ./

RUN npm ci && npm cache clean --force

COPY --chown=node:node ./src ./src
COPY --chown=node:node ./dist ./dist 
COPY --chown=node:node --chmod=775 ./entrypoint.sh ./

ENTRYPOINT ["./entrypoint.sh"]