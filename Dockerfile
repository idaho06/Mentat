ARG PASSWORD=docker_build_--build-arg_PASSWORD=your_password
ARG LOGDIR=/var/log/mentat

FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY mentat /usr/src/app/mentat

RUN python -m mentat -d DEBUG -p $PASSWORD --logdir $LOGDIR --reset --create-config-and-exit

CMD [ "python", "-m", "mentat" ]
