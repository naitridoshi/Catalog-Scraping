from common.custom_logger import get_logger
from suzuki.constants import MODELS, SUZUKI_HEADERS
from suzuki.request_helper import SuzukiRequestHelper
import json

logger, listener = get_logger("SuzukiMain")
listener.start()

if __name__ == '__main__':
    for model_name, model_id in MODELS.items():
        logger.info(f"Processing model: {model_name}")
        scraper = SuzukiRequestHelper(
            headers=SUZUKI_HEADERS
        )

        model_name = model_name.replace(" ", "_")
        model_name = model_name.replace("(", "_")
        model_name = model_name.replace(")", "_")
        model_name = model_name.replace("-", "_")
        model_name = model_name.replace(".", "_")
        model_name = model_name.replace("'", "_")
        model_name = model_name.replace("\"", "_")
        model_name = model_name.replace("/", "_")
        model_name = model_name.replace(":", "_")
        model_name = model_name.lower()
        
        logger.info(f"Processing model: {model_name}")
        logger.info(f"Model ID: {model_id}")

        completed_pages = 0
        completed=False

        part_list = []
        while not completed:
            res = scraper.get_filters_data(model_id=model_id, model_name=model_name)
            try:
                if res:
                    logger.info(f"Response: {res}")
                    try:
                        data = json.loads(res)
                        total_pages = data.get("TotalPages")
                        if total_pages > completed_pages:
                            part_list.extend(data.get("PartList"))
                            completed_pages += 1
                        else:
                            completed = True
                    except Exception as e:
                        logger.info(f"Could not parse response: {res}")
                        part_list.extend(res)
            except Exception as e:
                logger.error(f"Error: {e}")
                continue
        
        logger.info(f"Completed pages: {completed_pages}")
        with open(f"files/suzuki/{model_name}.json", "w") as f:
            json.dump(part_list, f, indent=4)

        logger.info(f"Completed model: {model_name}")