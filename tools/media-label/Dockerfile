# Media-label service: Python + a static ffmpeg with drawtext + one font. Burns the disclosure label into video and
# images, writes it into audio metadata. Called by the kit over HTTP so the n8n workflow itself needs no shell.
FROM alpine:3.20 AS fonts
RUN apk add --no-cache ttf-dejavu
FROM python:3.12-alpine
COPY --from=mwader/static-ffmpeg:7.1 /ffmpeg /ffprobe /usr/local/bin/
COPY --from=fonts /usr/share/fonts/dejavu/DejaVuSans.ttf /usr/share/fonts/DejaVuSans.ttf
COPY server.py /app/server.py
EXPOSE 8881
CMD ["python3", "/app/server.py", "--port", "8881"]
