import logging
import datetime
from Netbox_Route53_Integration.Netbox_Route53 import Netbox_route53

logger = logging.getLogger()
logger.setLevel(logging.INFO)


#pylint: disable=unused-argument
def lambda_handler(event, context):
    logger.debug('new event received: %s', str(event))
    start_time = datetime.datetime.now()
    Netbox_route53 = NetboxRoute53()
    Netbox_route53.integrate_records()
    end_time = datetime.datetime.now()
    logger.debug('Script complete, total runtime {%s - %s}', end_time, start_time)
