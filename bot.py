import random
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=["owo ", "OwO ", "OWO "], intents=intents, case_insensitive=True)

# Kendi Discord Kullanıcı ID'ni buraya yazmalısın! (Sadece sen owo ver komutunu kullanabileceksin)
OWNER_ID = 123456789012345678  # <- Burayı kendi Discord ID'n ile değiştir!

users = {}

def get_user_data(user_id):
    if user_id not in users:
        users[user_id] = {
            "balance": 1000,
            "inventory": {},
            "zoo": {},
            "daily_claimed": False
        }
    return users[user_id]

SHOP_ITEMS = {
    "1": {"name": "Lasso", "price": 100, "desc": "Hunting tool"},
    "2": {"name": "Crate", "price": 500, "desc": "Loot box"},
    "3": {"name": "Ring", "price": 2000, "desc": "Shiny accessory"}
}

ANIMALS = ["🐱 Cat", "🐶 Dog", "🐰 Bunny", "🦊 Fox", "🐻 Bear", "🦁 Lion", "🦄 Unicorn"]

@bot.event
async def on_ready():
    print(f"{bot.user.name} OwO Botu aktif!")

# 1. owo cash / owo cowoncy
@bot.command(aliases=["cowoncy"])
async def cash(ctx):
    data = get_user_data(ctx.author.id)
    await ctx.send(f"💵 | **{ctx.author.name}**, currently have **{data['balance']:,}** cowoncy!")

# 2. owo cf <miktar>
@bot.command()
async def cf(ctx, amount: str = None):
    if not amount or not amount.isdigit():
        await ctx.send("❓ | Lütfen geçerli bir bakiye girin! Örn: `owo cf 100`")
        return

    val = int(amount)
    data = get_user_data(ctx.author.id)

    if val <= 0 or val > data["balance"]:
        await ctx.send("❌ | Yetersiz bakiye veya geçersiz miktar!")
        return

    won = random.choice([True, False])
    choice = random.choice(["heads", "tails"])

    if won:
        data["balance"] += val
        await ctx.send(f"🪙 | **{ctx.author.name}** spent **{val:,}** 💵 and chose **{choice}**... and won **{val:,}** 💵!")
    else:
        data["balance"] -= val
        await ctx.send(f"🪙 | **{ctx.author.name}** spent **{val:,}** 💵 and chose **{choice}**... and lost it all... :c")

# 3. owo s <miktar>
@bot.command()
async def s(ctx, amount: str = None):
    if not amount or not amount.isdigit():
        await ctx.send("❓ | Lütfen geçerli bir bakiye girin! Örn: `owo s 100`")
        return

    val = int(amount)
    data = get_user_data(ctx.author.id)

    if val <= 0 or val > data["balance"]:
        await ctx.send("❌ | Yetersiz bakiye veya geçersiz miktar!")
        return

    icons = ["🍆", "💖", "7️⃣", "🍒", "💎"]
    s1, s2, s3 = random.choice(icons), random.choice(icons), random.choice(icons)

    if s1 == s2 == s3:
        win = val * 3
        data["balance"] += win
        res = f"and won **{win:,}** 💵!"
    elif s1 == s2 or s2 == s3 or s1 == s3:
        win = val
        data["balance"] += win
        res = f"and won **{win:,}** 💵!"
    else:
        data["balance"] -= val
        res = f"and lost **{val:,}** 💵... :c"

    await ctx.send(f"___SLOTS___\n| {s1} | {s2} | {s3} | **{ctx.author.name}** bet **{val:,}** 💵 {res}")

# 4. owo daily
@bot.command()
async def daily(ctx):
    data = get_user_data(ctx.author.id)
    reward = 5000
    data["balance"] += reward
    await ctx.send(f"📅 | **{ctx.author.name}**, günlük **{reward:,}** cowoncy ödülünü aldın!")

# 5. owo give @kullanıcı miktar
@bot.command()
async def give(ctx, member: discord.Member = None, amount: int = None):
    if not member or not amount or amount <= 0:
        await ctx.send("❓ | Kullanım: `owo give @kullanıcı <miktar>`")
        return

    sender = get_user_data(ctx.author.id)
    if sender["balance"] < amount:
        await ctx.send("❌ | Yetersiz bakiye!")
        return

    receiver = get_user_data(member.id)
    sender["balance"] -= amount
    receiver["balance"] += amount

    await ctx.send(f"🤝 | **{ctx.author.name}**, **{member.name}** kullanıcısına **{amount:,}** 💵 gönderdi!")

