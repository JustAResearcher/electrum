#!/bin/bash

set -e

PROJECT_ROOT="$(dirname "$(readlink -e "$0")")/../../.."
CONTRIB="$PROJECT_ROOT/contrib"
CONTRIB_APPIMAGE="$CONTRIB/build-linux/appimage"

# when bumping the runtime commit also check if the `type2-runtime-reproducible-build.patch` still works
TYPE2_RUNTIME_COMMIT="5e7217b7cfeecee1491c2d251e355c3cf8ba6e4d"
TYPE2_RUNTIME_REPO="https://github.com/AppImage/type2-runtime.git"

. "$CONTRIB"/build_tools_util.sh


TYPE2_RUNTIME_REPO_DIR="$PROJECT_ROOT/contrib/build-linux/appimage/.cache/appimage/type2-runtime"
if [ -f "$TYPE2_RUNTIME_REPO_DIR/runtime-x86_64" ]; then
    info "type2-runtime already built, skipping"
    exit 0
fi

# Building type2-runtime from source in the upstream Alpine Docker image
# fails because the Dockerfile pins Alpine package versions
# (clang19=19.1.4-r0, bash=5.2.37-r0, mimalloc2-dev=2.1.7-r0, ...) that have
# since been bumped in Alpine repos and are no longer fetchable from
# dl-cdn.alpinelinux.org. Until upstream rolls those pins forward, download
# the pre-built `runtime-x86_64` AppImage publishes at the `continuous`
# release on every push to its main branch.
mkdir -p "$TYPE2_RUNTIME_REPO_DIR"
RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
info "downloading prebuilt type2-runtime from $RUNTIME_URL ..."
curl -fL --retry 3 -o "$TYPE2_RUNTIME_REPO_DIR/runtime-x86_64" "$RUNTIME_URL" \
    || fail "could not download prebuilt runtime-x86_64"
chmod +x "$TYPE2_RUNTIME_REPO_DIR/runtime-x86_64"

info "runtime download successful: $(sha256sum "$TYPE2_RUNTIME_REPO_DIR/runtime-x86_64")"
