FROM apache/airflow:2.10.4-python3.12

# Install JRE for PySpark
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow
RUN pip install --no-cache-dir pyspark==3.5.1 sparkmeasure==0.24.0
