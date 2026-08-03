# Profiler Discovery Upgrade

## Public URL

Open the marketplace at:

```text
/discover/
```

Category pages continue to use:

```text
/discover/<category-slug>/
```

## Included in this release

- Responsive marketplace homepage for desktop, tablet and mobile.
- Search across business names, descriptions, categories, sub-categories,
  services and products.
- City, category, verified-only and sorting controls.
- AJAX result updates with normal server-rendered form fallback.
- Only active, super-admin-approved businesses are displayed.
- Accurate approved-business counts for categories, cities and platform stats.
- Query optimization using `select_related()` and filtered service prefetching.
- Direct Call, WhatsApp and View Profile actions.
- WhatsApp actions reuse the existing analytics endpoint.
- Compact mobile category carousel and sticky registration action.
- Empty, loading and pagination states.

## Database changes

No database migration is required for this upgrade.

## Validation

Run:

```bash
python manage.py check
python manage.py test app
```

The project test settings use SQLite and are available at
`project/test_settings.py`.
