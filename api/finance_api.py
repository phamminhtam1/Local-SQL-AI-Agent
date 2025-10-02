import datetime
from dotenv import load_dotenv
import requests
import os

load_dotenv()
BASE_URL = "https://www.alphavantage.co/query"
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

def get_stock_info(symbol):
    params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": API_KEY}
    response = requests.get(BASE_URL, params= params)
    
    data = response.json()
    print("DEBUG: API response:", data)
    
    return data.get("Global Quote", {})



def get_cpi(month: int, year: int):
    params = {"function": "CPI", "apikey": API_KEY}
    response = requests.get(BASE_URL, params=params)
    
    data = response.json()
    monthly_data = data.get("data", [])
    
    temp = f"{year}-{month:02d}"  
    for d in monthly_data:
        if d["date"].startswith(temp):
            print("DEBUG: Found CPI record:", d, flush=True)
            return d
    
    return {"error": f"No CPI data found for {temp}"}



def get_unemployment(month: int, year: int):
    params = {"function": "UNEMPLOYMENT", "apikey": API_KEY}
    response = requests.get(BASE_URL, params= params)
    
    data = response.json()
    monthly_data = data.get("data", [])
    
    temp = f"{year}-{month:02d}"  
    for d in monthly_data:
        if d["date"].startswith(temp):
            print("DEBUG: Found get_unemployment record:", d, flush=True)
            return d
    
    return {"error": f"No get_unemployment data found for {temp}"}



def get_nonfarm_payroll(month: int, year: int):
    params = {"function": "NONFARM_PAYROLL", "apikey": API_KEY}
    response = requests.get(BASE_URL, params= params)
    
    data = response.json()
    monthly_data = data.get("data", [])
    
    temp = f"{year}-{month:02d}"  
    for d in monthly_data:
        if d["date"].startswith(temp):
            print("DEBUG: Found get_nonfarm_payroll record:", d, flush=True)
            return d
    
    return {"error": f"No get_nonfarm_payroll data found for {temp}"}



def get_fed_rate(month: int, year: int):
    params = {"function": "FEDERAL_FUNDS_RATE", "apikey": API_KEY}
    response = requests.get(BASE_URL, params= params)
    
    data = response.json()
    monthly_data = data.get("data", [])
    
    temp = f"{year}-{month:02d}"  
    for d in monthly_data:
        if d["date"].startswith(temp):
            print("DEBUG: Found get_fed_rate record:", d, flush=True)
            return d
    
    return {"error": f"No get_fed_rate data found for {temp}"}


