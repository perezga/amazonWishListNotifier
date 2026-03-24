import random
import time
from jproperties import Properties
import locale
import re
import os

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from api.models import SessionLocal, Item, PriceHistory, Notification, Wishlist, Setting


from datetime import datetime

import sched, time

# Database initialization and migrations are now handled by Alembic on container startup

wish_list = {}
notified_items = {}
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except locale.Error as e:
    print(f"Could not set locale: {e}. Prices will be displayed without currency formatting.")

configs: Properties = Properties()
properties_path = os.path.join(os.path.dirname(__file__), 'amazonPriceUpdateNotifier.properties')
with open(properties_path, 'rb') as config_file:
    configs.load(config_file)

#Add as many comma separated wish lists as you desire
# wishlistURLs = configs.get("wishlist.urls").data.split(",") if configs.get("wishlist.urls") else []
wishlistURLs = []

#telegram
TOKEN = os.environ.get("TELEGRAM_TOKEN", configs.get("telegram.token").data if configs.get("telegram.token") else None)
chat_id = os.environ.get("TELEGRAM_CHAT_ID", configs.get("telegram.chatid").data if configs.get("telegram.chatid") else None)

def get_min_savings_percentage():
    session = SessionLocal()
    try:
        setting = session.query(Setting).filter(Setting.key == "min_savings_percentage").first()
        if setting:
            return float(setting.value)
    except Exception as e:
        print(f"Error fetching min_savings_percentage from DB: {e}")
    finally:
        session.close()
    
    # Fallback to properties file or default
    try:
        return float(configs.get("notification.savings.percentage").data)
    except:
        return 0.10

#Maximum historical data points to keep per item.
historyLimit = int(configs.get("history.limit").data) if configs.get("history.limit") else 100

used_condition_keywords = configs.get("used.condition.keywords").data.split(',')

def findTitle(item):
    try:
        itemId = findId(item)
        title_element = item.find("a", id=f"itemName_{itemId}")
        if title_element and title_element.has_attr('title'):
            return title_element["title"]
        else:
            print(f"Title attribute not found for item {itemId}")
            return "Title not found"
    except (TypeError, KeyError) as e:
        itemId = item.get("data-itemid", item.get("id", "item_N/A").replace("item_", ""))
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
            price_whole_text = price_whole_element.get_text(strip=True).replace(',', '').replace('.', '')
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
                    price_whole_text = price_whole_element.get_text(strip=True).replace(',', '').replace('.', '')
                    price_fraction_text = price_fraction_element.get_text(strip=True)
                    full_price_float = float(f"{price_whole_text}.{price_fraction_text}")

                    if full_price_float:
                        return float(full_price_float)

    except (AttributeError, ValueError) as e:
        print(f"Could not find or parse used price: {e}")

    return None


def findId(item):
    if item.has_attr("data-itemid"):
        return item["data-itemid"]
    if item.has_attr("id") and item["id"].startswith("item_"):
        return item["id"].replace("item_", "")
    return "N/A"
    
def findURLtoITEM(item, base_url):
    itemId = findId(item)
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
        itemsMap[findId(item)] = item

    return itemsMap


def cleanupRemovedItems(items):
    session = SessionLocal()
    try:
        for wishItem in wish_list.copy().values():
            itemId = wishItem["id"]

            if not findItem(items, itemId):
                print(f"Removing {wishItem['title'][:50]} (ID: {itemId}) from database and memory.")
                
                # 1. Delete from DB (cascades to PriceHistory and Notifications)
                db_item = session.query(Item).filter(Item.id == itemId).first()
                if db_item:
                    session.delete(db_item)
                
                # 2. Delete from in-memory list
                del wish_list[itemId]
        
        session.commit()
    except Exception as e:
        print(f"Error cleaning up removed items from database: {e}")
        session.rollback()
    finally:
        session.close()


def findItem(items, wishItemId):
    found = False
    for item in items:
        if wishItemId == item["id"]:
            found = True
            break
    return found


