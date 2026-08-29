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

# =========================
# SUNUCU YAPISI
# =========================

KATEGORILER = {
    "📌 BİLGİ MERKEZİ": [
        "📜・kurallar",
        "📢・duyurular",
        "📖・rp-kuralları",
        "🌍・ülke-bilgileri",
        "🗺️・harita",
        "📚・anayasa",
    ],

    "🏛️ DEVLET": [
        "👑・devlet-başkanlığı",
        "🏛️・meclis",
        "⚖️・anayasa-mahkeme",
        "📜・kanunlar",
        "🏢・bakanlıklar",
        "📋・resmî-kararlar",
    ],

    "🗳️ SİYASET": [
        "🗳️・seçimler",
        "🏴・siyasi-partiler",
        "📢・mitingler",
        "🎤・siyasi-konuşmalar",
        "📊・anketler",
    ],

    "💰 EKONOMİ": [
        "💰・ekonomi",
        "🏦・merkez-bankası",
        "📈・borsa",
        "🏢・şirketler",
        "💼・iş-ilanları",
        "🛒・pazar",
    ],

    "📰 MEDYA": [
        "📰・son-dakika",
        "📺・televizyon",
        "🗞️・gazeteler",
        "🎙️・basın-toplantıları",
    ],

    "👥 HALK": [
        "🏙️・şehirler",
        "💬・şehir-sohbetleri",
        "🏠・evler",
        "👤・vatandaş-kayıt",
        "🛍️・alışveriş",
    ],

    "🌎 DIŞ İLİŞKİLER": [
        "🌎・diplomasi",
        "🤝・antlaşmalar",
        "🏳️・büyükelçilikler",
        "📨・diplomatik-notalar",
    ],

    "⚙️ YÖNETİM": [
        "📋・başvurular",
        "📝・şikayetler",
        "🎫・destek",
        "📂・devlet-arşivi",
    ],
}

ROLLER = [
    ("👑 Devlet Başkanı", discord.Colour.gold()),
    ("⭐ Başkan Yardımcısı", discord.Colour.orange()),
    ("🏛️ Başbakan", discord.Colour.red()),
    ("🏢 Bakan", discord.Colour.blue()),
    ("🗳️ Milletvekili", discord.Colour.purple()),
    ("⚖️ Yargı", discord.Colour.dark_gray()),
    ("👮 Polis", discord.Colour.dark_blue()),
    ("📰 Gazeteci", discord.Colour.yellow()),
    ("🏢 Şirket Sahibi", discord.Colour.green()),
    ("💼 Çalışan", discord.Colour.teal()),
    ("👤 Vatandaş", discord.Colour.light_grey()),
    ("🌱 Yeni Vatandaş", discord.Colour.grey()),
]

# =========================
# BOT HAZIR
# =========================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} aktif!")
    print(f"🌍 Sunucu sayısı: {len(bot.guilds)}")


# =========================
# PING
# =========================

@bot.command()
async def ping(ctx):
    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


# =========================
# KUR KOMUTU
# =========================

@bot.command()
@commands.has_permissions(administrator=True)
async def kur(ctx):

    await ctx.send("🏗️ **Ülke RP sistemi kuruluyor...**")

    guild = ctx.guild

    # -------------------------
    # ROLLER
    # -------------------------

    mevcut_roller = {
        role.name: role
        for role in guild.roles
    }

    olusturulan_roller = 0

    for rol_adi, renk in ROLLER:

        if rol_adi not in mevcut_roller:

            await guild.create_role(
                name=rol_adi,
                colour=renk,
                reason="Ülke RP kurulumu"
            )

            olusturulan_roller += 1

    # -------------------------
    # KATEGORİLER VE KANALLAR
    # -------------------------

    mevcut_kategoriler = {
        category.name: category
        for category in guild.categories
    }

    mevcut_kanallar = {
        channel.name
        for channel in guild.channels
    }

    olusturulan_kanallar = 0

    for kategori_adi, kanallar in KATEGORILER.items():

        if kategori_adi in mevcut_kategoriler:

            kategori = mevcut_kategoriler[kategori_adi]

        else:

            kategori = await guild.create_category(
                kategori_adi,
                reason="Ülke RP kurulumu"
            )

        for kanal_adi in kanallar:

            if kanal_adi not in mevcut_kanallar:

                await guild.create_text_channel(
                    kanal_adi,
                    category=kategori,
                    reason="Ülke RP kurulumu"
                )

                olusturulan_kanallar += 1

    # -------------------------
    # BİLGİ MESAJLARI
    # -------------------------

    kurallar = guild.get_channel(
        next(
            (
                c.id for c in guild.text_channels
                if c.name == "📜・kurallar"
            ),
            0
        )
    )

    if kurallar:

        embed = discord.Embed(
            title="📜 Ülke RP Kuralları",
            description=(
                "**1.** Herkese saygılı davran.\n"
                "**2.** Spam ve reklam yapma.\n"
                "**3.** RP ile gerçek hayatı birbirinden ayır.\n"
                "**4.** Meta Gaming yapma.\n"
                "**5.** Power Gaming yapma.\n"
                "**6.** Diğer oyuncuların RP'sini zorla kontrol etme.\n"
                "**7.** Yetkililerin kararlarına uy.\n"
                "**8.** Açıkları veya bugları kötüye kullanma.\n\n"
                "🎭 **Amaç kazanmak değil, kaliteli RP yapmaktır.**"
            ),
            colour=discord.Colour.blue()
        )

        await kurallar.send(embed=embed)

    bilgi = guild.get_channel(
        next(
            (
                c.id for c in guild.text_channels
                if c.name == "🌍・ülke-bilgileri"
            ),
            0
        )
    )

    if bilgi:

        embed = discord.Embed(
            title="🌍 Yeni Dünya Cumhuriyeti",
            description=(
                "Ülke RP sistemine hoş geldiniz!\n\n"
                "👤 `.kayıt` → Vatandaş ol\n"
                "👤 `.profil` → Profilini görüntüle\n"
                "🌍 `.ülke` → Ülke bilgilerini görüntüle\n"
                "🏢 `.şirketkur` → Şirket kur\n"
                "💰 `.bakiye` → Bakiyeni görüntüle\n"
                "🗳️ `.seçim` → Seçimleri görüntüle"
            ),
            colour=discord.Colour.green()
        )

        await bilgi.send(embed=embed)

    await ctx.send(
        f"✅ **Kurulum tamamlandı!**\n\n"
        f"🎭 Oluşturulan roller: `{olusturulan_roller}`\n"
        f"📁 Oluşturulan kanallar: `{olusturulan_kanallar}`\n\n"
        "🌍 Ülke RP sistemi kullanıma hazır!"
    )


# =========================
# HATA YÖNETİMİ
# =========================

@kur.error
async def kur_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):

        await ctx.send(
            "❌ Bu komutu kullanmak için **Yönetici** yetkisine sahip olmalısın."
        )

    else:

        await ctx.send(
            f"❌ Kurulum sırasında hata oluştu:\n`{error}`"
        )


# =========================
# BOTU BAŞLAT
# =========================

bot.run(TOKEN)
