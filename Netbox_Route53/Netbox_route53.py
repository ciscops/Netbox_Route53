from datetime import datetime, timedelta
import logging
import json
import os
import sys
import pynetbox
import boto3

# Either manually enter the necessary keys or set them as environment variables. The latter is recommended and examples are provided
# Export Netbox: url, timespan & token....Examples:
# export NETBOX_URL=https://example.net
# export NETBOX_TOKEN=guyg3r2fw8e7tgf2898366487n
# export NETBOX_TIMESPAN=1   (<- value in days)

# Export Route53: access_key_id, secret_access_key, HostZoneId....Examples:
# export ROUTE53_ID=KUYGDS783WSKI
# export ROUTE53_KEY=JHIU243YT9F8UHSUY983Y
# export ROUTE53_HOSTEDZONE_ID=EROTIJGOI438979800BW

#Note: these are made up keys and are not valid


class NetboxRoute53:
    def __init__(self):
        logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
        self.logging = logging.getLogger()

        # Initialize Netbox
        if "NETBOX_URL" in os.environ:
            self.nb_url = os.getenv("NETBOX_URL")
        else:
            logging.error("Environmnet variable NETBOX_URL must be set")
            sys.exit(1)

        if "NETBOX_TOKEN" in os.environ:
            self.nb_token = os.getenv("NETBOX_TOKEN")
        else:
            logging.error("Environmnet variable NETBOX_TOKEN must be set")
            sys.exit(1)

        if "NETBOX_TIMESPAN" in os.environ:
            self.timespan = os.getenv("NETBOX_TIMESPAN")
        else:
            self.timespan = 1

        self.nb = pynetbox.api(url=self.nb_url, token=self.nb_token)
        self.nb_ip_addresses = self.nb.ipam.ip_addresses.all()

        # Custom tag for marking records in Route53 - this can be changed to any name
        self.r53_tag = "\"nbr53\""

        # Initialize Route53
        if "ROUTE53_ID" in os.environ:
            self.r53_id = os.getenv("ROUTE53_ID")
        else:
            logging.error("Environment variable ROUTE53_ID must be set")
            sys.exit(1)

        if "ROUTE53_KEY" in os.environ:
            self.r53_key = os.getenv("ROUTE53_KEY")
        else:
            logging.error("Environment variable ROUTE53_KEY must be set")
            sys.exit(1)

        # Gets the hosted zone id
        if "ROUTE53_HOSTEDZONE_ID" in os.environ:
            self.r53_zone_id = os.getenv("ROUTE53_HOSTEDZONE_ID")
        else:
            logging.error("Environment variable ROUTE53_HOSTEDZONE_ID must be set")
            sys.exit(1)

        # initiate connection to Route53 Via Boto3
        self.client = boto3.client('route53', aws_access_key_id=self.r53_id, aws_secret_access_key=self.r53_key)

        # Get hosted_zone domain name for appending to record names
        Hosted_zone_response = self.client.get_hosted_zone(Id=self.r53_zone_id)
        HZ = json.dumps(Hosted_zone_response)
        HZ1 = json.loads(HZ)
        self.HZ_Name = HZ1['HostedZone']['Name']

        R53_get_response = self.client.list_resource_record_sets(HostedZoneId=self.r53_zone_id)
        self.R53_Record = json.dumps(R53_get_response)
        self.R53 = json.loads(self.R53_Record)

        self.r53_record_dict = {}
        self.r53_tag_dict = {}

        self.dns_string = ""
        for i in self.nb_ip_addresses:
            nb_dns = i.dns_name + "." + self.HZ_Name
            self.dns_string += nb_dns

    def get_nb_records(self):
        timespan = datetime.today() - timedelta(days=self.timespan)
        timespan.strftime('%Y-%m-%dT%XZ')
        ip_search = self.nb.ipam.ip_addresses.filter(within=self.nb_ip_addresses, last_updated__gte=timespan)
        return ip_search

    def check_record_exists(self, dns, ip):
        if dns in self.r53_record_dict or ip in self.r53_record_dict.values():
            return True
        return False

    def get_r53_record_tag(self, dns):
        if dns in self.r53_tag_dict:
            return True
        return None

    def get_r53_records(self):
        R53_Record_response = self.client.list_resource_record_sets(HostedZoneId=self.r53_zone_id)
        R53_Record = json.dumps(R53_Record_response)
        R53 = json.loads(R53_Record)
        v = R53_Record.count('''"Name"''')
        for n in range(0, v):
            R53_Record_name = R53['ResourceRecordSets'][n]['Name']
            R53_Tag_response = self.client.list_resource_record_sets(
                HostedZoneId=self.r53_zone_id, StartRecordName=R53_Record_name, StartRecordType="TXT"
            )
            R53_ip = R53['ResourceRecordSets'][n]['ResourceRecords'][0]['Value']
            R53_Record_type = self.R53['ResourceRecordSets'][n]['Type']
            if R53_Record_type == 'A':
                self.r53_record_dict.update({R53_Record_name: R53_ip})
            if R53_Record_type == 'TXT':
                R53_tag = R53_Tag_response['ResourceRecordSets'][0]['ResourceRecords'][0]['Value']
                if R53_tag == self.r53_tag:
                    self.r53_tag_dict.update({R53_Record_name: R53_tag})

    def verify_and_update(self, dns, ip):
        for x in self.r53_record_dict:
            R53_ip = self.r53_record_dict[x]
            R53_Record_name = x
            if R53_Record_name == dns:
                if R53_ip == ip:
                    print("Record is a complete match")
                    break
                print("The ip passed in does not match the dns")
                if self.get_r53_record_tag(dns):
                    print("Updating record")
                    self.update_r53_record(dns, ip)
                    break
                print("Record not tagged, cant update")
                break
            if ip == R53_ip:
                if self.get_r53_record_tag(R53_Record_name):
                    print("Record exists, but Dns is wrong, cleaning...")
                    self.delete_r53_record(R53_Record_name, ip)
                    self.create_r53_record(dns, ip)
                    print("Record cleaned")
                    break
                print("Record not tagged, cant update")
                break

    def update_r53_record(self, dns, ip):
        self.client.change_resource_record_sets(
            HostedZoneId=self.r53_zone_id,
            ChangeBatch={
                'Comment':
                '',
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': dns,
                            'Type': 'A',
                            'TTL': 123,
                            'ResourceRecords': [
                                {
                                    'Value': ip,
                                },
                            ],
                        }
                    },
                ]
            }
        )

    def create_r53_record(self, dns, ip):
        self.client.change_resource_record_sets(
            HostedZoneId=self.r53_zone_id,
            ChangeBatch={
                'Changes': [{
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': dns,
                        'Type': 'A',
                        'TTL': 123,
                        'ResourceRecords': [{
                            'Value': ip
                        }]
                    }
                }, {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': dns,
                        'Type': 'TXT',
                        'TTL': 123,
                        'ResourceRecords': [{
                            'Value': self.r53_tag
                        }]
                    }
                }]
            }
        )

    def delete_r53_record(self, dns, ip):
        self.client.change_resource_record_sets(
            HostedZoneId=self.r53_zone_id,
            ChangeBatch={
                'Comment':
                '',
                'Changes': [{
                    'Action': 'DELETE',
                    'ResourceRecordSet': {
                        'Name': dns,
                        'Type': 'A',
                        'TTL': 123,
                        'ResourceRecords': [{
                            'Value': ip
                        }]
                    }
                }, {
                    'Action': 'DELETE',
                    'ResourceRecordSet': {
                        'Name': dns,
                        'Type': 'TXT',
                        'TTL': 123,
                        'ResourceRecords': [{
                            'Value': self.r53_tag
                        }]
                    }
                }]
            }
        )

    def purge_r53_records(self, R53_Record_name, R53_ip, ip):
        self.logging.debug("Checking record %s", R53_ip)
        print("Checking record: " + R53_Record_name + " " + R53_ip)
        if R53_Record_name in self.dns_string or R53_ip in ip:
            self.logging.debug("Record exists%s", R53_ip)
            print("Record exists")
        else:
            self.logging.debug("Purging record %s", R53_ip)
            print("purge: " + R53_Record_name + " " + R53_ip)
            self.delete_r53_record(R53_Record_name, R53_ip)

    # In the case that a dns name is changed, and the script is run, clean_r53_records wont
    # find that dns and won't attempt to clean it. Running the script again will clean it
    def clean_r53_records(self):
        print("Record cleaning...")
        ip = str(self.nb_ip_addresses)
        v = self.R53_Record.count('''"Name"''')
        if self.nb_ip_addresses != []:
            if v > 2:
                for n in range(0, v):
                    R53_Record_type = self.R53['ResourceRecordSets'][n]['Type']
                    R53_ip = self.R53['ResourceRecordSets'][n]['ResourceRecords'][0]['Value']
                    R53_Record_name = self.R53['ResourceRecordSets'][n]['Name']
                    if R53_Record_type == 'A':
                        if self.get_r53_record_tag(R53_Record_name):
                            self.purge_r53_records(R53_Record_name, R53_ip, ip)
        else:
            self.logging.debug("Netbox recordset is empty %s")
            print("Netbox recordset is empty")

    # Check all records in Netbox against Route53, and update the tagged record's ip/dns pair if they are incorrect
    def integrate_records(self):
        self.get_r53_records()
        print("Record integration...")
        for i in self.get_nb_records():
            nb_dns = i.dns_name + "." + self.HZ_Name
            ip = str(i)
            sep = '/'
            nb_ip = ip.split(sep, 2)[0]
            self.logging.debug("Checking %s", nb_ip)
            print("Checking record: " + nb_dns + " " + nb_ip)
            if self.check_record_exists(nb_dns, nb_ip):
                self.logging.debug("Verifying %s", nb_ip)
                print("Record exists, Verifying record...")
                self.verify_and_update(nb_dns, nb_ip)
            else:
                self.logging.debug("Adding %s", nb_ip)
                self.create_r53_record(nb_dns, nb_ip)
                print("Record created, continuing...")
