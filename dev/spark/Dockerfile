# Dev-only: Spark Connect server exposing the Iceberg hadoop catalog.
# The backend reads table schemas from this server over gRPC (sc://...),
# so no Iceberg REST catalog is needed anywhere.
FROM apache/spark:3.5.1

USER root

ENV SPARK_CONNECT_VERSION=3.5.1
ENV ICEBERG_VERSION=1.7.1
ENV SPARK_IVY_DIR=/opt/spark/.ivy2

# Pre-resolve the Spark Connect + Iceberg packages (and their transitive deps)
# into the image's Ivy cache so the server starts without hitting Maven at runtime.
RUN mkdir -p "$SPARK_IVY_DIR" && \
    /opt/spark/bin/spark-submit \
      --packages "org.apache.spark:spark-connect_2.12:${SPARK_CONNECT_VERSION},org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:${ICEBERG_VERSION}" \
      --conf "spark.jars.ivy=${SPARK_IVY_DIR}" \
      --class org.apache.spark.examples.SparkPi \
      /opt/spark/examples/jars/spark-examples_*.jar 1

COPY dev/spark/entrypoint.sh /opt/spark/connect-entrypoint.sh
RUN chmod +x /opt/spark/connect-entrypoint.sh && chown -R spark:spark "$SPARK_IVY_DIR"

USER spark

EXPOSE 15002

ENTRYPOINT ["/opt/spark/connect-entrypoint.sh"]
