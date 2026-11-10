# Protein Price Checks

Date of checks: 2026-11-10 · Currency: EUR · Prices incl. VAT, excl. shipping unless noted.

Automated checks run twice daily at 09:00 and 21:00 via `check_prices.py`; see
[README.md](README.md).

| # | Brand / Store | Product | Variant checked | Original price | Sale price | Unit price | Method used |
|---|---------------|---------|-----------------|----------------|------------|------------|-------------|
| 1 | Bulk (bulk.com/de) | Pure Whey Protein | 2.5 kg, Vanille / Neutral | €99.99 | **€89.99** (−€10.00) | €36.00/kg | Provided GraphQL `cs-graphql` `REFINE_PRODUCT_QUERY` curl; decoded size option IDs, refined with 2.5 kg option `Y29uZmlndXJhYmxlLzE3OS8zMw==` |
| 2 | MyProtein (de.myprotein.com) | Impact Whey Protein | 2.7 kg – 90 servings (Vanille, SKU 17712192) | €124.99 (RRP) | **€96.49** (−€28.50) | €35.74/kg | Provided `POST /api/operation/FBT/` curl (sku 10530943); parsed `.data.product.variants`, filtered `Amount = 2.7kg`. Note: some 2700 g milkshake flavours are €78.99 |
| 3 | HSN (hsnstore.eu) | EvoWhey Protein | 2 kg, Strawberry & Banana / Banana | €89.99 | **€59.99** (−33%, −€30.00) | €30.00/kg | Direct curl + WebFetch returned 403 (WAF); rendered via `r.jina.ai` reader proxy. Confirmed 2 Kg size option on the 500 g product page and on the 2 kg product URLs |
| 4 | ESN (esn.com) | Basic Whey | 2000 g pouch, Chocolate (variant 53658660241676) | — | **€65.90** | €32.95/kg | Store is Shopify; rendered via `r.jina.ai` reader proxy and read the variant price/selector. 1000 g pouch was sold out |
| 5 | PBN (Amazon.de) | PBN Whey Protein | 2.27 kg (ASIN B08L75XNXP) | — | **€81.81** | €36.04/kg | Provided Amazon twister AJAX curl `/gp/product/ajax/twisterDimensionSlotsDefault`; parsed streaming JSON `twisterSlotJson.price` / `twisterSlotDiv` per ASIN. 1 kg ASIN B08L75PF9N = €45.60 |
| 6 | Optimum Nutrition (Amazon.de) | Gold Standard 100% Whey | 2.27 kg (ASIN B0015R3AOA) | — | **€109.99** | €48.24/kg | Provided Amazon twister AJAX curl `/gp/product/ajax/twisterDimensionSlotsDefault`; parsed streaming JSON per ASIN. Variants B07G46TFL9 and B00OLSNOBE same price (€48.45/kg) |

## Method notes

- **Provided curl commands** (Bulk, MyProtein, Amazon/PBN): executed and piped to `jq`/`grep` for read-only parsing.
- **GraphQL (Bulk)**: the response's size option list was decoded (Base64 option IDs) to identify the 2.5 kg option, then a second `refineProduct` query returned the exact price.
- **Variant APIs (MyProtein/Amazon)**: price is not on the parent product; extracted from the variant/ASIN payload for the requested size.
- **HTML pages (HSN, ESN)**: direct requests were blocked (403) or JS-heavy, so pages were rendered through the `r.jina.ai` reader proxy and the size selector/prices were read from the resulting Markdown.
- **Caveats**: prices are point-in-time (2026-11-10) and may change; Bulk/MyProtein/Amazon prices are offer-dependent; HSN showed a "flash sale ended" state.

## Retailer verification

- `optimumnutrition.com` is the official Optimum Nutrition site.
- `opnutritionshopde.com` is **not** affiliated with Optimum Nutrition (lookalike
  domain registered 2026-07-06, no legal imprint, `noindex`, "warehouse sale"
  pricing). See [README.md](README.md) for tracked, verified sources.

## Quick comparison (sorted by €/kg, lowest first)

| Brand | Requested size | Unit price | Original price | Sale price |
|-------|----------------|------------|----------------|------------|
| HSN EvoWhey | 2 kg | €30.00/kg | €89.99 | **€59.99** |
| ESN Basic Whey | 2 kg | €32.95/kg | — | **€65.90** |
| MyProtein Impact Whey | 2.7 kg | €35.74/kg | €124.99 | **€96.49** |
| Bulk Pure Whey | 2.5 kg | €36.00/kg | €99.99 | **€89.99** |
| PBN Whey | 2.27 kg | €36.04/kg | — | **€81.81** |
| ON Gold Standard Whey | 2.27 kg | €48.24/kg | — | **€109.99** |
