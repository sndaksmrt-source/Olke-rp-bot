import os
import discord
from discord.ext import commands

# =========================================================
# AYARLAR
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN Railway Variables bölümünde bulunamadı!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=".",
    intents=intents,
    help_command=None
)

# =========================================================
# KATEGORİLER VE KANALLAR
# =========================================================

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

# =========================================================
# ROLLER
# =========================================================

ROLLER = [
    ("👑 Devlet Başkanı", discord.Colour.gold()),
    ("⭐ Başkan Yardımcısı", discord.Colour.orange()),
    ("🏛️ Başbakan", discord.Colour.red()),
    ("🏢 Bakan", discord.Colour.blue()),
    ("🗳️ Milletvekili", discord.Colour.purple()),
    ("⚖️ Yargı", discord.Colour.dark_grey()),
    ("👮 Polis", discord.Colour.dark_blue()),
    ("📰 Gazeteci", discord.Colour.yellow()),
    ("🏢 Şirket Sahibi", discord.Colour.green()),
    ("💼 Çalışan", discord.Colour.teal()),
    ("👤 Vatandaş", discord.Colour.light_grey()),
    ("🌱 Yeni Vatandaş", discord.Colour.light_grey()),
]

# =========================================================
# BOT HAZIR
# =========================================================

@bot.event
async def on_ready():
    print("=" * 40)
    print(f"✅ Bot aktif: {bot.user}")
    print(f"🌍 Sunucu sayısı: {len(bot.guilds)}")
    print("=" * 40)


# =========================================================
# PING
# =========================================================

@bot.command()
async def ping(ctx):
    ms = round(bot.latency * 1000)

    await ctx.send(
        f"🏓 **Pong!** `{ms}ms`"
    )


# =========================================================
# MERHABA
# =========================================================

@bot.command()
async def merhaba(ctx):
    await ctx.send(
        f"👋 Merhaba {ctx.author.mention}!"
    )


# =========================================================
# YARDIM
# =========================================================

@bot.command()
async def yardım(ctx):

    embed = discord.Embed(
        title="🌍 Ülke RP Bot",
        description="Kullanılabilir komutlar:",
        colour=discord.Colour.blue()
    )

    embed.add_field(
        name="⚙️ Sistem",
        value=(
            "`.ping` → Bot gecikmesini gösterir\n"
            "`.merhaba` → Selam verir\n"
            "`.kur` → Ülke RP sistemini kurar"
        ),
        inline=False
    )

    embed.set_footer(
        text="Yeni özellikler yakında eklenecek."
    )

    await ctx.send(embed=embed)


