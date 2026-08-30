import os
import sqlite3
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

# =========================================================
# AYARLAR
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("DB_PATH", "/data/ulke_rp.db")
PREFIX = "."

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN Railway Variables kısmında yok!")

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

# =========================================================
# VERİTABANI
# =========================================================

db = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

db.row_factory = sqlite3.Row

db.executescript("""
CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER PRIMARY KEY,
    country_created INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    balance INTEGER DEFAULT 1000,
    bank INTEGER DEFAULT 0,
    job TEXT DEFAULT 'İşsiz',
    country TEXT DEFAULT '',
    factory_count INTEGER DEFAULT 0,
    last_work INTEGER DEFAULT 0,
    registered_at TEXT NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS countries (
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    owner_id INTEGER DEFAULT 0,
    president_id INTEGER DEFAULT 0,
    treasury INTEGER DEFAULT 100000,
    population INTEGER DEFAULT 0,
    army INTEGER DEFAULT 0,
    defense INTEGER DEFAULT 0,
    last_income INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, name)
);

CREATE TABLE IF NOT EXISTS country_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    country TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS factories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    country TEXT NOT NULL,
    name TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    price INTEGER NOT NULL,
    hourly_income INTEGER NOT NULL,
    last_paid INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inventory (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    item TEXT NOT NULL,
    amount INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, item)
);

CREATE TABLE IF NOT EXISTS wars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    attacker TEXT NOT NULL,
    defender TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    started_at TEXT NOT NULL,
    ended_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS war_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    war_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diplomacy (
    guild_id INTEGER NOT NULL,
    country1 TEXT NOT NULL,
    country2 TEXT NOT NULL,
    status TEXT DEFAULT 'neutral',
    PRIMARY KEY (guild_id, country1, country2)
);

CREATE TABLE IF NOT EXISTS elections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    country TEXT NOT NULL,
    candidate_id INTEGER NOT NULL,
    votes INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS votes (
    guild_id INTEGER NOT NULL,
    election_id INTEGER NOT NULL,
    voter_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, election_id, voter_id)
);
""")

db.commit()

# =========================================================
# YARDIMCI
# =========================================================

def now():
    return int(datetime.now(timezone.utc).timestamp())


def get_user(guild_id, user_id):
    return db.execute(
        """
        SELECT *
        FROM users
        WHERE guild_id=? AND user_id=?
        """,
        (guild_id, user_id)
    ).fetchone()


def create_user(guild_id, user_id, name):
    existing = get_user(guild_id, user_id)

    if existing:
        return existing

    db.execute(
        """
        INSERT INTO users
        (
            guild_id,
            user_id,
            name,
            registered_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            guild_id,
            user_id,
            name,
            datetime.now(timezone.utc).isoformat()
        )
    )

    db.commit()

    return get_user(guild_id, user_id)


def get_country(guild_id, country):
    return db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=? AND name=?
        """,
        (guild_id, country)
    ).fetchone()


def get_owned_country(guild_id, user_id):
    return db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=?
        AND owner_id=?
        """,
        (guild_id, user_id)
    ).fetchone()


def is_staff(member):
    names = {
        "👑 Kurucu",
        "🛡️ Baş Yönetici",
        "🔧 Yönetici",
        "🔨 Baş Moderatör",
        "🛡️ Moderatör"
    }

    return (
        member.guild_permissions.administrator
        or any(role.name in names for role in member.roles)
    )


def is_management(member):
    names = {
        "👑 Kurucu",
        "🛡️ Baş Yönetici",
        "🔧 Yönetici"
    }

    return (
        member.guild_permissions.administrator
        or any(role.name in names for role in member.roles)
    )


def is_country_owner(member):
    return get_owned_country(
        member.guild.id,
        member.id
    ) is not None


def get_item(guild_id, user_id, item):
    row = db.execute(
        """
        SELECT amount
        FROM inventory
        WHERE guild_id=?
        AND user_id=?
        AND item=?
        """,
        (
            guild_id,
            user_id,
            item
        )
    ).fetchone()

    return row["amount"] if row else 0


def add_item(guild_id, user_id, item, amount):
    current = get_item(
        guild_id,
        user_id,
        item
    )

    if current == 0:
        db.execute(
            """
            INSERT INTO inventory
            (
                guild_id,
                user_id,
                item,
                amount
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                item,
                amount
            )
        )
    else:
        db.execute(
            """
            UPDATE inventory
            SET amount=amount+?
            WHERE guild_id=?
            AND user_id=?
            AND item=?
            """,
            (
                amount,
                guild_id,
                user_id,
                item
            )
        )

    db.commit()


# =========================================================
# ÜLKELER
# =========================================================

COUNTRIES = [
    "Türkiye",
    "Almanya",
    "Fransa",
    "İtalya",
    "İspanya",
    "İngiltere",
    "Portekiz",
    "Hollanda",
    "Belçika",
    "İsviçre",
    "Avusturya",
    "Polonya",
    "Norveç",
    "İsveç",
    "Finlandiya",
    "Danimarka",
    "Rusya",
    "Japonya",
    "Güney Kore",
    "Çin",
    "Hindistan",
    "Brezilya",
    "Arjantin",
    "Meksika",
    "Kanada",
    "ABD",
    "Mısır",
    "Avustralya",
    "Suudi Arabistan",
    "Endonezya"
]

# =========================================================
# ROLLER
# =========================================================

STAFF_ROLES = {
    "👑 Kurucu": discord.Colour.gold(),
    "🛡️ Baş Yönetici": discord.Colour.orange(),
    "🔧 Yönetici": discord.Colour.red(),
    "🔨 Baş Moderatör": discord.Colour.purple(),
    "🛡️ Moderatör": discord.Colour.blue()
}

RP_ROLES = {
    "🌱 Yeni Vatandaş": discord.Colour.dark_grey(),
    "👤 Vatandaş": discord.Colour.light_grey(),
    "🌍 Ülke Başkanı": discord.Colour.gold(),
    "🏛️ Bakan": discord.Colour.blue(),
    "🗳️ Milletvekili": discord.Colour.purple(),
    "⚖️ Yargı": discord.Colour.dark_grey(),
    "👮 Polis": discord.Colour.dark_blue(),
    "📰 Gazeteci": discord.Colour.yellow(),
    "🏢 Fabrika Sahibi": discord.Colour.green(),
    "💼 Çalışan": discord.Colour.teal(),
    "🎖️ Ordu": discord.Colour.dark_red()
}

ALL_ROLES = {
    **STAFF_ROLES,
    **RP_ROLES
}

# =========================================================
# KANALLAR
# =========================================================

