ARG PASSWORD=docker_build_--build-arg_PASSWORD...
ARG ADMINPASSWORD=docker_build_--build-arg_ADMINPASSWORD...
ARG LOGDIR=/var/log/mentat

FROM python:latest

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY mentat /usr/src/app/mentat

RUN python -m mentat -d DEBUG -p '${PASSWORD}' -a '${ADMINPASSWORD}' --logdir ${LOGDIR} --reset --create-config-and-exit

CMD [ "python", "-m", "mentat", "-d", "INFO" ]
