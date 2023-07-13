FROM python:3.10.12-bullseye

ARG USER=flask

ENV USER_NAME=$USER

WORKDIR /usr/src/app

RUN useradd -mU $USER_NAME && chown $USER_NAME:$USER_NAME ./

USER $USER

COPY requirements-lock.txt ./

RUN pip install --no-cache-dir -r requirements-lock.txt

COPY --chown=$USER:$USER . .

RUN chmod +x entrypoint.sh

RUN mkdir -p data 

ENTRYPOINT ["./entrypoint.sh"]
