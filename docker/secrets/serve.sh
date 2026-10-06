#!/bin/sh
# Serves /mem (tmpfs) read-only on the compose network, port 8080. Nothing is published to the host.
set -eu
mkdir -p /mem
exec httpd -f -v -p 8080 -h /mem