CATEGORIES = {
    "📌 BİLGİ": [
        "📜・kurallar",
        "📢・duyurular",
        "🌍・ülke-bilgileri",
        "🗺️・harita",
        "🪪・kayıt"
    ],

    "🏛️ DEVLET": [
        "🏛️・devlet",
        "🗳️・seçimler",
        "📜・kanunlar",
        "🤝・diplomasi"
    ],

    "🌍 ÜLKELER": [
        "🌍・ülkeler",
        "📨・ülke-istekleri",
        "⚔️・savaşlar",
        "🕊️・barış"
    ],

    "💰 EKONOMİ": [
        "💰・ekonomi",
        "🏦・banka",
        "🛒・market",
        "🏭・fabrikalar",
        "💼・işler"
    ],

    "👥 HALK": [
        "💬・sohbet",
        "🏙️・şehirler",
        "🏠・evler"
    ],

    "📰 MEDYA": [
        "📰・son-dakika",
        "🗞️・gazeteler"
    ],

    "🎖️ ORDU": [
        "🎖️・ordu",
        "📋・askerler",
        "⚔️・askeri-rapor"
    ],

    "🔐 YÖNETİM": [
        "🔐・yetkili",
        "📋・başvurular",
        "📝・şikayetler",
        "🤖・bot-komutları"
    ]
}

READ_ONLY = {
    "📜・kurallar",
    "📢・duyurular",
    "🌍・ülke-bilgileri",
    "🗺️・harita",
    "📜・kanunlar",
    "📰・son-dakika",
    "📨・ülke-istekleri"
}

# =========================================================
# FABRİKALAR
# =========================================================

FACTORIES = {
    "tarım": {
        "name": "🌾 Tarım Tesisi",
        "price": 15000,
        "income": 1500
    },
    "demir": {
        "name": "⛏️ Demir Fabrikası",
        "price": 25000,
        "income": 2500
    },
    "çelik": {
        "name": "🏭 Çelik Fabrikası",
        "price": 40000,
        "income": 4000
    },
    "otomobil": {
        "name": "🚗 Otomobil Fabrikası",
        "price": 60000,
        "income": 6000
    },
    "elektronik": {
        "name": "💻 Elektronik Fabrikası",
        "price": 75000,
        "income": 7500
    },
    "gemi": {
        "name": "🚢 Gemi Fabrikası",
        "price": 90000,
        "income": 9000
    },
    "uçak": {
        "name": "✈️ Havacılık Tesisi",
        "price": 120000,
        "income": 12000
    },
    "enerji": {
        "name": "⚡ Enerji Santrali",
        "price": 100000,
        "income": 10000
    }
}

# =========================================================
# MARKET
# Tamamen oyun içi kurgu birim/eşya sistemi
# =========================================================

MARKET = {
    "piyade": ("👥 Piyade Birliği", 1000, "army"),
    "zirhli": ("🛡️ Zırhlı Birlik", 3000, "army"),
    "tank": ("🚜 Tank Birliği", 5000, "army"),
    "topcu": ("🎯 Topçu Birliği", 4500, "army"),
    "kesif": ("🔭 Keşif Birliği", 2500, "army"),
    "hava": ("✈️ Hava Birliği", 8000, "army"),
    "iha": ("🛰️ Keşif İHA Birliği", 6000, "army"),
    "hava_savunma": ("🛡️ Hava Savunma Birliği", 7000, "defense"),
    "helikopter": ("🚁 Helikopter Birliği", 7500, "army"),
    "nakliye": ("🛫 Nakliye Birliği", 5500, "army"),
    "deniz": ("⚓ Deniz Birliği", 8000, "army"),
    "denizalti": ("🌊 Deniz Birliği", 10000, "army"),
    "firkateyn": ("🚢 Fırkateyn Birliği", 12000, "army"),
    "destroyer": ("🚢 Büyük Gemi Birliği", 15000, "army"),
    "amfibi": ("🌊 Amfibi Birlik", 9000, "army"),
    "muhendis": ("🔧 Mühendis Birliği", 3500, "defense"),
    "lojistik": ("📦 Lojistik Birliği", 4000, "defense"),
    "radar": ("📡 Radar Sistemi", 5000, "defense"),
    "komuta": ("🏛️ Komuta Merkezi", 7500, "defense"),
    "sahil": ("🛡️ Sahil Savunma", 6500, "defense"),
    "baris": ("🕊️ Barış Gücü", 3000, "defense"),
    "siber": ("💻 Siber Savunma Birimi", 7000, "defense"),
    "uydu": ("🛰️ Uydu Birimi", 9000, "defense"),
    "istihbarat": ("🕵️ İstihbarat Birimi", 6000, "defense"),
    "ozel": ("🎖️ Özel Birlik", 9000, "army"),
    "muhafiz": ("🏰 Muhafız Birliği", 4500, "defense"),
    "strateji": ("🗺️ Strateji Birimi", 5000, "defense"),
    "arac": ("🚙 Askeri Araç Birliği", 3500, "army"),
    "destek": ("📦 Destek Birliği", 2500, "defense")
}

# =========================================================
# BOT HAZIR
# =========================================================

@bot.event
async def on_ready():

    print("======================================")
    print(f"BOT: {bot.user}")
    print(f"SUNUCU: {len(bot.guilds)}")
    print("ÜLKE RP BOT AKTİF")
    print("======================================")

    if not factory_income.is_running():
        factory_income.start()


# =========================================================
# FABRİKA OTOMATİK GELİR
# =========================================================

