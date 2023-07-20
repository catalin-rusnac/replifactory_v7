#!/bin/sh

STDOUT_LOG=logs/flask.log
STDERR_LOG=logs/flask-error.log
mkdir -p logs data
(python server.py serve $@ | tee -a $STDOUT_LOG) 3>&1 1>&2 2>&3 | tee -a $STDERR_LOG