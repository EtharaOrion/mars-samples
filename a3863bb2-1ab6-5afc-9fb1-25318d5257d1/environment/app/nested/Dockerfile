FROM alpine:3.20
WORKDIR /nested
COPY compute.sh /nested/compute.sh
COPY values.txt /nested/values.txt
RUN chmod +x /nested/compute.sh
CMD ["/nested/compute.sh"]
