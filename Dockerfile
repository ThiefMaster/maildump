FROM python:3.13-alpine

RUN apk add --update apache2-utils bash
RUN python -m venv /maildump
RUN /maildump/bin/pip install maildump

ENV MAILDUMP_PASSWORD=
ENV MAILDUMP_HTTP_IP=0.0.0.0
ENV MAILDUMP_HTTP_PORT=1080
ENV MAILDUMP_SMTP_IP=0.0.0.0
ENV MAILDUMP_SMTP_PORT=1025

ADD docker/entrypoint.sh /
RUN mkdir /maildump/data
RUN chown 1000 /maildump/data

USER 1000

ENTRYPOINT ["/entrypoint.sh"]
