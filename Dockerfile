FROM hivesolutions/python:latest

LABEL version="1.0"
LABEL maintainer="Hive Solutions <development@hive.pt>"

EXPOSE 8080

ENV LEVEL INFO
ENV SERVER netius
ENV SERVER_ENCODING gzip
ENV HOST 0.0.0.0
ENV PORT 8080
ENV PYTHONPATH /src

ADD requirements.txt /
ADD extra.txt /
ADD src /src
ADD assets/fonts/* /usr/share/fonts/truetype/

RUN apk update && apk add libpng-dev libjpeg-turbo-dev libwebp-dev freetype-dev cairo-dev
RUN pip3 install -r /requirements.txt && pip3 install -r /extra.txt && pip3 install --upgrade netius

CMD ["/usr/bin/python3", "/src/colony_print/main.py"]
