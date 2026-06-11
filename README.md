# PAIMIE
Political and Industrial Monetary Intelligence Engine
# Political Finance Intelligence Platform

## Overview

This project is a **political-finance intelligence system** designed to identify relationships between:

* Corporate lobbying activity
* Legislative actions
* Campaign finance
* Congressional stock trades
* Market outcomes

The system ingests public disclosures, normalizes them, and constructs a **knowledge graph of political money flows**. Large Language Models (LLMs) are used to analyze unstructured legislative text and lobbying filings to infer economic beneficiaries and potential conflicts of interest.

The goal is to detect **financial signals derived from legislative information flow**.

---

# System Architecture

```
             DATA SOURCES
                 │
                 ▼
        Scrapers + API Collectors
                 │
                 ▼
            Raw Data Lake
            (Object Storage)
                 │
                 ▼
         ETL / Data Processing
        (Normalization Layer)
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
Structured Warehouse   Vector Store
(Postgres / DuckDB)    (Embeddings)
      │                     │
      ▼                     ▼
         Knowledge Graph
            (Neo4j)
                 │
                 ▼
           AI Reasoning
       (LLM + Retrieval)
                 │
                 ▼
          Query Engine
        (Dashboard / API)
```

---

# Core Components

## 1. Data Acquisition Layer

The acquisition layer collects raw political and financial data from public sources.

### Scraping Stack

Recommended tools:

* Python
* Scrapy (structured scraping)
* Playwright (dynamic sites)
* Requests + BeautifulSoup

### Scheduling

* Apache Airflow
* Prefect

### Storage

All scraped data is stored in **raw format** before processing.

Recommended storage:

* AWS S3
* Google Cloud Storage
* MinIO (local object storage)

---

# Data Sources

## Congressional Stock Trades

Sources include disclosures required by the
**STOCK Act (2012)** and platforms such as
**Quiver Quantitative**.

Data fields:

```
member_name
ticker
transaction_type
transaction_amount_range
transaction_date
filing_date
```

---

## Lobbying Filings

Filed under the **Lobbying Disclosure Act**.

Source:

* U.S. Senate Office of Public Records

Fields:

```
company
lobbying_firm
lobbying_amount
bill_reference
issue_area
reporting_quarter
```

---

## Campaign Finance

Sources:

* Federal Election Commission (FEC)
* OpenSecrets

Fields:

```
donor
recipient
pac
donation_amount
donation_date
```

---

## Legislative Data

Sources:

* Congress.gov
* Government Publishing Office (GPO)

Data includes:

```
bill_number
bill_text
amendments
committee_actions
vote_records
sponsors
```

---

# Raw Data Lake

All raw data is stored before transformation.

Recommended structure:

```
/data_lake
   /congress_trades
   /lobbying_filings
   /campaign_finance
   /bills
   /votes
```

File formats:

```
parquet
json
```

Benefits:

* reproducibility
* auditability
* historical backtesting

---

# ETL and Data Normalization

ETL processes transform raw data into normalized relational structures.

Key challenges:

* entity deduplication
* company name normalization
* politician identity resolution

Example normalization:

```
AT&T
AT and T
AT&T INC
```

All mapped to:

```
company_id: ATT
```

Recommended tools:

* Python
* Polars or Pandas
* dbt
* SQL

---

# Structured Data Warehouse

Recommended databases:

* PostgreSQL
* DuckDB
* BigQuery

Core tables:

```
companies
congress_members
bills
lobbying_activity
stock_trades
campaign_donations
votes
committee_memberships
```

These tables represent the **structured ground truth layer**.

---

# Knowledge Graph Layer

The knowledge graph models relationships between political actors, legislation, and financial activity.

Recommended database:

```
Neo4j
```

### Node Types

```
Company
CongressMember
Bill
PAC
Industry
Stock
Committee
```

### Edge Relationships

