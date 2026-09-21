# syntax=docker/dockerfile:1
ARG LOGDIR=/var/log/mentat

FROM python:latest

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY mentat /usr/src/app/mentat

ARG LOGDIR
# Secrets are read from BuildKit's ephemeral /run/secrets mount, not from
# --build-arg: build args are recoverable forever via `docker history` and
# the build cache, secret mounts are not. Note the generated mentat.conf
# still stores the password in plaintext inside the image filesystem
# (see README "Building the Docker image" for the resulting caveat).
RUN --mount=type=secret,id=password,required=true \
    --mount=type=secret,id=adminpassword,required=true \
    python -m mentat -d DEBUG \
        -p "$(cat /run/secrets/password)" \
        -a "$(cat /run/secrets/adminpassword)" \
        --logdir "${LOGDIR}" --reset --create-config-and-exit

CMD [ "python", "-m", "mentat", "-d", "INFO" ]
