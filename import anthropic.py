import anthropic

# Initialize the Gemini client
client = anthropic.Anthropic(api_key="YOUR_API_KEY")

# Test the API with a simple prompt
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.content[0].text)