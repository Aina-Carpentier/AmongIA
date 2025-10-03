# pylint: disable=import-error
# pylint: disable=bare-except

import time
from flask import Flask
from apiprovider import *
app = Flask(__name__)

@app.route("/temp/lat=<lat>;lon=<lon>")
def tempNow(lat, lon):
    temp = None
    while temp is None:
        try:
            temp = {"tmp" : round(getTemp(lon, lat)["current"]["temperature_2m"], 1)}

        except :
            time.sleep(1)

    return temp


if __name__ == "__main__":
    app.run(debug="true", host='10.109.111.21', port=8080)