#!/usr/bin/env bash
# Start the Spark Connect server in the foreground (SPARK_NO_DAEMONIZE keeps it
# attached so the container stays alive). The Iceberg tables are exposed through
# a hadoop catalog over the shared warehouse volume — no REST catalog.
set -euo pipefail

export SPARK_NO_DAEMONIZE=true
WAREHOUSE="${SPARK_WAREHOUSE:-/tmp/warehouse}"

exec /opt/spark/sbin/start-connect-server.sh \
  --packages "org.apache.spark:spark-connect_2.12:${SPARK_CONNECT_VERSION:-3.5.1},org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:${ICEBERG_VERSION:-1.7.1}" \
  --conf "spark.jars.ivy=${SPARK_IVY_DIR:-/opt/spark/.ivy2}" \
  --conf "spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog" \
  --conf "spark.sql.catalog.iceberg.type=hadoop" \
  --conf "spark.sql.catalog.iceberg.warehouse=${WAREHOUSE}" \
  --conf "spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions" \
  --conf "spark.sql.defaultCatalog=iceberg" \
  --conf "spark.hadoop.fs.permissions.umask-mode=000"
