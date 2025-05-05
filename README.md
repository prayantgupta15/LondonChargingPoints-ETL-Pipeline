# LondonChargingPoints-ETL-Pipeline

An ETL pipeline to analyse for how much time, each London public e-cycle charging point was in different status - "Available", "Unavailable", "Charging","OutOfService" and "Unknown".

Data is being feteched from UK Govt maintained API: https://api-portal.tfl.gov.uk/api-details#api=Occupancy&operation=Occupancy_GetAllChargeConnectorStatus
This API returns the occupancy for all charge connectors in JSON format.

Working:
Data is being fetched using Lambda function "londonChargingPointAPI" which then saves the data into S3 datalake under prefix "londonChargingPointsDataLake/raw_data/" with hive-style partioning like: year={year}/month={month}/day={day}/hour={hour}/{fileName}

Initially, this data is being stored in raw format without any transformation by Lambda function into S3 bucket.

Transform:
Then, raw data from prefix: "londonChargingPointsDataLake/raw_data/year={year}/month={month}/day={day}/hour={hour}/" is being read by Glue pyspark job for further transformation, cleansing and validating. Followed by, getting the new records and the records for which the status has been updated (Incremental data).

New records (new charging station points) are fetched using left anti join, as below:
    new_records_query = """
        select s.id, s.sourceSystemPlaceId, s.status,s.last_update_time
                from sourceTable s left anti join targetTable t 
                    on s.sourceSystemPlaceId = t.sourceSystemPlaceId
    """

Updated records (charging points which have undergone through the status change):
updated_status_records_query = """
        select s.id, s.sourceSystemPlaceId, s.status,s.last_update_time from
            sourceTable s join pre_inserted_records t on 
                s.sourceSystemPlaceId=t.sourceSystemPlaceId
                and s.status<>t.status and s.last_update_time > t.record_insert_time
    """
    
Load:
Then, using same glue pyspark job, doing union of both the dataframes - new records and status updated records, that are being then pushed to final SQL table (append).

Setup:
1. API is being hit using AWS Lambda function.
2. Pyspark Jobs hosted over Glue with S3 connection and S3 service role with required permissions.
3. Datalake hosted over S3 Bucket for source raw files (bronze) and transformed data (gold) and finally loading to SQL table.
4. SQL table hosted over Aurora MySQL DB.

  