```
(company)-[:LOBBIED_FOR]->(bill)

(member)-[:VOTED_ON]->(bill)

(member)-[:RECEIVED_DONATION]->(company)

(member)-[:TRADED]->(stock)

(company)-[:AFFECTED_BY]->(bill)
```

### Example Query

Detect potential conflicts of interest:

```
MATCH
(company)-[:LOBBIED_FOR]->(bill)
<-[:VOTED_ON]-(member)
-[:TRADED]->(company)

RETURN member, company
```

---

# Vector Database

Unstructured text (bill language, lobbying reports) is stored in a vector database for semantic search.

Recommended tools:

* pgvector
* Pinecone
* Weaviate

### Stored Data

```
bill_sections
lobbying_descriptions
committee_transcripts
policy summaries
```

Each text chunk contains:

```
text
embedding_vector
document_reference
policy_area
```

---

# AI / LLM Layer

Large Language Models assist with interpreting unstructured political text.

Primary functions:

### Entity Extraction

Example input:

```
AT&T lobbied for broadband provisions in HR 3684.
```

Output:

```
company: AT&T
bill: HR3684
policy_area: broadband
```

---

### Industry Impact Detection

Example:

```
Section 402 expands tax credits for semiconductor manufacturing.
```

Output:

```
beneficiary_industries:
- semiconductors
- chip manufacturing
```

---

### Relationship Inference

Example prompt:

```
Given this bill text, which industries financially benefit?
```

The LLM helps map legislation to affected companies.

---

# Signal Generation Engine

Signals estimate the probability that legislation benefits specific companies or sectors.

Example scoring model:

```
SignalScore =
    LobbyingIntensity
  + CampaignDonationExposure
  + CommitteeAccess
  + TradeTiming
  + LegislativeImpact
```

High scores indicate potential financial signals.

Example signal scenario:

```
Company increases lobbying
+
Committee member buys company stock
+
Bill benefiting industry advances
```

---

# Event Timeline Modeling

Political influence signals are strongest when modeled as **timelines**.

Example:

```
Jan 5  Lobbying increases
Feb 2  Bill introduced
Feb 10 Committee vote
Feb 12 Senator buys stock
Mar 3  Bill passes
```

Tracking these sequences enables stronger predictive signals.

---

# Query Engine

Users should be able to ask natural-language questions such as:

```
Which members of Congress traded stocks in industries affected by bills they voted on within 30 days?
```

Query pipeline:

```
User Question
    │
    ▼
LLM converts question to SQL + Graph query
    │
    ▼
Warehouse + Graph execution
    │
    ▼
LLM summarizes result
```

---

# Visualization Layer

Dashboards make patterns visible.

Recommended tools:

* Apache Superset
* Metabase
* Custom React dashboards

Potential visualizations:

* political money flow networks
* lobbying heatmaps
* congressional trading timelines
* legislation impact graphs

---

# Automation

Daily automated pipeline:

```
1. Scrape disclosures
2. Store raw data
3. Normalize entities
4. Update warehouse
5. Update graph database
6. Generate embeddings
7. Compute signals
```

Scheduler:

```
Apache Airflow
```

---

# Minimum Viable Product (MVP)

Start with a simplified version.

Phase 1:

```
congressional trades
lobbying filings
bill text
```

Phase 2:

```
campaign donations
committee memberships
vote records
```

Phase 3:

```
LLM bill impact analysis
predictive trading signals
```

---

# Design Principles

### Ground Truth Layer

```
SQL warehouse + knowledge graph
```

### Reasoning Layer

```
LLM analysis
```

LLMs should **interpret data**, not generate it.

---

# Potential Users

* hedge funds
* investigative journalists
* watchdog organizations
* regulatory analysts
* political researchers

---

# Long-Term Vision

This platform could evolve into:

```
Bloomberg Terminal for Political Capital Flows
```

A system that maps how **legislation, lobbying, money, and markets interact**.

---

# Disclaimer

All data sources referenced in this system are **public disclosures** and **public government records**.

The platform performs analysis on publicly available information.
