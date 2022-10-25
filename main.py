import os
import requests
import json
import yaml
import logging.config


def load_config(file):
    with open(file) as stream:
        config = yaml.safe_load(stream=stream)
    return config

logger_file_path = "logger.yaml"
config_file = "temp.yaml"

logger_config = load_config(file=logger_file_path)

logging.config.dictConfig(logger_config)
logger = logging.getLogger('info_logger')

with open(config_file, "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

if os.getenv("REGION") is None:
    regions = [region for region in config['gcp']['regions']]
else:
    regions = os.getenv("REGION").split(",")
if os.getenv("MACHINE_TYPE") is None:
    machine_types = [machine for machine in config['gcp']['machine_types']]
else:
    machine_types = os.getenv("MACHINE_TYPE").split(",")

api_key = 'AIzaSyA_laDLrFwP7McEGw0mafAEt01NJ5faE-g'
result = requests.get(url=f'https://cloudbilling.googleapis.com/v1/services?key={api_key}')
service_id_compute_engine = '6F81-5844-456A'

r = requests.get(f"https://cloudbilling.googleapis.com/v1/services/{service_id_compute_engine}/skus?key={api_key}")
data_gcp = json.loads(r.text)
result_data = {}
for machine_type in machine_types:
    for region in regions:
        result_data[region] = {}
        for sku in data_gcp['skus']:
            description_lower = sku["description"].lower()
            if region in sku["serviceRegions"] and \
                    sku["category"]["usageType"] == "Preemptible" and \
                    "custom" not in description_lower and \
                    f"{machine_type.lower()}" in description_lower and \
                    ("core" in description_lower or "ram" in description_lower):
                price = sku['pricingInfo'][0]['pricingExpression']['tieredRates'][0]['unitPrice']['nanos']
                if "ram" in description_lower:
                    price = price / 1000000000 * 730 * 128
                else:
                    price = price / 1000000000 * 730 * 16
                if machine_type not in result_data[region]:
                    result_data[region][machine_type] = 0
                result_data[region][machine_type] += price

while 'nextPageToken' in data_gcp and data_gcp['nextPageToken']:
    next_page_token = data_gcp['nextPageToken']
    r = requests.get(
        f"https://cloudbilling.googleapis.com/v1/services/{service_id_compute_engine}/skus?key={api_key}&pageToken={next_page_token}")
    data_gcp = json.loads(r.text)

    for machine_type in machine_types:
        for region in regions:
            for sku in data_gcp['skus']:
                description_lower = sku["description"].lower()

                if region in sku["serviceRegions"] and \
                        sku["category"]["usageType"] == "Preemptible" and \
                        "custom" not in description_lower and \
                        f"{machine_type.lower()}" in description_lower and \
                        ("core" in description_lower or "ram" in description_lower):
                    price = sku['pricingInfo'][0]['pricingExpression']['tieredRates'][0]['unitPrice']['nanos']
                    if "ram" in description_lower:
                        price = price / 1000000000 * 730 * 128
                    else:
                        price = price / 1000000000 * 730 * 16
                    if machine_type not in result_data[region]:
                        result_data[region][machine_type] = 0
                    result_data[region][machine_type] += price
                    logger.info(f"{region} {machine_type} {int(result_data[region][machine_type])}",
                                extra={'existence': True})
