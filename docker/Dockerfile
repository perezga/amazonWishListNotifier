# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Instala locales
RUN apt-get update && apt-get install -y locales \
    && rm -rf /var/lib/apt/lists/* \
    # Descomenta los locales que necesitas
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen \
    # Regenera los locales
    && locale-gen

# Establece las variables de entorno
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps

# Copy the rest of the application's code
COPY . .

# Set entrypoint
RUN chmod +x docker/entrypoint.sh
ENTRYPOINT ["docker/entrypoint.sh"]

# Command to run the application
CMD ["python", "scraper/amazonPriceUpdateNotification.py"]
