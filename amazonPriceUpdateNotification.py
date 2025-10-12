import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from jproperties import Properties
import locale
import re

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


def findUsedPriceOnProductPage(soup):
    """
    Finds the used price on the main product page from the 'save with used' block.
    """
    try:
        # Updated selector for the 'save with used' block
        used_price_element = soup.select_one('#usedBuyBox .a-price .a-offscreen, [id*="used_buybox"] .a-price .a-offscreen, #olp-upd-new-used .a-price .a-offscreen')

        if used_price_element:
            price_text = used_price_element.get_text(strip=True)
            price_str = re.sub(r'[^\d,.]', '', price_text)
            if ',' in price_str and '.' in price_str:
                price_str = price_str.replace('.', '').replace(',', '.')
            elif ',' in price_str:
                price_str = price_str.replace(',', '.')

            if price_str:
                return float(price_str)
    except (AttributeError, ValueError) as e:
        print(f"Could not find or parse used price on product page: {e}")

    return None


def findUsedPrice(soup):
    """
    Finds the best used price from the offer listing page.
    """
    try:
        # The new selector for the container of all offers
        offer_list = soup.select_one("#aod-offer-list, #olpOfferList")
        if not offer_list:
            return None

        # The new selector for individual offer containers
        offers = offer_list.select(".aod-offer, .olpOffer")
        for offer in offers:
            # The new selector for the condition text
            condition_element = offer.select_one(".aod-offer-heading, .olpCondition")
            if condition_element and any(keyword in condition_element.get_text(strip=True) for keyword in used_condition_keywords):
                # The new selector for the price
                price_element = offer.select_one(".a-price .a-offscreen, .olpOfferPrice")
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price_str = re.sub(r'[^\d,.]', '', price_text)
                    if ',' in price_str and '.' in price_str:
                        price_str = price_str.replace('.', '').replace(',', '.')
                    elif ',' in price_str:
                        price_str = price_str.replace(',', '.')

                    if price_str:
                        return float(price_str)

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


def scrape_wishlist_page(page, soup, base_url):
    notification_list = []
    scrappedItems = []
    items = soup.find_all(attrs={"data-itemid": True})

    for item in items:
        price = findPrice(item)
        url = findURLtoITEM(item, base_url)
        priceUsed = None

        if url:
            try:
                # First, try to get the used price from the product page itself
                page.goto(url, wait_until="load", timeout=60000)
                product_content = page.content()
                product_soup = BeautifulSoup(product_content, "html.parser")
                priceUsed = findUsedPriceOnProductPage(product_soup)

                # If not found on the product page, check the offer-listing page
                if priceUsed is None:
                    match = re.search(r'/dp/([A-Z0-9]{10})', url)
                    if match:
                        asin = match.group(1)
                        offer_url = f"{base_url}/gp/offer-listing/{asin}/ref=dp_olp_used?ie=UTF8&condition=used"

                        print(f"Scraping used price for {asin} from {offer_url}")
                        page.goto(offer_url, wait_until="load", timeout=60000)
                        offer_content = page.content()
                        offer_soup = BeautifulSoup(offer_content, "html.parser")
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

def scrape_wishlists(urls):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    scrappedItems = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for url in urls:
            try:
                base_url_match = re.search(r"(https?://www\.amazon\.[a-z\.]+)", url)
                if not base_url_match:
                    print(f"Could not determine base URL from {url}")
                    continue
                base_url = base_url_match.group(1)

                page.goto(url, wait_until="load", timeout=60000)
                html_text = page.content()
                soup = BeautifulSoup(html_text, "html.parser")

                items = scrape_wishlist_page(page, soup, base_url)
                scrappedItems.extend(items)
            except PlaywrightTimeoutError:
                print(f"Timeout while trying to load wishlist {url}")
                continue
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue

        browser.close()
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
        print(f"Number of items to notify: {len(filteredItems)}") 

        # Notify if there are any items that meet the criteria
        if filteredItems:
            notifyUpdates(filteredItems)

        print("Check complete.")
        # s.enter(120, 1, main, (sc,))

    # s.enter(1, 1, main, (s,))
    # s.run()
    main(s)