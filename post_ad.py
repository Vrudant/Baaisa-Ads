"""Post today's scheduled ad to Instagram. Runs in GitHub Actions at 9 AM IST.
Reads queue/schedule.json, posts the oldest unposted item dated today or earlier,
marks it posted, and refreshes the Instagram token so it never expires.
Uses only the Python standard library.
"""
import datetime, json, os, sys, time, urllib.parse, urllib.request

API = "https://graph.instagram.com/v21.0"
TOKEN = os.environ["IG_TOKEN"]
USER_ID = os.environ["IG_USER_ID"]
REPO = os.environ["GITHUB_REPOSITORY"]  # e.g. Vrudant/Baaisa-Ads
QUEUE = "queue/schedule.json"


def call(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body)) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Instagram error {e.code}: {e.read().decode()}")


def main():
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    today = datetime.datetime.now(ist).date().isoformat()

    # keep the token alive (extends it by 60 days; same token value)
    try:
        call(f"https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token={TOKEN}")
    except SystemExit as e:
        print("Token refresh skipped:", e)

    with open(QUEUE, encoding="utf-8") as f:
        items = json.load(f)
    due = [i for i in items if not i.get("posted") and i["date"] <= today]
    if not due:
        print(f"Nothing scheduled for {today}.")
        return
    item = sorted(due, key=lambda i: i["date"])[0]

    image_url = f"https://raw.githubusercontent.com/{REPO}/main/{item['image']}"
    c = call(f"{API}/{USER_ID}/media", {"image_url": image_url, "caption": item["caption"], "access_token": TOKEN})
    for _ in range(20):
        s = call(f"{API}/{c['id']}?fields=status_code&access_token={TOKEN}")
        if s["status_code"] == "FINISHED":
            break
        if s["status_code"] == "ERROR":
            sys.exit("Instagram could not process the image.")
        time.sleep(3)
    p = call(f"{API}/{USER_ID}/media_publish", {"creation_id": c["id"], "access_token": TOKEN})
    link = call(f"{API}/{p['id']}?fields=permalink&access_token={TOKEN}")["permalink"]
    item["posted"] = True
    item["permalink"] = link
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print("Posted:", link)


if __name__ == "__main__":
    main()
