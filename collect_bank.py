import re, time, requests
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]
AREA = 'area["ISO3166-2"="RU-ROS"][admin_level=4]->.a;'

def overpass(body):
    q = f"[out:json][timeout:300];{AREA}{body}out center tags;"
    for url in ENDPOINTS:
        try:
            r = requests.post(url, data={"data": q}, timeout=320,
                              headers={"User-Agent": "rostov-research/1.0"})
            r.raise_for_status()
            return r.json()["elements"]
        except Exception as e:
            print(url, "->", e); time.sleep(5)
    raise RuntimeError("Overpass недоступен")

def to_df(elements):
    rows = []
    for e in elements:
        t = e.get("tags", {})
        rows.append({
            "osm": f'{e["type"]}/{e["id"]}',
            "lat": e.get("lat") or e.get("center", {}).get("lat"),
            "lon": e.get("lon") or e.get("center", {}).get("lon"),
            **t})
    return pd.DataFrame(rows)

# 1. Отделения и банкоматы
banks = to_df(overpass('(nwr["amenity"="bank"](area.a);nwr["amenity"="atm"](area.a););'))
banks["kind"] = np.where(banks["amenity"] == "atm", "банкомат", "отделение")

# 2. Населённые пункты для привязки к месту
places = to_df(overpass('node["place"~"^(city|town|village|hamlet)$"](area.a);'))
places = places.dropna(subset=["lat", "lon", "name"])

# 3. Привязка к ближайшему населённому пункту
def xy(df):  # грубая проекция для небольшого региона
    return np.c_[df.lon * np.cos(np.radians(47.5)), df.lat]
b = banks.dropna(subset=["lat", "lon"]).copy()
_, idx = cKDTree(xy(places)).query(xy(b))
b["settlement"] = b["addr:city"].fillna(places.iloc[idx]["name"].values)

# 4. Банк: сначала brand:wikidata (устойчив к написаниям), потом regex
RX = {"Сбербанк": r"сбер", "ВТБ": r"втб", "Альфа-Банк": r"альфа",
      "Газпромбанк": r"газпром", "Россельхозбанк": r"россельхоз",
      "Т-Банк": r"тинькофф|т-банк", "Почта Банк": r"почта\s*банк",
      "Райффайзен": r"райффайзен", "Открытие": r"открытие",
      "Совкомбанк": r"совком", "Промсвязьбанк": r"промсвяз",
      "МКБ": r"московский кредитный|мкб", "Центр-инвест": r"центр-?инвест"}
def brand(r):
    s = " ".join(str(r.get(k, "")) for k in ("brand", "name", "operator")).lower()
    for k, rx in RX.items():
        if re.search(rx, s): return k
    return r.get("brand") or r.get("operator") or r.get("name") or "Не указан"
b["bank"] = b.apply(brand, axis=1)

# 5. Дубли (один банк мог быть нанесён и точкой, и зданием)
b["k"] = b.bank + b.lat.round(4).astype(str) + b.lon.round(4).astype(str)
b = b.drop_duplicates("k").drop(columns="k")

cols = ["osm", "kind", "bank", "name", "operator", "brand", "brand:wikidata",
        "settlement", "addr:street", "addr:housenumber", "opening_hours", "lat", "lon"]
b[[c for c in cols if c in b]].to_csv("export_bank.csv", index=False, encoding="utf-8-sig")