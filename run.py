from pprint import pprint
import json

from modules.application import Application

if __name__ == "__main__":
    with open("config/config.json", "r") as f:
        jd = json.load(f)
    pprint(jd)
    app = Application(jd)
    app()
