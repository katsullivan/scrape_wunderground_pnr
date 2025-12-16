#!/usr/bin/env python
# -*- coding: utf-8 -*-
############ version tested in portainer with output to csv

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
    "beautifulsoup4"
]

for pkg in required_packages:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing missing package: {pkg}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# -------------------------------
# Imports
# -------------------------------
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as BS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# -------------------------------
# Selenium setup
# -------------------------------
CHROMEDRIVER_PATH = "/usr/bin/chromedriver-linux64/chromedriver"

def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def render_page(url, driver):
    driver.get(url)
    time.sleep(3)
    return driver.page_source

# -------------------------------
# Scraping
# -------------------------------
def scrape_wunderground(station, date, driver, freq="5min"):
    """Scrape temperature only for a single date."""
    timespan = "daily" if freq == "5min" else "monthly"
    url = f"https://www.wunderground.com/dashboard/pws/{station}/table/{date}/{date}/{timespan}"

    soup = BS(render_page(url, driver), "html.parser")
    container = soup.find("lib-history-table")
    if container is None:
        raise RuntimeError("Weather table not found")

    time_body, data_body = container.find_all("tbody")
    time_rows = time_body.find_all("tr")
    data_rows = data_body.find_all("tr")

    timestamps = []
    temperatures = []

    for t_row, d_row in zip(time_rows, data_rows):
        time_text = t_row.get_text(strip=True)

        temp_span = d_row.find("span")  # first span = temperature
        temp_raw = temp_span.get_text(strip=True) if temp_span else "--"

        if temp_raw == "--":
            temp = np.nan
        else:
            temp_clean = "".join(c for c in temp_raw if c.isdigit() or c in ".-")
            try:
                temp = float(temp_clean)
            except ValueError:
                temp = np.nan

        timestamps.append(f"{date} {time_text}")
        temperatures.append(temp)

    df = pd.DataFrame(
        {"Temperature": temperatures},
        index=pd.to_datetime(timestamps, errors="coerce")
    )

    return df.dropna(how="all")

def scrape_multiattempt(station, date, driver, freq, attempts=4, wait_time=5):
    for i in range(attempts):
        try:
            return scrape_wunderground(station, date, driver, freq)
        except Exception as e:
            print(f"Attempt {i+1} failed for {date}: {e}")
            time.sleep(wait_time)
    return pd.DataFrame()

def scrape_from_date_file(station, date_file, driver, freq):
    with open(date_file, "r") as f:
        dates = [line.strip() for line in f if line.strip()]

    dfs = []
    for d in dates:
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            print(f"Skipping invalid date: {d}")
            continue

        print(f"Scraping {d}")
        df_day = scrape_multiattempt(station, d, driver, freq)
        if not df_day.empty:
            dfs.append(df_day)

    if dfs:
        return pd.concat(dfs).sort_index()
    else:
        return pd.DataFrame()

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape temperature data from Weather Underground"
    )
    parser.add_argument("station", help="Personal weather station ID")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="Single date YYYY-MM-DD")
    group.add_argument("--date-file", help="Text file with dates (one per line)")
    # group.add_argument("--start-date", help="Start date YYYY-MM-DD")

    # parser.add_argument("--end-date", help="End date YYYY-MM-DD (used with --start-date)")
    parser.add_argument("--freq", choices=["5min", "daily"], default="5min")

    args = parser.parse_args()

    driver = init_driver()
    try:
        if args.date_file:
            df = scrape_from_date_file(
                args.station,
                args.date_file,
                driver,
                args.freq
            )
            out = f"{args.station}_from_file.csv"

        else:
            df = scrape_multiattempt(
                args.station,
                args.date,
                driver,
                args.freq
            )
            out = f"{args.station}_{args.date}.csv"

    finally:
        driver.quit()

    df.to_csv(out)
    print(f"Saved {out}")

