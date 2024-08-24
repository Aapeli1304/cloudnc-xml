import requests
from lxml import html
import os
from datetime import datetime
import re
import xml.etree.ElementTree as ET
import time

# Kunta, joka käyttää Cloudnc-palvelua (esim. Tampere)
kunta = 'Tampere'

# Määrittele eri tiedot jokaiselle tiedostolle ja XPath:lle
data = {
    'esityslistat': {
        'xpath': '//*[@id="Content_ctl01_ncContainer"]/div/div/ul/li/a',
        'xml_file': 'esityslistat.xml',
        'date_required': True
    },
    'kuulutukset': {
        'xpath': '//*[@id="Content_ctl02_ncContainer"]/div/div/ul/li/a',
        'xml_file': 'kuulutukset.xml',
        'date_required': False
    },
    'pöytäkirjat': {
        'xpath': '//*[@id="Content_ctl00_ncContainer"]/div/div/ul/li/a',
        'xml_file': 'pöytäkirjat.xml',
        'date_required': True
    },
    'viranhaltijapäätökset': {
        'xpath': '//*[@id="Content_ctl03_ncContainer"]/div/div/ul/li/a',
        'xml_file': 'viranhaltijapäätökset.xml',
        'date_required': False
    }
}

here = os.path.dirname(os.path.abspath(__file__))
base_url = f'https://{kunta}.cloudnc.fi/fi-FI'

def process_data(xpath, xml_file, date_required):
    # Tee HTTP-pyyntö ja pura HTML-sisältö
    r = requests.get(base_url)
    tree = html.fromstring(r.text)
    
    # Hae kiinnostavat elementit XPathin avulla
    list_items = tree.xpath(xpath)

    # Määrittele RSS XML-tiedoston polku
    xml_file_path = os.path.join(here, xml_file)

    # Lataa olemassa oleva RSS-data tai luo uusi juurielementti
    if os.path.exists(xml_file_path):
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    else:
        # Luo uusi RSS-kanava
        root = ET.Element("rss", version="2.0")
        channel = ET.SubElement(root, "channel")
        ET.SubElement(channel, "title").text = f"{kunta} - {xml_file.split('.')[0]}"
        ET.SubElement(channel, "link").text = base_url
        ET.SubElement(channel, "description").text = f"{kunta} - {xml_file.split('.')[0]} RSS feed"
        ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
    
    channel = root.find("channel")

    # Käsittele jokainen elementti ja hae linkit
    for i in list_items:
        href = i.get('href')
        link = base_url + href
        title = i.text_content().split('\r\n')[0]
        
        # Jos päivämäärä vaaditaan, pura se
        if date_required:
            match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', title)
            if not match:
                continue
            day, month, year = match.groups()
            date_str = f'{day.zfill(2)}-{month.zfill(2)}-{year}'
            date_obj = datetime.strptime(date_str, '%d-%m-%Y')
            date = date_obj.strftime('%d.%m.%Y')
            toimielin = title.split(' - ')[0]
        else:
            date = ''
            toimielin = ''
        
        # Tarkista, onko tapahtuma jo RSS:ssä
        found = False
        for item in channel.findall('item'):
            if item.find('title').text == title:
                found = True
                break
        
        if found:
            continue
        
        # Luo uusi item-elementti
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "description").text = f"{title} - {link}"
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        if date_required:
            ET.SubElement(item, "category").text = toimielin

    # Päivitä kanavan viimeisin päivityspäivämäärä
    channel.find("lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

    # Kirjoita RSS XML-data tiedostoon
    tree = ET.ElementTree(root)
    tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)

# Aikaväli toistolle sekunteina (esim. 3600 sekuntia = 1 tunti)
interval = 3600

# Suorita käsittely jatkuvasti
while True:
    for key, value in data.items():
        process_data(value['xpath'], value['xml_file'], value['date_required'])
    
    # Odota määritelty aikaväli ennen seuraavaa suoritus
    time.sleep(interval)
