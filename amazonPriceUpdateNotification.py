import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from jproperties import Properties

import requests
from bs4 import BeautifulSoup

from datetime import datetime

import sched, time

wish_list = {}


def clean_up_wishlist():
    print("Wishlist cleanup process started...")
    scrappedItems = scrapeURLs(wishlistURLs)
    cleanupRemovedItems(scrappedItems)
    print("Wishlist cleanup process finished...")


def findTitle(item):
    itemId = item["data-itemid"]
    title = item.find("a", id=f"itemName_{itemId}")["title"]

    return title


def findPrice(item):
    price = item["data-price"]

    return f"{price} €" if price is not None and price != "-Infinity" else "N/A"


def findPriceUsed(item):
    priceUsed = item.find("span", class_="a-color-price itemUsedAndNewPrice")

    return priceUsed.text.strip() if priceUsed is not None else None


def findId(item):
    return item["data-itemid"]


# Remove items not in the wish list anymore. i.e. removed from actual amazon wish list.
def itemsToMap(items):
    itemsMap = {}
    for item in items:
        itemsMap[item["data-itemid"]] = item

    return itemsMap


def cleanupRemovedItems(items):
    for wishItem in wish_list.copy().values():
        itemId = wishItem["id"]

        if not findItem(items, itemId):
            print(f"Removing {wishItem}")
            del wish_list[itemId]


def findItem(items, wishItemId):
    found = False
    for item in items:
        if wishItemId == item["id"]:
            found = True
            break
    return found


def buildBody(items):
    body = "The following items have updated prices\n\n"
    for item in items:
        body += '***********************************\n'
        body += f'{item["title"]}\n\n'

        body += f'Price: {item["price"] if item["price"] else "N/A"}  -> {item["history"]["price"]}\n'
        body += f'Price used {item["priceUsed"] if item["priceUsed"] else "N/A"}  -> {item["history"]["priceUsed"]}\n\n'

    return body


def scrapeURL(soup):
    notification_list = []
    scrappedItems = []
    items = soup.find_all(attrs={"data-itemid": True})
    for item in items:
        scrappedItem = {
            "id": findId(item),
            "title": findTitle(item),
            "price": findPrice(item),
            "priceUsed": findPriceUsed(item),
            "history": {"price": [],
                        "priceUsed": []
                        }
        }

        scrappedItems.append(scrappedItem)

    return scrappedItems


def updateWishList(newItems):
    updatedItems = []
    for newItem in newItems:

        item = wish_list.get(newItem["id"])

        if item is None:
            wish_list[newItem["id"]] = newItem
            updatedItems.append(newItem)

        elif item["price"] != newItem["price"] or item["priceUsed"] != newItem["priceUsed"]:
            item["history"]["price"].insert(0, item["price"])
            item["history"]["priceUsed"].insert(0, item["priceUsed"])
            item["price"] = newItem["price"]
            item["priceUsed"] = newItem["priceUsed"]

            updatedItems.append(item)

    return updatedItems


def filterUpdates(items):
    filteredItems = only_if_smaller_price_strategy(items)
    # filteredItems = otherStrategy(filteredItems)

    return filteredItems


def only_if_smaller_price_strategy(items):
    filteredItems = []
    for item in items:
        priceUsedNew = item["priceUsed"]
        priceUsedOld = item["history"]["priceUsed"][0] if len(item["history"]["priceUsed"]) > 0 else None
        priceNew = item["price"]
        priceOld = item["history"]["price"][0] if len(item["history"]["price"]) > 0 else None

        if isSmallerPrice(priceUsedNew, priceUsedOld) or isSmallerPrice(priceNew, priceOld):
            filteredItems.append(item)

    return filteredItems


def isSmallerPrice(priceUsedNew, priceUsedOld):
    if priceUsedNew and priceUsedOld:
        if priceUsedOld > priceUsedNew:
            return True
    elif priceUsedNew and not priceUsedOld:
        return True
    else:
        return False


def notifyUpdates(items):
    # if not empty
    if items:
        text_type = 'plain'  # or 'html'
        text = buildBody(items)
        msg = MIMEText(text, text_type, 'utf-8')

        msg['Subject'] = get_subject(items)
        msg['From'] = configs.get("email.from").data
        msg['To'] = configs.get("email.to").data
        host = configs.get("email.host").data
        port = configs.get("email.port").data
        username = configs.get("email.username").data
        password = configs.get("email.password").data
        server = smtplib.SMTP_SSL(host, port)
        server.login(username, password)
        server.send_message(msg)
        server.quit()


def get_subject(items):
    subject = f"Price update ({len(items)})"
    for item in items:
        subject = f"{subject}  {item['title'][5]}...({item['priceUsed']}), "
    return subject


def browse_and_scrape(urls):
    scrappedItems = scrapeURLs(urls)
    print(f"Number of items scrapped {len(scrappedItems)}")

    updatedItems = updateWishList(scrappedItems)
    print(f"Updated items ({len(updatedItems)}) {updatedItems}")

    filteredItems = filterUpdates(updatedItems)
    print(f"Items to notify ({len(filteredItems)}) {filteredItems}")

    if filteredItems:
        notifyUpdates(filteredItems)


def scrapeURLs(urls):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    scrappedItems = []

    for url in urls:
        print(f"{dt_string} Scraping - {url}")

        html_text = requests.get(url).text
        soup = BeautifulSoup(html_text, "html.parser")
        items = scrapeURL(soup)

        scrappedItems.extend(items)
    return scrappedItems


if __name__ == "__main__":

    configs: Properties = Properties()
    with open('amazonPriceUpdateNotifier.properties', 'rb') as config_file:
        configs.load(config_file)

    wishlistURLs = configs.get("wishlist.urls").data.split(",")

    s = sched.scheduler(time.time, time.sleep)
    s.enter(60, 1, clean_up_wishlist)

    while True:
        browse_and_scrape(wishlistURLs)
        time.sleep(30)
