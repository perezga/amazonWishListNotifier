Script writen in Python to notify price changes of Products added in your Amazon wishlists.

*An email is sent to your inbox when a Product has a savings percentage of X between the normal Price and the Used price.*

**Prerequisites**

    Python version 3+

**Instructions**

    1 - Create a property file amazonPriceUpdateNotifier.properties in the same location as amazonPriceUpdateNotifier.py

        #comma separated list of wishlists

        wishlist.urls=

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