@tasks.loop(minutes=1)
async def factory_income():

    current = now()

    factories = db.execute(
        "SELECT * FROM factories"
    ).fetchall()

    for factory in factories:

        last_paid = factory["last_paid"]

        if last_paid <= 0:
            db.execute(
                """
                UPDATE factories
                SET last_paid=?
                WHERE id=?
                """,
                (
                    current,
                    factory["id"]
                )
            )
            continue

        elapsed = current - last_paid

        if elapsed < 3600:
            continue

        hours = elapsed // 3600
        income = factory["hourly_income"] * hours

        db.execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE guild_id=?
            AND user_id=?
            """,
            (
                income,
                factory["guild_id"],
                factory["owner_id"]
            )
        )

        db.execute(
            """
            UPDATE factories
            SET last_paid=?
            WHERE id=?
            """,
            (
                last_paid + hours * 3600,
                factory["id"]
            )
        )

    db.commit()


# =========================================================
# YARDIM
# =========================================================

@bot.command()
async def yardım(ctx):

    e = discord.Embed(
        title="🌍 ÜLKE RP KOMUTLARI",
        description="Ülke RP sistemindeki komutlar",
        colour=discord.Colour.blue()
    )

    e.add_field(
        name="👤 VATANDAŞ",
        value=(
            "`.kayıt İsim`\n"
            "`.profil`\n"
            "`.bal`\n"
            "`.çalış`\n"
            "`.öde @üye miktar`\n"
            "`.işler`\n"
            "`.iş meslek`"
        ),
        inline=False
    )

    e.add_field(
        name="🌍 ÜLKE",
        value=(
            "`.ülkeler`\n"
            "`.ülkeiste ülke`\n"
            "`.ülkem`\n"
            "`.ülkebilgi ülke`\n"
            "`.harita`"
        ),
        inline=False
    )

    e.add_field(
        name="💰 EKONOMİ",
        value=(
            "`.banka yatır miktar`\n"
            "`.banka çek miktar`\n"
            "`.market`\n"
            "`.satınal ürün miktar`\n"
            "`.envanter`\n"
            "`.fabrikalar`\n"
            "`.fabrika al tür`"
        ),
        inline=False
    )

    e.add_field(
        name="⚔️ RP SİSTEMİ",
        value=(
            "`.ordu`\n"
            "`.asker`\n"
            "`.savaş @ülke`\n"
            "`.savaşlar`\n"
            "`.barış @ülke`\n"
            "`.diplomasi`"
        ),
        inline=False
    )

    if is_staff(ctx.author):

        e.add_field(
            name="🔐 YETKİLİ",
            value=(
                "`.kur`\n"
                "`.ülkever @üye ülke`\n"
                "`.ülkereddet id`\n"
                "`.istekler`\n"
                "`.duyuru mesaj`\n"
                "`.söyle mesaj`\n"
                "`.temizle sayı`"
            ),
            inline=False
        )

    await ctx.send(embed=e)


# =========================================================
# KUR
# =========================================================

@bot.command()
@commands.cooldown(
    1,
    60,
    commands.BucketType.guild
)
async def kur(ctx):

    if not is_management(ctx.author):
        return await ctx.send(
            "❌ Bu komutu sadece yönetim kullanabilir."
        )

    me = ctx.guild.me

    if not me.guild_permissions.administrator:
        return await ctx.send(
            "❌ Botun **Yönetici** izni olmalı."
        )

    status = await ctx.send(
        "🏗️ **ÜLKE RP KURULUYOR...**\n"
        "Bu işlem mevcut kanalları ve botun silebildiği rolleri temizleyecek."
    )

    await asyncio.sleep(2)

    # -----------------------------------------------------
    # KANALLARI SİL
    # -----------------------------------------------------

    for channel in list(ctx.guild.channels):

        if channel.is_default():
            continue

        try:
            await channel.delete(
                reason="Ülke RP sıfırlama"
            )
            await asyncio.sleep(0.15)

        except Exception as error:
            print(
                f"Kanal silinemedi: "
                f"{channel.name} -> {error}"
            )

    # -----------------------------------------------------
    # ROLLERİ SİL
    # -----------------------------------------------------

    for role in list(ctx.guild.roles):

        if role.is_default():
            continue

        if role.managed:
            continue

        try:
            await role.delete(
                reason="Ülke RP sıfırlama"
            )
            await asyncio.sleep(0.15)

        except Exception as error:
            print(
                f"Rol silinemedi: "
                f"{role.name} -> {error}"
            )

    await status.edit(
        content="🎭 Roller oluşturuluyor..."
    )

    # -----------------------------------------------------
    # ROLLER
    # -----------------------------------------------------

    created_roles = {}

    for role_name, colour in ALL_ROLES.items():

        try:

            role = await ctx.guild.create_role(
                name=role_name,
                colour=colour,
                reason="Ülke RP kurulumu"
            )

            created_roles[role_name] = role

            await asyncio.sleep(0.2)

        except Exception as error:

            print(
                f"Rol oluşturulamadı: "
                f"{role_name} -> {error}"
            )

    # -----------------------------------------------------
    # KANALLAR
    # -----------------------------------------------------

    await status.edit(
        content="📁 Kategoriler ve kanallar oluşturuluyor..."
    )

    for category_name, channel_names in CATEGORIES.items():

        try:

            category = await ctx.guild.create_category(
                category_name,
                reason="Ülke RP kurulumu"
            )

        except Exception as error:

            print(
                f"Kategori hatası: {error}"
            )
            continue

        for channel_name in channel_names:

            try:

                channel = await ctx.guild.create_text_channel(
                    channel_name,
                    category=category,
                    reason="Ülke RP kurulumu"
                )

                # Herkes okuyabilir
                everyone = discord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True
                )

                if channel_name in READ_ONLY:
                    everyone.send_messages = False
                else:
                    everyone.send_messages = True

                await channel.set_permissions(
                    ctx.guild.default_role,
                    overwrite=everyone
                )

                # Yetkililer
                for role_name in STAFF_ROLES:

                    role = created_roles.get(role_name)

                    if not role:
                        continue

                    permissions = discord.PermissionOverwrite(
                        view_channel=True,
                        read_message_history=True,
                        send_messages=True,
                        manage_messages=True,
                        embed_links=True,
                        attach_files=True
                    )

                    await channel.set_permissions(
                        role,
                        overwrite=permissions
                    )

                await asyncio.sleep(0.15)

            except Exception as error:

                print(
                    f"Kanal oluşturulamadı: "
                    f"{channel_name} -> {error}"
                )

    # -----------------------------------------------------
    # 30 ÜLKEYİ VERİTABANINA EKLE
    # -----------------------------------------------------

    db.execute(
        """
        INSERT OR REPLACE INTO settings
        (guild_id, country_created)
        VALUES (?, 1)
        """,
        (ctx.guild.id,)
    )

    for country_name in COUNTRIES:

        existing = get_country(
            ctx.guild.id,
            country_name
        )

        if not existing:

            db.execute(
                """
                INSERT INTO countries
                (
                    guild_id,
                    name,
                    owner_id,
                    president_id,
                    treasury,
                    population,
                    army,
                    defense,
                    last_income
                )
                VALUES (?, ?, 0, 0, 100000, 0, 0, 0, ?)
                """,
                (
                    ctx.guild.id,
                    country_name,
                    now()
                )
            )

    db.commit()

    # -----------------------------------------------------
    # KURALLAR
    # -----------------------------------------------------

    rules = discord.utils.get(
        ctx.guild.text_channels,
        name="📜・kurallar"
    )

    if rules:

        await rules.send(
            embed=discord.Embed(
                title="📜 ÜLKE RP KURALLARI",
                description=(
                    "1. Saygılı davran.\n"
                    "2. Spam yapma.\n"
                    "3. Reklam yapma.\n"
                    "4. Meta Gaming yapma.\n"
                    "5. Power Gaming yapma.\n"
                    "6. RP dışı avantaj sağlamaya çalışma.\n"
                    "7. Gerçek hayat bilgilerini paylaşma.\n"
                    "8. Savaş sistemi yalnızca oyun içidir.\n"
                    "9. Yetkili kararlarına uy.\n"
                    "10. Açık/bug kullanma."
                ),
                colour=discord.Colour.blue()
            )
        )

    # -----------------------------------------------------
    # ÜLKE BİLGİ
    # -----------------------------------------------------

    info = discord.utils.get(
        ctx.guild.text_channels,
        name="🌍・ülke-bilgileri"
    )

    if info:

        await info.send(
            embed=discord.Embed(
                title="🌍 ÜLKE RP'YE HOŞ GELDİN",
                description=(
                    "Ülke seçmek için:\n"
                    "`.ülkeler`\n\n"
                    "Ülke istemek için:\n"
                    "`.ülkeiste Türkiye`\n\n"
                    "Para:\n"
                    "`.bal`\n\n"
                    "Çalışmak:\n"
                    "`.çalış`\n\n"
                    "Market:\n"
                    "`.market`\n\n"
                    "Harita:\n"
                    "`.harita`\n\n"
                    "Komutların tamamı için:\n"
                    "`.yardım`"
                ),
                colour=discord.Colour.green()
            )
        )

    await status.edit(
        content=(
            "✅ **ÜLKE RP KURULDU!**\n\n"
            "🌍 30 ülke hazır\n"
            "🎭 Roller hazır\n"
            "📁 Kanallar hazır\n"
            "🔐 İzinler ayarlandı\n"
            "💰 Ekonomi hazır\n"
            "🏭 Fabrika sistemi hazır\n"
            "🛒 Market hazır\n"
            "⚔️ Savaş sistemi hazır\n"
            "🗺️ Harita hazır\n"
            "🗳️ Ülke başvuru sistemi hazır\n\n"
            "`.yardım` yaz."
        )
    )


# =========================================================
# KAYIT
# =========================================================

@bot.command()
async def kayıt(ctx, *, isim=None):

    if not isim:
        return await ctx.send(
            "❌ Kullanım: `.kayıt İsim Soyisim`"
        )

    if len(isim) > 40:
        return await ctx.send(
            "❌ İsim çok uzun."
        )

    if get_user(
        ctx.guild.id,
        ctx.author.id
    ):
        return await ctx.send(
            "❌ Zaten kayıtlısın."
        )

    create_user(
        ctx.guild.id,
        ctx.author.id,
        isim
    )

    role = discord.utils.get(
        ctx.guild.roles,
        name="🌱 Yeni Vatandaş"
    )

    if role:

        try:
            await ctx.author.add_roles(role)
        except:
            pass

    await ctx.send(
        f"🪪 **{isim}** olarak kayıt oldun!\n"
        f"💰 Başlangıç paran: **₺1.000**"
    )


# =========================================================
# BAL
# =========================================================

@bot.command()
async def bal(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce `.kayıt İsim` yap."
        )

    country = get_owned_country(
        ctx.guild.id,
        ctx.author.id
    )

    country_text = "Yok"

    if country:
        country_text = country["name"]

    await ctx.send(
        f"💰 **Bakiye**\n\n"
        f"👛 Cüzdan: **₺{user['balance']:,}**\n"
        f"🏦 Banka: **₺{user['bank']:,}**\n"
        f"🌍 Ülke: **{country_text}**"
    )


# =========================================================
# PROFİL
# =========================================================

@bot.command()
async def profil(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    user = get_user(
        ctx.guild.id,
        member.id
    )

    if not user:
        return await ctx.send(
            "❌ Bu kişi kayıtlı değil."
        )

    country = get_owned_country(
        ctx.guild.id,
        member.id
    )

    e = discord.Embed(
        title=f"🪪 {user['name']}",
        colour=discord.Colour.blue()
    )

    e.add_field(
        name="💰 Para",
        value=f"₺{user['balance']:,}",
        inline=True
    )

    e.add_field(
        name="🏦 Banka",
        value=f"₺{user['bank']:,}",
        inline=True
    )

    e.add_field(
        name="💼 Meslek",
        value=user["job"],
        inline=True
    )

    e.add_field(
        name="🌍 Ülke",
        value=country["name"] if country else "Yok",
        inline=True
    )

    e.add_field(
        name="🏭 Fabrika",
        value=str(user["factory_count"]),
        inline=True
    )

    e.add_field(
        name="🆔 Discord",
        value=member.mention,
        inline=True
    )

    await ctx.send(embed=e)


# =========================================================
# ÇALIŞ
# =========================================================

JOBS = {
    "işçi": ("İşçi", 500),
    "öğretmen": ("Öğretmen", 700),
    "polis": ("Polis", 800),
    "doktor": ("Doktor", 900),
    "mühendis": ("Mühendis", 1000),
    "gazeteci": ("Gazeteci", 650),
    "çiftçi": ("Çiftçi", 550),
    "memur": ("Memur", 750)
}


@bot.command()
async def işler(ctx):

    lines = []

    for key, data in JOBS.items():

        lines.append(
            f"`{key}` — {data[0]} — ₺{data[1]:,}"
        )

    await ctx.send(
        "💼 **MESLEKLER**\n\n"
        + "\n".join(lines)
        + "\n\nMeslek seçmek: `.iş işçi`"
    )


@bot.command()
async def iş(ctx, meslek=None):

    if not meslek:
        return await ctx.send(
            "❌ `.işler` yaz."
        )

    meslek = meslek.lower()

    if meslek not in JOBS:
        return await ctx.send(
            "❌ Böyle bir meslek yok."
        )

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    job_name = JOBS[meslek][0]

    db.execute(
        """
        UPDATE users
        SET job=?
        WHERE guild_id=? AND user_id=?
        """,
        (
            job_name,
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.commit()

    await ctx.send(
        f"💼 Mesleğin **{job_name}** oldu."
    )


@bot.command()
@commands.cooldown(
    1,
    120,
    commands.BucketType.user
)
async def çalış(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    job = None

    for data in JOBS.values():

        if data[0] == user["job"]:
            job = data
            break

    if not job:
        return await ctx.send(
            "❌ Önce `.işler` ve `.iş meslek` kullan."
        )

    amount = job[1]

    db.execute(
        """
        UPDATE users
        SET balance=balance+?,
            last_work=?
        WHERE guild_id=? AND user_id=?
        """,
        (
            amount,
            now(),
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.commit()

    await ctx.send(
        f"💼 Çalıştın!\n"
        f"💰 **₺{amount:,}** kazandın.\n"
        f"⏳ Bir sonraki çalışma: **2 dakika**"
    )


# =========================================================
# ÖDE
# =========================================================

@bot.command()
async def öde(
    ctx,
    member: discord.Member = None,
    miktar: int = 0
):

    if not member or miktar <= 0:
        return await ctx.send(
            "❌ `.öde @üye 500`"
        )

    sender = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    receiver = get_user(
        ctx.guild.id,
        member.id
    )

    if not sender or not receiver:
        return await ctx.send(
            "❌ İki kişi de kayıtlı olmalı."
        )

    if sender["balance"] < miktar:
        return await ctx.send(
            "❌ Yeterli paran yok."
        )

    db.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE guild_id=? AND user_id=?
        """,
        (
            miktar,
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.execute(
        """
        UPDATE users
        SET balance=balance+?
        WHERE guild_id=? AND user_id=?
        """,
        (
            miktar,
            ctx.guild.id,
            member.id
        )
    )

    db.commit()

    await ctx.send(
        f"💸 {member.mention} kişisine "
        f"**₺{miktar:,}** gönderildi."
    )


# =========================================================
# BANKA
# =========================================================

@bot.command()
async def banka(
    ctx,
    islem=None,
    miktar: int = 0
):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    if islem not in ["yatır", "çek"]:
        return await ctx.send(
            "❌ `.banka yatır 500`\n"
            "`.banka çek 500`"
        )

    if miktar <= 0:
        return await ctx.send(
            "❌ Miktar 0'dan büyük olmalı."
        )

    if islem == "yatır":

        if user["balance"] < miktar:
            return await ctx.send(
                "❌ Cüzdanında yeterli para yok."
            )

        db.execute(
            """
            UPDATE users
            SET balance=balance-?,
                bank=bank+?
            WHERE guild_id=? AND user_id=?
            """,
            (
                miktar,
                miktar,
                ctx.guild.id,
                ctx.author.id
            )
        )

    else:

        if user["bank"] < miktar:
            return await ctx.send(
                "❌ Bankanda yeterli para yok."
            )

        db.execute(
            """
            UPDATE users
            SET balance=balance+?,
                bank=bank-?
            WHERE guild_id=? AND user_id=?
            """,
            (
                miktar,
                miktar,
                ctx.guild.id,
                ctx.author.id
            )
        )

    db.commit()

    await ctx.send(
        f"🏦 **₺{miktar:,}** {islem} işlemi tamamlandı."
    )


# =========================================================
# ÜLKELER
# =========================================================

@bot.command()
async def ülkeler(ctx):

    rows = db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=?
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "❌ Ülkeler henüz kurulmamış. `.kur`"
        )

    lines = []

    for country in rows:

        if country["owner_id"]:

            member = ctx.guild.get_member(
                country["owner_id"]
            )

            owner = (
                member.mention
                if member
                else "Bilinmiyor"
            )

            status = f"👑 {owner}"

        else:
            status = "🟢 Sahipsiz"

        lines.append(
            f"**{country['name']}** — {status}"
        )

    e = discord.Embed(
        title="🌍 30 ÜLKE",
        description="\n".join(lines),
        colour=discord.Colour.green()
    )

    await ctx.send(embed=e)