# =========================================================
# KUR KOMUTU
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def kur(ctx):

    guild = ctx.guild

    await ctx.send(
        "🏗️ **Ülke RP sistemi kuruluyor...**\n"
        "⏳ Lütfen biraz bekle."
    )

    # =====================================================
    # ROLLER
    # =====================================================

    mevcut_roller = {
        role.name: role
        for role in guild.roles
    }

    yeni_roller = 0

    for rol_adi, renk in ROLLER:

        if rol_adi not in mevcut_roller:

            try:
                await guild.create_role(
                    name=rol_adi,
                    colour=renk,
                    reason="Ülke RP kurulumu"
                )

                yeni_roller += 1

            except discord.Forbidden:
                await ctx.send(
                    "❌ Botun rol oluşturma izni yok!"
                )
                return

            except discord.HTTPException as error:
                print(f"Rol oluşturma hatası: {error}")

    # =====================================================
    # KATEGORİLER
    # =====================================================

    mevcut_kategoriler = {
        category.name: category
        for category in guild.categories
    }

    mevcut_kanallar = {
        channel.name
        for channel in guild.channels
    }

    yeni_kanallar = 0
    yeni_kategoriler = 0

    for kategori_adi, kanallar in KATEGORILER.items():

        # Kategori zaten varsa kullan
        if kategori_adi in mevcut_kategoriler:

            kategori = mevcut_kategoriler[kategori_adi]

        else:

            try:
                kategori = await guild.create_category(
                    name=kategori_adi,
                    reason="Ülke RP kurulumu"
                )

                yeni_kategoriler += 1

            except discord.Forbidden:
                await ctx.send(
                    "❌ Botun kategori oluşturma izni yok!"
                )
                return

            except discord.HTTPException as error:
                print(f"Kategori hatası: {error}")
                continue

        # =================================================
        # KANALLAR
        # =================================================

        for kanal_adi in kanallar:

            if kanal_adi in mevcut_kanallar:
                continue

            try:

                await guild.create_text_channel(
                    name=kanal_adi,
                    category=kategori,
                    reason="Ülke RP kurulumu"
                )

                yeni_kanallar += 1

            except discord.Forbidden:
                await ctx.send(
                    "❌ Botun kanal oluşturma izni yok!"
                )
                return

            except discord.HTTPException as error:
                print(f"Kanal hatası: {error}")

    # =====================================================
    # KURALLAR MESAJI
    # =====================================================

    kurallar = discord.utils.get(
        guild.text_channels,
        name="📜・kurallar"
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
                "**6.** Diğer oyuncuların karakterini izinsiz kontrol etme.\n"
                "**7.** Yetkililerin kararlarına uy.\n"
                "**8.** Bug ve açıkları kötüye kullanma.\n"
                "**9.** RP ortamını bozacak davranışlardan kaçın.\n\n"
                "🎭 **Amaç kazanmak değil, kaliteli RP yapmaktır.**"
            ),
            colour=discord.Colour.blue()
        )

        await kurallar.send(embed=embed)

    # =====================================================
    # ÜLKE BİLGİSİ
    # =====================================================

    bilgi = discord.utils.get(
        guild.text_channels,
        name="🌍・ülke-bilgileri"
    )

    if bilgi:

        embed = discord.Embed(
            title="🌍 Yeni Dünya Cumhuriyeti",
            description=(
                "🇹🇷 **Ülke RP sistemine hoş geldiniz!**\n\n"
                "Bu sunucuda kendi karakterinizi oluşturabilir, "
                "çalışabilir, şirket kurabilir, siyasete katılabilir "
                "ve ülkenin gelişimine katkıda bulunabilirsiniz.\n\n"
                "👤 `.kayıt`\n"
                "👤 `.profil`\n"
                "🌍 `.ülke`\n"
                "💰 `.bakiye`\n"
                "🏢 `.şirketkur`\n"
                "🗳️ `.seçim`\n\n"
                "🚀 **İyi RP'ler!**"
            ),
            colour=discord.Colour.green()
        )

        await bilgi.send(embed=embed)

    # =====================================================
    # SONUÇ
    # =====================================================

    embed = discord.Embed(
        title="✅ Kurulum Tamamlandı!",
        description=(
            "🇹🇷 **Ülke RP sistemi başarıyla kuruldu.**\n\n"
            f"📁 Yeni kategoriler: `{yeni_kategoriler}`\n"
            f"💬 Yeni kanallar: `{yeni_kanallar}`\n"
            f"🎭 Yeni roller: `{yeni_roller}`\n\n"
            "🌍 Sunucunuz RP için hazır!"
        ),
        colour=discord.Colour.green()
    )

    await ctx.send(embed=embed)


# =========================================================
# KUR HATA YÖNETİMİ
# =========================================================

@kur.error
async def kur_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):

        await ctx.send(
            "❌ Bu komutu kullanmak için **Yönetici** yetkisine sahip olmalısın."
        )

    elif isinstance(error, commands.BotMissingPermissions):

        await ctx.send(
            "❌ Botun gerekli Discord izinlerine sahip değil."
        )

    else:

        print(f".kur hatası: {error}")

        await ctx.send(
            f"❌ Kurulum sırasında hata oluştu:\n```{error}```"
        )


# =========================================================
# GENEL HATA YÖNETİMİ
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):

        await ctx.send(
            "❌ Komutu eksik kullandın. `.yardım` yazarak komutları görebilirsin."
        )

        return

    if isinstance(error, commands.MissingPermissions):

        await ctx.send(
            "❌ Bu komutu kullanmak için gerekli yetkiye sahip değilsin."
        )

        return

    print(f"Komut hatası: {error}")


# =========================================================
# BAŞLAT
# =========================================================

bot.run(TOKEN)
