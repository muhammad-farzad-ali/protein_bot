#!/usr/bin/env python3
"""Fetch protein prices and send a report to a Discord webhook.

Usage:
    python3 check_prices.py               # fetch all and send to Discord
    python3 check_prices.py --dry-run     # print the report, do not send
    python3 check_prices.py --changes-only
    python3 check_prices.py --webhook URL

The webhook is read from the DISCORD_WEBHOOK_URL environment variable or a
.env file next to this script.
"""

import argparse
import gzip
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)
STATE_FILE = Path(__file__).with_name("prices_state.json")
DEFAULT_WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"


@dataclass
class Price:
    brand: str
    variant: str
    size_kg: float
    price: float
    currency: str = "EUR"
    regular: float | None = None
    unit_price: float | None = None
    in_stock: bool | None = None
    url: str = ""
    error: str | None = None


def load_env() -> None:
    path = Path(__file__).with_name(".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _request(url, data=None, headers=None, timeout=60, method=None):
    hdrs = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(
        url, data=data, headers=hdrs, method=method or ("POST" if data is not None else "GET")
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")


def get_text(url, headers=None, timeout=60):
    return _request(url, headers=headers, timeout=timeout)


def post_json(url, payload, headers=None, timeout=60):
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    body = json.dumps(payload).encode("utf-8")
    return json.loads(_request(url, data=body, headers=hdrs, timeout=timeout))


def fetch_bulk() -> Price:
    url = "https://www.bulk.com/de/cs-graphql"
    query = (
        "query($o:[String!]!,$s:String!){refineProduct(optionIds:$o,sku:$s){"
        "... on SimpleProductView{name sku price{final{amount{value currency}}"
        "regular{amount{value currency}}}}}}"
    )
    payload = {
        "query": query,
        "variables": {
            "o": ["Y29uZmlndXJhYmxlLzE3OS8zMw==", "Y29uZmlndXJhYmxlLzE3OC8yNg=="],
            "s": "BPB-WPC8-0000",
        },
    }
    headers = {
        "x-api-key": "d3f6d917148f42d5bb7eb7eb3272cf0e",
        "magento-customer-group": "0",
        "magento-environment-id": "bf658f50-a0ce-4baa-b707-a7622f75a311",
        "magento-store-code": "bulkpowders_germany",
        "magento-store-view-code": "bp_germany_view",
        "magento-website-code": "bp_germany",
    }
    data = post_json(url, payload, headers)
    product = data["data"]["refineProduct"]
    price = product["price"]["final"]["amount"]["value"]
    regular = product["price"]["regular"]["amount"]["value"]
    return Price(
        brand="Bulk Pure Whey",
        variant="Vanille",
        size_kg=2.5,
        price=float(price),
        regular=float(regular),
        unit_price=float(price) / 2.5,
        in_stock=True,
        url="https://www.bulk.com/de/products/pure-whey-protein-de/bpb-wpc8-0000",
    )


def fetch_myprotein() -> Price:
    url = "https://de.myprotein.com/api/operation/FBT/"
    payload = {
        "operationName": "FBT",
        "variables": {"currency": "EUR", "shippingDestination": "DE", "sku": 10530943},
    }
    headers = {
        "Accept": "*/*",
        "Content-Type": "text/plain;charset=UTF-8",
        "Origin": "https://de.myprotein.com",
        "Referer": "https://de.myprotein.com/p/sporternahrung/impact-whey-protein/10530943/",
        "x-altitude-instance": "de.myprotein.com",
        "x-horizon-client": "altitude-storefront-nutrition",
    }
    data = post_json(url, payload, headers)
    variants = data["data"]["product"]["variants"]
    variant = next(v for v in variants if v.get("sku") == 17712192)
    price = float(variant["price"]["price"]["amount"])
    rrp = float(variant["price"]["rrp"]["amount"])
    return Price(
        brand="MyProtein Impact Whey",
        variant="Vanille",
        size_kg=2.7,
        price=price,
        regular=rrp,
        unit_price=price / 2.7,
        in_stock=bool(variant.get("inStock")),
        url="https://de.myprotein.com/p/sporternahrung/impact-whey-protein/10530943/?variation=17712192",
    )


def fetch_hsn() -> Price:
    target = (
        "https://www.hsnstore.eu/brands/sport-series/"
        "evowhey-protein-2kg-strawberry-banana"
    )
    text = get_text("https://r.jina.ai/" + target, timeout=90)
    marker = re.search(r"Price/kg:\s*€([\d.]+)", text)
    tail = text[marker.end() : marker.end() + 2500] if marker else text
    match = re.search(r"-?\d+%€(\d+\.\d{2})\s*\n€(\d+\.\d{2})", tail)
    regular = None
    if match:
        regular = float(match.group(1))
        price = float(match.group(2))
    else:
        match = re.search(r"€(\d+\.\d{2})\s*\n-?\d+%", tail)
        if not match:
            raise ValueError("HSN price not found")
        price = float(match.group(1))
    unit = float(marker.group(1)) if marker else price / 2.0
    return Price(
        brand="HSN EvoWhey",
        variant="Strawberry & Banana",
        size_kg=2.0,
        price=price,
        regular=regular,
        unit_price=unit,
        in_stock=True,
        url=target,
    )


def fetch_esn() -> Price:
    target = "https://www.esn.com/en/products/basic-whey?variant=53658660241676"
    text = get_text("https://r.jina.ai/" + target, timeout=90)
    match = re.search(
        r"€([0-9]+,[0-9]{2})€([0-9]+,[0-9]{2})/kg, incl\. VAT", text
    )
    if not match:
        match = re.search(r"€([0-9]+,[0-9]{2})€([0-9]+,[0-9]{2})/kg", text)
    if not match:
        raise ValueError("ESN price not found")
    price = float(match.group(1).replace(",", "."))
    unit = float(match.group(2).replace(",", "."))
    return Price(
        brand="ESN Basic Whey",
        variant="Chocolate",
        size_kg=2.0,
        price=price,
        unit_price=unit,
        in_stock=True,
        url=target,
    )


def amazon_twister(params: dict) -> dict:
    url = (
        "https://www.amazon.de/gp/product/ajax/twisterDimensionSlotsDefault?"
        + urllib.parse.urlencode(params)
    )
    headers = {
        "Accept": "text/html,*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "x-requested-with": "XMLHttpRequest",
    }
    raw = get_text(url, headers=headers, timeout=90)
    results = {}
    for chunk in raw.split("&&&"):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            item = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        content = item.get("Value", {}).get("content", {})
        if not isinstance(content, dict):
            continue
        slot = content.get("twisterSlotJson", {})
        div = content.get("twisterSlotDiv", "")
        stock = re.search(r'id="twisterAvailability"[^>]*>([^<]+)', div)
        unit = re.search(r"(?:€|&amp;euro;|&euro;)\s?([\d.]+)\s*per kg", div)
        results[item.get("ASIN")] = {
            "price": slot.get("price"),
            "available": slot.get("isAvailable"),
            "stock": stock.group(1).strip() if stock else None,
            "unit_price": float(unit.group(1)) if unit else None,
        }
    return results


def fetch_pbn() -> Price:
    params = {
        "isDimensionSlotsAjax": "1",
        "asinList": "B08L75PF9N,B08L75XNXP",
        "vs": "1",
        "asin": "B08L75XNXP",
        "productTypeDefinition": "PROTEIN_SUPPLEMENT_POWDER",
        "productGroupId": "health_and_beauty_display_on_website",
        "parentAsin": "B095DDZ8ZF",
        "isPrime": "0",
        "deviceType": "web",
        "showFancyPrice": "false",
        "twisterFlavor": "twisterPlusDesktopConfigurator",
    }
    data = amazon_twister(params).get("B08L75XNXP", {})
    price = data.get("price")
    if price is None:
        raise ValueError("PBN price not found")
    return Price(
        brand="PBN Whey",
        variant="Chocolate",
        size_kg=2.27,
        price=float(price),
        unit_price=data.get("unit_price") or float(price) / 2.27,
        in_stock=data.get("available"),
        url="https://www.amazon.de/dp/B08L75XNXP",
    )


def fetch_on() -> Price:
    params = {
        "isDimensionSlotsAjax": "1",
        "asinList": "B0015R3AOA,B07G46TFL9,B00OLSNOBE",
        "vs": "1",
        "asin": "B000QSTBNS",
        "productTypeDefinition": "PROTEIN_SUPPLEMENT_POWDER",
        "productGroupId": "health_and_beauty_display_on_website",
        "storeId": "drugstore",
        "parentAsin": "B0GM17VNN4",
        "isPrime": "0",
        "deviceType": "web",
        "showFancyPrice": "false",
        "twisterFlavor": "twisterPlusDesktopConfigurator",
    }
    data = amazon_twister(params).get("B0015R3AOA", {})
    price = data.get("price")
    if price is None:
        raise ValueError("ON price not found")
    return Price(
        brand="ON Gold Standard Whey",
        variant="Double Rich Chocolate",
        size_kg=2.27,
        price=float(price),
        unit_price=data.get("unit_price") or float(price) / 2.27,
        in_stock=data.get("available"),
        url="https://www.amazon.de/dp/B0015R3AOA",
    )


FETCHERS = [fetch_bulk, fetch_myprotein, fetch_hsn, fetch_esn, fetch_pbn, fetch_on]


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(prices: dict) -> None:
    STATE_FILE.write_text(json.dumps(prices, indent=2), encoding="utf-8")


def delta_text(current: float, previous: float | None) -> str:
    if previous is None:
        return ""
    diff = current - previous
    if abs(diff) < 0.005:
        return " (no change)"
    arrow = "▲" if diff > 0 else "▼"
    return f" ({arrow} €{abs(diff):.2f} vs last run)"


def format_report(results: list[Price], previous: dict) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ordered = sorted(
        results,
        key=lambda r: (
            r.error is not None,
            r.unit_price if r.unit_price is not None else float("inf"),
        ),
    )
    lines = [f"**Protein Price Check** · {stamp}"]
    for item in ordered:
        if item.error:
            lines.append(f"⚠️ **{item.brand}** — failed: {item.error[:140]}")
            continue
        unit = f" · €{item.unit_price:.2f}/kg" if item.unit_price else ""
        stock = "" if item.in_stock is not False else " · out of stock"
        delta = delta_text(item.price, previous.get(item.brand))
        if item.regular and item.regular > item.price + 0.005:
            price_text = (
                f"~~€{item.regular:.2f}~~ → **€{item.price:.2f}** "
                f"(was €{item.regular:.2f}, save €{item.regular - item.price:.2f})"
            )
        else:
            price_text = f"**€{item.price:.2f}** (no original price listed)"
        lines.append(
            f"• **{item.brand}** {item.size_kg:g} kg: {price_text}"
            f"{unit} — {item.variant}{stock}{delta}"
        )
    lines.append("")
    lines.append(
        "Sorted by €/kg (lowest first). Sources: "
        + " | ".join(f"<{r.url}>" for r in ordered if r.url and not r.error)
    )
    return "\n".join(lines)


def post_discord(webhook: str, content: str, timeout: int = 30) -> None:
    payload = {"content": content[:2000], "allowed_mentions": {"parse": []}}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check protein prices and notify Discord.")
    parser.add_argument("--dry-run", action="store_true", help="print report without sending")
    parser.add_argument(
        "--changes-only",
        action="store_true",
        help="send only if a price changed or a check failed",
    )
    parser.add_argument("--webhook", help="Discord webhook URL (overrides env)")
    args = parser.parse_args()

    load_env()
    webhook = args.webhook or os.environ.get(DEFAULT_WEBHOOK_ENV, "").strip()

    previous = load_state()
    results = []
    for fetcher in FETCHERS:
        try:
            results.append(fetcher())
        except Exception as exc:
            results.append(
                Price(
                    brand=fetcher.__name__.removeprefix("fetch_").upper(),
                    variant="",
                    size_kg=0,
                    price=0,
                    error=str(exc),
                )
            )
        time.sleep(1)

    report = format_report(results, previous)
    print(report)

    changed = any(
        (not r.error and previous.get(r.brand) != round(r.price, 2)) or r.error
        for r in results
    )

    if args.dry_run:
        return 0

    if not webhook:
        print(f"error: set {DEFAULT_WEBHOOK_ENV} or pass --webhook", file=sys.stderr)
        return 2

    if args.changes_only and not changed:
        print("no changes; skipping Discord notification")
        return 0

    post_discord(webhook, report)
    if changed:
        save_state(
            {r.brand: round(r.price, 2) for r in results if not r.error}
        )
    print("sent to Discord")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
