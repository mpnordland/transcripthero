FROM python:3.7-alpine

RUN adduser -D transcripthero 

WORKDIR /home/transcripthero

COPY dist/transcript_hero-2.0.tar.gz transcript_hero-2.0.tar.gz
COPY docker-files/* ./
RUN python -m venv venv

RUN apk update && apk add --virtual build-dependencies gcc libc-dev make libffi-dev openssl-dev python3-dev libxml2-dev libxslt-dev
# Pillow deps
RUN apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev harfbuzz-dev fribidi-dev
RUN LIBRARY_PATH=/lib:/usr/lib /bin/sh -c "venv/bin/pip install transcript_hero-2.0.tar.gz"
RUN apk del build-dependencies
RUN venv/bin/pip install gunicorn

RUN mkdir data
RUN chown -R transcripthero:transcripthero ./
USER transcripthero

RUN chmod +x boot-web.sh
RUN chmod +x boot-task.sh
RUN chmod +x migrate-db.sh

ENTRYPOINT ["./boot-web.sh"]