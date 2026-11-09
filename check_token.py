"""Token türünü ve bitiş tarihini yazdırır (token'ın kendisini yazdırmaz)."""
import datetime
import requests
from bot import ACCESS_TOKEN, BASE_URL

r = requests.get(f"{BASE_URL}/debug_token",
                 params={"input_token": ACCESS_TOKEN, "access_token": ACCESS_TOKEN}, timeout=30)
d = r.json().get("data", r.json())
exp = d.get("expires_at")
print("Tür      :", d.get("type"))
print("Geçerli  :", d.get("is_valid"))
print("Bitiş    :", "ASLA (süresiz)" if exp == 0 else
      datetime.datetime.fromtimestamp(exp, datetime.timezone.utc) if exp else d)
