"""
RE AI Suite - Lead Generation Module v1.0
Data Source: US Census Bureau ACS5 (Free)
Upgrade Path: Swap _fetch_census_data() for _fetch_attom_data() post-revenue
"""
 
import requests
import json
import csv
import os
from datetime import datetime
 
# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
CENSUS_API_KEY = "981ef300b8ed9cfbc235b85c13e8ce18f7817230"   # Replace this with your key
ATTOM_API_KEY  = None
 
VACANCY_THRESHOLD  = 10.0
POVERTY_THRESHOLD  = 15.0
RENTER_THRESHOLD   = 60.0
 
OUTPUT_DIR = "re_leads_output"
 
# ─────────────────────────────────────────────
#  CENSUS DATA FETCHER
# ─────────────────────────────────────────────
def _fetch_census_data(zip_codes: list) -> list:
    zips = ",".join(zip_codes)
    url = "https://api.census.gov/data/2022/acs/acs5"
    params = {
        "get": "NAME,B25002_001E,B25002_003E,B25003_001E,B25003_002E,B17001_001E,B17001_002E",
        "for": f"zip code tabulation area:{zips}",
        "key": CENSUS_API_KEY
    }
 
    print(f"  → Querying Census API for {len(zip_codes)} zip code(s)...")
 
    if CENSUS_API_KEY == "YOUR_CENSUS_API_KEY":
        raise ValueError(
            "\n\n  ❌ API key not set!\n"
            "  Get your free key at: https://api.census.gov/data/key_signup.html\n"
            "  Replace YOUR_CENSUS_API_KEY on line 19 of this file.\n"
        )
 
    response = requests.get(url, params=params, timeout=15)
 
    print(f"  → Status code: {response.status_code}")
    print(f"  → Response preview: {repr(response.text[:400])}")
 
    if "Invalid Key" in response.text or "invalid key" in response.text.lower():
        raise ValueError(
            "\n\n  ❌ Census API says: Invalid Key\n"
            "  Your key may not be activated yet — keys take up to 1 hour after signup.\n"
            "  Check your email for a confirmation/activation link and try again.\n"
        )
 
    if response.status_code == 400:
        raise ValueError(
            f"\n\n  ❌ Census API returned 400.\n"
            f"  Response: {response.text.strip()}\n"
        )
 
    response.raise_for_status()
 
    if not response.text.strip():
        raise ValueError("\n\n  ❌ Census API returned an empty response.\n")
 
    try:
        raw = response.json()
    except Exception:
        raise ValueError(
            f"\n\n  ❌ Could not parse Census response as JSON.\n"
            f"  Raw response: {response.text[:500]}\n"
        )
 
    headers = raw[0]
    rows    = raw[1:]
    results = []
    for row in rows:
        record = dict(zip(headers, row))
        results.append(record)
 
    return results
 
 
# ─────────────────────────────────────────────
#  ATTOM DATA FETCHER (post-revenue upgrade)
# ─────────────────────────────────────────────
def _fetch_attom_data(zip_codes: list) -> list:
    all_properties = []
    for zip_code in zip_codes:
        url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/snapshot"
        headers = {
            "Accept": "application/json",
            "apikey": ATTOM_API_KEY
        }
        params = {
            "postalcode": zip_code,
            "propertytype": "SFR",
            "foreclosurestatus": "default",
            "pagesize": 50
        }
        print(f"  → Querying ATTOM API for zip {zip_code}...")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        properties = data.get("property", [])
        for prop in properties:
            all_properties.append({
                "zip":          zip_code,
                "address":      prop.get("address", {}).get("oneLine", "N/A"),
                "beds":         prop.get("building", {}).get("rooms", {}).get("beds", "N/A"),
                "baths":        prop.get("building", {}).get("rooms", {}).get("bathsFull", "N/A"),
                "est_value":    prop.get("avm", {}).get("amount", {}).get("value", "N/A"),
                "last_sale":    prop.get("sale", {}).get("amount", {}).get("saleamt", "N/A"),
                "distress_flag": "pre-foreclosure"
            })
    return all_properties
 
 
# ─────────────────────────────────────────────
#  LEAD SCORER
# ─────────────────────────────────────────────
def score_lead(vacancy_rate, poverty_rate, renter_rate):
    signals = sum([
        vacancy_rate >= VACANCY_THRESHOLD,
        poverty_rate >= POVERTY_THRESHOLD,
        renter_rate  >= RENTER_THRESHOLD
    ])
    if signals == 3: return "HOT"
    elif signals == 2: return "WARM"
    else: return "COLD"
 
 
