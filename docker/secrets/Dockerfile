# Sidecar that holds the secrets for the project container. Nothing secret is built in.
# `unlock` signs in with the user's own GitHub account, asks the private secrets repo (workflow broker.yml) for the
# secrets encrypted to a one-time key made here, decrypts them into /mem (tmpfs, memory only) and serves them to
# the skill container on the compose network. Stopping the container wipes everything.
FROM alpine:3.22
RUN apk add --no-cache github-cli openssl openssh-keygen busybox-extras jq bash
COPY serve.sh unlock.sh check.sh secret.sh common.sh /tmp/s/
RUN install -m755 /tmp/s/serve.sh /usr/local/bin/serve.sh \
 && install -m755 /tmp/s/unlock.sh /usr/local/bin/unlock \
 && install -m755 /tmp/s/check.sh /usr/local/bin/check \
 && install -m755 /tmp/s/secret.sh /usr/local/bin/secret \
 && install -D -m644 /tmp/s/common.sh /usr/local/lib/common.sh \
 && rm -rf /tmp/s
ENV HOME=/tmp GH_CONFIG_DIR=/tmp/gh
CMD ["/usr/local/bin/serve.sh"]
