import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from jproperties import Properties
import locale

import requests
from bs4 import BeautifulSoup

from datetime import datetime

import sched, time

wish_list = {}
locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')

configs: Properties = Properties()
with open('amazonPriceUpdateNotifier.properties', 'rb') as config_file:
    configs.load(config_file)

wishlistURLs = configs.get("wishlist.urls").data.split(",")
host = configs.get("email.host").data
port = configs.get("email.port").data
username = configs.get("email.username").data
password = configs.get("email.password").data
emailFrom =  configs.get("email.from").data
emailTo = configs.get("email.to").data

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
    priceWhole = item.find("span", class_="a-price-whole")
    priceFraction = item.find("span", class_="a-price-fraction")
    return float(f"{locale.atof(f'{priceWhole.text}{priceFraction.text}')}") if priceWhole else None


def findPriceUsed(item):
    priceUsed = item.find("span", class_="a-color-price itemUsedAndNewPrice")
    return locale.atof(f'{priceUsed.text.strip()}'.split()[0]) if priceUsed else None


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
        title = item["title"]
        price = item["price"]
        priceOld = item["history"]["price"]
        priceUsed = item["priceUsed"]
        priceUsedOld = item["history"]["priceUsed"]
        body += '***********************************\n'
        body += f'{title}\n\n'
        body += f'Price: {locale.currency(price, grouping=True) if price else "N/A"}  -> ' \
                f'{locale.currency(priceOld, grouping=True) if priceOld else "N/A"}\n'
        body += f'Price used {locale.currency(priceUsed, grouping=True) if priceUsed else "N/A"}  -> ' \
                f'{locale.currency(priceUsedOld, grouping=True) if priceUsedOld else "N/A"}\n\n'

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
        itemId = newItem["id"]
        item = wish_list.get(itemId)

        if item is None:
            wish_list[itemId] = newItem
            updatedItems.append(newItem)

        elif item["price"] != newItem["price"] or item["priceUsed"] != newItem["priceUsed"]:
            item["history"]["price"].insert(0, item["price"])
            item["history"]["price"] = item["history"]["price"][0:4]
            item["history"]["priceUsed"].insert(0, item["priceUsed"])
            item["history"]["priceUsed"] = item["history"]["priceUsed"][0:4]
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
        msg['From'] = emailFrom
        msg['To'] = emailTo

        server = smtplib.SMTP_SSL(host, port)
        server.login(username, password)
        server.send_message(msg)
        server.quit()


def get_subject(items):
    numItems = len(items)
    item = items[0]
    title = item['title'][0:10]
    price = locale.currency(item['price'], grouping=True) if item['price'] else "N/A"
    priceUsed = locale.currency(item['priceUsed'], grouping=True) if item['priceUsed'] else "N/A"

    return f"Wishlist({numItems}): {title}...({price}/{priceUsed})"


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

    s = sched.scheduler(time.time, time.sleep)
    s.enter(60, 1, clean_up_wishlist)

    while True:
        try:
            browse_and_scrape(wishlistURLs)
        except Exception as inst:
            print(inst)

        time.sleep(30)