# =========================================================
# ÜLKE İSTE
# =========================================================

@bot.command()
async def ülkeiste(ctx, *, ülke=None):

    if not ülke:
        return await ctx.send(
            "❌ `.ülkeiste Türkiye`"
        )

    country = get_country(
        ctx.guild.id,
        ülke
    )

    if not country:
        return await ctx.send(
            "❌ Böyle bir ülke yok."
        )

    if country["owner_id"]:
        return await ctx.send(
            "❌ Bu ülke zaten alınmış."
        )

    if get_owned_country(
        ctx.guild.id,
        ctx.author.id
    ):
        return await ctx.send(
            "❌ Zaten bir ülken var."
        )

    pending = db.execute(
        """
        SELECT *
        FROM country_requests
        WHERE guild_id=?
        AND user_id=?
        AND status='pending'
        """,
        (
            ctx.guild.id,
            ctx.author.id
        )
    ).fetchone()

    if pending:
        return await ctx.send(
            "❌ Zaten bekleyen ülke başvurun var."
        )

    db.execute(
        """
        INSERT INTO country_requests
        (
            guild_id,
            user_id,
            country,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            ctx.guild.id,
            ctx.author.id,
            ülke,
            datetime.now(timezone.utc).isoformat()
        )
    )

    db.commit()

    await ctx.send(
        f"📨 **{ülke}** için başvurun gönderildi.\n"
        "Yetkililerin onaylaması gerekiyor."
    )

    channel = discord.utils.get(
        ctx.guild.text_channels,
        name="📨・ülke-istekleri"
    )

    if channel:

        await channel.send(
            f"📨 **Ülke Başvurusu**\n"
            f"👤 Oyuncu: {ctx.author.mention}\n"
            f"🌍 Ülke: **{ülke}**"
        )


# =========================================================
# İSTEKLER
# =========================================================

@bot.command()
async def istekler(ctx):

    if not is_management(ctx.author):
        return await ctx.send(
            "❌ Yetkin yok."
        )

    rows = db.execute(
        """
        SELECT *
        FROM country_requests
        WHERE guild_id=?
        AND status='pending'
        ORDER BY id ASC
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "📨 Bekleyen başvuru yok."
        )

    lines = []

    for row in rows:

        member = ctx.guild.get_member(
            row["user_id"]
        )

        user = (
            member.mention
            if member
            else str(row["user_id"])
        )

        lines.append(
            f"**ID:** `{row['id']}` | "
            f"{user} → **{row['country']}**"
        )

    await ctx.send(
        "📨 **ÜLKE BAŞVURULARI**\n\n"
        + "\n".join(lines)
        + "\n\n"
        "Onay: `.ülkever @üye Ülke`\n"
        "Reddet: `.ülkereddet ID`"
    )


