import requests
from bs4 import BeautifulSoup
import re
import time

def get_company_info(ticker):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}"
    
    # Set headers to mimic a real, up-to-date browser and include personal information
    headers = {
        "User-Agent": "PersonalUseBot/1.0 (john.m.orjias@gmail.com) Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the div with class 'companyInfo'
    company_info_div = soup.find('div', class_='companyInfo')
    
    # Extract the CIK from the URL within the div
    cik = None
    if company_info_div:
        anchor_tag = company_info_div.find('a', href=True)
        if anchor_tag:
            href = anchor_tag['href']
            cik_match = re.search(r'CIK=(\d+)', href)
            if cik_match:
                cik = cik_match.group(1)
    
    # Extract the text within the div and find the most recent date
    most_recent_date = None
    if company_info_div:
        text = company_info_div.get_text()
        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', text)
        if dates:
            most_recent_date = max(dates)
    
    return cik, most_recent_date
