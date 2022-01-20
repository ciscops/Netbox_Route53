from datetime import datetime, timedelta
import logging
import os
import sys
import pynetbox
import boto3

# Either manually enter the necessary keys or set them as environment variables. The latter is recommended and examples are provided
# Export Netbox: url, timespan & token....Examples:
# export NETBOX_URL=https://example.net
# export NETBOX_TOKEN=guyg3r2fw8e7tgf2898366487n
# export NETBOX_TIMESPAN=1   (<- value in days)

# Export Route53: access_key_id, secret_access_key....Examples:
# export ROUTE53_ID=KUYGDS783WSKI
# export ROUTE53_KEY=JHIU243YT9F8UHSUY983Y
# export ROUTE53_TAG="nbr53" (note: the " " are necessary here)
# Note: these are made up keys and are not valid


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
            self.timespan = int(os.getenv("NETBOX_TIMESPAN"))
        else:
            self.timespan = "all"

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

        if "ROUTE53_TAG" in os.environ:
            self.r53_tag = os.getenv("ROUTE53_TAG")
        else:
            #self.r53_tag = "\"nbr53\""
            self.r53_tag = "nbr53"

        self.r53_record_tag = f"\"{self.r53_tag}\""
        self.client = boto3.client('route53', aws_access_key_id=self.r53_id, aws_secret_access_key=self.r53_key)
        self.nb = pynetbox.api(url=self.nb_url, token=self.nb_token)
        self.hosted_zone_dict = {}

    def get_nb_records(self, nb_timespan):
        if nb_timespan == "all":
            ip_search = self.nb.ipam.ip_addresses.all(limit=2000)
        else:
            nb_timespan = int(nb_timespan)
            timespan = datetime.today() - timedelta(days=nb_timespan)
            timespan.strftime('%Y-%m-%dT%XZ')
            ip_search = self.nb.ipam.ip_addresses.filter(last_updated__gte=timespan, limit=2000)
        return ip_search

    def get_r53_records(self, hz_list):
        route53_records = {}

        for i, value in enumerate(hz_list):
            nb_hz_name = value
            try:
                response = self.client.list_hosted_zones_by_name(DNSName=nb_hz_name)
            except Exception:
                continue

            hz_id = response['HostedZones'][0]['Id'].strip('/hostedzone/')
            hz_name = response['HostedZones'][0]['Name']
            if nb_hz_name + "." == hz_name:
                self.hosted_zone_dict.update({nb_hz_name: hz_id})
                self.logging.debug("Searching records for hosted zone: %s", hz_name)
                #hosted_zone_records = self.client.list_resource_record_sets(HostedZoneId=hz_id)
                r53_dns_records = []

                hosted_zone_records = self.client.list_resource_record_sets(HostedZoneId=hz_id)
                r53_dns_records.extend(hosted_zone_records['ResourceRecordSets'])

                while 'NextRecordName' in hosted_zone_records.keys():
                    next_record_name = hosted_zone_records['NextRecordName']
                    hosted_zone_records = self.client.list_resource_record_sets(
                        HostedZoneId=hz_id, StartRecordName=next_record_name
                    )
                    r53_dns_records.extend(hosted_zone_records['ResourceRecordSets'])

                # Above needs the paginator true false bit
                for record in r53_dns_records:
                    if record['Type'] == 'TXT':
                        value = record['ResourceRecords'][0]['Value']
                        if self.r53_tag in value:  # Use the env var for this
                            #rebuild this using regex
                            tag = value.split(' ', 1)[1]
                            tag = tag.split(",", 1)[0]
                            tag = '"' + tag + '"'
                            rec_id = value.split('Id: ', 1)[1]
                            rec_id = rec_id.strip('"')
                            key = f"{nb_hz_name}|{rec_id}|TXT"
                            value = {'value': value, 'dns': record['Name']}
                        else:
                            key = f"{nb_hz_name}|{record['Name']}|TXT"
                        route53_records.update({key: value})

                    elif record['Type'] == 'A':
                        ip = record['ResourceRecords'][0]['Value']
                        key = f"{nb_hz_name}|{record['Name']}|A"
                        ip_key = f"{nb_hz_name}|{ip}|A"
                        route53_records.update({key: ip, ip_key: record['Name']})
        return route53_records

    def verify_and_update(self, dns, ip, r53_dns, r53_ip, tag, zone_id):
        dns = dns + "."
        if r53_dns == dns and r53_ip == ip:
            self.logging.debug("Record matches")
        elif r53_dns != dns and r53_ip == ip:
            self.logging.debug("Dns does not match")
            self.delete_r53_record(r53_dns, ip, tag, zone_id)
            self.create_r53_record(dns, ip, tag, zone_id)
            self.logging.debug("Record updated")
        elif r53_dns == dns and r53_ip != ip:
            self.logging.debug("Ip does not match")
            self.update_r53_record(r53_dns, ip, zone_id)
            self.logging.debug("Record updated")
        else:
            self.logging.debug("Ip and dns do not match, both were simultaneously updated")
            self.delete_r53_record(r53_dns, r53_ip, tag, zone_id)
            self.create_r53_record(dns, ip, tag, zone_id)
            self.logging.debug("Record updated")

    def route53_tag_creator(self, request_id):
        tag = self.r53_record_tag
        tag_strip = tag.strip('"')
        return_tag = '"Tag: ' + tag_strip + ", Id: " + request_id + '"'
        return (return_tag)

    def create_r53_record(self, dns, ip, tag, zone_id):
        self.client.change_resource_record_sets(
            HostedZoneId=zone_id,
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
                            'Value': tag
                        }]
                    }
                }]
            }
        )

    def update_r53_record(self, dns, ip, zone_id):
        self.client.change_resource_record_sets(
            HostedZoneId=zone_id,
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

    def delete_r53_record(self, dns, ip, tag, zone_id):
        self.client.change_resource_record_sets(
            HostedZoneId=zone_id,
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
                            'Value': tag
                        }]
                    }
                }]
            }
        )

    # Check all records in Netbox against Route53, and update the tagged record's ip/dns pair if they are incorrect
    def integrate_records(self, event=None):
        if event is not None and "Timespan" in event:
            nb_timespan = event["Timespan"]
        else:
            nb_timespan = self.timespan

        self.logging.debug("Timespan %s", nb_timespan)
        self.logging.debug("Fetching netbox records")
        netbox_records_response = self.get_nb_records(nb_timespan)
        nb_records_list = []
        nb_hz_list = []

        for record in netbox_records_response:
            dns = record.dns_name
            if len(dns) > 0 and '.' in dns:
                self.logging.debug("Located Netbox record: %s | ip: %s", dns, str(record))
                nb_hz = dns.split('.', 1)[1]
                nb_records_dictionary = {'dns': dns, 'ip': str(record), 'id': record.id, 'hz': nb_hz}
                nb_records_list.append(nb_records_dictionary)
                if nb_hz not in nb_hz_list:
                    nb_hz_list.append(nb_hz)

        r53_records_dict = self.get_r53_records(nb_hz_list)
        self.logging.debug(r53_records_dict)
        self.logging.debug("Integrating records")

        for i, value in enumerate(nb_records_list):
            dns = value['dns']
            ip = value['ip'].split('/', 2)[0]
            nb_id = str(value['id'])
            hz = value['hz']
            self.logging.debug("Checking Netbox record: %s | ip: %s | id: %s", dns, ip, nb_id)
            txt_key = f"{hz}|{nb_id}|TXT"
            a_key_dns = f"{hz}|{dns}.|A"
            a_key_ip = f"{hz}|{ip}.|A"

            tag = self.route53_tag_creator(nb_id)

            try:
                zone_id = self.hosted_zone_dict[hz]
            except Exception:
                self.logging.debug("Cannot locate hosted zone %s", hz)
                continue

            # This first lookup checks for a txt record with the unique netbox id
            if txt_key in r53_records_dict:
                self.logging.debug("TXT record located")
                a_key = f"{hz}|{r53_records_dict[txt_key]['dns']}|A"
                if a_key in r53_records_dict:
                    self.logging.debug("Matching A record located")
                    value = r53_records_dict[txt_key]['value']
                    if self.r53_tag in value:
                        self.logging.debug("Record is tagged, validating record")
                        r53_dns = r53_records_dict[txt_key]['dns']
                        r53_ip = r53_records_dict[a_key]
                        self.verify_and_update(dns, ip, r53_dns, r53_ip, tag, zone_id)
            # Second lookup checks to see if the record exists at all in route53
            elif a_key_dns in r53_records_dict or a_key_ip in r53_records_dict:
                self.logging.debug("A type record located but isn't tagged, continuing")
            else:
                self.logging.debug("No record located, creating record")
                self.create_r53_record(dns, ip, tag, zone_id)