# =========================================================
# ÜLKE VER
# =========================================================

@bot.command()
async def ülkever(
    ctx,
    member: discord.Member = None,
    *,
    ülke=None
):

    if not is_management(ctx.author):
        return await ctx.send(
            "❌ Yetkin yok."
        )

    if not member or not ülke:
        return await ctx.send(
            "❌ `.ülkever @üye Türkiye`"
        )

    country = get_country(
        ctx.guild.id,
        ülke
    )

    if not country:
        return await ctx.send(
            "❌ Ülke bulunamadı."
        )

    if country["owner_id"]:
        return await ctx.send(
            "❌ Bu ülke zaten alınmış."
        )

    old_country = get_owned_country(
        ctx.guild.id,
        member.id
    )

    if old_country:
        return await ctx.send(
            "❌ Bu kişinin zaten ülkesi var."
        )

    db.execute(
        """
        UPDATE countries
        SET owner_id=?,
            president_id=?
        WHERE guild_id=?
        AND name=?
        """,
        (
            member.id,
            member.id,
            ctx.guild.id,
            ülke
        )
    )

    db.execute(
        """
        UPDATE users
        SET country=?
        WHERE guild_id=?
        AND user_id=?
        """,
        (
            ülke,
            ctx.guild.id,
            member.id
        )
    )

    db.execute(
        """
        UPDATE country_requests
        SET status='approved'
        WHERE guild_id=?
        AND user_id=?
        AND country=?
        AND status='pending'
        """,
        (
            ctx.guild.id,
            member.id,
            ülke
        )
    )

    db.commit()

    role = discord.utils.get(
        ctx.guild.roles,
        name="🌍 Ülke Başkanı"
    )

    if role:

        try:
            await member.add_roles(role)
        except:
            pass

    await ctx.send(
        f"✅ {member.mention} artık "
        f"**{ülke}** ülkesinin başkanı."
    )


