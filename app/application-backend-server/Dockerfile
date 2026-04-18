FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir \
    flask \
    requests \
    python-jose \
    pymysql \
    prometheus_client
EXPOSE 8081
CMD ["python","app.py"]