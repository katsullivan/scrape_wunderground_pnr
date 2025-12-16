############version for wsl scrape env
import subprocess
import sys
import time
from datetime import datetime, timedelta
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
        __import__(pkg.split("==")[0])
    except ImportError:
        print(f"Installing missing package: {pkg}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# -------------------------------
# Imports (after ensuring installed)
# -------------------------------
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as BS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# -------------------------------
# Selenium driver initialization
# -------------------------------
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"  # Adjust if needed

def init_driver():
    options = Options()
    options.binary_location = "/usr/bin/google-chrome"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def render_page(url, driver):
    driver.get(url)
    time.sleep(3)
    return driver.page_source

# -------------------------------
# Scraping functions
# -------------------------------
def scrape_wunderground(station, date, driver, freq="5min"):
    """Scrape only temperature data from Weather Underground."""
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
        time_text = t_row.get_text().strip()
        temp_span = d_row.find("span")  # First span = Temperature
        temp_value = temp_span.get_text().strip() if temp_span else "--"

        if temp_value == "--":
            temp_float = np.nan
        else:
            # Keep digits, minus, dot only
            temp_clean = "".join(c for c in temp_value if c.isdigit() or c in ".-")
            try:
                temp_float = float(temp_clean)
            except ValueError:
                temp_float = np.nan

        timestamps.append(f"{date} {time_text}" if freq=="5min" else time_text)
        temperatures.append(temp_float)

    idx = pd.to_datetime(timestamps)
    df = pd.DataFrame({"Temperature": temperatures}, index=idx)
    return df

def scrape_multiattempt(station, date, driver, freq='5min', attempts=4, wait_time=5.0):
    for i in range(attempts):
        try:
            return scrape_wunderground(station, date, driver, freq)
        except Exception as e:
            print(f"Attempt {i+1} failed: {e}")
            time.sleep(wait_time)
    return pd.DataFrame()

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape temperature data from Weather Underground")
    parser.add_argument("station", type=str, help="The personal weather station ID")
    parser.add_argument("date", type=str, help="The date for which to acquire data, formatted as YYYY-MM-DD")
    parser.add_argument("freq", type=str, choices=["5min", "daily"], help="Download 5-minute or daily data")
    args = parser.parse_args()

    driver = init_driver()
    try:
        df = scrape_multiattempt(args.station, args.date, driver, freq=args.freq)
    finally:
        driver.quit()

    filename = f"{args.station}_{args.date}.csv"
    df.to_csv(filename)
    print(f"Saved {filename}")