# =========================================================
# ÜLKE REDDET
# =========================================================

@bot.command()
async def ülkereddet(ctx, request_id: int = 0):

    if not is_management(ctx.author):
        return await ctx.send(
            "❌ Yetkin yok."
        )

    if request_id <= 0:
        return await ctx.send(
            "❌ `.ülkereddet 12`"
        )

    row = db.execute(
        """
        SELECT *
        FROM country_requests
        WHERE id=?
        AND guild_id=?
        AND status='pending'
        """,
        (
            request_id,
            ctx.guild.id
        )
    ).fetchone()

    if not row:
        return await ctx.send(
            "❌ Başvuru bulunamadı."
        )

    db.execute(
        """
        UPDATE country_requests
        SET status='rejected'
        WHERE id=?
        """,
        (request_id,)
    )

    db.commit()

    await ctx.send(
        f"❌ `{request_id}` numaralı başvuru reddedildi."
    )


# =========================================================
# ÜLKEM
# =========================================================

@bot.command()
async def ülkem(ctx):

    country = get_owned_country(
        ctx.guild.id,
        ctx.author.id
    )

    if not country:
        return await ctx.send(
            "❌ Sana verilmiş bir ülke yok."
        )

    await ctx.send(
        f"🌍 **{country['name']}**\n\n"
        f"💰 Hazine: **₺{country['treasury']:,}**\n"
        f"👥 Nüfus: **{country['population']:,}**\n"
        f"🎖️ Ordu: **{country['army']:,}**\n"
        f"🛡️ Savunma: **{country['defense']:,}**"
    )


# =========================================================
# ÜLKE BİLGİ
# =========================================================

@bot.command()
async def ülkebilgi(ctx, *, ülke=None):

    if not ülke:
        return await ctx.send(
            "❌ `.ülkebilgi Türkiye`"
        )

    country = get_country(
        ctx.guild.id,
        ülke
    )

    if not country:
        return await ctx.send(
            "❌ Ülke bulunamadı."
        )

    owner = "Sahipsiz"

    if country["owner_id"]:

        member = ctx.guild.get_member(
            country["owner_id"]
        )

        if member:
            owner = member.mention

    e = discord.Embed(
        title=f"🌍 {country['name']}",
        colour=discord.Colour.blue()
    )

    e.add_field(
        name="👑 Başkan",
        value=owner
    )

    e.add_field(
        name="💰 Hazine",
        value=f"₺{country['treasury']:,}"
    )

    e.add_field(
        name="👥 Nüfus",
        value=f"{country['population']:,}"
    )

    e.add_field(
        name="🎖️ Ordu",
        value=f"{country['army']:,}"
    )

    e.add_field(
        name="🛡️ Savunma",
        value=f"{country['defense']:,}"
    )

    await ctx.send(embed=e)


# =========================================================
# HARİTA
# =========================================================

@bot.command()
async def harita(ctx):

    rows = db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=?
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "❌ Önce `.kur`"
        )

    lines = []

    for country in rows:

        if country["owner_id"]:

            owner = ctx.guild.get_member(
                country["owner_id"]
            )

            if owner:
                symbol = "🟥"
                text = owner.display_name
            else:
                symbol = "🟨"
                text = "Sahibi yok"

        else:
            symbol = "🟩"
            text = "Sahipsiz"

        lines.append(
            f"{symbol} **{country['name']}** — {text}"
        )

    e = discord.Embed(
        title="🗺️ ÜLKE RP HARİTASI",
        description="\n".join(lines),
        colour=discord.Colour.green()
    )

    e.set_footer(
        text="🟩 Sahipsiz • 🟥 Sahipli"
    )

    await ctx.send(embed=e)


# =========================================================
# MARKET
# =========================================================

@bot.command()
async def market(ctx):

    lines = []

    for key, data in MARKET.items():

        name, price, _ = data

        lines.append(
            f"`{key}` — {name} — **₺{price:,}**"
        )

    e = discord.Embed(
        title="🛒 RP MARKETİ",
        description="\n".join(lines),
        colour=discord.Colour.green()
    )

    e.set_footer(
        text="Satın almak: .satınal ürün miktar"
    )

    await ctx.send(embed=e)


# =========================================================
# SATIN AL
# =========================================================

