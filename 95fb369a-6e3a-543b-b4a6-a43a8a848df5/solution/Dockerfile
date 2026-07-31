FROM python:3.12-slim
WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app/server.py /app/server.py
COPY app/data/ /app/data/
EXPOSE 8000
CMD ["python", "server.py"]
