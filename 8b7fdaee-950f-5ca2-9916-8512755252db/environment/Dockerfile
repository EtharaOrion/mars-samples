FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir --disable-pip-version-check \
    build==1.2.2.post1 setuptools==75.6.0 wheel==0.45.1 pip==24.3.1
COPY app/ /app/
CMD ["sleep", "infinity"]
