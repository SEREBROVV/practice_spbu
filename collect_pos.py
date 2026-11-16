import re, time, requests
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree

URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
AREA = 'area["ISO3166-2"="RU-ROS"][admin_level=4]->.a;'

def overpass(body):
    q = f"[out:json][timeout:600];{AREA}{body}out center tags;"
    for u in URLS:
        try:
            r = requests.post(u, data={"data": q}, timeout=620,
                              headers={"User-Agent": "XXX"})
            r.raise_for_status(); return r.json()["elements"]
        except Exception as e:
            print(u, e); time.sleep(5)
    raise RuntimeError("Overpass недоступен")

def to_df(els):
    return pd.DataFrame([{"osm": f'{e["type"]}/{e["id"]}',
        "lat": e.get("lat") or e.get("center", {}).get("lat"),
        "lon": e.get("lon") or e.get("center", {}).get("lon"), **e.get("tags", {})} for e in els])

FOOD = "supermarket|convenience|grocery|greengrocer|butcher|bakery|alcohol|beverages|seafood|deli|kiosk|general|variety_store"
shops = to_df(overpass(f'nwr["shop"~"^({FOOD}|department_store|mall|clothes|shoes|electronics|mobile_phone|hardware|doityourself|furniture|chemist|cosmetics|pet|books|stationery|gift|sports|florist)$"](area.a);'))
shops["segment"] = np.where(shops["shop"].str.match(f"^({FOOD})$", na=False), "Продукты", "Непродовольственная розница")

# Сеть
CHAINS = {"Пятёрочка": r"пят[её]рочка", "Магнит": r"магнит", "Перекрёсток": r"перекр[её]ст",
          "Лента": r"лента", "Ашан": r"ашан", "Дикси": r"дикси", "Светофор": r"светофор",
          "Красное&Белое": r"красное|белое", "Бристоль": r"бристоль", "Fix Price": r"fix\s*price|фикс\s*прайс",
          "Ярче": r"ярче", "Спар": r"\bспар\b|\bspar\b", "Metro": r"\bmetro\b|метро кэш",
          "Dns": r"\bdns\b|днс", "М.Видео": r"м\.?видео", "Леруа Мерлен": r"леруа", "Wildberries": r"wildberries|вайлдберриз"}
def chain(r):
    s = f"{r.get('brand','')} {r.get('name','')} {r.get('operator','')}".lower()
    for k, rx in CHAINS.items():
        if re.search(rx, s): return k
    return "Независимые/прочие"
shops["chain"] = shops.apply(chain, axis=1)

# Ближайший населённый пункт
pl = to_df(overpass('node["place"~"^(city|town|village|hamlet)$"](area.a);')).dropna(subset=["lat", "lon", "name"])
xy = lambda d: np.c_[d.lon * np.cos(np.radians(47.5)), d.lat]
s = shops.dropna(subset=["lat", "lon"]).copy()
_, i = cKDTree(xy(pl)).query(xy(s))
s["settlement"] = s["addr:city"].fillna(pl.iloc[i]["name"].values)
s = s.drop_duplicates(["chain", "lat", "lon"])
s.to_csv("rostov_shops.csv", index=False, encoding="utf-8-sig")