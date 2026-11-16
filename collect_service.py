import time, requests
import pandas as pd
import matplotlib.pyplot as plt

URLS = ["https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"]
AREA = 'area["ISO3166-2"="RU-ROS"][admin_level=4]->.a;'

def overpass(body):
    q = f"[out:json][timeout:300];{AREA}({body});out center tags;"
    for u in URLS:
        try:
            r = requests.post(u, data={"data": q}, timeout=320,
                              headers={"User-Agent": "XXX"})
            r.raise_for_status()
            return r.json()["elements"]
        except Exception as e:
            print(u, e); time.sleep(5)
    raise RuntimeError("Overpass недоступен")

# категория -> селекторы OSM
CATS = {
    "Парикмахерские и салоны красоты": ['nwr["shop"~"^(hairdresser|beauty)$"](area.a);',
                                        'nwr["amenity"="beauty"](area.a);'],
    "Маникюр, косметология, массаж, спа": ['nwr["shop"~"^(massage|nails)$"](area.a);',
                                           'nwr["leisure"="spa"](area.a);'],
    "Тату и пирсинг": ['nwr["shop"="tattoo"](area.a);'],
    "Рестораны": ['nwr["amenity"="restaurant"](area.a);'],
    "Кафе и кофейни": ['nwr["amenity"="cafe"](area.a);'],
    "Фастфуд": ['nwr["amenity"="fast_food"](area.a);'],
    "Бары и пабы": ['nwr["amenity"~"^(bar|pub)$"](area.a);'],
    "Столовые": ['nwr["amenity"="canteen"](area.a);'],
    "Фитнес и спорт": ['nwr["leisure"~"^(fitness_centre|sports_centre)$"](area.a);'],
    "Гостиницы": ['nwr["tourism"~"^(hotel|hostel|guest_house)$"](area.a);'],
    "Автосервис и мойки": ['nwr["shop"="car_repair"](area.a);', 'nwr["amenity"="car_wash"](area.a);'],
    "Химчистки и прачечные": ['nwr["shop"~"^(laundry|dry_cleaning)$"](area.a);'],
    "Стоматология и клиники": ['nwr["amenity"~"^(dentist|clinic|doctors)$"](area.a);'],
    "Ветеринария": ['nwr["amenity"="veterinary"](area.a);'],
}

frames = []
for cat, sels in CATS.items():
    els = []
    for s in sels:
        els += overpass(s)
        time.sleep(2)  # не нагружаем общедоступный сервер
    rows = []
    for e in els:
        t = e.get("tags", {})
        rows.append({"osm": f'{e["type"]}/{e["id"]}', "category": cat,
                     "lat": e.get("lat") or e.get("center", {}).get("lat"),
                     "lon": e.get("lon") or e.get("center", {}).get("lon"),
                     "name": t.get("name"), "brand": t.get("brand"),
                     "city": t.get("addr:city"), "street": t.get("addr:street"),
                     "house": t.get("addr:housenumber"), "phone": t.get("phone") or t.get("contact:phone"),
                     "hours": t.get("opening_hours"), "website": t.get("website") or t.get("contact:website")})
    frames.append(pd.DataFrame(rows))
    print(cat, len(rows))

svc = pd.concat(frames, ignore_index=True)
svc = svc.drop_duplicates(["category", "name", "lat", "lon"])
svc.to_csv("export_service.csv", index=False, encoding="utf-8-sig")