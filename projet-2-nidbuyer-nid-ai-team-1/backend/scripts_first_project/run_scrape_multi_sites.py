from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


CSV_COLUMNS = [
    "source",
    "titre",
    "prix_eur",
    "surface_m2",
    "quartier",
    "type_bien",
    "description",
    "url",
    "date_scrape",
]


def price_from_text(text: str) -> float | None:
    m = re.search(r"(\d[\d\s\.,]{2,})\s*€", text.replace("\xa0", " "))
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(1))
    return float(digits) if digits else None


def surface_from_text(text: str) -> float | None:
    m = re.search(r"(\d+[\.,]?\d*)\s*m(?:²|2)", text.lower())
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def type_from_text(text: str) -> str:
    t = text.lower()
    if "appartement" in t:
        return "Appartement"
    if "maison" in t:
        return "Maison"
    return "Autre"


def title_from_text(text: str) -> str:
    s = " ".join(text.split())
    return s[:160]


def source_from_domain(domain: str) -> str:
    d = domain.lower()
    if "seloger" in d:
        return "SeLoger"
    if "logic-immo" in d:
        return "Logic-Immo"
    if "leboncoin" in d:
        return "Leboncoin"
    if "bienici" in d:
        return "Bienici"
    if "paruvendu" in d:
        return "ParuVendu"
    return domain


def href_allowed(domain: str, href: str) -> bool:
    h = href.lower()
    d = domain.lower()
    if "seloger" in d:
        return "/annonces/" in h or "/list.htm" in h
    if "logic-immo" in d:
        return "/annonces-" in h or "/vente-" in h
    if "leboncoin" in d:
        return "/ad/" in h
    if "bienici" in d:
        return "/annonce/" in h or "/achat/" in h
    if "paruvendu" in d:
        return "/immobilier/" in h or "pa" in h
    return True


def collect_page_cards(page) -> list[dict]:
    js = """
    () => {
      const out = [];
      const anchors = Array.from(document.querySelectorAll('a[href]'));
      for (const a of anchors) {
        const href = a.getAttribute('href') || '';
        const card = a.closest('article, li, div') || a;
        const text = ((card && card.innerText) ? card.innerText : a.innerText || '').trim();
        out.push({ href, text });
      }
      return out;
    }
    """
    return page.evaluate(js)


def scrape_url(
    page_url: str,
    budget_max: int,
    per_url_limit: int,
    scroll_steps: int,
    city_keywords: tuple[str, ...],
    manual_wait_s: int,
    max_pages: int,
) -> list[dict]:
    parsed = urlparse(page_url)
    domain = parsed.netloc
    source = source_from_domain(domain)

    rows: list[dict] = []
    seen: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="fr-FR")
        page = context.new_page()

        cards: list[dict] = []
        for page_num in range(1, max_pages + 1):
            target_url = build_paged_url(page_url, page_num)
            print(f"    page {page_num}/{max_pages}: {target_url}")
            page.goto(target_url, wait_until="domcontentloaded", timeout=90_000)

            # Cookie/challenge handling is mostly needed on first page.
            if page_num == 1:
                for label in ["Tout accepter", "Accepter", "J'accepte", "Accept all"]:
                    try:
                        page.get_by_role("button", name=label).click(timeout=2_000)
                        break
                    except PlaywrightTimeoutError:
                        pass
                    except Exception:
                        pass

                if manual_wait_s > 0:
                    print(f"[{source}] validation manuelle/cookies: attente {manual_wait_s}s")
                    page.wait_for_timeout(manual_wait_s * 1000)

            for _ in range(scroll_steps):
                page.mouse.wheel(0, 6000)
                page.wait_for_timeout(1000)

            cards.extend(collect_page_cards(page))
        browser.close()

    for item in cards:
        href = str(item.get("href", "")).strip()
        text = str(item.get("text", "")).strip()
        if not href or not text:
            continue

        full_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", href)
        if full_url in seen:
            continue
        seen.add(full_url)

        if not href_allowed(domain, full_url):
            continue

        price = price_from_text(text)
        surface = surface_from_text(text)

        if price is None or price <= 0 or price > budget_max:
            continue
        if surface is None or surface <= 0:
            continue

        blob = f"{text} {full_url}".lower()
        if city_keywords and not any(k.lower() in blob for k in city_keywords):
            continue

        rows.append(
            {
                "source": source,
                "titre": title_from_text(text),
                "prix_eur": price,
                "surface_m2": surface,
                "quartier": "",
                "type_bien": type_from_text(text),
                "description": "",
                "url": full_url,
                "date_scrape": datetime.now(timezone.utc).isoformat(),
            }
        )

        if len(rows) >= per_url_limit:
            break

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape multiple real-estate sites into one CSV")
    parser.add_argument("--url", action="append", required=True, help="Search URL (repeatable)")
    parser.add_argument("--budget-max", type=int, default=500000)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--per-url-limit", type=int, default=80)
    parser.add_argument("--max-pages", type=int, default=1, help="Number of paginated result pages per URL")
    parser.add_argument("--scroll-steps", type=int, default=20)
    parser.add_argument("--city-keywords", default="toulon,83000,83100,83200")
    parser.add_argument("--manual-wait", type=int, default=15)
    parser.add_argument("--output", default="data/annonces.csv")
    args = parser.parse_args()

    urls = list(dict.fromkeys([u.strip() for u in args.url if u.strip()]))
    if args.city_keywords.strip().lower() in {"none", "all", "*"}:
        city_keywords = tuple()
    else:
        city_keywords = tuple(k.strip() for k in args.city_keywords.split(",") if k.strip())

    all_rows: list[dict] = []
    for i, u in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] {u}")
        try:
            rows = scrape_url(
                page_url=u,
                budget_max=args.budget_max,
                per_url_limit=args.per_url_limit,
                scroll_steps=args.scroll_steps,
                city_keywords=city_keywords,
                manual_wait_s=args.manual_wait,
                max_pages=args.max_pages,
            )
            print(f"  -> {len(rows)} annonces retenues")
            all_rows.extend(rows)
        except Exception as exc:
            print(f"  -> erreur: {exc}")

    df = pd.DataFrame(all_rows)
    if df.empty:
        df = pd.DataFrame(columns=CSV_COLUMNS)
    else:
        df = df.drop_duplicates(subset=["url"], keep="first").head(args.limit)
        for col in CSV_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[CSV_COLUMNS]

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    print(f"Saved {len(df)} annonces to {out}")
    if len(df):
        print(df[["source", "titre", "prix_eur", "surface_m2", "url"]].head(15).to_string(index=False))


def build_paged_url(base_url: str, page_num: int) -> str:
    if page_num <= 1:
        return base_url
    parsed = urlparse(base_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


if __name__ == "__main__":
    main()

# .venv\Scripts\python.exe scripts/run_scrape_multi_sites.py --url "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD08FR34378&priceMax=500000" --url "https://www.bienici.com/recherche/achat/toulon-83000?prix-max=500000" --budget-max 500000 --limit 220 --per-url-limit 150 --max-pages 5 --scroll-steps 12 --manual-wait 8 --output data/annonces.csv