# 6. owo ver <miktar> (Sadece senin kullanabileceğin para ekleme komutu)
@bot.command()
async def ver(ctx, amount: int = None):
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ | Bu komutu sadece botun sahibi kullanabilir!")
        return
    
    if not amount or amount <= 0:
        await ctx.send("❓ | Lütfen geçerli bir miktar girin! Örn: `owo ver 50000`")
        return

    data = get_user_data(ctx.author.id)
    data["balance"] += amount
    await ctx.send(f"👑 | Patron! Hesabına başarıyla **{amount:,}** 💵 eklendi. Güncel bakiye: **{data['balance']:,}** 💵")

# 7. owo shop
@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 OwO Shop", color=discord.Color.blue())
    for item_id, info in SHOP_ITEMS.items():
        embed.add_field(name=f"`{item_id}` - {info['name']}", value=f"Fiyat: **{info['price']:,}** 💵\nAçıklama: {info['desc']}", inline=False)
    await ctx.send(embed=embed)

# 8. owo buy <id>
@bot.command()
async def buy(ctx, item_id: str = None):
    if not item_id or item_id not in SHOP_ITEMS:
        await ctx.send("❓ | Geçerli bir ürün ID'si girin! Örn: `owo buy 1`")
        return

    item = SHOP_ITEMS[item_id]
    data = get_user_data(ctx.author.id)

    if data["balance"] < item["price"]:
        await ctx.send("❌ | Yetersiz bakiye!")
        return

    data["balance"] -= item["price"]
    data["inventory"][item["name"]] = data["inventory"].get(item["name"], 0) + 1
    await ctx.send(f"🛍️ | **{ctx.author.name}**, başarıyla **{item['name']}** satın aldın!")

# 9. owo inv
@bot.command()
async def inv(ctx):
    data = get_user_data(ctx.author.id)
    inv_list = data["inventory"]
    
    if not inv_list:
        await ctx.send(f"🎒 | **{ctx.author.name}**, envanterin boş!")
        return

    desc = "\n".join([f"• **{k}**: {v}x" for k, v in inv_list.items()])
    embed = discord.Embed(title=f"🎒 {ctx.author.name}'in Envanteri", description=desc, color=discord.Color.green())
    await ctx.send(embed=embed)

# 10. owo hunt
@bot.command()
async def hunt(ctx):
    data = get_user_data(ctx.author.id)
    caught = random.choice(ANIMALS)
    data["zoo"][caught] = data["zoo"].get(caught, 0) + 1
    await ctx.send(f"🌿 | **{ctx.author.name}** avlanmaya çıktı ve bir **{caught}** yakaladı!")

# 11. owo zoo
@bot.command()
async def zoo(ctx):
    data = get_user_data(ctx.author.id)
    zoo_list = data["zoo"]

    if not zoo_list:
        await ctx.send(f"🐾 | **{ctx.author.name}**, hayvan koleksiyonun henüz boş! `owo hunt` yazarak avlan.")
        return

    desc = "\n".join([f"{k}: **{v}** tane" for k, v in zoo_list.items()])
    embed = discord.Embed(title=f"🐾 {ctx.author.name}'in Hayvanat Bahçesi", description=desc, color=discord.Color.gold())
    await ctx.send(embed=embed)

# 12. owo quest
@bot.command()
async def quest(ctx):
    quests = [
        "🎯 **Görev:** 3 kez `owo hunt` yap. (Ödül: 1,000 💵)",
        "🎯 **Görev:** 1 kez `owo cf` kazan. (Ödül: 2,500 💵)",
        "🎯 **Görev:** Bir arkadaşına `owo give` ile para at. (Ödül: 500 💵)"
    ]
    await ctx.send(f"📜 | **{ctx.author.name}**, günün görevi:\n{random.choice(quests)}")

# 13. owo cl (Checklist)
@bot.command()
async def cl(ctx):
    embed = discord.Embed(title=f"📋 {ctx.author.name}'in Günlük Checklist'i", color=discord.Color.purple())
    embed.add_field(name="Daily", value="✅ Alındı" if get_user_data(ctx.author.id)["daily_claimed"] else "❌ Alınmadı (`owo daily`)", inline=False)
    embed.add_field(name="Vote", value="❌ Oylanmadı", inline=False)
    embed.add_field(name="Quest", value="🔄 Devam ediyor (`owo quest`)", inline=False)
    await ctx.send(embed=embed)

bot.run("YOUR_BOT_TOKEN_HERE")
