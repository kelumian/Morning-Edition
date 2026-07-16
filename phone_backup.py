import os
import sys
import subprocess
import requests
from datetime import datetime

# 1. Determine which show we are running
show_argument = sys.argv[1].lower() if len(sys.argv) > 1 else "morning"

# The base Git repository remains Morning-Edition for both
repo_dir = "/root/news/Morning-Edition"

if show_argument in ["shaw", "5h4w"]:
    show_title = "5H4w things considered"
    # Target the subfolder inside the Git repo
    script_dir = os.path.join(repo_dir, "5H4w-things-considered")  
    file_prefix = "shaw_"
    prompt_style = "Write a sharp, analytical executive-level brief focusing on systemic impacts, core data, and strategic context."
    notebook_id_prefix = "phone-shaw-"
else:
    show_title = "Morning Edition"
    script_dir = repo_dir
    file_prefix = "news_"
    prompt_style = "Write a deep-dive, long-form 6th-grade level brief."
    notebook_id_prefix = "phone-backup-"

# Make sure the target directory exists
os.makedirs(script_dir, exist_ok=True)
# Always run Git operations from the repository root
os.chdir(repo_dir)

today_str = datetime.now().strftime("%Y-%m-%d")
today_file = f"{file_prefix}{today_str}.txt"
# Local path where the text file will be saved
output_file_path = os.path.join(script_dir, today_file)

# 2. Grab latest text file history seamlessly from the specific show directory
all_files = os.listdir(script_dir)
historical_files = [f for f in all_files if f.startswith(file_prefix) and f.endswith(".txt") and f != today_file]

yesterday_context = ""
if historical_files:
    historical_files.sort()
    with open(os.path.join(script_dir, historical_files[-1]), "r", encoding="utf-8") as f:
        yesterday_context = f.read()

# 3. Re-verify keys are present on phone
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ Phone Environment Error: GEMINI_API_KEY missing.")

# 4. Request today's fresh content
print(f"🤖 Phone pipeline initiating Gemini text harvest for [{show_title}]...")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
prompt = f"{prompt_style} Target Date: {today_str}. Previous Context/History: {yesterday_context}"

payload = {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]}
response = requests.post(url, json=payload)

if response.status_code == 200:
    try:
        response_json = response.json()
        harvested_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(harvested_text)
        print(f"📝 Text backup successfully saved to {output_file_path}")
    except (KeyError, IndexError) as e:
        print(f"❌ Failed to parse response from Gemini: {e}")
        sys.exit(1)
else:
    print(f"❌ Gemini API request failed with status code {response.status_code}: {response.text}")
    sys.exit(1)

# 5. Force Cloud Sync & RSS Deploy
print("☁️ Shipping backup to Supabase via raw HTTP API & updating RSS tower...")
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if supabase_url and supabase_key and os.path.exists(output_file_path):
    upload_url = f"{supabase_url}/storage/v1/object/podcasts/{today_file}"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "ApiKey": supabase_key,
        "Content-Type": "text/plain"
    }
    
    with open(output_file_path, 'rb') as f:
        upload_resp = requests.post(upload_url, headers=headers, data=f)
    
    if upload_resp.status_code not in [200, 201]:
        print(f"⚠️ Supabase upload warning/error: {upload_resp.text}")
    else:
        print("✅ Success! Backup text file successfully uploaded to Supabase storage bucket.")
    
    # Check for rss.xml relative to the show's specific subdirectory
    rss_path = os.path.join(script_dir, "rss.xml")
    if os.path.exists(rss_path):
        rss_content = open(rss_path, "r", encoding="utf-8").read()
        pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S EST")
        public_url = f"{supabase_url}/storage/v1/object/public/podcasts/{today_file}"
        
        desc = f"Automated text briefing for {show_title} on {today_str}."
        notebook_id = f"{notebook_id_prefix}{today_str}"
        
        new_item = f"""    <item>
          <title>{show_title} - {today_str}</title>
          <description>{desc}</description>
          <pubDate>{pub_date}</pubDate>
          <enclosure url="{public_url}" type="text/plain" length="0"/>
          <itunes:author>Kareem Shaw</itunes:author>
          <guid isPermaLink="false">{notebook_id}</guid>
        </item>"""
        
        updated_rss = rss_content.replace("<!-- EPISODE_ANCHOR -->", new_item + "\n<!-- EPISODE_ANCHOR -->")
        with open(rss_path, "w", encoding="utf-8") as f:
            f.write(updated_rss)
        
        # Git commands run from repo_dir
        subprocess.run(["git", "add", os.path.join(script_dir, "rss.xml"), output_file_path])
        subprocess.run(["git", "commit", "-m", f"Manual phone backup deploy ({show_title}) for {today_str}"])
        subprocess.run(["git", "push", "origin", "main"])
        print(f"🚀 {show_title} successfully deployed via manual phone tower!")
    else:
        print(f"⚠️ rss.xml not found in {script_dir}; skipping RSS generation.")
        subprocess.run(["git", "add", output_file_path])
        subprocess.run(["git", "commit", "-m", f"Manual phone backup text deploy ({show_title}) for {today_str}"])
        subprocess.run(["git", "push", "origin", "main"])
else:
    print(f"❌ Error: Text file ({output_file_path}) or Supabase credentials missing during deployment phase.")
