from datetime import datetime, timedelta
import logging
import json
import re
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
            # self.r53_tag = "\"nbr53\""
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

        for hosted_zone in hz_list:
            nb_hz_name = hosted_zone
            try:
                response = self.client.list_hosted_zones_by_name(DNSName=nb_hz_name)
            except Exception:
                continue

            hz_id = response['HostedZones'][0]['Id'].strip('/hostedzone/')
            hz_name = response['HostedZones'][0]['Name']
            if nb_hz_name + "." == hz_name:
                self.hosted_zone_dict.update({nb_hz_name: hz_id})
                self.logging.debug("Searching records for hosted zone: %s", hz_name)
                r53_dns_records = self.get_hosted_zone_records(hz_id)

                for record in r53_dns_records:
                    if record['Type'] == 'TXT':
                        value = record['ResourceRecords'][0]['Value']
                        if re.match('^"Tag: {},'.format(self.r53_tag), value):
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

    def get_hosted_zone_records(self, hz_id):
        r53_dns_records = []

        hosted_zone_records = self.client.list_resource_record_sets(HostedZoneId=hz_id)
        r53_dns_records.extend(hosted_zone_records['ResourceRecordSets'])

        while 'NextRecordName' in hosted_zone_records.keys():
            next_record_name = hosted_zone_records['NextRecordName']
            hosted_zone_records = self.client.list_resource_record_sets(
                HostedZoneId=hz_id, StartRecordName=next_record_name
            )
            r53_dns_records.extend(hosted_zone_records['ResourceRecordSets'])
        return r53_dns_records

    def verify_and_update(self, dns, ip, r53_dns, r53_ip, tag, zone_id):
        update_record = {}
        update_record[zone_id] = []
        dns = dns + "."
        if r53_dns == dns and r53_ip == ip:
            self.logging.debug("Record matches")
        elif r53_dns != dns and r53_ip == ip or r53_dns != dns and r53_ip != ip:
            self.logging.debug("Record does not match")
            update_record[zone_id].extend(self.format_change_json('DELETE', r53_dns, r53_ip, tag, 'txt, a', 'set'))
            update_record[zone_id].extend(self.format_change_json('CREATE', dns, ip, tag, 'txt, a', 'set'))
        elif r53_dns == dns and r53_ip != ip:
            self.logging.debug("Ip does not match")
            update_record[zone_id].extend(self.format_change_json('UPSERT', r53_dns, ip, 'none', 'A', 'single'))

        self.logging.debug(update_record)
        self.update_route53(update_record)

    def route53_tag_creator(self, request_id):
        tag = self.r53_record_tag
        tag_strip = tag.strip('"')
        return_tag = '"Tag: ' + tag_strip + ", Id: " + request_id + '"'
        return (return_tag)

    def txt_key_lookup(self, txt_key, r53_records_dict, hz):
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
                    return r53_dns, r53_ip
        self.logging.debug("Could not locate a valid TXT record")
        return 'empty', 'empty'

    def format_change_json(self, action, name, value, value2, single_type, format_type):
        if format_type == 'set':
            change_format = [{
                'Action': action,
                'ResourceRecordSet': {
                    'Name': name,
                    'Type': 'A',
                    'TTL': 123,
                    'ResourceRecords': [{
                        'Value': value
                    }]
                }
            }, {
                'Action': action,
                'ResourceRecordSet': {
                    'Name': name,
                    'Type': 'TXT',
                    'TTL': 123,
                    'ResourceRecords': [{
                        'Value': value2
                    }]
                }
            }]

        else:
            change_format = [{
                'Action': action,
                'ResourceRecordSet': {
                    'Name': name,
                    'Type': single_type,
                    'TTL': 123,
                    'ResourceRecords': [{
                        'Value': value
                    }]
                }
            }]
        return change_format

    def update_route53(self, record_changes):
        for batch in record_changes:
            zone_id = batch
            changes = record_changes[batch]
            if len(changes) != 0:
                self.client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch={'Changes': changes})

    # Create/update/delete a single netbox record based on webhook request
    def webhook_update_record(self, event):
        webhook_json = json.loads((event["body"]))
        request_type = webhook_json['event']
        nb_ip = str(webhook_json['data']['address']).split('/', 2)[0]
        nb_dns = webhook_json['data']['dns_name']
        nb_id = str(webhook_json['data']['id'])

        self.logging.debug("Webhook received")
        if len(nb_dns) > 0 and '.' in nb_dns:
            self.logging.debug("A Netbox record was updated: %s | ip: %s", nb_dns, nb_ip)
            nb_hz = nb_dns.split('.', 1)[1]
            r53_records_dict = self.get_r53_records([nb_hz])

            txt_key = f"{nb_hz}|{nb_id}|TXT"
            a_key_dns = f"{nb_hz}|{nb_dns}.|A"
            a_key_ip = f"{nb_hz}|{nb_ip}|A"
            tag = self.route53_tag_creator(nb_id)

            try:
                zone_id = self.hosted_zone_dict[nb_hz]
            except Exception:
                self.logging.debug("Cannot locate hosted zone %s", nb_hz)
                sys.exit(1)

            record_webhook_changes = {}
            record_webhook_changes[zone_id] = []

            r53_dns, r53_ip = self.txt_key_lookup(txt_key, r53_records_dict, nb_hz)
            if r53_dns != 'empty':
                if request_type == 'updated':
                    self.logging.debug("Updating record %s", nb_dns)
                    self.verify_and_update(nb_dns, nb_ip, r53_dns, r53_ip, tag, zone_id)
                elif request_type == 'deleted':
                    self.logging.debug("Deleting record %s", nb_dns)
                    record_webhook_changes[zone_id].extend(self.format_change_json('DELETE', nb_dns, nb_ip, tag, 'txt, a', 'set'))
                    self.update_route53(record_webhook_changes)
                else:
                    self.logging.debug("Record already exists %s")
            elif a_key_dns not in r53_records_dict and a_key_ip not in r53_records_dict:
                if request_type == 'created':
                    self.logging.debug("Creating record %s", nb_dns)
                    record_webhook_changes[zone_id].extend(self.format_change_json('CREATE', nb_dns, nb_ip, tag, 'txt, a', 'set'))
                    self.update_route53(record_webhook_changes)
            else:
                self.logging.debug("Record already exists")
        else:
            self.logging.debug("Hosted zone cannot be parsed from record name, quitting")

    def clean_r53_records(self):
        self.logging.debug("Cleaning records without a netbox match")
        response = self.client.list_hosted_zones()
        all_route53_records = {}
        # Obtain all the records in all the hosted zones of an account
        for hz in response['HostedZones']:
            hz_record_count = hz['ResourceRecordSetCount']
            hz_id = hz['Id'].strip('/hostedzone/')
            if hz_id not in all_route53_records:
                all_route53_records[hz_id] = []
            if hz_record_count > 2:
                hosted_zone_records = self.get_hosted_zone_records(hz_id)
                all_route53_records[hz_id].extend(hosted_zone_records)

        netbox_records_list = self.nb.ipam.ip_addresses.all(limit=2000)
        nb_ip_dict = {}
        r53_A_record_dict = {}
        r53_records_to_purge = []

        for nb_record in netbox_records_list:
            ip = str(nb_record).split('/', 2)[0]
            nb_ip_dict.update({str(nb_record.id): ""})
        if nb_ip_dict == {}:
            self.logging.debug("No Netbox records")
            sys.exit(1)
        # Check if a route53 record has a valid set, and assign it to a dict
        for r53_record_key in all_route53_records:
            zone_id = r53_record_key
            r53_records = all_route53_records[r53_record_key]
            for record in r53_records:
                if record['Type'] == 'TXT':
                    value = record['ResourceRecords'][0]['Value']
                    r53_dns = record['Name']
                    if re.match('^"Tag: {},'.format(self.r53_tag), value):
                        rec_id = value.split('Id: ', 1)[1]
                        rec_id = str(rec_id.strip('"'))
                        if rec_id not in nb_ip_dict:
                            r53_records_to_purge.append({
                                'id': rec_id,
                                'dns': r53_dns,
                                'tag': value,
                                'zone_id': zone_id
                            })
                    else:
                        self.logging.debug("Record not tagged")
                if record['Type'] == 'A' and 'ResourceRecords' in record:
                    ip = record['ResourceRecords'][0]['Value']
                    dns = record['Name']
                    r53_A_record_dict.update({dns: ip})

        purging_record_changes = {}
        # Iterate through dict of known route53 records without a matching netbox set and scrub them
        for record in r53_records_to_purge:
            r53_dns = record['dns']
            tag = record['tag']
            zone_id = record['zone_id']
            if zone_id not in purging_record_changes:
                purging_record_changes[zone_id] = []
            if r53_dns in r53_A_record_dict:
                self.logging.debug("Purging record %s : record not found in netbox", r53_dns)
                r53_ip = r53_A_record_dict[r53_dns]
                purging_record_changes[zone_id].extend(
                    self.format_change_json('DELETE', r53_dns, r53_ip, tag, 'txt, a', 'set')
                )
            else:
                self.logging.debug("Txt record has no matching A record, purging txt record %s", r53_dns)
                purging_record_changes[zone_id].extend(
                    self.format_change_json('DELETE', r53_dns, tag, 'none', 'TXT', 'single')
                )

        self.logging.debug(purging_record_changes)
        self.update_route53(purging_record_changes)

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

        # Iterate through all netbox records and create a dict with record information
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

        record_changes = {}
        # For each record, create keys to look up in key dict index
        for nb_record in nb_records_list:
            dns = nb_record['dns']
            ip = nb_record['ip'].split('/', 2)[0]
            nb_id = str(nb_record['id'])
            hz = nb_record['hz']
            self.logging.debug("Checking Netbox record: %s | ip: %s | id: %s", dns, ip, nb_id)
            txt_key = f"{hz}|{nb_id}|TXT"
            a_key_dns = f"{hz}|{dns}.|A"
            a_key_ip = f"{hz}|{ip}|A"
            tag = self.route53_tag_creator(nb_id)

            try:
                zone_id = self.hosted_zone_dict[hz]
            except Exception:
                self.logging.debug("Cannot locate hosted zone %s", hz)
                continue

            if zone_id not in record_changes:
                record_changes[zone_id] = []
            # This first lookup checks for a txt record with the unique netbox id
            r53_dns, r53_ip = self.txt_key_lookup(txt_key, r53_records_dict, hz)
            if r53_dns != 'empty':
                dns = dns + "."
                if r53_dns == dns and r53_ip == ip:
                    self.logging.debug("Record matches")
                elif r53_dns != dns and r53_ip == ip or r53_dns != dns and r53_ip != ip:
                    self.logging.debug("Record does not match")
                    record_changes[zone_id].extend(
                        self.format_change_json('DELETE', r53_dns, r53_ip, tag, 'txt, a', 'set')
                    )
                    record_changes[zone_id].extend(self.format_change_json('CREATE', dns, ip, tag, 'txt, a', 'set'))
                elif r53_dns == dns and r53_ip != ip:
                    self.logging.debug("Ip does not match")
                    record_changes[zone_id].extend(
                        self.format_change_json('UPSERT', r53_dns, ip, 'none', 'A', 'single')
                    )

            # Second lookup checks to see if the record exists at all in route53
            elif a_key_dns in r53_records_dict or a_key_ip in r53_records_dict:
                self.logging.debug("A type record located but isn't tagged, continuing")
            else:
                self.logging.debug("No record located, creating record")
                record_changes[zone_id].extend(self.format_change_json('CREATE', dns, ip, tag, 'txt, a', 'set'))

        self.logging.debug(record_changes)
        self.update_route53(record_changes)
        self.clean_r53_records()
