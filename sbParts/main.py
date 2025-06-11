import asyncio

from common.constants import BASIC_HEADERS
from sbParts.constants import HEADERS
from sbParts.request_helper import SbPartsRequestHelper


if __name__ == '__main__':


    scraper = SbPartsRequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        headers=HEADERS
    )

    asyncio.run(scraper.collect_all_part_numbers())