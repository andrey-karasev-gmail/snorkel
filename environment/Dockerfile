FROM public.ecr.aws/docker/library/node:24.4-alpine@sha256:820e86612c21d0636580206d802a726f2595366e1b867e564cbc652024151e8a

RUN sed -i 's|https://dl-cdn.alpinelinux.org|http://dl-cdn.alpinelinux.org|g' /etc/apk/repositories \
    && apk add --no-cache \
        bash \
        tmux \
        python3 \
        py3-pip

RUN pip3 install --no-cache-dir --break-system-packages \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    asciinema==2.4.0 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /app

COPY app/package.json app/package-lock.json ./
COPY app/packages/core/package.json ./packages/core/
COPY app/packages/api/package.json ./packages/api/
COPY app/packages/ui/package.json ./packages/ui/
COPY app/packages/cli/package.json ./packages/cli/

RUN npm config set strict-ssl false \
    && npm install

# Pre-cache the override target versions so solve.sh can run npm install offline
RUN npm install --no-save \
    lodash@4.17.21 \
    semver@7.6.3 \
    axios@1.6.8 \
    express@4.19.2 \
    react@18.3.1

COPY app/ .
