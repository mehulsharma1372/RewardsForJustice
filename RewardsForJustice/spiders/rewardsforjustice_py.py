from datetime import datetime

from scrapy import FormRequest
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError, TCPTimedOutError
from bs4 import BeautifulSoup
import scrapy


class RewardsforJusticeSpider(scrapy.Spider):
    name = "rewardsforjustice"
    allowed_domains = ["rewardsforjustice.net"]
    start_urls = "https://rewardsforjustice.net/index/?jsf=jet-engine:rewards-grid&tax=crime-category:1070%2C1071%2C1073%2C1072%2C1074&pagenum="

    data = []
    hrefs = []

    output_filename = f"{name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    custom_settings = {
        "FEEDS": {
            f"{output_filename}.json": {"format": "json"},
            f"{output_filename}.csv": {"format": "csv"},
        }
    }

    def start_requests(self):
        meta = {
            "payload": {
                "action": "jet_engine_ajax",
                "handler": "get_listing",
                "page_settings[post_id]": "22076",
                "page_settings[queried_id]": "22076|WP_Post",
                "page_settings[element_id]": "ddd7ae9",
                "page_settings[page]": "1",
                "listing_type": "elementor",
                "isEditMode": "false",
                "addedPostCSS[]": "22078",
            },
            "spider_name": self.name,
        }

        for i in range(1, 23):

            r = FormRequest(
                url=self.start_urls + str(i),
                formdata=meta["payload"],
                callback=self.parse,
                errback=self.error_handler,
                meta=meta,
            )

            yield r

    def parse(self, response, **kwargs):
        json_response = response.json()["data"]["html"]
        soup = BeautifulSoup(json_response, "html5lib")
        anchors = soup.find_all("a")
        for anchor in anchors:
            href = anchor["href"]
            yield FormRequest(
                url=href, callback=self.parse_subinfo, errback=self.error_handler
            )
            self.hrefs.append(href)

    def parse_subinfo(self, response, **kwargs):
        dict = {}
        sel = scrapy.Selector(response)
        try:
            name = sel.xpath("//h2/text()")
            dict["title"] = name[0].get()

        except TypeError:
            print("the error in in name")
            dict["title"] = "null"

        try:
            url = response.url
            dict["url"] = url

        except TypeError:
            print("the error in in url")
            dict["url"] = "null"

        try:
            about = sel.xpath(
                "//div[@data-widget_type='theme-post-content.default']/div/p"
            )
            ab_lis = []
            for node in about:
                soup = BeautifulSoup(node.get()).text
                ab_lis.append(soup)
            dict["about"] = ab_lis

        except TypeError:
            print("the error in in about")
            dict["about"] = "null"

        try:
            reward_amount = sel.xpath(
                "//h4[contains(text(),'Reward')]/parent::div/parent::div/following-sibling::div[1]/div/h2"
            )
            soup = BeautifulSoup(reward_amount.get()).text

            dict["reward_amount"] = soup

        except TypeError:
            print("the error in in amount")
            dict["reward_amount"] = "null"

        location = sel.xpath(
            "//h2[contains(text(),'Associated Location')]/parent::div/parent::div/"
            + "following-sibling::div[1]//span[@class='jet-listing-dynamic-terms__link']"
        )
        try:
            soup = BeautifulSoup(location.get()).text

            dict["location"] = soup

        except TypeError:
            dict["location"] = "null"

        try:
            image = sel.xpath("//div[contains(@class,'terrorist-gallery')]//img/@src")
            soup = BeautifulSoup(image.get()).text

            dict["image_url"] = soup

        except TypeError:
            print("the error in in image")
            dict["image_url"] = "null"

        dob = sel.xpath(
            "//h2[contains(text(),'Date of Birth')]/parent::div/parent::div/following-sibling::div[1]/div"
        )
        try:
            soup = BeautifulSoup(dob.get()).text

            dict["dob"] = soup

        except TypeError:

            dict["dob"] = "null"

        self.data.append(dict)

        yield dict

    def error_handler(self, failure):
        self.logger.error(repr(failure))
        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error("HttpError on %s", response.url)

        elif failure.check(DNSLookupError):
            request = failure.request
            self.logger.error("DNSLookupError on %s", request.url)

        elif failure.check(TimeoutError, TCPTimedOutError):
            request = failure.request
            self.logger.error("TimeoutError on %s", request.url)
