"""Network Threat Assessment - Comprehensive per-IP network health scoring
fusing flow analytics, threat intelligence, DHCP context, syslog anomalies,
endpoint activity, billing metrics, and switch port health into a single
assessment with ranked tiers, percentile scores, and temporal trends."""

from etls import (
    fact_netflow_records,
    raw_syslog_events,
    stg_dhcp_leases,
    ml_threat_scores,
    bandwidth_invoices,
    ml_endpoint_activity_scores,
    switch_interface_snapshot,
)
from base_etl import BaseETL



class NetworkThreatAssessment(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "NetworkThreatAssessment"

    def extract(self):
        self.flows = fact_netflow_records(self.start_date, self.end_date).consume()
        self.syslog = raw_syslog_events(self.start_date, self.end_date).consume()
        self.leases = stg_dhcp_leases(self.start_date, self.end_date).consume()
        self.threats = ml_threat_scores(self.start_date, self.end_date).consume()
        self.billing = bandwidth_invoices(self.start_date, self.end_date).consume()
        self.activity = ml_endpoint_activity_scores(self.start_date, self.end_date).consume()
        self.ports = switch_interface_snapshot(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        # ── Data amplification: multiply input rows to create a heavier workload
        # Cross-join with a small range then union — produces ~20x flow data
        # and ~10x syslog data to generate real CPU/memory/shuffle pressure.
        amplifier = self.spark.range(20).withColumnRenamed("id", "_amp_id")
        amplified_flows = (
            self.flows
            .crossJoin(F.broadcast(amplifier))
            .withColumn(
                "bytes_transferred",
                (F.col("bytes_transferred") * (F.lit(1.0) + F.col("_amp_id") * F.lit(0.05))).cast("long"),
            )
            .withColumn(
                "flow_id",
                F.concat(F.col("flow_id"), F.lit("_"), F.col("_amp_id").cast("string")),
            )
            .drop("_amp_id")
        )

        syslog_amplifier = self.spark.range(10).withColumnRenamed("id", "_amp_id")
        amplified_syslog = (
            self.syslog
            .crossJoin(F.broadcast(syslog_amplifier))
            .withColumn(
                "event_id",
                F.col("event_id") * F.lit(100) + F.col("_amp_id"),
            )
            .drop("_amp_id")
        )

        # ── Stage 1: Aggregate netflow traffic per source IP ───────────
        # Exercises: groupBy, count, sum, avg, min, max, countDistinct,
        #            collect_set, concat_ws, filter
        flow_stats = (
            amplified_flows
            .filter(F.col("bytes_transferred") > 0)
            .groupBy("src_ip")
            .agg(
                F.count("flow_id").alias("total_flows"),
                F.sum("bytes_transferred").alias("total_bytes"),
                F.avg("bytes_transferred").alias("avg_bytes_per_flow"),
                F.min("capture_time").alias("first_seen"),
                F.max("capture_time").alias("last_seen"),
                F.countDistinct("dst_ip").alias("unique_destinations"),
                F.countDistinct("protocol").alias("protocol_count"),
                F.concat_ws(",", F.collect_set("protocol")).alias("protocols_csv"),
            )
            .repartition(200, "src_ip")  # Force heavy shuffle
        )

        # ── Stage 2: Syslog critical anomaly scoring per host ─────────
        # Exercises: filter with isin, groupBy, sum with when/otherwise
        syslog_critical = (
            amplified_syslog
            .filter(F.col("severity").isin("emerg", "alert", "crit", "err"))
            .groupBy("source_host")
            .agg(
                F.count("event_id").alias("critical_event_count"),
                F.countDistinct("facility").alias("affected_facilities"),
                F.max("event_time").alias("last_critical_event"),
                F.sum(
                    F.when(F.col("severity") == "emerg", 10)
                     .when(F.col("severity") == "alert", 8)
                     .when(F.col("severity") == "crit", 6)
                     .otherwise(4)
                ).alias("syslog_severity_score"),
            )
        )

        # ── Stage 3: Syslog warning branch + union ────────────────────
        # Exercises: union (guarantees Union node in physical plan)
        syslog_warnings = (
            amplified_syslog
            .filter(F.col("severity").isin("warning", "notice"))
            .groupBy("source_host")
            .agg(
                F.count("event_id").alias("critical_event_count"),
                F.countDistinct("facility").alias("affected_facilities"),
                F.max("event_time").alias("last_critical_event"),
                F.sum(
                    F.when(F.col("severity") == "warning", 2)
                     .otherwise(1)
                ).alias("syslog_severity_score"),
            )
        )

        syslog_combined = syslog_critical.union(syslog_warnings)

        # Repartition after union to test Exchange node metrics
        syslog_repartitioned = syslog_combined.repartition(4, "source_host")

        # Re-aggregate after union to merge host entries from both branches
        syslog_scores = (
            syslog_repartitioned
            .groupBy("source_host")
            .agg(
                F.sum("critical_event_count").alias("critical_event_count"),
                F.max("affected_facilities").alias("affected_facilities"),
                F.max("last_critical_event").alias("last_critical_event"),
                F.sum("syslog_severity_score").alias("syslog_severity_score"),
            )
        )

        # ── Stage 4: DHCP lease context — broadcast join ──────────────
        # Exercises: broadcast, left join, dropDuplicates, select/project
        active_leases = (
            self.leases
            .filter(F.col("lease_state") == "active")
            .select("ip_address", "mac_address", "hostname", "pool_name")
            .dropDuplicates(["ip_address"])
        )

        # Cache the DHCP leases lookup (small dimension table, reused via broadcast).
        # cache()/persist() on side inputs don't truncate the main result lineage.
        active_leases.cache()

        flow_with_dhcp = (
            flow_stats
            .join(
                F.broadcast(active_leases),
                F.col("src_ip") == F.col("ip_address"),
                "left",
            )
            .drop("ip_address")
        )

        # ── Stage 5: Threat intelligence — inner join (SortMergeJoin) ─
        # Exercises: inner join on non-broadcast DFs
        flow_threat = (
            flow_with_dhcp
            .join(
                self.threats.select(
                    "source_ip", "threat_score", "risk_bucket",
                    "anomaly_score", "reputation_score", "is_blocked",
                ),
                F.col("src_ip") == F.col("source_ip"),
                "inner",
            )
            .drop("source_ip")
        )

        # Persist the syslog scores (side input) at MEMORY_AND_DISK level.
        # Persisting side inputs exercises the StorageLevel without truncating
        # the main result chain's execution plan.
        from pyspark import StorageLevel
        syslog_scores.persist(StorageLevel.MEMORY_AND_DISK)

        # ── Stage 6: Syslog left join + activity broadcast join ───────
        # Exercises: left outer join (SortMergeJoin), second broadcast join
        with_syslog = (
            flow_threat
            .join(
                syslog_scores,
                F.col("src_ip") == F.col("source_host"),
                "left",
            )
            .drop("source_host")
        )

        activity_dim = (
            self.activity
            .select(
                F.col("endpoint_id").alias("act_endpoint"),
                "activity_score",
                F.col("tier").alias("activity_tier"),
                "recency_score",
                "frequency_score",
            )
        )

        # Checkpoint activity dimension (side input) to exercise checkpoint
        # without truncating the main result chain's plan.
        self.spark.sparkContext.setCheckpointDir("/tmp/spark-checkpoint")
        activity_dim = activity_dim.checkpoint(eager=True)

        with_activity = (
            with_syslog
            .join(
                F.broadcast(activity_dim),
                F.col("src_ip") == F.col("act_endpoint"),
                "left",
            )
            .drop("act_endpoint")
        )

        # ── Stage 6b: Switch port context — additional enrichment ───────
        # Exercises: groupBy on ports, left join for port health context
        port_health = (
            self.ports
            .filter(F.col("is_active") == True)
            .groupBy("mac_address")
            .agg(
                F.first("port_speed").alias("port_speed"),
                F.first("vlan_id").alias("switch_vlan"),
                F.count("port_number").alias("active_port_count"),
            )
        )

        with_ports = (
            with_activity
            .join(
                port_health,
                with_activity["mac_address"] == port_health["mac_address"],
                "left",
            )
            .drop(port_health["mac_address"])
        )

        # ── Stage 6c: Billing correlation — subscription bandwidth ────
        # Exercises: another groupBy + agg chain, left join
        billing_summary = (
            self.billing
            .filter(F.col("status") == "billed")
            .groupBy("subscription_id")
            .agg(
                F.sum("bandwidth_used_mbps").alias("billed_bandwidth_mbps"),
                F.max("billing_tier").alias("billing_tier"),
                F.count("invoice_id").alias("invoice_count"),
            )
        )

        with_billing = (
            with_ports
            .join(
                billing_summary,
                F.col("src_ip") == F.col("subscription_id"),
                "left",
            )
            .drop("subscription_id")
        )

        # ── Stage 7: Window functions — ranking and temporal analysis ──
        # Exercises: row_number, dense_rank, percent_rank, ntile, lag, lead
        #            across 3 different window specs
        risk_window = Window.partitionBy("risk_bucket").orderBy(F.desc("total_bytes"))
        global_window = Window.orderBy(F.desc("total_bytes"))
        pool_window = Window.partitionBy("pool_name").orderBy(F.desc("total_flows"))

        windowed = (
            with_billing
            .withColumn("rank_in_risk_bucket", F.row_number().over(risk_window))
            .withColumn("dense_rank_in_bucket", F.dense_rank().over(risk_window))
            .withColumn("global_percentile", F.percent_rank().over(global_window))
            .withColumn("traffic_quartile", F.ntile(4).over(global_window))
            .withColumn("prev_peer_bytes", F.lag("total_bytes", 1).over(pool_window))
            .withColumn("next_peer_bytes", F.lead("total_bytes", 1).over(pool_window))
        )

        # ── Stage 8: Final scoring, complex expressions, sort ─────────
        # Exercises: withColumn with arithmetic/coalesce/when, orderBy, select
        scored = (
            windowed
            .withColumn(
                "composite_health_score",
                F.round(
                    F.coalesce(F.col("reputation_score"), F.lit(0.5)) * F.lit(30.0)
                    + (F.lit(100.0) - F.coalesce(F.col("threat_score"), F.lit(0.0))) * F.lit(0.25)
                    + F.coalesce(F.col("activity_score"), F.lit(50.0)) * F.lit(0.2)
                    + (F.lit(100.0) - F.least(
                        F.coalesce(F.col("syslog_severity_score"), F.lit(0)).cast("double"),
                        F.lit(100.0),
                    )) * F.lit(0.15)
                    + F.coalesce(F.col("global_percentile"), F.lit(0.5)) * F.lit(10.0),
                    2,
                )
            )
            .withColumn(
                "assessment_tier",
                F.when(F.col("composite_health_score") >= 80, F.lit("healthy"))
                 .when(F.col("composite_health_score") >= 60, F.lit("moderate"))
                 .when(F.col("composite_health_score") >= 40, F.lit("degraded"))
                 .when(F.col("composite_health_score") >= 20, F.lit("critical"))
                 .otherwise(F.lit("severe")),
            )
            .withColumn(
                "requires_action",
                (F.col("is_blocked") == True)
                | (F.col("composite_health_score") < 30)
                | (F.coalesce(F.col("critical_event_count"), F.lit(0)) > 10),
            )
        )

        # Coalesce partitions before final select to test Coalesce node
        coalesced = scored.coalesce(2)

        self.result = (
            coalesced
            .repartition(4)
            .select(
                F.col("src_ip").alias("ip_address"),
                F.coalesce(F.col("hostname"), F.lit("unknown")).alias("hostname"),
                F.coalesce(F.col("mac_address"), F.lit("unknown")).alias("mac_address"),
                F.coalesce(F.col("pool_name"), F.lit("unassigned")).alias("network_zone"),
                "total_flows",
                "total_bytes",
                "avg_bytes_per_flow",
                "unique_destinations",
                "protocol_count",
                "protocols_csv",
                "threat_score",
                "risk_bucket",
                "anomaly_score",
                "reputation_score",
                "is_blocked",
                F.coalesce(F.col("critical_event_count"), F.lit(0)).alias("critical_event_count"),
                F.coalesce(F.col("affected_facilities"), F.lit(0)).alias("affected_facilities"),
                F.coalesce(F.col("syslog_severity_score"), F.lit(0)).cast("double").alias("syslog_severity_score"),
                "composite_health_score",
                "assessment_tier",
                "requires_action",
                "rank_in_risk_bucket",
                "global_percentile",
                "traffic_quartile",
                F.coalesce(F.col("activity_score"), F.lit(0.0)).alias("activity_score"),
                F.coalesce(F.col("activity_tier"), F.lit("unknown")).alias("activity_tier"),
                F.current_timestamp().alias("assessed_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
        # Cleanup cached/persisted DataFrames
        self.spark.catalog.clearCache()
