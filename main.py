from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import requests, re, yfinance as yf
from bs4 import BeautifulSoup
from typing import Optional

app = FastAPI(title="India Gold Rate API (Surat Edition)")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)

TROY_OZ_TO_GRAM = 31.1035
TOLA = 11.6638

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/147.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Connection": "keep-alive",
}


def build_response(g22, g24, source, accuracy_text="actual Indian market rate"):
    return {
        "22k": {
            "per_gram": round(g22, 2),
            "per_10g": round(g22 * 10, 2),
            "per_tola": round(g22 * TOLA, 2),
        },
        "24k": {
            "per_gram": round(g24, 2),
            "per_10g": round(g24 * 10, 2),
            "per_tola": round(g24 * TOLA, 2),
        },
        "source": source,
        "accuracy": accuracy_text,
    }


def parse_rates(soup):
    """HTML se 22K/24K rate extract karne ka purana logic (Fallbacks ke liye)"""
    rate_24k = rate_22k = None
    for tag in soup.find_all(
        ["td", "span", "div", "p", "h2", "h3", "li", "b", "strong"]
    ):
        text = tag.get_text(strip=True).replace(",", "")
        m = re.search(r"\d{5,6}(\.\d+)?", text)
        if not m:
            continue
        val = float(m.group())

        if 100000 < val < 250000:
            val = val / 10
        elif not (8000 < val < 25000):
            continue

        if re.search(r"999|24\s*[kK]|24\s*carat|fine\s*gold", text, re.I):
            rate_24k = val
        elif re.search(r"916|22\s*[kK]|22\s*carat", text, re.I):
            rate_22k = val
    return rate_22k, rate_24k


def scrape_navkargold_api():
    """Source 1: Navkar Gold ka Direct Live API (Bulletproof Version)"""
    try:
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        url = f"https://bcast.navkargold.com:7768/VOTSBroadcastStreaming/Services/xml/GetLiveRateByTemplateID/navkar?_={timestamp}"

        custom_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/147.0.0.0",
            "Accept": "text/plain, */*; q=0.01",
            "Origin": "https://navkargold.com",
            "Referer": "https://navkargold.com/",
        }

        resp = requests.get(url, headers=custom_headers, timeout=10)
        text = resp.text.replace(",", "")
        lines = text.upper().split("\n")

        target_line = ""

        # LAYER 1: Multiple Keywords Fallback
        keywords = ["999", "24K", "24 CARAT", "FINE", "IMP", "PURE"]
        for line in lines:
            if "GOLD" in line and any(k in line for k in keywords):
                target_line = line
                break

        # LAYER 2: Price Logic Fallback
        if not target_line:
            highest_bid_price = 0
            for line in lines:
                nums = [float(n) for n in re.findall(r"\b\d{5,6}(?:\.\d+)?\b", line)]
                if nums:
                    val = nums[0]
                    normalized_val = val / 10 if 100000 < val < 250000 else val
                    if 8000 < normalized_val < 25000:
                        if normalized_val > highest_bid_price:
                            highest_bid_price = normalized_val
                            target_line = line

        # LAYER 3: Extreme Fallback
        if not target_line:
            target_line = text

        numbers = [float(n) for n in re.findall(r"\b\d{5,6}(?:\.\d+)?\b", target_line)]

        valid_rates = []
        for val in numbers:
            if 100000 < val < 250000:
                valid_rates.append(val / 10)
            elif 8000 < val < 25000:
                valid_rates.append(val)

        if valid_rates:
            r24 = valid_rates[0]
            r22 = round(r24 * (22 / 24), 2)
            return build_response(r22, r24, "navkargold.com (Surat - Smart API)")

    except Exception as e:
        print(f"Navkar API error: {e}")
    return None


def get_yfinance_rate():
    """Source 2: Yahoo Finance Fallback (Updated with Surat Premium)"""
    try:
        gold_usd_oz = yf.Ticker("GC=F").fast_info.last_price
        usd_inr = yf.Ticker("USDINR=X").fast_info.last_price
        intl_g = (gold_usd_oz / TROY_OZ_TO_GRAM) * usd_inr

        # Surat Premium Adjustment (8.5% added to intl spot)
        g24 = round(intl_g * 1.085, 2)
        g22 = round(g24 * (22 / 24), 2)

        return build_response(
            g22,
            g24,
            "Yahoo Finance (Surat Fallback)",
            "approx — intl spot + Indian duty/premium",
        )
    except Exception as e:
        print(f"Yahoo Finance error: {e}")
    return None


def scrape_ibja():
    """Source 3: Official IBJA rates site"""
    try:
        resp = requests.get("https://ibjarates.com/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, "lxml")
        r22, r24 = parse_rates(soup)
        if r24:
            return build_response(
                r22 or round(r24 * (22 / 24), 2), r24, "ibjarates.com (official IBJA)"
            )
    except Exception as e:
        print(f"IBJA error: {e}")
    return None


def scrape_goldpriceindia():
    """Source 4: goldpriceindia.com"""
    try:
        resp = requests.get("https://goldpriceindia.com/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, "lxml")
        r22, r24 = parse_rates(soup)
        if r24:
            return build_response(
                r22 or round(r24 * (22 / 24), 2), r24, "goldpriceindia.com"
            )
    except Exception as e:
        print(f"goldpriceindia error: {e}")
    return None


# --- ROUTES ---


@app.get("/gold")
def get_gold_navkar():
    """Default route: Sabse pehle Navkar (Surat) check karega"""
    data = scrape_navkargold_api() or get_yfinance_rate()

    if not data:
        return {"status": "error", "message": "Navkar and Yahoo both are down"}

    return {
        "status": "ok",
        "provider": "navkar",
        "prices": {"22k": data["22k"], "24k": data["24k"]},
        "meta": {
            "source": data["source"],
            "location": "Surat, Gujarat",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@app.get("/gold/yahoo")
def get_gold_yahoo():
    """Sirf Yahoo Finance ka rate dikhayega (Surat Adjusted)"""
    data = get_yfinance_rate()

    if not data:
        return {"status": "error", "message": "Yahoo Finance is currently unavailable"}

    return {
        "status": "ok",
        "provider": "yahoo",
        "prices": {"22k": data["22k"], "24k": data["24k"]},
        "meta": {
            "source": data["source"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@app.get("/gold/ibja")
def get_gold_ibja():
    """Sirf IBJA ka official rate dikhayega"""
    # Isme hum IBJA ko priority denge, fail hone par Yahoo
    data = scrape_ibja() or get_yfinance_rate()

    if not data:
        return {"status": "error", "message": "IBJA and Yahoo both are down"}

    return {
        "status": "ok",
        "provider": "ibja",
        "prices": {"22k": data["22k"], "24k": data["24k"]},
        "meta": {
            "source": data["source"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@app.get("/")
def root():
    return {
        "api": "Surat Gold Rate API",
        "endpoints": {
            "default": "/gold (Navkar Surat)",
            "yahoo": "/gold/yahoo (Live Intl Adjusted)",
            "ibja": "/gold/ibja (Official IBJA)",
        },
    }


@app.get("/")
def root():
    return {"api": "Surat Gold Rate API", "usage": "Visit /gold for live rates"}
