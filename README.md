# LondonChargingPoints-ETL-Pipeline

This project implements an end-to-end ETL pipeline to analyze the status duration of public e-cycle charging points across London. Specifically, it tracks how long each charging point remained in one of the following statuses: **Available**, **Unavailable**, **Charging**, **OutOfService**, and **Unknown**.


## Data Source
The source data is fetched from the UK Government's Transport for London (TfL) API:

[TfL Charge Connector Status API](https://api-portal.tfl.gov.uk/api-details#api=Occupancy&operation=Occupancy_GetAllChargeConnectorStatus)

This API provides real-time occupancy data for all charge connectors in JSON format.



## Architecture Overview
![image](https://github.com/user-attachments/assets/0c44afc4-7f62-4f19-9407-cf1bd2d5b7c2)

The ETL pipeline follows a modern data lake architecture leveraging AWS services:

**Extract** (via Lambda)

**Transform** (via AWS Glue using PySpark)

**Load** (to Aurora MySQL)

### Extract:

A scheduled AWS Lambda function named `londonChargingPointAPI` triggers at regular intervals to invoke the TfL API.
The response JSON is ingested and saved in raw form to an S3 bucket (`londonChargingPointsDataLake`) under the path:
  ```
  raw_data/year={year}/month={month}/day={day}/hour={hour}/{fileName}.json
  ```
The data is partitioned using a Hive-style directory structure for efficient querying.

### Transform:

A PySpark job hosted on AWS Glue reads the raw data from the S3 path. 

The data is then cleaned, validated, and transformed.


Incremental processing is performed to extract:

**New records** (new charging stations not present in the previous snapshot) using a left anti join:

     ```
     SELECT s.id, s.sourceSystemPlaceId, s.status, s.last_update_time
     FROM sourceTable s
     LEFT ANTI JOIN targetTable t
     ON s.sourceSystemPlaceId = t.sourceSystemPlaceId
     ```

**Updated records** (stations whose status has changed since the last update) using:

     ```
     SELECT s.id, s.sourceSystemPlaceId, s.status, s.last_update_time
     FROM sourceTable s
     JOIN pre_inserted_records t
     ON s.sourceSystemPlaceId = t.sourceSystemPlaceId
     WHERE s.status <> t.status
       AND s.last_update_time > t.record_insert_time
     ```
Both datasets (new and updated records) are unioned and prepared for loading.

### Load

The final transformed dataset is appended to a SQL table hosted in **Amazon Aurora MySQL**.
This enables historical tracking and analytical querying of charging point statuses.


## Deployment Setup

**API Extraction:** AWS Lambda function scheduled to invoke the TfL API.

**Data Lake Storage:** Raw and processed data stored in Amazon S3 using Bronze-Gold data zones.

**Transformation:** AWS Glue jobs (PySpark) with appropriate IAM roles and S3 access.

**Database:** Aurora MySQL instance with a target table for analytical querying.

**Querying Tool:** MySQL Workbench used to run SQL queries and perform analysis.


---

## Final Table Schema (Aurora MySQL)
| Column                | Type      |
| --------------------- | --------- |
| `id`                  | INT       |
| `sourceSystemPlaceId` | VARCHAR   |
| `status`              | VARCHAR   |
| `record_insert_time`  | TIMESTAMP |

---
  
**Ouput:**
- All Charging points:
<img width="644" alt="all charging points" src="https://github.com/user-attachments/assets/c8a08881-8cd9-4047-82e5-1743b795005b" />

---

- Time analysis using pivotting and window functions:
<img width="678" alt="TimeAnalysis" src="https://github.com/user-attachments/assets/e18d2f7b-57cf-4cb6-bab1-e5e26d7b65a2" />
