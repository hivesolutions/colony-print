FROM ubuntu:latest
MAINTAINER Hive Solutions

EXPOSE 8080

ENV LEVEL INFO
ENV SERVER netius
ENV SERVER_ENCODING gzip
ENV HOST 0.0.0.0
ENV PORT 8080

ADD requirements.txt /
ADD src /src
ADD assets/fonts/* /usr/share/fonts/truetype/

RUN apt-get update && apt-get install -y -q python python-setuptools python-dev python-pip libpng12-dev libjpeg-turbo8-dev libfreetype6-dev
RUN pip install -r /requirements.txt && pip install --upgrade netius

CMD python /src/colony_print/main.py
