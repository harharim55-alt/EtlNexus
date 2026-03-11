"""A/B Routing Experiment Engine - Routing experiment metrics and convergence analysis."""

from etls import fact_packet_inspection, rpt_protocol_adoption
from base_etl import BaseETL

SUFFIXES = ["path_variants", "convergence"]


class AbRoutingExperimentEngine(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "ab_routing_experiment_engine"

    def extract(self):
        self.packets = fact_packet_inspection(self.start_date, self.end_date).consume()
        self.adoption = rpt_protocol_adoption(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Compute experiment variants by comparing protocol performance across routes
        packet_stats = (
            self.packets
            .groupBy("protocol", "application_layer")
            .agg(
                F.count("packet_id").alias("sample_size"),
                F.avg("vlan_id").cast("double").alias("avg_vlan"),
                F.countDistinct("src_ip").alias("distinct_endpoints"),
            )
        )

        self.result = (
            packet_stats
            .join(
                self.adoption.select(
                    F.col("protocol_name").alias("a_protocol"),
                    F.col("adoption_rate"),
                ),
                F.col("protocol") == F.col("a_protocol"),
                "left",
            )
            .select(
                F.concat_ws("-", F.lit("EXP"), F.col("protocol"), F.col("application_layer")).alias("experiment_id"),
                F.col("application_layer").alias("route_variant"),
                F.col("sample_size"),
                F.coalesce(F.col("adoption_rate") * F.lit(100.0), F.lit(0.0)).alias("latency_improvement_pct"),
                (F.col("distinct_endpoints").cast("double") / F.greatest(F.col("sample_size").cast("double"), F.lit(1.0)) * F.lit(100.0)).alias("throughput_uplift_pct"),
                F.when(F.col("sample_size") > 100, F.lit(0.01))
                 .when(F.col("sample_size") > 30, F.lit(0.05))
                 .otherwise(F.lit(0.15)).alias("p_value"),
                (F.col("sample_size") > 30).alias("is_significant"),
                F.current_timestamp().alias("computed_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
