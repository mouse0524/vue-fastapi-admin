#!/bin/sh
set -e

nginx -g "pid /tmp/nginx.pid;"
python run.py
