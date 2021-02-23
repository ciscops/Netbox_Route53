# Netbox-Route53-Integration

Collection of scripts to integrate Netbox records to route53 based on ip and dns


Requirements

Python

Python requirements are contained in requirements.txt:

pip install -r requirements.txt

Netbox

Boto3

Description:

This script iterates through Netbox records based on a time-period of 24 hours since the last time updated. For each record, it
checks if Route53 contains the same record, iterating initially based on if the records in Route53 contain a special tag.
From there if a record exists, it verifies if it matches the Netbox record, and if not is updated accordingly. If no record is found
with either a matching dns or ip, a record is created with the appropriate parameters as well as a custom tag. There is a lambda
function created for this purpose as well. Finally, the script checks if all records in Route53 are in Netbox, if they are not, it purges them.
