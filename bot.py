import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=".",
    intents=intents
)

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı!")
    print(f"{len(bot.guilds)} sunucuda aktif.")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def merhaba(ctx):
    await ctx.send(f"👋 Merhaba {ctx.author.mention}!")

bot.run(TOKEN)
