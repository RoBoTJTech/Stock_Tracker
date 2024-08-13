from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_tickers_from_page(url):
    # Set up the Selenium WebDriver with user agent
    options = Options()
    options.add_argument("--headless")  # Run headlessly (without opening a browser window)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(60)
    # Open the web page
    driver.get(url)
    print(f"Querying URL: {url}")

    tickers = []

    # Wait for the table to load
    time.sleep(10)
    try:
        table = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, 'etfs'))
        )
    except Exception as e:
        driver.quit()
        raise Exception("Could not find the ETF table on the page") from e

    # Find all rows in the table body
    rows = table.find_elements(By.CSS_SELECTOR, 'tbody tr')

    for row in rows:
        # Find the ticker symbol in the first column
        symbol_cell = row.find_element(By.CSS_SELECTOR, 'td[data-th="Symbol"]')
        if symbol_cell:
            ticker = symbol_cell.text.strip()
            tickers.append(ticker)

    # Close the browser
    driver.quit()

    return tickers
