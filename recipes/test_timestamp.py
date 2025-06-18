import jwt
import time

secret = "mysecretkey"

# Create token with 1-second expiry
token = jwt.encode({"some": "payload", "exp": time.time() + 1}, secret, algorithm="HS256")

time.sleep(2)  # Wait 2 seconds so token expires

try:
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
except jwt.ExpiredSignatureError:
    print("Token has expired!")

