import requests
 
CENSUS_API_KEY = "981ef300b8ed9cfbc235b85c13e8ce18f7817230"  # <-- paste your key here
 
url = "https://api.census.gov/data/2022/acs/acs5"
params = {
    "get": "NAME,B25002_001E,B25002_003E,B25003_001E,B25003_002E,B17001_001E,B17001_002E",
    "for": "zip code tabulation area:94601,94621",
    "key": CENSUS_API_KEY
}
 
response = requests.get(url, params=params, timeout=15)
print(f"Status code : {response.status_code}")
print(f"Raw response: {repr(response.text[:500])}")
 