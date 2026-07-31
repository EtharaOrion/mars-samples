FROM gradle:8-jdk21
WORKDIR /warm
COPY warmup/ /warm/
RUN gradle --no-daemon build >/dev/null 2>&1 && cd / && rm -rf /warm
WORKDIR /app
COPY app/ /app/
RUN rm -rf /app/build /app/*/build
CMD ["sleep", "infinity"]
