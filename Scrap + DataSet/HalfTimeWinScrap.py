from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
from selenium.webdriver.chrome.service import Service


URL = "https://rugby.statbunker.com/competitions/HalfTimeTableWin?comp_id=727"

options = Options()
options.headless = False
options.add_argument("--window-size=1920x1080")
options.add_argument("start-maximized")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

service = Service(executable_path=r'C:\Users\akher\Desktop\PGD2\chromedriver.exe')
driver = webdriver.Chrome(service=service, options=options)
driver.get(URL)

soup = BeautifulSoup(driver.page_source, 'html.parser')


table = soup.find('table', class_='table')


headings = []
for th in table.find('thead').find('tr').find_all('th'):
    headings.append(th.text.strip())

rows = table.find('tbody').find_all('tr')


data = []
for row in rows:
    current_row = []
    for td in row.find_all('td'):
        current_row.append(td.text.strip())
    data.append(current_row)


filename = "HalfTimeWinScrap.csv"
with open(filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(headings)
    writer.writerows(data)

print(f"Data saved to {filename}")

driver.close()
