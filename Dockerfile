from ubuntu:22.04

### Setup env

user root

ARG discord_token
ARG discord_token_dev
ARG gitlab_token 
ARG mongo_url
ARG spotify_id
ARG spotify_secret

ENV DSC_API_TOKEN=$discord_token
ENV DSC_DEV_TOKEN=$discord_token_dev
ENV GITLAB_TOKEN=$gitlab_token
ENV MONG_URL=$mongo_url
ENV SPOTIFY_ID=$spotify_id
ENV SPOTIFY_SECRET=$spotify_secret

COPY . /home/baseplate/compass-bot

################################################################################

### Build instructions

WORKDIR /home/baseplate

RUN apt update -y && apt upgrade -y ffmpeg libffi-dev libnacl-dev libopus0
RUN apt install -y sudo git python3.10 python3-pip
RUN ln -s /usr/bin/python3 /usr/bin/python 
RUN pip install --upgrade pip && \
    cd compass-bot && \
    pip install -r requirements.txt

### Configure user, env, and entrypoint ###
#RUN groupadd --gid 101 sudo
RUN useradd -ms /bin/bash -g root -G sudo -u 1000 baseplate && \
  echo 'baseplate:letmein' | chpasswd && \
  chown -R baseplate /home/baseplate && \ 
  chmod -R a+rw /opt
USER baseplate

WORKDIR /home/baseplate
EXPOSE 8888
EXPOSE 27015
ENTRYPOINT ["/bin/bash"]
