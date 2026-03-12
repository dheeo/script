import json, hmac, hashlib, base64, struct, io
import cloudscraper
from PIL import Image
import discord
from discord import app_commands

ACC_URL = "https://api.rec.net/api/images/v4/uploadsaved"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def get_sig(key_b64, uri, body):
    key = base64.b64decode(key_b64)
    h = hmac.new(key, digestmod=hashlib.sha256)
    h.update(uri.encode('ascii'))

    if body:
        h.update(struct.pack('<I', len(body)))

        if len(body) > 2048:
            step = len(body) // 16
            for i in range(16):
                h.update(body[i * step : i * step + 128])
        else:
            h.update(body)

    return base64.b64encode(h.digest()).decode()

@tree.command(name="upload", description="Upload image to RecNet")
@app_commands.describe(image="Upload image", bearer="RecNet Bearer Token", key="RecNet Key")
async def upload(interaction: discord.Interaction, image: discord.Attachment, bearer: str, key: str):

    await interaction.response.defer()

    img_bytes = await image.read()
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_data = buf.getvalue()

    uri = "/api/images/v4/uploadsaved"

    meta = json.dumps({
        "playerIds": None,
        "savedImageType": 1,
        "roomId": 1,
        "playerEventId": 0,
        "accessibility": 0,
        "description": None
    }, separators=(',', ':'))

    bd = "Boundary123"

    body = (f"--{bd}\r\nContent-Disposition: form-data; name=\"imgMeta\"\r\n\r\n{meta}\r\n"
            f"--{bd}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"file.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + img_data + f"\r\n--{bd}--\r\n".encode()

    headers = {
        "Authorization": f"Bearer {bearer}",
        "X-RNSIG": get_sig(key, uri, body),
        "Content-Type": f"multipart/form-data; boundary={bd}",
        "User-Agent": "BestHTTP"
    }

    scraper = cloudscraper.create_scraper()
    r = scraper.post(ACC_URL, data=body, headers=headers)

    if r.status_code == 200:
        res = r.json()
        url = f"https://img.rec.net/{res.get('ImageName')}"
        await interaction.followup.send(url)
    else:
        await interaction.followup.send("Upload failed")

@client.event
async def on_ready():
    await tree.sync()
    print("Bot Ready")

token = input("Enter Discord Bot Token: ")
client.run(token)
