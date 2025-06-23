GOOGLE_GEMINI_EMAIL_PROMPT="""
You are given the Instagram URL . 
Extract the following details from the HTML and provide them in a JSON object:

- username: Instagram handle (e.g., @username)

Output only the final JSON object in this format:

{
  "username": "",
}

Do not include any explanations or extra text—return **only the JSON object**.
"""