
# ETL Explorer Hub

## Overview

**ETL Explorer Hub** is a next-generation data architecture command center designed for data engineers, analysts, and product managers. It bridges the gap between raw data pipelines and analytical value by providing a stunning, highly visual, and AI-powered interface to discover, understand, and utilize ETL (Extract, Transform, Load) processes across your organization.

Designed with a sleek, dark-themed "bento-box" architecture, it transforms a static data dictionary into an interactive, engineering-grade workspace.

## Core Features

### 1. Dynamic Pipeline Registry & Search

- **Master-Detail Interface:** Browse a highly scannable, always-visible catalog of all data pipelines while viewing deep-dive details in the adjacent workspace.
    
- **Deep Search:** Don't just search by pipeline name—search by specific database fields (e.g., `user_id`, `email`) or descriptions to instantly find which ETLs contain the data you need.
    
- **Live Airflow Integration:** Visual health indicators instantly tell you if an ETL was successful (Contains Data) or failed (No Data) during its last Airflow run.
    

### 2. The Bento-Box Data Workspace

When you select an ETL, the platform generates a comprehensive, at-a-glance workspace containing:

- **Pipeline Topology (Lineage):** A visual map showing exactly where the pipeline reads from (upstream tables, APIs, or other ETLs) and where it writes to in the data warehouse. Read the ETL code check the extract section for what ETLs does it consume, check the class init to see what table it writes. make it that there will be a configurable git repository that it clones and pulls it hourly to keep it updated.
    
- **Volume & Schedule Metrics:** Instantly see how much data is moving (`rows/day`) and how often it updates (Hourly, Daily, Real-time).
    
- **Schema Structure Viewer:** A clean breakdown of all fields within the ETL, complete with automatically inferred SQL data types (e.g., `UUID`, `TIMESTAMP`, `FLOAT8`, `VARCHAR`).
    
- **1-Click Consume Snippets:** Generates ready-to-paste Python code (e.g., `from etls import my_etl; my_etl("2026-01-25").consume()`) to instantly import and run the pipeline locally or in a notebook.
    

### 3. Dual Join Intelligence

Stop guessing how to connect datasets. The Hub provides two layers of join recommendations:

- **Schema Matches:** An automated engine that scans the entire catalog and lists simple, exact field matches (e.g., "Join with _Salesforce CRM Sync_ ON: `email`").
    
- **AI Insights:** Context-aware, semantic suggestions that explain _why_ and _how_ to join datasets, even if the field names aren't identical (e.g., mapping a support `email` to a production `user_profile`).
    

### 4. Global Schema Matrix

- **Cross-Product Discovery:** A dedicated visual matrix that calculates field frequency across your entire data ecosystem.
    
- **Entity Mapping:** Easily spot the most common keys (like `customer_id` or `email`) and see exactly which pipelines share them, acting as a global map for your data models.
    

### 5. AI Data Architect Terminal

- **openAPi-compatible-Powered Assistant:** A built-in, terminal-style AI assistant that has full context of your entire ETL catalog.
    
- **Goal-Oriented Queries:** Users can type business objectives (e.g., _"How do I calculate Customer LTV based on support tickets?"_). The AI will analyze the catalog, recommend the exact ETLs to combine, and explain the required joins and transformations.
    

## Who is this for?

- **Data Analysts:** To discover what data exists, trust its freshness, and instantly grab the code to query it.
    
- **Data Engineers:** To map out lineage, monitor Airflow statuses, and identify cross-pipeline dependencies.
    
- **Product Managers:** To understand the data available for feature analytics without needing to write SQL.


The technologies that it can work with are: Airflow, Hue, PySpark (can have a scheduled task in airflow), git (it can read the code through the cloned repository),

I want it to only display ETLs that are under Dagger folder in the code/ in the catalog after catalog.iceberg.dagger.

Also add a bento box for: which networks is it scheduled on using a python function that you will get that is called get_etl_dags which you just provide the etl name and it returns a list of networks.



the website must be containerized.
write it in python fastapi + typecsript, react, zustand if you need, shadcn/ui, vite, pnpm, uv, TanStack Query, SQLAlchemy.

dont use redux.
write down in claude.md the technologies that you will use.