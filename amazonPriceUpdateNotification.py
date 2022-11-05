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

#Add as many comma separated wish lists as you desire
wishlistURLs = configs.get("wishlist.urls").data.split(",")

notification_method = configs.get("notification_method").data

#telegram
TOKEN = configs.get("telegram.token").data
chat_id = configs.get("telegram.chatid").data

#Email
host = configs.get("email.host").data
port = configs.get("email.port").data
username = configs.get("email.username").data
password = configs.get("email.password").data
emailFrom =  configs.get("email.from").data
emailTo = configs.get("email.to").data

#Minimum savings percentage between normal price and Used price.Used to notify only when that condition meets.
minSavingsPercentage = float(configs.get("notification.savings.percentage").data)

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
    #body = "The following items have updated prices\n\n"
    body = ''
    for item in items:
        title = item["title"][0:25]
        savings = f"{item['savings']}".rjust(6)
        price = item["price"]
        priceOld = item["history"]["price"]
        priceUsed = item["priceUsed"]
        priceUsedOld = item["history"]["priceUsed"]
        bestUsedPrice = item['bestUsedPrice']
        #body += '***********************************\n'
        body += f'{savings}% - {title}\n{locale.currency(price, grouping=True) if price else "N/A"}/{locale.currency(priceUsed, grouping=True) if priceUsed else "N/A"} - Best:{locale.currency(bestUsedPrice, grouping=True) if bestUsedPrice else "-"}\n'
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
            "savings": float(f"{100 - (priceUsed/price)*100:.2f}") if priceUsed and price else float(0),
            "bestUsedPrice": priceUsed
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
            item["history"]["price"] = item["history"]["price"][0:2]
            item["history"]["priceUsed"].insert(0, item["priceUsed"])
            item["history"]["priceUsed"] = item["history"]["priceUsed"][0:2]
            item["price"] = newItem["price"]
            item["priceUsed"] = newItem["priceUsed"]
            item["savings"] = newItem["savings"]
            item["bestUsedPrice"] = newItem["priceUsed"] if (newItem["priceUsed"] is not None and (item["bestUsedPrice"] is None or newItem["priceUsed"] < item["bestUsedPrice"])) else item["bestUsedPrice"]
            updatedItems.append(item)

    return updatedItems


def filterUpdates(items):
    filteredItems = []
    for item in items:
        priceUsedNew = item["priceUsed"]
        priceUsedOld = item["history"]["priceUsed"][0] if len(item["history"]["priceUsed"]) > 0 else None
        priceNew = item["price"]
        priceOld = item["history"]["price"][0] if len(item["history"]["price"]) > 0 else None

        #if isSmallerPriceStrategy(priceUsedNew, priceUsedOld) or isSmallerPrice(priceNew, priceOld):
        if isSavingsGreaterThanStrategy(priceNew, priceUsedNew, minSavingsPercentage):        
            filteredItems.append(item)
            printItem(item, True)
        else:
            printItem(item, False)

    return filteredItems

# True if PriceUsed is not set or when any of New or Old prices is smaller than its previous value.
def isSmallerPriceStrategy(priceUsedNew, priceUsedOld):
    if priceUsedNew and priceUsedOld:
        if priceUsedOld > priceUsedNew:
            return True
    elif priceUsedNew and not priceUsedOld:
        return True
    else:
        return False

# True only if Used price is X percent smaller than the normal price.
#Where X is minSavingsPercentage
def isSavingsGreaterThanStrategy(price, priceUsed, minSavingsPercentage):
    if price and priceUsed:
        if price > priceUsed:
            return True if (price - (minSavingsPercentage * price)) > priceUsed else False 
    else:
        return False



def notifyUpdates(items):
    # if not empty
    if items:
        body = buildBody(items)
        match notification_method:
            case "TELEGRAM":
                sendTelegram(body)
            case "EMAIL":
                sendEmail(body)
            case _:
                print("Set a notification method TELEGRAM|EMAIL in properties")

def sendTelegram(body):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={body}"
    requests.get(url).json()
       
def sendEmail(body):
    text_type = 'plain'  # or 'html'
    
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

    return f"AMAZON{numItems}): {title}...({priceLocale}/{priceUsedLocale})"

def printItems(items):
    for item in items:
        printItem(item, False)
        
def printItem(item, isSent):
    savings = f"{item['savings']}".rjust(6)
    price = f"{item['price']}".rjust(7)
    used = f"{item['priceUsed']}".rjust(7)
    bestUsedPrice = f"{item['bestUsedPrice']}".rjust(7)
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print(f"{dt_string} {'NOTIFIED' if isSent else '        '} {item['title'][0:50]:55}\tsavings:{savings}% \tprice:{price} \tused: {used}\tbestUsed:{bestUsedPrice}\tHistory(price/used): {item['history']['price']}/{item['history']['priceUsed']}")
    	
def printItemsTitles(items):
    for item in items:
    	print(f"{item['title'][0:60]:60}")

def browse_and_scrape(urls):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    scrappedItems = scrapeURLs(urls)
    #print(f"{dt_string} Number of items scrapped {len(scrappedItems)}")

    scrappedItems = sorted(scrappedItems, key=lambda x: x["savings"], reverse=True)
    
    updatedItems = updateWishList(scrappedItems)
    filteredItems = filterUpdates(updatedItems)
    if len(filteredItems) > 0:
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
