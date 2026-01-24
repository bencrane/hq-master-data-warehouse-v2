-- Export all records from location_lookup
SELECT location_name, city, state, country, has_city, has_state, has_country
FROM reference.location_lookup
ORDER BY location_name;
