#!/bin/sh
cd $1
[ -f package-lock.json ] && rm package-lock.json
npm install
npm ci --production=false
npm run build
npm ci --production=true
rm -rf node_modules/.cache
