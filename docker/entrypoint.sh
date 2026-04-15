#!/bin/bash

ARGS="--http-ip ${MAILDUMP_HTTP_IP} \
  --http-port ${MAILDUMP_HTTP_PORT} \
  --smtp-ip ${MAILDUMP_SMTP_IP} \
  --smtp-port ${MAILDUMP_SMTP_PORT} \
  -f"

PASSWORD_FILE=/maildump/data/passwd

if [[ ! -z $MAILDUMP_PASSWORD ]]; then
    htpasswd -bc $PASSWORD_FILE maildump $MAILDUMP_PASSWORD;
    /maildump/bin/maildump ${ARGS} --htpasswd $PASSWORD_FILE;
else
    /maildump/bin/maildump ${ARGS}
fi
