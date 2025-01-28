import json

import curl
import requests

from constants import BRANDS, JINKU_PAYLOAD, JINKU_CATALOG_URL, JINKU_HEADERS
from db import jinku_models_collection
from logger import logger


def send_request(url, headers, payload, params=None):
    response=requests.post(url,headers=headers,data=payload,params=params)
    return response

def parse_response_to_get_models_list(data):
    logger.info("Parsing Response to get Models")
    models_dict=data.get("serverMemo").get("data").get("models")
    if models_dict is None:
        logger.error(f"Some Error in parsing response to get models - Data - {data}")
        raise Exception("parse_response_to_get_models_list Error")
    for model in models_dict:
        models_dict[model]["jinku_model_id"]=model
        jinku_models_collection.insert_one(models_dict[model])

def get_model_lists():
    logger.info("Getting model lists")
    JINKU_PAYLOAD["updates"][0]["payload"]["params"].append("5")
    new_payload=json.dumps(JINKU_PAYLOAD)
    response=send_request(JINKU_CATALOG_URL,JINKU_HEADERS,new_payload)

    curl.parse(response)

    if response.status_code==419:
        logger.error(f"Received 419 Status Code - Data Received - {response.text}")
        raise Exception("UPDATE CSRF TOKEN FROM ENV")

    if response.status_code==200:
        logger.info(f"Received 200 Status Code - Data Received - {response.json()}")
        data=response.json()
        parse_response_to_get_models_list(data)
        logger.info("Complete!")

    else:
        logger.error(f"Received Status Code - {response.status_code} - response data - {response.text}")
        raise Exception("Some Error")

if __name__ == '__main__':
    get_model_lists()