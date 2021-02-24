import logging
import datetime
from Netbox_Route53.Netbox_route53 import NetboxRoute53

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event):
    logger.debug('new event received: %s', str(event))
    start_time = datetime.datetime.now()
    netbox_r53 = NetboxRoute53()
    netbox_r53.integrate_records()
    netbox_r53.clean_r53_records()
    end_time = datetime.datetime.now()
    logger.debug('Script complete, total runtime {%s - %s}', end_time, start_time)
