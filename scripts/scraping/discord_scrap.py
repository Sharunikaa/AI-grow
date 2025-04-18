import discord
import pymongo
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
mongo_client = pymongo.MongoClient(MONGODB_URI)
db = mongo_client["company_data"]
collection = db["discord_data"]

PRODUCT_CATEGORIES = ["earbuds", "skincare", "storage", "plushies", "cosmetics", "stationery", "toys", "home goods"]

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
discord_client = discord.Client(intents=intents)

async def store_in_mongodb(data):
    existing_ids = set(doc["record_id"] for doc in collection.find({"record_id": {"$in": [d["record_id"] for d in data]}}))
    new_data = [d for d in data if d["record_id"] not in existing_ids]
    if new_data:
        collection.insert_many(new_data)
        print(f"Stored {len(new_data)} Discord messages")

async def scrape_channel(channel):
    messages = []
    async for message in channel.history(limit=100):
        message_content = message.content.lower()
        # Tag product category based on content
        category = next((cat for cat in PRODUCT_CATEGORIES if cat in message_content), "general")
        message_data = {
            "record_id": str(message.id),
            "platform": "Discord",
            "content": message.content,
            "author": str(message.author),
            "author_id": str(message.author.id),
            "timestamp": message.created_at.isoformat(),
            "engagement_metrics": {
                "upvotes": 0,
                "comments": 0,
                "shares": 0,
                "likes": sum(r.count for r in message.reactions),
                "follows": 0
            },
            "product_category": category,
            "platform_specific": {
                "channel_name": channel.name,
                "guild_name": channel.guild.name
            },
            "raw_data": {"message_id": message.id}
        }
        messages.append(message_data)
    if messages:
        await store_in_mongodb(messages)

@discord_client.event
async def on_ready():
    print(f"Logged in as {discord_client.user}")
    TARGET_SERVER_ID = 1343290576677896192
    target_server = discord_client.get_guild(TARGET_SERVER_ID)
    if not target_server:
        print(f"Server {TARGET_SERVER_ID} not found.")
        await discord_client.close()
        return
    for channel in target_server.text_channels:
        if channel.permissions_for(target_server.me).read_messages:
            print(f"Scraping channel: {channel.name}")
            await scrape_channel(channel)
    await discord_client.close()

if __name__ == "__main__":
    discord_client.run(DISCORD_BOT_TOKEN)
