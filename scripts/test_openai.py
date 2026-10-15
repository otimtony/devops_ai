from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

response = client.responses.create(
    model="gpt-4o-mini",
    input="Reply with exactly: DevOpsAI connection successful.",
    max_output_tokens=30,
)

print(response.output_text)
