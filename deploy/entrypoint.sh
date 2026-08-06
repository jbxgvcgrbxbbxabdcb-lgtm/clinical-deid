#!/bin/sh
# Prefer a warm openmed/HF cache; otherwise allow Hub download on first detect.
set -eu

CACHE="${HF_HOME:-/root/.cache/openmed}"
MODEL_REPO="models--OpenMed--OpenMed-PII-SuperClinical-Small-44M-v1"
SNAP_ROOT="${CACHE}/${MODEL_REPO}"

has_model=0
if [ -f "${SNAP_ROOT}/refs/main" ]; then
  rev="$(tr -d '[:space:]' <"${SNAP_ROOT}/refs/main")"
  if [ -n "${rev}" ] && {
    [ -f "${SNAP_ROOT}/snapshots/${rev}/model.safetensors" ] \
      || [ -L "${SNAP_ROOT}/snapshots/${rev}/model.safetensors" ]
  }; then
    has_model=1
  fi
fi

if [ "${has_model}" -eq 1 ]; then
  export HF_HUB_OFFLINE=1
  export TRANSFORMERS_OFFLINE=1
  # Host-built integrity manifests often embed absolute paths that do not exist
  # inside the container; skip verify when loading a pre-seeded cache.
  export OPENMED_SKIP_MODEL_VERIFY=1
  echo "openmed: local model cache found — offline mode"
else
  export HF_HUB_OFFLINE=0
  export TRANSFORMERS_OFFLINE=0
  unset OPENMED_SKIP_MODEL_VERIFY || true
  echo "openmed: no local model cache — first detect will download from Hugging Face"
  echo "openmed: if Hub is unreachable, pre-seed ~/.cache/openmed on the host (see deploy/README.md)"
fi

exec "$@"