@bot.command()
async def satınal(
    ctx,
    ürün=None,
    miktar: int = 1
):

    if not ürün:
        return await ctx.send(
            "❌ `.satınal tank 2`"
        )

    ürün = ürün.lower()

    if ürün not in MARKET:
        return await ctx.send(
            "❌ Market ürünlerinde böyle bir ürün yok."
        )

    if miktar <= 0 or miktar > 100:
        return await ctx.send(
            "❌ Miktar 1-100 arasında olmalı."
        )

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    name, price, _ = MARKET[ürün]

    total = price * miktar

    if user["balance"] < total:
        return await ctx.send(
            f"❌ Yeterli paran yok.\n"
            f"Gereken: **₺{total:,}**"
        )

    db.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE guild_id=? AND user_id=?
        """,
        (
            total,
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.commit()

    add_item(
        ctx.guild.id,
        ctx.author.id,
        ürün,
        miktar
    )

    await ctx.send(
        f"🛒 **{name}** x{miktar} satın alındı.\n"
        f"💰 Harcanan: **₺{total:,}**"
    )


# =========================================================
# ENVANTER
# =========================================================

@bot.command()
async def envanter(ctx):

    rows = db.execute(
        """
        SELECT *
        FROM inventory
        WHERE guild_id=?
        AND user_id=?
        AND amount>0
        ORDER BY item
        """,
        (
            ctx.guild.id,
            ctx.author.id
        )
    ).fetchall()

    if not rows:
        return await ctx.send(
            "🎒 Envanterin boş."
        )

    lines = []

    for row in rows:

        if row["item"] in MARKET:
            name = MARKET[row["item"]][0]
        else:
            name = row["item"]

        lines.append(
            f"{name} × **{row['amount']}**"
        )

    await ctx.send(
        "🎒 **ENVANTERİN**\n\n"
        + "\n".join(lines)
    )


# =========================================================
# FABRİKALAR
# =========================================================

@bot.command()
async def fabrikalar(ctx):

    lines = []

    for key, data in FACTORIES.items():

        lines.append(
            f"`{key}` — {data['name']}\n"
            f"💰 Fiyat: ₺{data['price']:,}\n"
            f"⏰ Saatlik: ₺{data['income']:,}"
        )

    await ctx.send(
        "🏭 **FABRİKA TÜRLERİ**\n\n"
        + "\n\n".join(lines)
    )


@bot.command()
async def fabrika(
    ctx,
    işlem=None,
    tür=None
):

    if işlem not in ["al", "liste"]:
        return await ctx.send(
            "❌ `.fabrika al demir`\n"
            "veya `.fabrika liste`"
        )

    if işlem == "liste":
        return await fabrikalar(ctx)

    if not tür:
        return await ctx.send(
            "❌ Fabrika türü yaz."
        )

    tür = tür.lower()

    if tür not in FACTORIES:
        return await ctx.send(
            "❌ Böyle bir fabrika yok.\n"
            "`.fabrikalar`"
        )

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    country = get_owned_country(
        ctx.guild.id,
        ctx.author.id
    )

    if not country:
        return await ctx.send(
            "❌ Fabrika satın almak için bir ülken olmalı."
        )

    data = FACTORIES[tür]

    if user["balance"] < data["price"]:
        return await ctx.send(
            f"❌ Yeterli paran yok.\n"
            f"Gereken: **₺{data['price']:,}**"
        )

    db.execute(
        """
        UPDATE users
        SET balance=balance-?,
            factory_count=factory_count+1
        WHERE guild_id=? AND user_id=?
        """,
        (
            data["price"],
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.execute(
        """
        INSERT INTO factories
        (
            guild_id,
            owner_id,
            country,
            name,
            level,
            price,
            hourly_income,
            last_paid
        )
        VALUES (?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            ctx.guild.id,
            ctx.author.id,
            country["name"],
            data["name"],
            data["price"],
            data["income"],
            now()
        )
    )

    db.commit()

    await ctx.send(
        f"🏭 **{data['name']}** satın alındı!\n"
        f"💰 Fiyat: **₺{data['price']:,}**\n"
        f"⏰ Saatlik gelir: **₺{data['income']:,}**"
    )


# =========================================================
# BENİM FABRİKALARIM
# =========================================================

@bot.command()
async def fabrikalarım(ctx):

    rows = db.execute(
        """
        SELECT *
        FROM factories
        WHERE guild_id=?
        AND owner_id=?
        """,
        (
            ctx.guild.id,
            ctx.author.id
        )
    ).fetchall()

    if not rows:
        return await ctx.send(
            "🏭 Hiç fabrikan yok."
        )

    lines = []

    for row in rows:

        lines.append(
            f"**{row['name']}**\n"
            f"🌍 {row['country']}\n"
            f"⭐ Seviye: {row['level']}\n"
            f"⏰ Saatlik gelir: ₺{row['hourly_income']:,}"
        )

    await ctx.send(
        "🏭 **FABRİKALARIN**\n\n"
        + "\n\n".join(lines)
    )


# =========================================================
# ORDU
# =========================================================

@bot.command()
async def ordu(ctx):

    country = get_owned_country(
        ctx.guild.id,
        ctx.author.id
    )

    if not country:
        return await ctx.send(
            "❌ Bir ülken yok."
        )

    rows = db.execute(
        """
        SELECT item, amount
        FROM inventory
        WHERE guild_id=?
        AND user_id=?
        AND amount>0
        """,
        (
            ctx.guild.id,
            ctx.author.id
        )
    ).fetchall()

    army_items = []

    for row in rows:

        if row["item"] in MARKET:

            if MARKET[row["item"]][2] == "army":

                army_items.append(
                    f"{MARKET[row['item']][0]} × {row['amount']}"
                )

    text = (
        "\n".join(army_items)
        if army_items
        else "Henüz birim yok."
    )

    await ctx.send(
        f"🎖️ **{country['name']} ORDUSU**\n\n"
        f"🎖️ Genel Ordu: **{country['army']}**\n"
        f"🛡️ Savunma: **{country['defense']}**\n\n"
        f"**Birimler:**\n{text}"
    )


# =========================================================
# ASKER
# =========================================================

@bot.command()
async def asker(ctx):

    country = get_owned_country(
        ctx.guild.id,
        ctx.author.id
    )

    if not country:
        return await ctx.send(
            "❌ Bir ülken yok."
        )

    rows = db.execute(
        """
        SELECT item, amount
        FROM inventory
        WHERE guild_id=?
        AND user_id=?
        AND amount>0
        """,
        (
            ctx.guild.id,
            ctx.author.id
        )
    ).fetchall()

    army = 0
    defense = 0

    for row in rows:

        if row["item"] not in MARKET:
            continue

        _, _, stat = MARKET[row["item"]]

        if stat == "army":
            army += row["amount"]
        else:
            defense += row["amount"]

    db.execute(
        """
        UPDATE countries
        SET army=?,
            defense=?
        WHERE guild_id=?
        AND name=?
        """,
        (
            army,
            defense,
            ctx.guild.id,
            country["name"]
        )
    )

    db.commit()

    await ctx.send(
        f"🎖️ **{country['name']}**\n"
        f"Ordu birimi: **{army}**\n"
        f"Savunma birimi: **{defense}**"
    )


# =========================================================
# SAVAŞ
# =========================================================

