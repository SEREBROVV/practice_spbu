import time, requests, pandas as pd

BASE = "https://opendata.trudvsem.ru/api/v1/vacancies/region/6100000000000"
LIMIT = 100
S = requests.Session()
S.headers["User-Agent"] = "XXX"

def get_page(offset, retries=5):
    for i in range(retries):
        try:
            r = S.get(BASE, params={"offset": offset, "limit": LIMIT}, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            time.sleep(2 ** i)
    raise RuntimeError(f"offset={offset} не загрузился")

# В этом API offset обычно номер страницы (0, 1, 2...), а не число записей.
first = get_page(0)
print("meta:", first.get("meta"))

raw, seen, offset = [], set(), 0
while True:
    data = first if offset == 0 else get_page(offset)
    items = [x["vacancy"] for x in data.get("results", {}).get("vacancies", [])]
    new = [v for v in items if v["id"] not in seen]
    if not items or not new:      # пусто или страница повторилась: конец
        break
    seen.update(v["id"] for v in new)
    raw.extend(new)
    print(offset, len(raw))
    offset += 1
    time.sleep(0.3)

def flat(v):
    emp = v.get("company") or v.get("employer") or {}
    addr = (v.get("addresses") or {}).get("address") or [{}]
    cat = v.get("category") or {}
    return {
        "id": v.get("id"),
        "profession": v.get("job-name"),
        "specialisation": cat.get("specialisation"),
        "salary_min": v.get("salary_min"),
        "salary_max": v.get("salary_max"),
        "employment": v.get("employment"),
        "schedule": v.get("schedule"),
        "education": (v.get("requirement") or {}).get("education"),
        "experience": (v.get("requirement") or {}).get("experience"),
        "employer": emp.get("name"),
        "inn": emp.get("inn"),
        "address": addr[0].get("location"),
        "lat": addr[0].get("lat"),
        "lon": addr[0].get("lng"),
        "created": v.get("creation-date"),
        "url": v.get("vac_url"),
    }

df = pd.DataFrame(flat(v) for v in raw)
for c in ("salary_min", "salary_max"):
    df[c] = pd.to_numeric(df[c], errors="coerce").replace(0, pd.NA)
df.to_csv("trudvsem_rostov.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(raw).to_json("trudvsem_rostov_raw.json", force_ascii=False, orient="records")
print(len(df), "вакансий")