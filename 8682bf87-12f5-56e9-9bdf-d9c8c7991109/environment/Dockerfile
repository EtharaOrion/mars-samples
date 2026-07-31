FROM golang:1.26-bookworm
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOPROXY=off
WORKDIR /app
COPY app/ /app/
RUN go build -o /app/server .
EXPOSE 8000
CMD ["/app/server"]
