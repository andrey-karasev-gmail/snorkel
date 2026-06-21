#!/bin/sh

cd /app

node -e "
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
pkg.overrides = {
  'lodash': '4.17.21',
  'semver': '7.6.3',
  'axios': '1.6.8',
  'express': '4.19.2',
  'react': '18.3.1'
};
fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2) + '\n');
"

rm -f package-lock.json
npm install --prefer-offline
