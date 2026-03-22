Script writen in Python to notify price changes of Products added in your Amazon wishlists.

*A Telegram notification is sent to your chat when a Product has a savings percentage of X between the normal Price and the Used price.*

**Prerequisites**

    Python version 3+

**Instructions**

    1 - Configure the properties in `amazonPriceUpdateNotifier.properties` or set them as environment variables.

        Environment variables supported:
        - `TELEGRAM_TOKEN`: Your Telegram Bot API token.
        - `TELEGRAM_CHAT_ID`: Your Telegram chat ID.

        #amazonPriceUpdateNotifier.properties
        #comma separated list of wishlists (Create a wishlist in amazon and copy/paste the url)
        wishlist.urls=
        
        #telegram configuration (can also be set via TELEGRAM_TOKEN and TELEGRAM_CHAT_ID env vars)
        telegram.token=
        telegram.chatid=

        #Minimum savings percentage between normal price and Used price.Used to notify only when that condition meets.
        notification.savings.percentage=0.15

    2 - Run the script amazonPriceUpdateNotifier
        python amazonPriceUpdateNotification.py

## Running with Docker Compose

**Prerequisites**

    Docker and Docker Compose

**Instructions**

    1 - Configure the `amazonPriceUpdateNotifier.properties` file as described above.

    2 - Build and run the container in detached mode:
        docker-compose up --build -d

    3 - To view the logs:
        docker-compose logs -f

    4 - To stop the container:
        docker-compose down
