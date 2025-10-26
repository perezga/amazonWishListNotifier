Script writen in Python to notify price changes of Products added in your Amazon wishlists.

*An email is sent to your inbox when a Product has a savings percentage of X between the normal Price and the Used price.*

**Prerequisites**

    Python version 3+

**Instructions**

    1 - Create a property file amazonPriceUpdateNotifier.properties in the same location as amazonPriceUpdateNotifier.py

        #comma separated list of wishlists (Create a wishlist in amazon and copy/paste the url)
        wishlist.urls=
        
        #TELEGRAM|EMAIL
        notification_method=TELEGRAM
        
        #telegram configuration (follow instruction here https://medium.com/codex/using-python-to-send-telegram-messages-in-3-simple-steps-419a8b5e5e2)
        telegram.token=
        telegram.chatid=

        #email configuration
        email.username=<your username>  
        email.password=<your password>  
        email.to=<your inbox>  
        email.host=smtp.gmail.com  
        email.port=465  
        email.from=priceupdate@amazon.priceupdate.notification.com
        email.subject="Amazon price change notification

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
