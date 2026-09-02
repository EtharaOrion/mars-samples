FROM golang:1.22-alpine@sha256:6d405dfc5fdf3a45df1529cf060b920041f52ce523487e0f36f02765af294a51

ENV GOPROXY=off
ENV GOFLAGS=-mod=mod
ENV GOSUMDB=off
ENV CGO_ENABLED=0
ENV GOTOOLCHAIN=local

RUN apk add --no-cache bash python3

WORKDIR /workspace

COPY workspace /workspace

# Freeze the broken-state observation the agent will read from
# /workspace/observed_error.txt at task start. The || true suffix keeps
# the docker build green even though the go build itself deliberately
# fails: the failure text is the whole point.
RUN cd /workspace/myapp && \
    (go mod verify > /workspace/observed_error.txt 2>&1 ; \
     go build ./... >> /workspace/observed_error.txt 2>&1 ; \
     go test ./... >> /workspace/observed_error.txt 2>&1 ; \
     true)

CMD ["/bin/bash"]
