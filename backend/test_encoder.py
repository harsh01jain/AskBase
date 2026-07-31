from fastapi.encoders import jsonable_encoder
from datetime import date
from psycopg2.extras import RealDictRow
import json

# Create a dummy cursor description to initialize RealDictRow properly if needed
# Actually RealDictRow might need a RealDictCursor to initialize, 
# but let's just make a dict subclass.
class DummyRow(dict):
    pass

r = DummyRow()
r['signup_date'] = date(2023, 1, 15)

payload = {'type': 'result', 'results': {'rows': [r]}}
try:
    encoded = jsonable_encoder(payload)
    print("ENCODED:", encoded)
    print("JSON:", json.dumps(encoded))
except Exception as e:
    print("ERROR:", e)
