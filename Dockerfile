# Stock n8n (Docker Hardened Image, no package manager) + static ffmpeg + one font for drawtext.
FROM alpine:3.20 AS fonts
RUN apk add --no-cache ttf-dejavu

FROM n8nio/n8n:latest
COPY --from=mwader/static-ffmpeg:7.1 /ffmpeg /ffprobe /usr/local/bin/
COPY --from=fonts /usr/share/fonts/dejavu/DejaVuSans.ttf /usr/share/fonts/DejaVuSans.ttf