# ─────────────────────────────────────────────
#  MAIN PROCESSOR
# ─────────────────────────────────────────────
def process_leads(zip_codes):
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  RE AI Suite — Lead Generation v1.0")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Mode:       Census Bureau ACS5 (Free)")
    print(f"  Zips:       {', '.join(zip_codes)}")
    print(f"  Thresholds: Vacancy>{VACANCY_THRESHOLD}% | Poverty>{POVERTY_THRESHOLD}% | Renter>{RENTER_THRESHOLD}%")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
 
    raw_data = _fetch_census_data(zip_codes)
    leads    = []
 
    for record in raw_data:
        try:
            total_units  = int(record["B25002_001E"])
            vacant_units = int(record["B25002_003E"])
            total_occ    = int(record["B25003_001E"])
            owner_occ    = int(record["B25003_002E"])
            total_pop    = int(record["B17001_001E"])
            poverty_pop  = int(record["B17001_002E"])
            zip_code     = record["zip code tabulation area"]
            name         = record["NAME"]
 
            vacancy_rate = (vacant_units / total_units * 100) if total_units > 0 else 0
            renter_occ   = total_occ - owner_occ
            renter_rate  = (renter_occ / total_occ * 100) if total_occ > 0 else 0
            poverty_rate = (poverty_pop / total_pop * 100) if total_pop > 0 else 0
            score        = score_lead(vacancy_rate, poverty_rate, renter_rate)
 
            leads.append({
                "zip":             zip_code,
                "area_name":       name,
                "score":           score,
                "vacancy_rate":    round(vacancy_rate, 2),
                "poverty_rate":    round(poverty_rate, 2),
                "renter_rate":     round(renter_rate,  2),
                "total_units":     total_units,
                "vacant_units":    vacant_units,
                "owner_occupied":  owner_occ,
                "renter_occupied": renter_occ,
            })
 
        except (ValueError, ZeroDivisionError, KeyError) as e:
            print(f"  ⚠️  Skipped zip {record.get('zip code tabulation area', '?')}: {e}")
            continue
 
    order = {"HOT": 0, "WARM": 1, "COLD": 2}
    leads.sort(key=lambda x: order.get(x["score"], 3))
    return leads
 
 
# ─────────────────────────────────────────────
#  EXPORT
# ─────────────────────────────────────────────
def export_json(leads, filepath):
    with open(filepath, "w") as f:
        json.dump(leads, f, indent=2)
    print(f"  ✅ JSON saved → {filepath}")
 
def export_csv(leads, filepath):
    if not leads:
        print("  ⚠️  No leads to export.")
        return
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=leads[0].keys())
        writer.writeheader()
        writer.writerows(leads)
    print(f"  ✅ CSV  saved → {filepath}")
 
def print_summary(leads):
    hot  = [l for l in leads if l["score"] == "HOT"]
    warm = [l for l in leads if l["score"] == "WARM"]
    cold = [l for l in leads if l["score"] == "COLD"]
 
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  RESULTS: {len(leads)} zip codes scored")
    print(f"  HOT  : {len(hot)}")
    print(f"  WARM : {len(warm)}")
    print(f"  COLD : {len(cold)}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
 
    print(f"  {'ZIP':<8} {'SCORE':<8} {'VACANCY':>8} {'POVERTY':>8} {'RENTER':>8}  AREA")
    print(f"  {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}  {'─'*30}")
    for lead in leads:
        print(
            f"  {lead['zip']:<8} {lead['score']:<8} "
            f"{lead['vacancy_rate']:>7.1f}% "
            f"{lead['poverty_rate']:>7.1f}% "
            f"{lead['renter_rate']:>7.1f}%  "
            f"{lead['area_name']}"
        )
    print()
 
 
# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
 
    TARGET_ZIPS = [
        "94601",
        "94621",
        "94103",
        "89101",
        "89106",
        "30310",
        "60621",
        "77051",
    ]
 
    leads = process_leads(TARGET_ZIPS)
    print_summary(leads)
 
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_json(leads, f"{OUTPUT_DIR}/leads_{timestamp}.json")
    export_csv( leads, f"{OUTPUT_DIR}/leads_{timestamp}.csv")
 
    print(f"\n  Done. Files saved to /{OUTPUT_DIR}/\n")