#!/usr/bin/env python3
# ############ version for wsl scrape env ############
import subprocess
import sys
import time
from datetime import datetime
import argparse

# -------------------------------
# Auto-install required packages
# -------------------------------
required_packages = [
    "selenium",
    "pandas",
    "numpy",
    "beautifulsoup4"  # kept, although we'll primarily use Selenium due to shadow DOM
]

for pkg in required_packages:
    try:
        __import__(pkg.split("==")[0])
    except ImportError:
        print(f"Installing missing package: {pkg}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# -------------------------------
# Imports (after ensuring installed)
# -------------------------------
import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------------------------------
# Selenium driver initialization
# -------------------------------
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"  # Adjust if needed
CHROME_BINARY = "/usr/bin/google-chrome"     # Adjust if needed

def init_driver():
    options = Options()
    options.binary_location = CHROME_BINARY
    # WSL/headless stability flags
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

def build_url(station: str, date: str, freq: str) -> str:
    # WU uses /table/{from}/{to}/{timespan}
    # Your mapping: "5min" -> daily (intra-day rows), otherwise monthly.
    timespan = "daily" if freq == "5min" else "monthly"
    return f"https://www.wunderground.com/dashboard/pws/{station}/table/{date}/{date}/{timespan}"

def wait_for_table_root(driver, timeout=20):
    # Wait for the custom element to be present in the DOM
    root = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "lib-history-table"))
    )
    # Access shadow root (Selenium 4.10+)
    try:
        shadow = root.shadow_root
    except Exception:
        # Fallback via JS for older Selenium
        shadow = driver.execute_script("return arguments[0].shadowRoot", root)
    return shadow

def get_table_bodies_from_shadow(shadow_root, driver):
    """
    Inside the lib-history-table shadow DOM, locate the two <tbody> sections:
    one for time rows and one for data rows. The structure can change, so
    we use a flexible approach to detect both bodies.
    """
    # The shadow DOM typically contains an internal <table> with two <tbody>s.
    # We query within shadow_root using JS to navigate inside.
    tables = driver.execute_script("""
        const shadow = arguments[0];
        return shadow.querySelectorAll('table');
    """, shadow_root)

    if not tables or len(tables) < 1:
        raise RuntimeError("No internal table found within lib-history-table shadow DOM")

    # Find tbodies within the first table
    tbodies = driver.execute_script("""
        const tbl = arguments[0];
        return tbl.querySelectorAll('tbody');
    """, tables[0])

    if not tbodies or len(tbodies) < 2:
        raise RuntimeError("Expected at least two <tbody> elements in the history table")

    time_body = tbodies[0]
    data_body = tbodies[1]
    return time_body, data_body

def extract_rows_from_tbody(tbody, driver):
    return driver.execute_script("""
        const body = arguments[0];
        return Array.from(body.querySelectorAll('tr'));
    """, tbody)

def text_content(el, driver):
    return driver.execute_script("return arguments[0].textContent", el).strip()

def scrape_wunderground(station, date, driver, freq="5min"):
    url = build_url(station, date, freq)
    driver.get(url)

    # Wait for the table component (and handle async loading spinners)
    shadow_root = wait_for_table_root(driver, timeout=30)

    # Optional: wait for data-loaded attribute if present
    # Web components often toggle attributes; try to wait for populated rows
    time_body, data_body = get_table_bodies_from_shadow(shadow_root, driver)

    time_rows = extract_rows_from_tbody(time_body, driver)
    data_rows = extract_rows_from_tbody(data_body, driver)

    if not time_rows or not data_rows:
        raise RuntimeError("No table rows found (station may have no data for this date).")

    timestamps = []
    temperatures = []

    for t_row, d_row in zip(time_rows, data_rows):
        time_text = text_content(t_row, driver)

        # First span in data row often corresponds to Temperature
        # But the structure can vary; we select the first numeric-ish cell/span.
        spans = driver.execute_script("""
            const row = arguments[0];
            return Array.from(row.querySelectorAll('span'));
        """, d_row)

        temp_value = None
        if spans and len(spans) > 0:
            temp_value = driver.execute_script("return arguments[0].textContent", spans[0]).strip()
        else:
            # Fallback to first cell text
            temp_value = text_content(d_row, driver)

        if temp_value in (None, "", "--"):
            temp_float = np.nan
        else:
            # Keep digits, minus, dot only
            temp_clean = "".join(c for c in temp_value if c.isdigit() or c in ".-")
            try:
                temp_float = float(temp_clean)
            except ValueError:
                temp_float = np.nan

        # If freq is 5min, time_text is an HH:MM or similar; prepend date for timestamp
        timestamps.append(f"{date} {time_text}" if freq == "5min" else time_text)
        temperatures.append(temp_float)

    # Build DataFrame
    try:
        idx = pd.to_datetime(timestamps)
    except Exception:
        # In case monthly page returns date strings already
        idx = pd.Series(timestamps)

    df = pd.DataFrame({"Temperature": temperatures}, index=idx)
    return df

def scrape_multiattempt(station, date, driver, freq='5min', attempts=4, wait_time=5.0):
    last_exc = None
    for i in range(attempts):
        try:
            return scrape_wunderground(station, date, driver, freq)
        except Exception as e:
            last_exc = e
            print(f"Attempt {i+1} failed: {e}")
            time.sleep(wait_time)
    print("All attempts failed.")
    if last_exc:
        print(f"Last error: {last_exc}")
    return pd.DataFrame()

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape temperature data from Weather Underground")
    parser.add_argument("station", type=str, help="The personal weather station ID (e.g., KPAxxxxxx)")
    parser.add_argument("date", type=str, help="Date formatted as YYYY-MM-DD")
    parser.add_argument("freq", type=str, choices=["5min", "daily"], help="Download 5-minute or daily data")
    args = parser.parse_args()

    driver = init_driver()
    try:
        df = scrape_multiattempt(args.station, args.date, driver, freq=args.freq)
    finally:
        driver.quit()

    if df.empty:
        print("No data scraped; CSV will not be saved.")
        sys.exit(1)

    filename = f"{args.station}_{args.date}.csv"
    df.to_csv(filename)
   
