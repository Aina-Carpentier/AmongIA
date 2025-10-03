# pylint: disable=import-error

import requests
import json
from datetime import datetime

def getLogLat(adresse):

    response = requests.get(f"https://geocode.maps.co/search?q={adresse}&api_key=68beee408c01a165506958ewl57d04f")
    print(f"adresse: {adresse}")

    return json.loads(response.text)[0]

def getTemp(lon, lat, start_date = datetime.now().date(), end_date = datetime.now().date()):
     
    response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&start_date={start_date}&end_date={end_date}")

    print(response.text[1])
    
    return json.loads(response.text)

