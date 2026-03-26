FROM apache/airflow:2.10.4-python3.12

# Install JRE for PySpark
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow

# Install etlnexus-hooks package for BaseETL auto-instrumentation
COPY --chown=airflow:root ./etlnexus-hooks/ /tmp/etlnexus-hooks/
RUN pip install --no-cache-dir /tmp/etlnexus-hooks/ && rm -rf /tmp/etlnexus-hooks/

RUN pip install --no-cache-dir pyspark==3.5.1 sparkmeasure==0.24.0 && \
    mkdir -p /opt/airflow/jars && \
    python -c "import urllib.request; \
urllib.request.urlretrieve('https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.7.1/iceberg-spark-runtime-3.5_2.12-1.7.1.jar', '/opt/airflow/jars/iceberg-spark-runtime.jar'); \
urllib.request.urlretrieve('https://repo1.maven.org/maven2/ch/cern/sparkmeasure/spark-measure_2.12/0.24/spark-measure_2.12-0.24.jar', '/opt/airflow/jars/spark-measure.jar')"
