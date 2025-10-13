import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from jproperties import Properties
import locale
import re
import random

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


from datetime import datetime

import sched, time

wish_list = {}
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except locale.Error as e:
    print(f"Could not set locale: {e}. Prices will be displayed without currency formatting.")

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

used_condition_keywords = configs.get("used.condition.keywords").data.split(',')

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


def findPrice(soup):
    
    try:
        pinned_offer = soup.select_one("#aod-pinned-offer")
        if not pinned_offer:
            return None
        price_whole_element = pinned_offer.select_one('span.a-price-whole')
        price_fraction_element = pinned_offer.select_one('span.a-price-fraction')
        
        if price_whole_element:
            price_whole_text = price_whole_element.get_text(strip=True).replace(',', '')
            price_fraction_text = price_fraction_element.get_text(strip=True)
            full_price_float = float(f"{price_whole_text}.{price_fraction_text}")

            if full_price_float:
                return float(full_price_float)

    except (AttributeError, ValueError) as e:
        print(f"Could not find or parse used price: {e}")

    return None

def findUsedPrice(soup):
    """
    Finds the best used price from the offer listing page.
    """
    try:
        offer_list = soup.select_one("#aod-offer-list")
        if not offer_list:
            return None
        offers = offer_list.select("#aod-offer")
        for offer in offers:
            condition_element = offer.select_one("#aod-offer-heading span.a-text-bold")
            if condition_element and "De 2ª mano" in condition_element.get_text(strip=True):
                price_whole_element = offer.select_one('span.a-price-whole')
                price_fraction_element = offer.select_one('span.a-price-fraction')
                if price_whole_element:
                    price_whole_text = price_whole_element.get_text(strip=True).replace(',', '')
                    price_fraction_text = price_fraction_element.get_text(strip=True)
                    full_price_float = float(f"{price_whole_text}.{price_fraction_text}")

                    if full_price_float:
                        return float(full_price_float)

    except (AttributeError, ValueError) as e:
        print(f"Could not find or parse used price: {e}")

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
    
def scrape_wishlist_page(items):
    notification_list = []
    scrappedItems = []
    base_url = "https://www.amazon.es"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for item in items:
            #price = findPrice(item)
            url = findURLtoITEM(item, base_url)
            priceUsed = None
            price = None

            if url:
                try:
                    match = re.search(r'/dp/([A-Z0-9]{10})', url)
                    if match:
                        asin = match.group(1)
                        offer_url = f"{base_url}/gp/offer-listing/{asin}/ref=dp_olp_used?ie=UTF8&condition=used"
                        page.goto(offer_url, wait_until="load", timeout=60000)
                        offer_content = page.content()
                        offer_soup = BeautifulSoup(offer_content, "html.parser")
                        price = findPrice(offer_soup)
                        priceUsed = findUsedPrice(offer_soup)
                except PlaywrightTimeoutError:
                    print(f"Timeout while trying to load page for {url}")
                except Exception as e:
                    print(f"An unexpected error occurred while scraping used price for {url}: {e}")

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
            
            # Generate a random float between 5 and 15
            random_delay = random.uniform(5, 15)
            # Pause the execution for the random amount of time
            time.sleep(random_delay)


        browser.close()
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
            item["history"]["price"] = item["history"]["price"][:2]
            item["history"]["priceUsed"].insert(0, item["priceUsed"])
            item["history"]["priceUsed"] = item["history"]["priceUsed"][:2]

            item["price"] = newItem["price"]
            item["priceUsed"] = newItem["priceUsed"]
            item["savings"] = newItem["savings"]

            # Update bestUsedPrice if the new used price is better
            if newItem["priceUsed"] is not None:
                if item.get("bestUsedPrice") is None or newItem["priceUsed"] < item["bestUsedPrice"]:
                    item["bestUsedPrice"] = newItem["priceUsed"]

            updatedItems.append(item)

    return updatedItems


def filterUpdates(items):
    filteredItems = []
    for item in items:
        # We only notify if there's a valid used price that meets the savings criteria
        if isSavingsGreaterThanStrategy(item["price"], item["priceUsed"], minSavingsPercentage):
            filteredItems.append(item)
            printItem(item, True)
        else:
            printItem(item, False)

    return filteredItems

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
    if not TOKEN or not chat_id:
        print("Telegram token or chat_id not provided in properties file. Skipping notification.")
        return

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

def printItemsUrls(list_items):
    
    base_url = "https://www.amazon.es"
    print(f"Num of items {len(list_items)}")
    for item in list_items:
                    url = findURLtoITEM(item, base_url)

                    match = re.search(r'/dp/([A-Z0-9]{10})', url)
                    asin = match.group(1)
                    print(f"{base_url}/gp/offer-listing/{asin}/ref=dp_olp_used?ie=UTF8&condition=used")

def scrape_wishlists(urls):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for url in urls:
            print(f"Scraping {url}")
            try:
                page.goto(url, wait_until="load", timeout=60000)
                html_text = page.content()
                soup = BeautifulSoup(html_text, "html.parser")
                
                list_items = soup.find_all(attrs={"data-itemid": True})
                printItemsUrls(list_items)
                
                items.extend(list_items)
                
                
            except PlaywrightTimeoutError:
                print(f"Timeout while trying to load wishlist {url}")
                continue
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue

        browser.close()
    return items


if __name__ == "__main__":
    s = sched.scheduler(time.time, time.sleep)
    
    print("Scraping wishlist items...")
    items = scrape_wishlists(wishlistURLs)
        
    def main(sc, items):
        
        
        scrappedItems = scrape_wishlist_page(items)
        scrappedItems.extend(scrappedItems)

        # First, clean up any items that are no longer on the wishlist
        cleanupRemovedItems(scrappedItems)

        # Then, update the price history for the remaining items
        updatedItems = updateWishList(scrappedItems)

        # Filter for items with significant price drops
        filteredItems = filterUpdates(updatedItems)
        print(f"Number of items to notify: {len(filteredItems)}") 

        # Notify if there are any items that meet the criteria
        if filteredItems:
            notifyUpdates(filteredItems)

        print("Check complete.")
        s.enter(300, 1, main, (sc, items))

    s.enter(1, 1, main, (s,items))
    s.run()
    main(s)
