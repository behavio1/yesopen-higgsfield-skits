# Client environment for this skill: the GPU client needs rsync, OpenSSH with ControlMaster, pkill, ffmpeg and the
# Verda CLI, which Windows lacks. Everything runs in a container; nothing is installed on Windows.
#
#   docker compose build            (from the repo root)
#   scripts\skill.ps1 <command>     see scripts/skill.ps1
#
# Two stages: the downloads (curl, xz, checksums) happen in a throwaway Alpine stage, so the final image carries
# only the binaries. ffmpeg is the shared build: the libraries exist once, ffmpeg and ffprobe are small.
#
# BuildKit cache mounts keep the apk, apt and pip packages and the downloaded archives between builds, so a rebuild
# after a change does not fetch them again. They live in the builder, not in the image; `docker builder prune` clears
# them. The ffmpeg download is cached by series: to take a newer "latest" build, prune the cache.
FROM alpine:3.20 AS fetch

ARG VERDA_VERSION=1.8.2
ARG FFMPEG_SERIES=8.1

RUN --mount=type=cache,target=/var/cache/apk \
    ln -sf /var/cache/apk /etc/apk/cache \
 && apk add curl xz ca-certificates

# ffmpeg and ffprobe (shared GPL build) into /out/ffmpeg: bin/ and lib/
RUN --mount=type=cache,target=/dl \
    set -eux; mkdir -p /out/ffmpeg /tmp/f; f="/dl/ffmpeg-${FFMPEG_SERIES}-gpl-shared.txz"; \
    name="ffmpeg-n${FFMPEG_SERIES}-latest-linux64-gpl-shared-${FFMPEG_SERIES}.tar.xz"; \
    base="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"; \
    if [ ! -s "$f" ]; then curl -fsSL -o "$f.part" "$base/$name"; mv "$f.part" "$f"; fi; \
    curl -fsSL "$base/checksums.sha256" | grep " $name\$" | sed "s# .*#  $f#" > /tmp/ffmpeg.sum; \
    if ! { [ -s /tmp/ffmpeg.sum ] && sha256sum -c /tmp/ffmpeg.sum; }; then \
      echo "ffmpeg checksum mismatch (a newer build of the series? then run: docker builder prune)"; rm -f "$f"; exit 1; \
    fi; \
    tar xJf "$f" -C /tmp/f --strip-components=1; \
    cp -a /tmp/f/bin/ffmpeg /tmp/f/bin/ffprobe /out/ffmpeg/; \
    cp -a /tmp/f/lib /out/ffmpeg/lib; \
    rm -rf /tmp/f

# Verda CLI, SHA-256 checked (also when the archive comes from the cache)
RUN --mount=type=cache,target=/dl \
    set -eux; tmp=$(mktemp -d); base="https://github.com/verda-cloud/verda-cli/releases/download/v${VERDA_VERSION}"; \
    v="/dl/verda_${VERDA_VERSION}.tgz"; s="/dl/verda_${VERDA_VERSION}.sums"; \
    if [ ! -s "$v" ]; then curl -fsSL -o "$v.part" "$base/verda_${VERDA_VERSION}_linux_amd64.tar.gz"; mv "$v.part" "$v"; fi; \
    if [ ! -s "$s" ]; then curl -fsSL -o "$s.part" "$base/verda_${VERDA_VERSION}_SHA256SUMS"; mv "$s.part" "$s"; fi; \
    cp "$v" "$tmp/v.tgz"; \
    (cd /dl && grep linux_amd64.tar.gz "$s" | sed 's/ .*/  verda_'"${VERDA_VERSION}"'.tgz/' | sha256sum -c -); \
    tar xzf "$tmp/v.tgz" -C "$tmp" verda; \
    install -m755 "$tmp/verda" /out/verda


FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    YESOPEN_GPU_HOME=/root/.config/yesopen-gpu

# the base image deletes downloaded .debs after every install; keep them in the cache mount instead
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
 && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache \
 && apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends \
      rsync openssh-client procps ca-certificates

# Whisper (qa_report.py --whisper, inspect_take.py) runs on the CPU here, so torch comes from the CPU-only index
# (no CUDA libraries); its models download on first use into /root/.cache/whisper (a volume, see docker-compose.yml).
# pip and the packages' own test folders are not needed once the packages are in
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install pillow numpy \
 && pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install openai-whisper \
 && pip uninstall -y pip setuptools wheel \
 && find /usr/local/lib/python3.12/site-packages -type d -name tests -prune -exec rm -rf {} +

COPY --from=fetch /out/ffmpeg/ffmpeg /out/ffmpeg/ffprobe /usr/local/bin/
COPY --from=fetch /out/ffmpeg/lib/ /usr/local/lib/ffmpeg/
COPY --from=fetch /out/verda /usr/local/bin/verda
RUN echo /usr/local/lib/ffmpeg > /etc/ld.so.conf.d/ffmpeg.conf && ldconfig \
 && ffmpeg -version | head -1 && ffprobe -version | head -1 && verda --version

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# the repo is mounted here, so edits on Windows apply at once
WORKDIR /skill
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
