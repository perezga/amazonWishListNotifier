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
    return locale.atof(f'{priceWhole.text}{priceFraction.text}') if priceWhole else None


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
        title = item["title"][0:40]
        savings = f"{item['savings']}".rjust(6)
        price = item["price"]
        priceOld = item["history"]["price"]
        priceUsed = item["priceUsed"]
        priceUsedOld = item["history"]["priceUsed"]
        body += '***********************************\n'
        body += f'{title}\nsavings: {savings} % \t price: {locale.currency(price, grouping=True) if price else "N/A"} \t used {locale.currency(priceUsed, grouping=True) if priceUsed else "N/A"}\n'
    return body


def scrapeURL(soup):
    notification_list = []
    scrappedItems = []
    items = soup.find_all(attrs={"data-itemid": True})
    for item in items:
        price = findPrice(item)
        priceUsed = findPriceUsed(item)
        scrappedItem = {
            "id": findId(item),
            "title": findTitle(item),
            "price": price,
            "priceUsed": priceUsed,
            "history": {"price": [], "priceUsed": []},
            "savings": float(f"{100 - (priceUsed/price)*100:.2f}") if priceUsed and price else float(0)
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
            item["savings"] = newItem["savings"]
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
    price = item['price']
    priceLocale = locale.currency(price, grouping=True) if price else "N/A"
    priceUsed = item['priceUsed']
    priceUsedLocale = locale.currency(priceUsed, grouping=True) if priceUsed else "N/A"

    return f"Wishlist({numItems}): {title}...({priceLocale}/{priceUsedLocale})"

def printItems(items):
    for item in items:
        savings = f"{item['savings']}".rjust(6)
        price = f"{item['price']}".rjust(7)
        used = f"{item['priceUsed']}".rjust(7)
        print(f"{item['title'][0:60]:60} \t savings: {savings}% \t price: {price} \t used: {used} \t priceHistory: {item['history']['price']} \t priceUsedHistory: {item['history']['priceUsed']}")
    	
def printItemsTitles(items):
    for item in items:
    	print(f"{item['title'][0:60]:60}")

def browse_and_scrape(urls):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    scrappedItems = scrapeURLs(urls)
    #print(f"{dt_string} Number of items scrapped {len(scrappedItems)}")

    scrappedItems = sorted(scrappedItems, key=lambda x: x["savings"], reverse=True)
    
    updatedItems = updateWishList(scrappedItems)
    if len(updatedItems) > 0:
        print(f"{dt_string} ********************************************** {len(updatedItems)} ITEMS UPDATED ************************")
        printItems(updatedItems)

    filteredItems = filterUpdates(updatedItems)
    if len(filteredItems) > 0:
        print(f"{dt_string} ********************************************** {len(filteredItems)} ITEMS NOTIFIED **********************")
        printItemsTitles(filteredItems)
        notifyUpdates(filteredItems)


def scrapeURLs(urls):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    scrappedItems = []

    for url in urls:
        #print(f"{dt_string} Scraping - {url}")

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