def escape_markdown_v2(text):
    """Escapes characters for Telegram's MarkdownV2 format."""
    # Chars to escape: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'([_*\[\]()~`>#\+\-=|{}.!])'
    return re.sub(escape_chars, r'\\\1', text)


def buildBody(items):
    body = ""
    for item in items:
        title = item["title"]
        # Truncate title to max 25 characters
        truncated_title = (title[:22] + '...') if len(title) > 25 else title
        escaped_title = escape_markdown_v2(truncated_title)

        url = escape_markdown_v2(item["url"].split('?')[0])
        price = item["price"]
        priceUsed = item["priceUsed"]
        savings = item['savings']

        # Line 1: Plain, truncated title as a link. [text](url)
        body += f"[{escaped_title}]({url})\n"

        # Line 2: Price, Used Price, and Savings
        price_str = escape_markdown_v2(f"Price: {locale.currency(price, grouping=True) if price else 'N/A'}")
        used_price_str = escape_markdown_v2(f"Used: {locale.currency(priceUsed, grouping=True) if priceUsed else 'N/A'}")
        savings_str = escape_markdown_v2(f"Savings: {savings:.2f}%".strip())

        separator = escape_markdown_v2(" | ")
        body += f"{price_str}{separator}{used_price_str}{separator}{savings_str}\n\n"

    return body.strip()
    
import os

def findImageURL(item):
    try:
        itemId = findId(item)
        # Try to find by id first
        img_element = item.find("img", id=f"itemImage_{itemId}")
        if img_element and img_element.has_attr('src'):
            return img_element["src"]
        
        # Fallback to any img in the item
        img_element = item.find("img")
        if img_element and img_element.has_attr('src'):
            return img_element["src"]
    except Exception as e:
        print(f"Could not find image for item {itemId}: {e}")
    return None

