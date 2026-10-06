#!/bin/bash
# exit 0: the secrets in memory are current; exit 1: not loaded, or somebody changed them since (then run unlock)
set -u
. /usr/local/lib/common.sh
[ -f /mem/.ready ] || exit 1
gh auth status >/dev/null 2>&1 || exit 0     # cannot ask GitHub: keep what is loaded
now=$(version)
[ "$now" = unknown ] && exit 0
[ "$now" = "$(cat /mem/.version 2>/dev/null)" ]
