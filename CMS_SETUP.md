# Expanded Landing Page CMS

## Apply the database update

From the `project` directory:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The project keeps the MySQL connection already configured in
`project/settings.py`.

## Manage page content

1. Sign in as the administrator of an approved business.
2. Open **Page CMS** from the dashboard.
3. Add hero slides, promotions, features, maximise steps, FAQs, success
   stories, and dealer locations.
4. Use the same screen to save Facebook, Instagram, LinkedIn, X/Twitter and
   Google Maps embed links.
5. Services, products and customer feedback remain available from their
   dedicated managers linked at the top of Page CMS.
6. Subscription plans are created by the super admin and are rendered from
   active `Plan` database rows.
7. Open the public business page and choose **Customize Page** to change
   colors, copy and section visibility.

Empty CMS collections do not render placeholder claims on the public page.
The new migration is:

```text
app/migrations/0026_expanded_landing_page_cms.py
```

## Google Maps

In Google Maps choose **Share → Embed a map**. Copy only the `src` URL from
the iframe and save it under **Footer, Social Media & Google Map**.

## Nearest dealer

Add both latitude and longitude to dealer records to enable the public
**Find nearest** button. Location is requested only after the visitor presses
the button; distance sorting runs in the browser.
