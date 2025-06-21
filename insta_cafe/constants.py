GOOGLE_GEMINI_EMAIL_PROMPT="""
You are given the HTML source of a public Instagram profile page. 
Extract the following details from the HTML and provide them in a JSON object:

- username: Instagram handle (e.g., @username)
- name: Profile display name
- bio: The biography or description in the profile
- profile_pic_url: URL of the profile picture
- website: Website linked in the profile
- followers: Number of followers
- following: Number of accounts followed
- posts: Number of posts

Output only the final JSON object in this format:

{
  "username": "",
  "name": "",
  "bio": "",
  "profile_pic_url": "",
  "website": "",
  "followers": 0,
  "following": 0,
  "posts": 0
}

Leave any missing or unavailable fields as an empty string or zero. Do not include any explanations or extra text—return **only the JSON object**.
"""