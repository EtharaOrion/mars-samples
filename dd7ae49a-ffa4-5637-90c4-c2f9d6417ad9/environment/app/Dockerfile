FROM golang:1.26-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
COPY vendor ./vendor
COPY main.go ./
RUN CGO_ENABLED=0 GOFLAGS=-mod=vendor go build -trimpath -o /out/api .

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=build /out/api /app/api
EXPOSE 8080
CMD ["/app/api"]
