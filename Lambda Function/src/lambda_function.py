import json
import requests, json
from datetime import datetime
import boto3,botocore
import random
def lambda_handler(event, context):


    DATA_LAKE_LOCATION = 's3://aws-glue-assets-079448565720-ap-south-1/londonChargingPointsDataLake/raw_data/'
    # print(DATA_LAKE_LOCATION.split('/'))
    BUCKET = DATA_LAKE_LOCATION.split('/')[2]
    PREFIX = '/'.join(DATA_LAKE_LOCATION.split('/')[3:])
    # print(BUCKET)
    print(PREFIX)

    API_URL = "https://api.tfl.gov.uk/Occupancy/ChargeConnector"

    try:
        # A GET request to the API
        response = requests.get(API_URL)
        # print("raise for status")
        # response.raise_for_status()
        if response.status_code==200:
            response_dict = response.json()
            print('len(response_dict)',len(response_dict))
            
            
            change_ctr = 5
            for resp in response_dict:
                resp['last_update_time']=str(datetime.now())
                # changing records logic
                # =====================
                if change_ctr>0:
                    random_id = random.randrange(61218, 62170)
                    print(random_id)
                    if resp['id']==random_id:
                        print("Mil gya")
                        change_ctr-=1
                        if resp['status']=="Available":
                            newChoice = random.choices(["Charging","Unavailable","Unknown"])
                            print("changing for ",resp['id'], " from ", resp['status'], "to ",newChoice )
                            resp['status'] = newChoice[0]
                        elif resp['status']=="Unknown":
                            newChoice = random.choices(["Charging","Unavailable","Available"])
                            print("changing for ",resp['id'], " from ", resp['status'], "to ",newChoice )
                            resp['status'] = newChoice[0]
                        elif resp['status']=="Unavailable":
                            newChoice = random.choices(["Charging","Available","Unknown"])
                            print("changing for ",resp['id'], " from ", resp['status'], "to ",newChoice )
                            resp['status'] = newChoice[0]                                                      
                        else:
                            newChoice = random.choices(["Available","Unavailable","Unknown"])
                            print("changing for ",resp['id'], " from ", resp['status'], "to ",newChoice )
                            resp['status'] = newChoice[0]
                # =====================
            if response_dict:
                print("Uploading data to S3 bucket")
                s3_cilent = boto3.client('s3')
                current_time = datetime.now()
                year=current_time.year
                month=current_time.month
                day= current_time.day
                hour = current_time.hour
                minute = current_time.minute
            
                fileName = f'output-{minute}.json'

                try:
                    print("Saving to S3")
                    s3_cilent.put_object(
                    Body = json.dumps(response_dict, indent=4, sort_keys=True),
                    Bucket=BUCKET,
                    Key = f'{PREFIX}year={year}/month={month}/day={day}/hour={hour}/{fileName}')
                except botocore.exceptions.ClientError as error:
                    print("Error uploading file to S3 ",error)
                    raise error    
            else:
                print("Nothing to write")
    
    
    except Exception as e:
            print(e)
    ####################################

