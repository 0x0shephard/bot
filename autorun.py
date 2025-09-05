
import requests


url = "https://basxvmmtxwlxylpukqjj.supabase.co/functions/v1/fetch-price"

try:
    response = requests.get(url)
    response.raise_for_status()  
    print("Response:", response.text)
except requests.exceptions.RequestException as err:
    print("Error occurred:", err)
