import logging
import datetime
import json
import socket
from Netbox_Route53.Netbox_route53 import NetboxRoute53

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def lambda_handler(event, handle):
    logger.debug('new event received: %s', str(event))
    logger.debug(str(event))
    logger.debug(socket.gethostbyname('netbox3.aws.ciscops.net'))
    start_time = datetime.datetime.now()
    netbox_r53 = NetboxRoute53()
    netbox_r53.integrate_records()
    netbox_r53.clean_r53_records()
    end_time = datetime.datetime.now()
    logger.debug('Script complete, total runtime {%s - %s}', end_time, start_time)
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "testkey ": "testval"
        })
    }
