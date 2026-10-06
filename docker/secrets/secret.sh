#!/bin/bash
# secret list | set <NAME> | rotate-ssh   (needs write access to the secrets repo). Run through scripts\skill.ps1 secret.
set -euo pipefail
. /usr/local/lib/common.sh
allowed='^(VERDA_CLIENT_ID|VERDA_CLIENT_SECRET|YESOPEN_GPU_SSH_KEY|YESOPEN_GPU_SSH_KEY_PUB)$'
ensure_gh
case "${1:-}" in
  list) gh secret list --env broker --repo "$repo" ;;
  set)
    name="${2:?usage: secret set <NAME>}"
    [[ "$name" =~ $allowed ]] || { echo "unknown secret $name" >&2; exit 1; }
    gh secret set "$name" --env broker --repo "$repo"    # the value is typed hidden and goes straight to GitHub
    exec unlock ;;
  rotate-ssh)
    d=$(mktemp -d /tmp/k.XXXXXX); trap 'rm -rf "$d"' EXIT; umask 077
    ssh-keygen -q -t ed25519 -N '' -C yesopen-gpu -f "$d/k"    # tmpfs: never on disk
    base64 -w0 "$d/k" | gh secret set YESOPEN_GPU_SSH_KEY --env broker --repo "$repo"
    gh secret set YESOPEN_GPU_SSH_KEY_PUB --env broker --repo "$repo" --body "$(cat "$d/k.pub")"
    echo; echo "new SSH key set. Add this public key in Verda as 'yesopen-gpu' (and remove the old one):"; cat "$d/k.pub"
    rm -rf "$d"; trap - EXIT
    exec unlock ;;
  *) echo "usage: secret list | set <NAME> | rotate-ssh" >&2; exit 1 ;;
esac
