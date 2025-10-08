Usage:
Run the scraper:
python idealista_scraper.py
Project Structure:
data/bronze/idealista/    - Output CSV files
config/idealista/         - Configuration files
logs/                     - Scraping and error logs

Configuration:
Edit JSON files in config/idealista/ for:
cities.json - Target cities
operations.json - Sale/rent operations
property_types.json - Types of properties
url_mapping.json - Parameter mappings

Output:
The scraper generates CSV files with the following fields:
listing_id, url, scraped_at, operation, property_type, city
title, price, area, bedrooms, bathrooms, location
description, property_type_detail, update_date
agency, energy_certificate

Note:
This is a development version. Currently processes listings from the first page with full data extraction. Pagination functionality is under active development.


