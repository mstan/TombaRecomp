#!/usr/bin/env bash
# Thin wrapper around the shared psxrecomp setup-host packager.
# Autofilled by tools/new_project_layout/setup_project.{sh,ps1}.
#
# Usage:
#   scripts/package_setup_release.sh <build-dir> <artifact-tag> [recompiler-build-dir]
#
# Writes: dist/tomba-<VERSION>-<artifact-tag>.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${1:-}"
ARTIFACT_TAG="${2:-}"
RECOMPILER_BUILD="${3:-build-recompiler}"
GAME_ID="SCUS-94236"

if [[ -z "${BUILD_DIR}" || -z "${ARTIFACT_TAG}" ]]; then
  echo "usage: $0 <build-dir> <artifact-tag> [recompiler-build-dir]" >&2
  exit 2
fi

PACKAGER="${ROOT}/psxrecomp/tools/package_setup_host.sh"
if [[ ! -f "${PACKAGER}" ]]; then
  echo "error: missing ${PACKAGER} (psxrecomp submodule)" >&2
  exit 1
fi
chmod +x "${PACKAGER}" 2>/dev/null || true

EXTRA_PROJECT=()
if [[ -f "${ROOT}/catalog_identity.json" ]]; then
  EXTRA_PROJECT+=(--project-file catalog_identity.json)
fi
if [[ -f "${ROOT}/framework_pins.txt" ]]; then
  EXTRA_PROJECT+=(--project-file framework_pins.txt)
fi
# Optional in-game options defaults — CMake POST_BUILD may copy this beside the
# runtime. Omitting it from the setup-host zip makes cmake --build fail after
# link and leaves RetComM without a releases/ binary.
if [[ -f "${ROOT}/game_options.toml" ]]; then
  EXTRA_PROJECT+=(--project-file game_options.toml)
fi

cd "${ROOT}"
bash "${PACKAGER}" \
  --root "${ROOT}" \
  --build-dir "${BUILD_DIR}" \
  --artifact "${ARTIFACT_TAG}" \
  --zip-prefix tomba \
  --exe-name Tomba__Recompiled \
  --display-name "Tomba! Recompiled" \
  --recompiler-build "${RECOMPILER_BUILD}" \
  --version-env RELEASE_VERSION \
  --disc-hint "your legally owned Tomba disc" \
  --project-file CMakeLists.txt \
  --project-file game.toml \
  --project-file VERSION \
  --project-file codegen_setup.c \
  --project-file codegen_setup.h \
  --project-file README.md \
  --project-dir src \
  --project-dir mods \
  --project-dir seeds \
  --project-dir launcher_assets \
  --runtime-dir-optional mods \
  "${EXTRA_PROJECT[@]}"

DIST="${ROOT}/dist"
STAGE="${DIST}/stage-setup-${ARTIFACT_TAG}"
if [[ ! -d "${STAGE}" ]]; then
  echo "error: setup stage missing after packager: ${STAGE}" >&2
  exit 1
fi
if [[ ! -f "${STAGE}/psx_game_version.txt" ]]; then
  echo "error: setup stage missing psx_game_version.txt" >&2
  exit 1
fi
VERSION="$(tr -d '[:space:]' <"${STAGE}/psx_game_version.txt")"
ZIP_NAME="tomba-${VERSION}-${ARTIFACT_TAG}.zip"
ZIP_PATH="${DIST}/${ZIP_NAME}"

resolve_cache_source() {
  local cand
  local roots=()
  for cand in \
    "${TOMBA_SHARD_CACHE_DIR:-}" \
    "${PSXRECOMP_SHARD_CACHE_DIR:-}" \
    "${OVERLAY_CACHE_DIR:-}" \
    "${ROOT}/build-setup-shards/cache" \
    "${ROOT}/build-stable/cache" \
    "${ROOT}/build-release/cache" \
    "${ROOT}/psxrecomp-shards/${GAME_ID}/cache" \
    "${ROOT}/../psxrecomp-shards/${GAME_ID}/cache"
  do
    [[ -n "${cand}" ]] && roots+=("${cand}")
  done

  for cand in "${roots[@]}"; do
    [[ -d "${cand}" ]] || continue
    if [[ -d "${cand}/gcc" || -d "${cand}/tcc" ]]; then
      printf '%s\n' "${cand}"
      return 0
    fi
    if [[ -d "${cand}/${GAME_ID}/gcc" || -d "${cand}/${GAME_ID}/tcc" ]]; then
      printf '%s\n' "${cand}/${GAME_ID}"
      return 0
    fi
    if [[ -d "${cand}/cache/${GAME_ID}/gcc" || -d "${cand}/cache/${GAME_ID}/tcc" ]]; then
      printf '%s\n' "${cand}/cache/${GAME_ID}"
      return 0
    fi
    if [[ -d "${cand}/${GAME_ID}/cache/gcc" || -d "${cand}/${GAME_ID}/cache/tcc" ]]; then
      printf '%s\n' "${cand}/${GAME_ID}/cache"
      return 0
    fi
  done
  return 1
}

CACHE_SRC="$(resolve_cache_source || true)"
if [[ -z "${CACHE_SRC}" ]]; then
  echo "error: no compiled shard cache found for ${GAME_ID}" >&2
  echo "  Set TOMBA_SHARD_CACHE_DIR to a cache root containing ${GAME_ID}/gcc/...," >&2
  echo "  or build shards into build-setup-shards/cache before packaging." >&2
  exit 1
fi

CACHE_DST="${STAGE}/cache/${GAME_ID}"
rm -rf "${CACHE_DST}"
mkdir -p "${CACHE_DST}"
shard_count=0
while IFS= read -r -d '' rel; do
  rel="${rel#./}"
  mkdir -p "${CACHE_DST}/$(dirname "${rel}")"
  cp -a "${CACHE_SRC}/${rel}" "${CACHE_DST}/${rel}"
  case "${rel}" in
    *.dll|*.so) shard_count=$((shard_count + 1)) ;;
  esac
done < <(
  cd "${CACHE_SRC}"
  find . -type f \
    \( -name '*.dll' -o -name '*.so' -o -name '*.ranges' -o -name '*.resident' \) \
    \( -path './gcc/*/cg*_gc*_f*/*' -o -path './tcc/*/cg*_gc*_f*/*' \) \
    -print0
)

if [[ "${shard_count}" -eq 0 ]]; then
  echo "error: ${CACHE_SRC} has no current-format compiled shards" >&2
  echo "  Expected ${GAME_ID}/{gcc,tcc}/<arch>/cg<ver>_<hash>_gc<config>_f<flavor>/*.dll|*.so" >&2
  exit 1
fi

bad_asset=0
while IFS= read -r bad; do
  rel="${bad#${STAGE}/}"
  case "${rel}" in
    psxrecomp/bios/openbios.bin|psxrecomp/dummy.0.mcr|psxrecomp/dummy.1.mcr)
      continue
      ;;
  esac
  echo "error: forbidden game-user asset staged in setup package: ${rel}" >&2
  bad_asset=1
done < <(
  find "${STAGE}" -type f \
    \( -name 'overlay_captures*.json' -o -name '*.bin' -o -name '*.cue' -o -name '*.iso' -o -name '*.chd' -o -name '*.mcr' -o -name '*.srm' \)
)
if [[ "${bad_asset}" -ne 0 ]]; then
  exit 1
fi

rm -f "${ZIP_PATH}"
(
  cd "${STAGE}"
  zip -r -q "${ZIP_PATH}" .
)
echo "Bundled ${shard_count} compiled overlay shard(s) from ${CACHE_SRC}"
echo "Updated ${ZIP_PATH}"
