FROM python:3.10.12-bullseye

RUN apt-get update && apt-get install -y \
    libusb-1.0 \
    && rm -rf /var/lib/apt/lists/*

ARG USER=flask

ENV USER_NAME=$USER

WORKDIR /usr/src/app

RUN useradd -mU $USER_NAME && \
    chown $USER_NAME:$USER_NAME ./ && \
    usermod -aG plugdev $USER

USER $USER

COPY requirements-lock.txt ./

RUN pip install --no-cache-dir -r requirements-lock.txt

COPY --chown=$USER:$USER . .

RUN chmod +x entrypoint.sh

ENV PATH=$PATH:/home/flask/.local/bin/

ENTRYPOINT ["./entrypoint.sh"]
