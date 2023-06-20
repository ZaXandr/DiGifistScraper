import time

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from datetime import datetime
from urllib.parse import quote

from bs4 import BeautifulSoup

import requests
import random
import sys
import mysql.connector
import json

arguments = sys.argv

json_str = arguments[1]
data = json.loads(json_str)

search_text = data["them_name"][0]
search_category = data["category"]
number_of_clicks = data["clicks"][0]
price = data["price"]
catalog_size = data["catalog_size"]
features = data["features"]
search_category_id = data["them_id"][0]

clicks_per_hour = int(data["clicks"][0]) // 24

proxy_list = []

API_KEY = "Token 50xn49ng5y38gkca2zdy8q0akqhi5gsp0sl7rsqo"

i = 1

while True:
    response = requests.get(
    f"https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page={i}&page_size=100",
    headers={"Authorization": API_KEY}
    )
    response_data = response.json()
    print(response_data)
    for obj in response_data["results"]:
        proxy = {
            "proxy_address": obj["proxy_address"],
            "port": obj["port"],
            "username" : obj["username"],
            "password": obj["password"]
        }
        proxy_list.append(proxy)
    i += 1
    if response_data["next"] is None:
        break

def format_string(str):
    lowercase_string = str.lower()
    transformed_string = lowercase_string.replace(" ", "-")
    return transformed_string


def format_arr(arr, unit):
    if not arr:
        return ""
    formatted_arr = [f"{unit}%5B%5D={quote(format_string(element))}" for element in arr]
    return "&".join(formatted_arr) + "&"


def get_random_sleep(N):
    average = 3500 / N
    return random.randint(int(average * 0.75), int(average * 1.25))


url = "https://themes.shopify.com/themes?" + format_arr(price, "price") + format_arr(catalog_size,
                                                                                     "catalog_size") + format_arr(
    features, "features") + format_arr(search_category, "industry")

for i in range(clicks_per_hour):
    url_template = url + 'page={page_num}&sort_by=most_relevant'
    unique_elements = []

    f_page = requests.get(url + 'sort_by=most_relevant')
    f_soup = BeautifulSoup(f_page.content, 'html.parser')
    f_element = f_soup.find('div', role='navigation')
    if f_element is not None:
        max_pages = int(f_element.find_all('a', {'aria-label': True})[-2].text)
    else:
        max_pages = 1

    conn = mysql.connector.connect(
        host='localhost',
        database='scraper',
        user='scraper',
        password='1234'
    )
    cursor = conn.cursor()
    insert_query = "INSERT into output (name,position,them_id,set_amount,date) VALUES (%s,%s,%s,%s,%s)"

    for page_num in range(1, max_pages + 1):
        url_t = url_template.format(page_num=page_num)
        print(url_t)
        page = requests.get(url_t)
        soup = BeautifulSoup(page.content, 'html.parser')

        for element in soup.find_all('span',
                                     class_='heading--4 theme-v2-info__name theme-info__name gutter-bottom--reset'):
            if not any(element.text == e[0].text for e in unique_elements):
                unique_elements.append((element, page_num))

    for i, element in enumerate(unique_elements):
        if search_text in element[0].text:
            page_num = str(element[1])
            them_number = i + 1
            print(f"Element '{element[0].text}'. Counter: {them_number}")
            current_time = datetime.now()
            formatted_datetime = current_time.strftime('%Y-%m-%d %H:%M:%S')
            data = (element[0].text, them_number, search_category_id, number_of_clicks, formatted_datetime)
            cursor.execute(insert_query, data)
            conn.commit()
            cursor.close()
            conn.close()

    current_proxy = random.choice(proxy_list)
    proxy_settings = f"{current_proxy['username']}:{current_proxy['password']}@{current_proxy['proxy_address']}:{current_proxy['port']}"

    proxy_options = {
        'proxy': {
            'http': 'http://'+proxy_settings,
            'https': 'https://'+proxy_settings,
            'no_proxy': 'localhost,127.0.0.1'
        }
    }

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')

    driver_path = "/usr/bin/chromedriver"
    service = Service(driver_path)
    driver = webdriver.Chrome(seleniumwire_options=proxy_options,options=chrome_options,service=service)

    driver.maximize_window()
    print(url + "page=" + str(page_num) + "&sort_by=most_relevant")
    driver.get(url + "page=" + str(page_num) + "&sort_by=most_relevant")
    try:
        them_style = driver.find_element(By.XPATH, f"//a[@data-theme-name='{search_text}' and @data-state='0']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", them_style)
        time.sleep(1)
        them_style.click()
        theme_to_click = driver.find_element(By.XPATH, f"//span[contains(text(), '{search_text}')]")
        theme_to_click.click()
    except NoSuchElementException:
        print("Тема без стилей")
        try:
            theme_to_click = driver.find_element(By.XPATH, f"//span[contains(text(), '{search_text}')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", theme_to_click)
            time.sleep(1)
            theme_to_click.click()
        except NoSuchElementException:
            print("не найден элемент дял килка")

    driver.quit()
    time.sleep(int(get_random_sleep(clicks_per_hour)))
