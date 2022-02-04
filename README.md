# Netbox-Route53-Integration

Lambda run script, using Netbox as a source of truth to integrate ip/dns pairs into Route53 via webhook and on a schedule basis.

## Requirements  
* Boto3 1.17.6
* Netbox 6.1.3
* Python 3.8

## Description

Netbox-Route53 is a python script that is used to sync Route53 records with
Netbox. This script uses webhooks for instant updating, as well as an
integration function that runs on an hourly and daily timer to fully sync up
records.

Netbox record id's are permanently unique, so when the script adds records to
Route53, it creates an accompanying txt record with a special identifier tag
as well as the Netbox record id. This prevents the script from updating records
that it hasn't created and ensures that it always updates the correct record
inside of Route53. (The id is seen as the only identifier for a record)

The webhooks work by having Netbox configured to send events to the
script anytime a record in Netbox is created, updated or deleted. The script
parses these webhooks and decides what action to take based on the type of
event (c/u/d). Only records with the special txt identifier record will be
modified.

The timer based portion of the script will integrate records from Netbox to
Route53 based on a timespan variable. This retrieves the newer records in Netbox
and compares them to what is in Route53, following the same create/update/delete
logic as webhooks for each record. After integrating all the records, the script
purges any Route53 record that has a tag, but is not present in Netbox. This is
to prevent stale records from hanging around.

### How the comparisons work:

To quickly compare a large number of records and minimize on script uptime, all
Netbox records are retrieved in 1 api call and stored in a dictionary as mapped
key values. The hosted zones are parsed from the Netbox record names so only
the necessary hosted zone records are retrieved and put into a key value mapping
for Route53 records.

The script then iterates through these two dictionaries, determining what to do
for each Netbox record, then formulates the update in json, finishing by storing
it in a changebatch variable which contains all the changes to be sent to Route53
in a single api batch call.

The purging function (clean_r53_records) works in a similar manner, however it
calls Netbox and Route53 again, to get an up-to-date snapshot post integration.

Example of the three different type of key value mappings used:

txt_key = f"{hz}|{nb_id}|TXT"
a_key_dns = f"{hz}|{dns}.|A"
a_key_ip = f"{hz}|{ip}|A"

All 3 keys contain value pairs that give extra information about a record.

Txt keys are built to check if an A record has an accompanying txt record
which then can be checked for presence of the tag, and the Netbox id.

A keys (dns and ip) are necessary to check if a record exists already. Dns and ip
need to be separate because duplicates of either kind are not supported by script
logic.

Keys are generated and stored in a dictionary every time the script starts. For
every record the script checks, it generates a new key and checks the dict it created
to see if the key is present.


### Aws Function Setup   
To prepare the framework inside AWS LAMBDA for uploading the script via Makefile commands

-Create a lambda function, appropriately named
(Use Python version 3.8)  
* [Aws docs Functions](https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html)


-Aws Cloudwatch Trigger Setup  
(Start from step 2, set timer to run every 30 minutes)
* [Aws docs Cloudwatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html)

To store the timespan within cloudwatch timer for multiple timer use, under targets, constant(json text) paste
the following:  {"Timespan": "1" }   (note, any other cloudwatch timers will be set up the same but with different time spans)

If there is no cloudwatch timespan set, or is set incorrectly, the script will use the environment variable "TIMESPAN"

-Aws API Gateway Trigger Setup  
(For the Netbox setup below, you will need the AWS API gateway Arn from creating an api gateway trigger)
* [Aws docs Apigateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/getting-started.html)


### Netbox Webhook Setup
To enable Netbox webhooks:
* [Netbox docs Webhooks](https://Netbox.readthedocs.io/en/stable/additional-features/webhooks/)


  Netbox>Other>Webhooks>Add Webhook

  Name: ()
  Object types: (IP addess, prefix)  
  Enabled: (checked)  
  Type Create: (checked)  
  Type Update: (checked)  
  Type Delete: (checked)  
  URL: (AWS API gateway arn) < (See Api gateway trigger setup)  
  HTTP method: (POST)
  HTTP content type: (application/json)

### IAM user setup & env vars (aws)

The following environment variables need to be added to the lambda function
NETBOX_TIMESPAN: 1
NETBOX_TOKEN: (access token for Netbox)
NETBOX_URL: (url for Netbox)
ROUTE53_ID: See IAM user setup below
ROUTE53_KEY: See IAM user setup below
ROUTE53_TAG: nbr53

An aws IAM user needs to be created and the access key/secret key are put in as env
vars in the order ROUTE53_ID = access key | ROUTE53_KEY: secret key

The IAM user needs to have the following policies attached:
- AmazonRoute53DomainsReadOnlyAccess
- AmazonAPIGatewayPushToCloudWatchLogs
- AmazonRoute53FullAccess

### Makefile
To push script to lamdba, use Makefile commands

Rename LAMBDA_FUNCTION_NAME inside the makefile to match the name of the  Aws Lambda function

(Terminal/Cmd commands to port script to aws)

-Specify Aws account details
```bash
aws configure    
aws sts get-caller-identity
```

-Compile Script and upload to both functions

```bash
make lambda-layer
make lambda-upload
```    
