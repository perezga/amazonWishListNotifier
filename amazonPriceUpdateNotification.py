import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from jproperties import Properties
import locale
import re

import requests
from bs4 import BeautifulSoup

from datetime import datetime

import sched, time

wish_list = {}
#locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')

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
    try:
        itemId = item["data-itemid"]
        title_element = item.find("a", id=f"itemName_{itemId}")
        if title_element and title_element.has_attr('title'):
            return title_element["title"]
        else:
            print(f"Title attribute not found for item {itemId}")
            return "Title not found"
    except (TypeError, KeyError) as e:
        itemId = item.get("data-itemid", "N/A")
        print(f"Could not find title for item {itemId}: {e}")
        return "Title not found"


def findPrice(item):
    price_str = item.get('data-price')
    itemId = item.get("data-itemid", "N/A")
    if not price_str or price_str == "-Infinity":
        # This is not an error, just means the item might be unavailable
        # print(f"Price not available for item {itemId}.")
        return None
    try:
        # The data-price attribute uses a period as a decimal separator.
        return float(price_str)
    except (ValueError) as e:
        print(f"Could not parse price for item {itemId} from value '{price_str}': {e}")
    return None


def findUsedPrice(soup):
    try:
        # Strategy 1: Look for a link to used offers on the product page.
        # This is often more reliable than a specific element ID.
        used_offer_link = soup.find('a', href=lambda href: href and 'condition=used' in href)
        if used_offer_link:
            price_text = used_offer_link.get_text(strip=True)
            # Find the first number-like pattern in the link text.
            match = re.search(r'[\d\.,]+', price_text)
            if match:
                price_str = match.group(0)
                # Clean the price string
                cleaned_price = price_str.replace(",", ".")
                if cleaned_price.count('.') > 1:
                    cleaned_price = cleaned_price.replace(".", "", cleaned_price.count('.') - 1)
                return float(cleaned_price)

        # Strategy 2: Fallback to the original logic for the all-offers-display page.
        offer_list = soup.find(id="aod-offer-list")
        if offer_list:
            price_span = offer_list.find('span', class_='a-offscreen')
            if price_span and price_span.string:
                usedPrice = price_span.string.strip()
                cleaned_price = usedPrice.replace("€", "").replace("$", "").replace(",", ".").strip()
                if cleaned_price.count('.') > 1:
                    cleaned_price = cleaned_price.replace(".", "", cleaned_price.count('.') - 1)
                return float(cleaned_price)

    except Exception as e:
        print(f"Error parsing used price: {e}")

    return None


def findId(item):
    return item["data-itemid"]
    
def findURLtoITEM(item, base_url):
    itemId = item.get("data-itemid", "N/A")
    try:
        link = item.find("a", id=f"itemName_{itemId}")
        if link and link.has_attr('href'):
            url = link['href']
            # Ensure the URL is absolute
            if url.startswith('/'):
                return f"{base_url}{url}"
            return url
        else:
            print(f"URL not found for item {itemId}")
            return None
    except (TypeError, KeyError) as e:
        print(f"Error finding URL for item {itemId}: {e}")
    return None

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
        itemId = item["id"]
        title = item["title"][0:25]
        savings = f"{item['savings']}".rjust(6)
        price = item["price"]
        priceOld = item["history"]["price"]
        priceUsed = item["priceUsed"]
        priceUsedOld = item["history"]["priceUsed"]
        bestUsedPrice = item['bestUsedPrice']
        url = item["url"]
        #body += '***********************************\n'
        body += f'{savings}% - [{title}]({url})\n({locale.currency(price, grouping=True) if price else "N/A"} -> {locale.currency(priceUsed, grouping=True) if priceUsed else "N/A"}) - Best:{locale.currency(bestUsedPrice, grouping=True) if bestUsedPrice else "-"}\n---------------\n'

    return body


def scrape_wishlist_page(soup, base_url):
    notification_list = []
    scrappedItems = []
    items = soup.find_all(attrs={"data-itemid": True})
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Connection": "keep-alive",
    }
    for item in items:
        price = findPrice(item)
        url = findURLtoITEM(item, base_url)
        priceUsed = None

        if url:
            try:
                product_page_text = requests.get(url, headers=headers).text
                product_soup = BeautifulSoup(product_page_text, "html.parser")
                priceUsed = findUsedPrice(product_soup)
            except requests.exceptions.RequestException as e:
                print(f"Could not fetch product page for {url}: {e}")

        savings = float(f"{100 - (priceUsed/price)*100:.2f}") if priceUsed and price and price > 0 else float(0)

        scrappedItem = {
            "id": findId(item),
            "title": findTitle(item),
            "price": price,
            "priceUsed": priceUsed,
            "history": {"price": [], "priceUsed": []},
            "savings": savings,
            "bestUsedPrice": priceUsed,
            "url": url
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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&disable_web_page_preview=true&parse_mode=Markdown&text={body}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        print("Telegram notification sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram notification: {e}")
       
def sendEmail(body):
    text_type = 'plain'  # or 'html'
    
    try:
        msg = MIMEText(body, text_type, 'utf-8')
        msg['Subject'] = get_subject(items)
        msg['From'] = emailFrom
        msg['To'] = emailTo

        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            server.login(username, password)
            server.send_message(msg)
            print("Email notification sent successfully.")
    except smtplib.SMTPException as e:
        print(f"Failed to send email notification (SMTP Error): {e}")
    except Exception as e:
        print(f"An unexpected error occurred while sending email: {e}")

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

def scrape_wishlists(urls):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    scrappedItems = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Connection": "keep-alive",
    }
    for url in urls:
        try:
            base_url_match = re.search(r"(https?://www\.amazon\.[a-z\.]+)", url)
            if not base_url_match:
                print(f"Could not determine base URL from {url}")
                continue
            base_url = base_url_match.group(1)
            html_text = requests.get(url, headers=headers).text
            soup = BeautifulSoup(html_text, "html.parser")
            items = scrape_wishlist_page(soup, base_url)
            scrappedItems.extend(items)
        except requests.exceptions.RequestException as e:
            print(f"Error scraping {url}: {e}")
            continue
    return scrappedItems


if __name__ == "__main__":
    s = sched.scheduler(time.time, time.sleep)

    def main(sc):
        print("Scraping and checking for price updates...")
        scrappedItems = scrape_wishlists(wishlistURLs)

        # First, clean up any items that are no longer on the wishlist
        cleanupRemovedItems(scrappedItems)

        # Then, update the price history for the remaining items
        updatedItems = updateWishList(scrappedItems)

        # Filter for items with significant price drops
        filteredItems = filterUpdates(updatedItems)

        # Notify if there are any items that meet the criteria
        if filteredItems:
            notifyUpdates(filteredItems)

        print("Check complete. Next check scheduled.")
        s.enter(3600, 1, main, (sc,))

    # Initial call to start the process
    s.enter(1, 1, main, (s,))
    s.run()
