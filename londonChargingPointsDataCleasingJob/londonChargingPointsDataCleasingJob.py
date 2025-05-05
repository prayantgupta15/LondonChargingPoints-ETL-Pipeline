import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.window import Window
from pyspark.sql.functions import col,dense_rank


## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)
from datetime import datetime

current_time = datetime.now()
year=current_time.year
month=current_time.month
day= current_time.day
hour = current_time.hour
minute = current_time.minute

SOURCE_DATA_FILES_PATH = f's3://aws-glue-assets-079448565720-ap-south-1/londonChargingPointsDataLake/raw_data/year={year}/month={month}/day={day}/hour={hour}'

print(SOURCE_DATA_FILES_PATH)
json_dyf = glueContext.create_dynamic_frame.from_options(
  connection_type="s3",
  connection_options={"paths": [SOURCE_DATA_FILES_PATH],
      "recurse": True
  },
  format="json",
  transformation_ctx = "json_dyf"
)
print("json_dyf")
json_df = json_dyf.toDF()
json_df.printSchema()
# Will process if we have source data.

# json_df.where(col('id')==61926).show()
if json_df.isEmpty():
   print("Nothing read")
else:    
    # Target table DF
    # ======================================================
    # targetTbleDYF = glueContext.create_dynamic_frame_from_catalog(
    #                 database = 'london_ev_db',
    #                 table_name = 'charingPointsSatusTable')
    
    targetTbleDYF = glueContext.create_dynamic_frame.from_options(
                    connection_type = "mysql",
                    connection_options = {
                        "useConnectionProperties": "true",
                        "dbtable": "charingpointssatustable",
                        "connectionName": "london_ev_db_rds_mysql_conn",
                        }
                    )    
    
    print("targetTbleDYF")
    targetTbleDYF.printSchema()
    targetTbleDF = targetTbleDYF.toDF()
    targetTbleDF.createOrReplaceTempView('targetTable')
    # ======================================================
    
    
    # filtering out to remove duplicates based on id/sourceSystemPlaceId and taking the latest one.
    # ======================================================    
    wd = Window.partitionBy('sourceSystemPlaceId').orderBy(col('last_update_time').desc())
    json_df = json_df.withColumn('rnk',dense_rank().over(wd)).where(col('rnk')==1).drop('rnk')
    # json_df = json_df.dropDuplicates(['sourceSystemPlaceId'])
    json_df.createOrReplaceTempView('sourceTable')
    # ======================================================
    
    
    # New records/New charing stations (means not yet added in target catalog)
    # ======================================================    
    print("New records:")
    new_records_query = """
        select s.id, s.sourceSystemPlaceId, s.status,s.last_update_time
                from sourceTable s left anti join targetTable t 
                    on s.sourceSystemPlaceId = t.sourceSystemPlaceId
    """
    
        
    new_records_df = spark.sql(new_records_query)
    new_records_df.show(truncate=False)
    new_records_df.createOrReplaceTempView('new_records')
    # ======================================================
    
    
    # get the last inserted record of each charging station, in catalog table
    # ======================================================    
    pre_inserted_records_query = """
                select id, status, sourceSystemPlaceId, record_insert_time
                from (
                    select *,
                        dense_rank() over(partition by sourceSystemPlaceId order by record_insert_time desc) rnk
                        from targetTable
                 ) tbl
                where rnk=1;
    """
    pre_inserted_records_df = spark.sql(pre_inserted_records_query)
    print("pre inserted reocrds")
    pre_inserted_records_df.show(truncate=False)    
    pre_inserted_records_df.createOrReplaceTempView('pre_inserted_records')
    # ======================================================
    
    # Records which got updated (means status of charging station has been changed)
    # ======================================================    
    updated_status_records_query = """
        select s.id, s.sourceSystemPlaceId, s.status,s.last_update_time from
            sourceTable s join pre_inserted_records t on 
                s.id=t.id and s.sourceSystemPlaceId=t.sourceSystemPlaceId
                and s.status<>t.status and s.last_update_time > t.record_insert_time
    """
    updated_status_records_query = """
        select s.id, s.sourceSystemPlaceId, s.status,s.last_update_time from
            sourceTable s join pre_inserted_records t on 
                s.sourceSystemPlaceId=t.sourceSystemPlaceId
                and s.status<>t.status and s.last_update_time > t.record_insert_time
    """    
    updated_status_records_df = spark.sql(updated_status_records_query)
    print("updated_status_records")
    updated_status_records_df.show()
    updated_status_records_df.createOrReplaceTempView('updated_status_records')
    # ======================================================
    
    
    # Records needs to be inserted into catalog: updated_status_records + new_records
    # concat(id,date_format(current_timestamp,'_%Y%m%d%h%i')) surrogate_key,
    # ======================================================    
    finalData_query= """
    select id, sourceSystemPlaceId, status, 
    last_update_time as record_insert_time from 
        (
            (select * from new_records)
                union all
            (select * from updated_status_records)
        ) tbl;
    """
    final_df = spark.sql(finalData_query)
    print("final df:")
    final_df.show()
    # ======================================================    
    
    
    # Writing final data to catalo
    # ======================================================        
    from awsglue.dynamicframe import DynamicFrame
    final_dyf = DynamicFrame.fromDF(final_df,glueContext,'final_dyf')
    
    print("final_dyf")
    final_dyf.show()
    final_dyf.printSchema()
    glueContext.write_dynamic_frame.from_options(
                    frame = final_dyf,
                    connection_type = "mysql",
                    connection_options = {
                        "useConnectionProperties": "true",
                        "dbtable": "charingpointssatustable",
                        "connectionName": "london_ev_db_rds_mysql_conn",
                        }
                    )    
        
    # glueContext.write_dynamic_frame_from_catalog(
        # frame = final_1dyf,
        # database = 'london_ev_db',
        # table_name = 'charingPointsSatusTable')
        
    # ======================================================    


job.commit()