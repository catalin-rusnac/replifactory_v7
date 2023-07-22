#!/bin/sh

STDOUT_LOG=logs/express_server.log
STDERR_LOG=logs/express_server-error.log
mkdir -p logs
(node ./src/server/express_server.js $@ | tee -a $STDOUT_LOG) 3>&1 1>&2 2>&3 | tee -a $STDERR_LOG