from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
from selenium.webdriver.chrome.service import Service
import time

URL = "https://www.zebet.fr/en/category/143-world_cup"

options = Options()
options.headless = False
options.add_argument("--window-size=1920x1080")
options.add_argument("start-maximized")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

service = Service(executable_path=r'C:\Users\akher\Desktop\PGD2\chromedriver.exe')
driver = webdriver.Chrome(service=service, options=options)
driver.get(URL)

try:
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "CybotCookiebotDialogBodyButtonAccept"))).click()
except:
    print("Erreur lors de la tentative d'acceptation des cookies ou bouton non trouvé.")

SCROLL_PAUSE_TIME = 2
last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SCROLL_PAUSE_TIME)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

soup = BeautifulSoup(driver.page_source, 'html.parser')

containers = soup.find_all('div', class_='item-content catcomp item-bloc-type-13')

winners = []
second_places = []

for container in containers:
    title = container.find('div', class_='bet-question').get_text(strip=True)
    
    divs = container.find_all('div', class_='bet-actorodd1')
    for div in divs:
        if div.find('a'):
            country = div.find('span', class_='pmq-cote-acteur').text.strip()
            odd = div.find('span', class_='pmq-cote').text.strip()

            if "World Cup 2023 - Winner" in title:
                winners.append([country, odd])
            elif "World Cup 2023 - Which team will finish in second place?" in title:
                second_places.append([country, odd])

entries = []
for winner, second_place in zip(winners, second_places):
    entries.append(winner + second_place)

with open('ZebetScrap.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Pays Vainqueur", "Cote vainqueur", "Pays deuxième", "Cote deuxième"])
    for entry in entries:
        writer.writerow(entry)

driver.close()


