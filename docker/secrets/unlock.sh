#!/bin/bash
# Run interactively:  docker compose exec secrets unlock
# Access is decided by GitHub: you get the secrets only if your account can see the private secrets repo
# (a collaborator). Remove someone from the repo and their next unlock fails.
set -euo pipefail
. /usr/local/lib/common.sh
umask 077
work=$(mktemp -d /tmp/unlock.XXXXXX)   # tmpfs: gone when the container stops
trap 'rm -rf "$work"' EXIT

# 1. your GitHub account
ensure_gh
version_before=$(version)   # taken before the request: a change in the meantime only makes the next check refresh again

# 2. a one-time key pair, made here; only the public half leaves the container
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$work/key.pem" 2>/dev/null
openssl pkey -in "$work/key.pem" -pubout -out "$work/pub.pem"
req=$(openssl rand -hex 16)

# 3. ask the secrets repo; its workflow encrypts the secrets to that public key
gh workflow run broker.yml --repo "$repo" -f request_id="$req" -f pubkey="$(base64 -w0 "$work/pub.pem")"
run=""
for _ in $(seq 1 30); do
  sleep 3
  run=$(gh run list --repo "$repo" --workflow broker.yml --limit 10 --json databaseId,displayTitle \
        --jq ".[] | select(.displayTitle|endswith(\"$req\")) | .databaseId" | head -1)
  [ -n "$run" ] && break
done
[ -n "$run" ] || { echo "the broker run did not start" >&2; exit 1; }
echo "waiting for the broker run $run (an approval may be required in the secrets repo)..."
gh run watch "$run" --repo "$repo" --exit-status >/dev/null || { echo "the broker run failed: see $repo, Actions" >&2; exit 1; }

# 4. fetch, decrypt in memory, remove the artifact
gh run download "$run" --repo "$repo" --name "bundle-$req" --dir "$work/dl"
aid=$(gh api "repos/$repo/actions/runs/$run/artifacts" --jq ".artifacts[] | select(.name==\"bundle-$req\") | .id")
openssl pkeyutl -decrypt -inkey "$work/key.pem" -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 \
  -in "$work/dl/pass.enc" -out "$work/pass"
openssl enc -d -aes-256-cbc -pbkdf2 -pass "file:$work/pass" -in "$work/dl/data.enc" -out "$work/plain"
[ -z "$aid" ] || gh api -X DELETE "repos/$repo/actions/artifacts/$aid" >/dev/null 2>&1 || true

mkdir -p /mem
find /mem -mindepth 1 -delete   # a refresh replaces everything: a secret removed upstream disappears here too
while IFS= read -r line; do
  name="${line%%=*}"; b64="${line#*=}"
  [[ "$name" =~ ^[A-Z_][A-Z0-9_]*$ ]] || continue
  printf '%s' "$b64" | base64 -d > "/mem/$name.tmp" && mv "/mem/$name.tmp" "/mem/$name"
  echo "loaded: $name"
done < "$work/plain"
printf "%s" "$version_before" > /mem/.version
touch /mem/.ready
echo "secrets are in memory; 'scripts\skill.ps1 lock' wipes them"
