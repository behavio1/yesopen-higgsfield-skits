#!/usr/bin/env bash
# Prepares the container's home from what is mounted from Windows, then runs the command.
#   environment       VERDA_CLIENT_ID, VERDA_CLIENT_SECRET, YESOPEN_GPU_SSH_KEY[_PUB]: filled below from the secrets sidecar
#                     (scripts\skill.ps1 unlock). Never baked into the image or kept in a file.
#   $YESOPEN_GPU_HOME a named volume: config.json and state.json survive between runs
# Windows mounts have no usable file modes or LF endings, so the files are copied and fixed here.
set -euo pipefail

KEY_NAME=id_ed25519_yesopen_gpu

# no value in the environment (local run): ask the secrets sidecar, which holds them in memory after `skill.ps1 unlock`
if [ -n "${SECRETS_URL:-}" ]; then
  for name in VERDA_CLIENT_ID VERDA_CLIENT_SECRET YESOPEN_GPU_SSH_KEY YESOPEN_GPU_SSH_KEY_PUB; do
    [ -z "${!name:-}" ] || continue
    value=$(python3 -c 'import sys,urllib.request; sys.stdout.write(urllib.request.urlopen(sys.argv[1], timeout=3).read().decode())' \
            "$SECRETS_URL/$name" 2>/dev/null || true)
    [ -z "$value" ] || export "$name=$value"
  done
fi


mkdir -p "$HOME/.ssh" "$YESOPEN_GPU_HOME"
chmod 700 "$HOME/.ssh"

# an env value holding a key: real line breaks, \n written out, or the whole file in base64
key_from_env() {
  local value="$1" out
  if [[ "$value" == *"BEGIN "* ]]; then
    out=$(printf '%b' "$value")   # %b turns the two characters \n into a line break
  else
    out=$(printf '%s' "$value" | base64 -d 2>/dev/null | tr -d '\r')
  fi
  printf '%s\n' "$out"   # OpenSSH rejects a key without the final line break
}

if [ -n "${YESOPEN_GPU_SSH_KEY:-}" ]; then
  key_from_env "$YESOPEN_GPU_SSH_KEY" > "$HOME/.ssh/$KEY_NAME"
  [ -n "${YESOPEN_GPU_SSH_KEY_PUB:-}" ] && printf '%s\n' "$YESOPEN_GPU_SSH_KEY_PUB" | tr -d '\r' > "$HOME/.ssh/$KEY_NAME.pub"
  chmod 600 "$HOME/.ssh/$KEY_NAME"
  # the key is a file now; keep it out of the environment of every command that follows
  unset YESOPEN_GPU_SSH_KEY YESOPEN_GPU_SSH_KEY_PUB
  if ! ssh-keygen -y -f "$HOME/.ssh/$KEY_NAME" >/dev/null 2>&1; then
    echo "YESOPEN_GPU_SSH_KEY is not a valid private key" >&2
    rm -f "$HOME/.ssh/$KEY_NAME" "$HOME/.ssh/$KEY_NAME.pub"
  fi
fi


# first run: a config from the example, with the key path of this container
conf="$YESOPEN_GPU_HOME/config.json"
if [ ! -f "$conf" ] && [ -f /skill/gpu/client/config.example.json ]; then
  python3 - /skill/gpu/client/config.example.json "$conf" "$KEY_NAME" <<'EOF'
import json, sys
config = json.loads(open(sys.argv[1], encoding="utf-8-sig").read())
config["ssh_key"] = f"~/.ssh/{sys.argv[3]}"
open(sys.argv[2], "w").write(json.dumps(config, indent=2) + "\n")
EOF
  echo "config made from the example in $conf: fill verda.instance_type and verda.ssh_key_id" >&2
fi

exec "$@"
