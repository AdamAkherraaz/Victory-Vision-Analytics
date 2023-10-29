from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
from selenium.webdriver.chrome.service import Service
import time

URL = "https://www.betclic.fr/rugby-a-xv-s5/coupe-du-monde-2023-c34"

options = Options()
options.headless = False
options.add_argument("--window-size=1920x1080")
options.add_argument("start-maximized")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

service = Service(executable_path=r'C:\Users\akher\Desktop\PGD2\chromedriver.exe')
driver = webdriver.Chrome(service=service, options=options)
driver.get(URL)


try:
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "popin_tc_privacy_button_2"))).click()
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

wait = WebDriverWait(driver, 20)
wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "groupEvents_content")))

soup = BeautifulSoup(driver.page_source, 'html.parser')


countries_1_divs = soup.find_all('div', class_='scoreboard_contestant-1')
country_names_1 = [country.find('div', class_='scoreboard_contestantLabel').text.strip() for country in countries_1_divs if country.find('div', class_='scoreboard_contestantLabel')]

countries_2_divs = soup.find_all('div', class_='scoreboard_contestant-2')
country_names_2 = [country.find('div', class_='scoreboard_contestantLabel').text.strip() for country in countries_2_divs if country.find('div', class_='scoreboard_contestantLabel')]


matches = soup.find_all('a', class_='cardEvent')

with open('BetclicScrap.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)


    writer.writerow(["Pays 1", "Pays 2", "Cote 1", "Cote Egalité", "Cote 2"])

    for i, match in enumerate(matches):
        cotes = [elem.text.strip() for elem in match.find_all('span', class_='oddValue')]
        if len(country_names_1) > i and len(country_names_2) > i and len(cotes) >= 3:
            writer.writerow([country_names_1[i], country_names_2[i], cotes[0], cotes[1], cotes[2]])
        else:
            print(f"Le match {i+1} n'a pas toutes les informations nécessaires.")

driver.close()