@bot.command()
async def savaş(
    ctx,
    *,
    ülke=None
):

    attacker = get_owned_country(
        ctx.guild.id,
        ctx.author.id
    )

    if not attacker:
        return await ctx.send(
            "❌ Bir ülken yok."
        )

    if not ülke:
        return await ctx.send(
            "❌ `.savaş Almanya`"
        )

    defender = get_country(
        ctx.guild.id,
        ülke
    )

    if not defender:
        return await ctx.send(
            "❌ Böyle bir ülke yok."
        )

    if attacker["name"] == defender["name"]:
        return await ctx.send(
            "❌ Kendi ülkene savaş açamazsın."
        )

    if not defender["owner_id"]:
        return await ctx.send(
            "❌ Sahipsiz ülkeye savaş açılamaz."
        )

    existing = db.execute(
        """
        SELECT *
        FROM wars
        WHERE guild_id=?
        AND status='active'
        AND (
            (attacker=? AND defender=?)
            OR
            (attacker=? AND defender=?)
        )
        """,
        (
            ctx.guild.id,
            attacker["name"],
            defender["name"],
            defender["name"],
            attacker["name"]
        )
    ).fetchone()

    if existing:
        return await ctx.send(
            "⚔️ Bu iki ülke zaten savaşta."
        )

    db.execute(
        """
        INSERT INTO wars
        (
            guild_id,
            attacker,
            defender,
            status,
            started_at
        )
        VALUES (?, ?, ?, 'active', ?)
        """,
        (
            ctx.guild.id,
            attacker["name"],
            defender["name"],
            datetime.now(timezone.utc).isoformat()
        )
    )

    db.commit()

    await ctx.send(
        f"⚔️ **SAVAŞ İLANI**\n\n"
        f"🌍 Saldıran: **{attacker['name']}**\n"
        f"🌍 Savunan: **{defender['name']}**\n\n"
        f"🔴 Savaş başladı!"
    )


# =========================================================
# SAVAŞLAR
# =========================================================

@bot.command()
async def savaşlar(ctx):

    rows = db.execute(
        """
        SELECT *
        FROM wars
        WHERE guild_id=?
        AND status='active'
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "🕊️ Aktif savaş yok."
        )

    lines = []

    for row in rows:

        lines.append(
            f"⚔️ **{row['attacker']}** "
            f"vs "
            f"**{row['defender']}**"
        )

    await ctx.send(
        "⚔️ **AKTİF SAVAŞLAR**\n\n"
        + "\n".join(lines)
    )


# =========================================================
# BARIŞ
# =========================================================

@bot.command()
async def barış(ctx, *, ülke=None):

    my_country = get_owned_country(
        ctx.guild.id,
        ctx.author.id
    )

    if not my_country:
        return await ctx.send(
            "❌ Bir ülken yok."
        )

    if not ülke:
        return await ctx.send(
            "❌ `.barış Almanya`"
        )

    war = db.execute(
        """
        SELECT *
        FROM wars
        WHERE guild_id=?
        AND status='active'
        AND (
            (attacker=? AND defender=?)
            OR
            (attacker=? AND defender=?)
        )
        """,
        (
            ctx.guild.id,
            my_country["name"],
            ülke,
            ülke,
            my_country["name"]
        )
    ).fetchone()

    if not war:
        return await ctx.send(
            "❌ Bu ülkeyle aktif savaş yok."
        )

    db.execute(
        """
        UPDATE wars
        SET status='ended',
            ended_at=?
        WHERE id=?
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            war["id"]
        )
    )

    db.commit()

    await ctx.send(
        f"🕊️ **{my_country['name']}** ile "
        f"**{ülke}** arasındaki savaş sona erdi."
    )


# =========================================================
# DİPLOMASİ
# =========================================================

@bot.command()
async def diplomasi(ctx):

    rows = db.execute(
        """
        SELECT *
        FROM diplomacy
        WHERE guild_id=?
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "🤝 Henüz diplomatik anlaşma yok."
        )

    lines = []

    for row in rows:

        lines.append(
            f"🌍 {row['country1']} ↔ "
            f"{row['country2']} — **{row['status']}**"
        )

    await ctx.send(
        "🤝 **DİPLOMASİ**\n\n"
        + "\n".join(lines)
    )


# =========================================================
# SÖYLE
# =========================================================

@bot.command()
async def söyle(ctx, *, mesaj=None):

    if not is_staff(ctx.author):
        return await ctx.send(
            "❌ Yetkin yok."
        )

    if not mesaj:
        return await ctx.send(
            "❌ `.söyle mesaj`"
        )

    try:
        await ctx.message.delete()
    except:
        pass

    await ctx.send(mesaj)


# =========================================================
# DUYURU
# =========================================================

@bot.command()
async def duyuru(ctx, *, mesaj=None):

    if not is_staff(ctx.author):
        return await ctx.send(
            "❌ Yetkin yok."
        )

    if not mesaj:
        return await ctx.send(
            "❌ `.duyuru mesaj`"
        )

    channel = discord.utils.get(
        ctx.guild.text_channels,
        name="📢・duyurular"
    )

    if not channel:
        return await ctx.send(
            "❌ Duyuru kanalı yok."
        )

    e = discord.Embed(
        title="📢 DUYURU",
        description=mesaj,
        colour=discord.Colour.blue()
    )

    e.set_footer(
        text=f"Yetkili: {ctx.author}"
    )

    await channel.send(embed=e)

    await ctx.send(
        "✅ Duyuru gönderildi."
    )


# =========================================================
# TEMİZLE
# =========================================================

@bot.command()
async def temizle(ctx, miktar: int = 10):

    if not is_staff(ctx.author):
        return await ctx.send(
            "❌ Yetkin yok."
        )

    miktar = max(
        1,
        min(100, miktar)
    )

    try:

        deleted = await ctx.channel.purge(
            limit=miktar + 1
        )

        await ctx.send(
            f"🧹 **{len(deleted)}** mesaj silindi.",
            delete_after=3
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Mesaj silme iznim yok."
        )


# =========================================================
# BİLGİ
# =========================================================

@bot.command()
async def bilgi(ctx):

    if not is_staff(ctx.author):
        return await ctx.send(
            "❌ Yetkin yok."
        )

    e = discord.Embed(
        title=f"📊 {ctx.guild.name}",
        colour=discord.Colour.blue()
    )

    e.add_field(
        name="👥 Üye",
        value=str(ctx.guild.member_count)
    )

    e.add_field(
        name="📁 Kanal",
        value=str(len(ctx.guild.channels))
    )

    e.add_field(
        name="🎭 Rol",
        value=str(len(ctx.guild.roles))
    )

    e.add_field(
        name="📡 Ping",
        value=f"{round(bot.latency * 1000)}ms"
    )

    await ctx.send(embed=e)


# =========================================================
# HATA YÖNETİMİ
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.CommandOnCooldown
    ):

        await ctx.send(
            f"⏳ Bu komutu tekrar kullanmak için "
            f"**{error.retry_after:.0f} saniye** bekle."
        )
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "❌ Eksik bilgi girdin. `.yardım` yaz."
        )
        return

    if isinstance(
        error,
        commands.BadArgument
    ):

        await ctx.send(
            "❌ Kullanıcı veya sayı hatalı."
        )
        return

    print(
        f"[HATA] {ctx.command}: {repr(error)}"
    )


# =========================================================
# BAŞLAT
# =========================================================

bot.run(TOKEN)
