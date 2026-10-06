# shared by unlock, check and secret (sourced)
repo="${SECRETS_REPO:?set SECRETS_REPO=<owner>/<private-secrets-repo> in your environment (see docs/docker-client.md)}"

# your GitHub account (token kept in tmpfs only; the one-time code is entered in your browser)
ensure_gh() {
  if ! gh auth status >/dev/null 2>&1; then
    gh auth login --hostname github.com --git-protocol https --web --scopes repo --skip-ssh-key
  fi
  gh api "repos/$repo" --jq .full_name >/dev/null \
    || { echo "no access to $repo: ask the owner to add your GitHub account as a collaborator" >&2; return 1; }
}

# names and update times of the secrets: changes whenever anyone sets or rotates one
version() {
  gh api "repos/$repo/environments/broker/secrets" --jq '[.secrets[] | "\(.name):\(.updated_at)"] | sort | join(",")' 2>/dev/null || echo unknown
}