def scrape_wishlist_page(wishlist_mapping):
    notification_list = []
    scrappedItems = []
    base_url = "https://www.amazon.es"
    
    print(f"Scraping detailed info for {sum(len(v['items']) for v in wishlist_mapping.values())} items...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for url, wishlist_data in wishlist_mapping.items():
                items = wishlist_data["items"]
                for item in items:
                    # Random user agent and delay for each item
                    context = browser.new_context(user_agent=random.choice(USER_AGENTS))
                    page = context.new_page()
                    
                    #price = findPrice(item)
                    item_url = findURLtoITEM(item, base_url)
                    priceUsed = None
                    price = None

                    if item_url:
                        try:
                            # Random sleep between 1-3 seconds before each item
                            time.sleep(random.uniform(1.0, 3.0))
                            
                            match = re.search(r'/dp/([A-Z0-9]{10})', item_url)
                            if match:
                                asin = match.group(1)
                                offer_url = f"{base_url}/dp/{asin}/?aod=1&th=1"
                                page.goto(offer_url, wait_until="load", timeout=60000)
                                
                                # Randomise the wait time slightly
                                page.wait_for_timeout(random.randint(10000, 20000))
                                
                                offer_content = page.content()
                                offer_soup = BeautifulSoup(offer_content, "html.parser")
                                price = findPrice(offer_soup)                        
                                priceUsed = findUsedPrice(offer_soup)
                        except PlaywrightTimeoutError:
                            print(f"Timeout while trying to load page for {item_url}")
                        except Exception as e:
                            print(f"An unexpected error occurred processing {item_url}: {e}")
                        finally:
                            page.close()
                            context.close()

                    savings = float(f"{100 - (priceUsed/price)*100:.2f}") if priceUsed and price and price > 0 else float(0)

                    scrappedItem = {
                        "id": findId(item),
                        "title": findTitle(item),
                        "price": price,
                        "priceUsed": priceUsed,
                        "history": {"price": [], "priceUsed": []},
                        "savings": savings,
                        "bestUsedPrice": priceUsed,
                        "url": item_url,
                        "imageURL": findImageURL(item),
                        "wishlist_url": url,
                        "wishlist_name": wishlist_data["name"]
                    }

                    scrappedItems.append(scrappedItem)

        finally:
            browser.close()    
    return scrappedItems


def enforce_ilm_policy(session, item_id, max_history=None):
    """Deletes oldest price history entries, keeping only the most recent 'max_history'."""
    if max_history is None:
        max_history = historyLimit
    try:
        # Get history entries ordered by timestamp DESC
        history_to_keep = session.query(PriceHistory.id)\
            .filter(PriceHistory.item_id == item_id)\
            .order_by(PriceHistory.timestamp.desc())\
            .limit(max_history)\
            .all()
        
        keep_ids = [h.id for h in history_to_keep]
        
        # Delete entries not in the top N
        if keep_ids:
            session.query(PriceHistory)\
                .filter(PriceHistory.item_id == item_id)\
                .filter(PriceHistory.id.notin_(keep_ids))\
                .delete(synchronize_session=False)
    except Exception as e:
        print(f"Error enforcing ILM policy for item {item_id}: {e}")

def run_ilm_cleanup(sc):
    """Periodically cleans up old price history for all items."""
    print("Running daily ILM cleanup...")
    session = SessionLocal()
    try:
        items = session.query(Item).all()
        for item in items:
            enforce_ilm_policy(session, item.id)
        session.commit()
    except Exception as e:
        print(f"Error during ILM cleanup: {e}")
        session.rollback()
    finally:
        session.close()
    
    # Schedule the next run in 24 hours (86400 seconds)
    sc.enter(86400, 1, run_ilm_cleanup, (sc,))

def updateWishList(newItems):
    updatedItems = []
    session = SessionLocal()
    try:
        for newItem in newItems:
            itemId = newItem["id"]
            
            # Update/Create Wishlist
            wishlist = session.query(Wishlist).filter(Wishlist.url == newItem["wishlist_url"]).first()
            if not wishlist:
                wishlist = Wishlist(url=newItem["wishlist_url"], name=newItem["wishlist_name"])
                session.add(wishlist)
                session.flush() # Get ID
            elif wishlist.name != newItem["wishlist_name"]:
                wishlist.name = newItem["wishlist_name"]

            # 1. Update/Create Item in DB
            db_item = session.query(Item).filter(Item.id == itemId).first()
            if not db_item:
                db_item = Item(id=itemId)
                session.add(db_item)
            
            db_item.title = newItem["title"]
            db_item.url = newItem["url"]
            db_item.image_url = newItem["imageURL"]
            db_item.wishlist_id = wishlist.id
            
            if newItem["priceUsed"] is not None:
                if db_item.best_used_price is None or newItem["priceUsed"] < db_item.best_used_price:
                    db_item.best_used_price = newItem["priceUsed"]

            # 2. Add Price History Entry ONLY if price changed
            latest_history = session.query(PriceHistory)\
                .filter(PriceHistory.item_id == itemId)\
                .order_by(PriceHistory.timestamp.desc())\
                .first()
            
            if not latest_history or latest_history.price != newItem["price"] or latest_history.price_used != newItem["priceUsed"]:
                history_entry = PriceHistory(
                    item_id=itemId,
                    price=newItem["price"],
                    price_used=newItem["priceUsed"],
                    savings=newItem["savings"],
                    timestamp=datetime.now()
                )
                session.add(history_entry)
            
            # 3. Handle memory-based wish_list (keeping it for existing notification logic)
            item = wish_list.get(itemId)
            if item is None:
                wish_list[itemId] = newItem
                updatedItems.append(newItem)
            else:
                # Always update these fields in memory
                item["title"] = newItem["title"]
                item["imageURL"] = newItem["imageURL"]
                item["url"] = newItem["url"]
                item["wishlist_url"] = newItem["wishlist_url"]
                item["wishlist_name"] = newItem["wishlist_name"]

                if item["price"] != newItem["price"] or item["priceUsed"] != newItem["priceUsed"]:
                    item["history"]["price"].insert(0, item["price"])
                    item["history"]["price"] = item["history"]["price"][:2]
                    item["history"]["priceUsed"].insert(0, item["priceUsed"])
                    item["history"]["priceUsed"] = item["history"]["priceUsed"][:2]

                    item["price"] = newItem["price"]
                    item["priceUsed"] = newItem["priceUsed"]
                    item["savings"] = newItem["savings"]
                    item["bestUsedPrice"] = db_item.best_used_price

                    updatedItems.append(item)
        
        session.commit()
    except Exception as e:
        print(f"Error updating database: {e}")
        session.rollback()
    finally:
        session.close()

    return updatedItems


def filterUpdates(items, min_savings):
    filteredItems = []
    for item in items:
        # We only notify if there's a valid used price that meets the savings criteria
        if isSavingsGreaterThanStrategy(item["price"], item["priceUsed"], min_savings):
            filteredItems.append(item)
            printItem(item, True)
        else:
            printItem(item, False)

    return filteredItems


def filter_duplicate_notifications(items):
    non_duplicate_items = []
    for item in items:
        item_id = item["id"]
        notified_item = notified_items.get(item_id)

        if notified_item and notified_item.get("price") == item["price"] and notified_item.get("priceUsed") == item["priceUsed"]:
            dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            print(f"{dt_string} {'SKIPPING DUPLICATE'} {item['title'][0:50]:55}")
        else:
            non_duplicate_items.append(item)

    return non_duplicate_items

# True only if Used price is X percent smaller than the normal price.
#Where X is minSavingsPercentage
def isSavingsGreaterThanStrategy(price, priceUsed, minSavingsPercentage):
    if price and priceUsed:
        if price > priceUsed:
            return True if (price - (minSavingsPercentage * price)) > priceUsed else False 
    else:
        return False



def store_notified_item(items):
    for item in items:
        notified_items[item["id"]] = {
            "price": item["price"],
            "priceUsed": item["priceUsed"]
        }

def notifyUpdates(items):
    # if not empty
    if items:
        body = buildBody(items)
        sendTelegram(body)
        saveNotifications(items)

def saveNotifications(items):
    session = SessionLocal()
    try:
        for item in items:
            notification = Notification(
                item_id=item["id"],
                title=item["title"],
                message=f"Price drop! Current price: {item['price']}, Used price: {item['priceUsed']}, Savings: {item['savings']}%",
                price=item["priceUsed"] if item["priceUsed"] else item["price"]
            )
            session.add(notification)
        session.commit()
    except Exception as e:
        print(f"Error saving notifications to DB: {e}")
        session.rollback()
    finally:
        session.close()

def sendTelegram(body):
    if not TOKEN or not chat_id:
        print("Telegram token or chat_id not provided in properties file. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&disable_web_page_preview=true&parse_mode=MarkdownV2&text={body}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        #print("Telegram notification sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram notification: {e}")
       
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
    #print(f"Num of items {len(list_items)}")
    for item in list_items:
                    url = findURLtoITEM(item, base_url)

                    match = re.search(r'/dp/([A-Z0-9]{10})', url)
                    asin = match.group(1)
      #              print(f"{base_url}/gp/offer-listing/{asin}/ref=dp_olp_used?ie=UTF8&condition=used")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0",
]

def scrape_wishlists(urls=None):
    if urls is None:
        urls = []
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    wishlist_mapping = {}
    
    # 1. Fetch URLs from Database
    session = SessionLocal()
    try:
        db_urls = [w.url for w in session.query(Wishlist).all()]
    except Exception as e:
        print(f"Error fetching wishlists from DB: {e}")
        db_urls = []
    finally:
        session.close()

    all_urls = list(set(urls + db_urls))
    print(f"Scraping {len(all_urls)} URLs: {all_urls}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a random user agent for the browser context
        context = browser.new_context(user_agent=random.choice(USER_AGENTS), viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        # Stealth: Visit homepage first to set cookies
        print("Visiting Amazon homepage for cookies...")
        try:
            page.goto("https://www.amazon.es/", wait_until="load", timeout=60000)
            time.sleep(random.uniform(3.0, 5.0))
        except Exception as e:
            print(f"Error visiting homepage: {e}")

        for url in all_urls:
            print(f"Loading wishlist URL: {url}")
            try:
                # Add a small random jitter delay between wishlist scrapes
                time.sleep(random.uniform(2.0, 5.0))
                
                page.goto(url, wait_until="load", timeout=60000)
                print(f"Page loaded for {url}")
                # Wait a bit for JS to execute
                time.sleep(2)
                
                html_text = page.content()
                soup = BeautifulSoup(html_text, "html.parser")
                
                # Try to find wishlist name
                wishlist_name = soup.find("span", id="profile-list-name")
                if wishlist_name:
                    wishlist_name = wishlist_name.get_text(strip=True)
                else:
                    wishlist_name = url.split("/")[-1] # Fallback to part of URL

                list_items = soup.find_all(attrs={"data-itemid": True})
                if not list_items:
                    list_items = soup.find_all(lambda tag: tag.name in ["div", "li"] and tag.has_attr("id") and tag["id"].startswith("item_") and "itemName_" not in tag["id"])
                
                print(f"Found {len(list_items)} items in wishlist: {wishlist_name}")
                
                wishlist_mapping[url] = {
                    "name": wishlist_name,
                    "items": list_items
                }
                
            except PlaywrightTimeoutError:
                print(f"Timeout while trying to load wishlist {url}")
                continue
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue

        browser.close()
    return wishlist_mapping


if __name__ == "__main__":
    s = sched.scheduler(time.time, time.sleep)

    sendTelegram("Amazon Notification service RESTARTING")

    print("Scraping wishlist...")
    try:
        wishlist_mapping = scrape_wishlists(wishlistURLs)
    except Exception as e:
        print(f"CRITICAL ERROR in initial scrape_wishlists: {e}")
        import traceback
        traceback.print_exc()
        wishlist_mapping = {}
        
    # The main function now accepts an 'iteration_count'
    def main(sc, wishlist_mapping, iteration_count):
        print(f"Entering main iteration {iteration_count}...")
        
        # Every 10 iterations, re-scrape the main wishlist URLs to find new or removed items
        if iteration_count > 0 and iteration_count % 10 == 0:
            print("Refreshing full wishlist...")
            wishlist_mapping = scrape_wishlists(wishlistURLs)
            
        scrappedItems = scrape_wishlist_page(wishlist_mapping)

        # First, clean up any items that are no longer on the wishlist
        cleanupRemovedItems(scrappedItems)

        # Then, update the price history for the remaining items
        updatedItems = updateWishList(scrappedItems)

        # Dynamic Fetch of min_savings
        current_min_savings = get_min_savings_percentage()

        # Filter for items with significant price drops
        filteredItems = filterUpdates(updatedItems, current_min_savings)
        #print(f"Number of items to notify: {len(filteredItems)}")

        non_duplicate_items = filter_duplicate_notifications(filteredItems)

        # Notify if there are any items that meet the criteria
        if len(non_duplicate_items) > 0:
            notifyUpdates(non_duplicate_items)
            store_notified_item(non_duplicate_items)

        #print("Check complete.")
        # Schedule the next run and increment the iteration_count
        s.enter(20, 1, main, (sc, wishlist_mapping, iteration_count + 1))

    # Schedule the first run with iteration_count starting at 1
    s.enter(1, 1, main, (s, wishlist_mapping, 1))
    
    # Schedule the first ILM cleanup to run shortly after start
    s.enter(5, 1, run_ilm_cleanup, (s,))

    s.run()
