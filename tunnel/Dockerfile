FROM alpine:3.19

RUN apk add --no-cache curl jq bash

# Download cloudflared binary
RUN curl -fsSL -o /usr/local/bin/cloudflared \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" \
    && chmod +x /usr/local/bin/cloudflared

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
