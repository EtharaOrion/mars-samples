FROM golang:1.26-bookworm AS builder
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOPROXY=off
WORKDIR /app
COPY app/ /app/
RUN go build -o /app/server .

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/server /app/server
COPY --from=builder /app/data/ /app/data/
EXPOSE 8000
CMD ["/app/server"]
