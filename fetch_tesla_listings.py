#!/usr/bin/env python3
"""Fetch used Tesla Model Y listings from Tesla NL inventory, filtered to year >= 2024.

Requirements (install one of):
    pip install cloudscraper   # preferred — handles Cloudflare
    pip install requests       # fallback

Usage:
    python3 fetch_tesla_listings.py
    python3 fetch_tesla_listings.py --min-year 2023 --zip 5642 --count 100
"""

import json
import sys
import argparse

API_URL = "https://www.tesla.com/inventory/api/v4/inventory-results"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Referer": "https://www.tesla.com/nl_NL/inventory/used/my",
    "Origin": "https://www.tesla.com",
}


def make_session():
    """Return a session object, preferring cloudscraper over requests."""
    try:
        import cloudscraper
        return cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "linux", "mobile": False}
        )
    except ImportError:
        pass
    try:
        import requests
        s = requests.Session()
        s.headers.update(HEADERS)
        return s
    except ImportError:
        pass
    raise SystemExit(
        "Neither 'cloudscraper' nor 'requests' is installed.\n"
        "Run: pip install cloudscraper"
    )


def fetch_page(session, zip_code: str, offset: int, count: int) -> dict:
    query = {
        "query": {
            "model": "my",
            "condition": "used",
            "options": {},
            "arrangeby": "Price",
            "order": "asc",
            "market": "NL",
            "language": "nl",
            "super_region": "europe",
            "zip": zip_code,
            "range": 0,
            "region": "NL",
        },
        "offset": offset,
        "count": count,
        "outsideOffset": 0,
        "outsideSearch": False,
    }
    resp = session.get(
        API_URL,
        params={"query": json.dumps(query, separators=(",", ":"))},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all(session, zip_code: str, page_size: int = 50) -> list[dict]:
    listings: list[dict] = []
    offset = 0

    while True:
        data = fetch_page(session, zip_code, offset, page_size)
        page = data.get("results", [])
        total = data.get("total_matches_found", 0)

        listings.extend(page)
        offset += len(page)
        print(f"  Fetched {offset}/{total} listings…", end="\r", flush=True)

        if not page or offset >= total:
            break

    print()
    return listings


def fmt_money(value, currency="EUR") -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.0f} {currency}"
    return f"{value} {currency}"


def fmt_odometer(value, unit="km") -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.0f} {unit}"
    return f"{value} {unit}"


def print_listing(i: int, car: dict) -> None:
    vin = car.get("VIN", "N/A")
    year = car.get("Year", "?")
    trim = car.get("TrimName") or car.get("Model", "Model Y")
    paint = (car.get("PAINT") or ["?"])[0]
    interior = (car.get("INTERIOR") or ["?"])[0]
    odometer = fmt_odometer(car.get("Odometer", "?"), car.get("OdometerType", "km"))
    price = fmt_money(
        car.get("InventoryPrice") or car.get("Price", "?"),
        car.get("CurrencyCode", "EUR"),
    )
    city = car.get("MetroName") or car.get("City", "?")
    autopilot = ", ".join(car.get("AUTOPILOT") or []) or "Standard Autopilot"
    wheels = (car.get("WHEELS") or ["?"])[0]

    print(f"\n[{i}] {year} Tesla Model Y — {trim}")
    print(f"    VIN      : {vin}")
    print(f"    Price    : {price}")
    print(f"    Mileage  : {odometer}")
    print(f"    Color    : {paint}")
    print(f"    Interior : {interior}")
    print(f"    Wheels   : {wheels}")
    print(f"    Autopilot: {autopilot}")
    print(f"    Location : {city}")


def main():
    parser = argparse.ArgumentParser(description="Fetch Tesla Model Y NL inventory")
    parser.add_argument("--min-year", type=int, default=2024, help="Minimum model year (default: 2024)")
    parser.add_argument("--zip", default="5642", help="Dutch ZIP code (default: 5642)")
    parser.add_argument("--count", type=int, default=50, help="Results per page (default: 50)")
    args = parser.parse_args()

    print(f"Fetching used Tesla Model Y inventory (NL, ZIP {args.zip}, year >= {args.min_year})…")

    session = make_session()

    try:
        all_listings = fetch_all(session, args.zip, page_size=args.count)
    except Exception as exc:
        print(f"\nError fetching listings: {exc}", file=sys.stderr)
        sys.exit(1)

    filtered = [
        c for c in all_listings
        if int(c.get("Year", 0)) >= args.min_year
    ]
    filtered.sort(key=lambda c: c.get("InventoryPrice") or c.get("Price") or float("inf"))

    print(f"\nTotal fetched  : {len(all_listings)}")
    print(f"After filter   : {len(filtered)} (year >= {args.min_year})")
    print("=" * 60)

    if not filtered:
        print("No listings match the filter criteria.")
        return

    for i, car in enumerate(filtered, 1):
        print_listing(i, car)

    print("\n" + "=" * 60)
    print(f"Showing {len(filtered)} Model Y listings (year >= {args.min_year})")


if __name__ == "__main__":
    main()
