import json
import time
import os
from dotenv import load_dotenv
from src.classifier.groq_client import GroqClient

load_dotenv()
client = GroqClient(api_key=os.environ['GROQ_API_KEY'], model='openai/gpt-oss-20b')

with open('data/filtered/filtered_items.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data[487:497]

start_time = time.time()
for item in items:
    res = client.classify('Respond with a JSON object {"is_relevant": true}', item.get('content', ''))
    print('.', end='', flush=True)

end_time = time.time()
print(f'\nTime taken for 10 items: {end_time - start_time:.2f} seconds')
