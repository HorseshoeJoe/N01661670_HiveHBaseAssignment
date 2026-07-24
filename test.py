import requests
r = requests.get("http://10.118.12.193:60080/version/cluster")
print(r.status_code, r.text)