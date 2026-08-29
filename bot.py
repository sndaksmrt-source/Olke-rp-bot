import os
import sqlite3
from datetime import datetime, timezone

import discord
from discord.ext import commands

# =========================================================
# AYARLAR
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("DB_PATH", "/data/ulke_rp.db")
PREFIX = "."

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN bulunamadı! Railway > Variables bölümüne ekle."
    )

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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
CREATE TABLE IF NOT EXISTS users (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL DEFAULT 1000,
    bank INTEGER NOT NULL DEFAULT 0,
    job TEXT NOT NULL DEFAULT 'İşsiz',
    city TEXT NOT NULL DEFAULT 'Başkent',
    country TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    house TEXT NOT NULL DEFAULT '',
    registered_at TEXT NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS countries (
    guild_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    capital TEXT NOT NULL,
    president_id INTEGER,
    treasury INTEGER NOT NULL DEFAULT 100000,
    founded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL DEFAULT 5000,
    employees INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS elections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    votes INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS votes (
    guild_id INTEGER NOT NULL,
    voter_id INTEGER NOT NULL,
    election_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, voter_id, election_id)
);
""")

db.commit()


def now():
    return datetime.now(timezone.utc).isoformat()


def get_user(guild_id, user_id):
    return db.execute(
        """
        SELECT *
        FROM users
        WHERE guild_id=? AND user_id=?
        """,
        (guild_id, user_id)
    ).fetchone()


def ensure_user(guild_id, user_id, name):
    user = get_user(guild_id, user_id)

    if user is None:
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
                now()
            )
        )
        db.commit()

    return get_user(guild_id, user_id)


# =========================================================
# ROLLER
# =========================================================

STAFF_ROLES = {
    "👑 Kurucu": discord.Colour.gold(),
    "🛡️ Baş Yönetici": discord.Colour.orange(),
    "🔧 Yönetici": discord.Colour.red(),
    "🔨 Baş Moderatör": discord.Colour.purple(),
    "🛡️ Moderatör": discord.Colour.blue(),
}

RP_ROLES = {
    "👑 Devlet Başkanı": discord.Colour.gold(),
    "⭐ Başkan Yardımcısı": discord.Colour.orange(),
    "🏛️ Başbakan": discord.Colour.red(),
    "🏢 Bakan": discord.Colour.blue(),
    "🗳️ Milletvekili": discord.Colour.purple(),
    "⚖️ Yargı": discord.Colour.dark_grey(),

    "👮 Emniyet Müdürü": discord.Colour.dark_blue(),
    "👮 Polis": discord.Colour.blue(),
    "🪖 Asker": discord.Colour.dark_green(),
    "🚑 Sağlık Görevlisi": discord.Colour.red(),

    "📰 Gazeteci": discord.Colour.yellow(),
    "📺 Haberci": discord.Colour.orange(),

    "🏢 Şirket Sahibi": discord.Colour.green(),
    "💼 Çalışan": discord.Colour.teal(),
    "🏦 Bankacı": discord.Colour.dark_gold(),

    "👤 Vatandaş": discord.Colour.light_grey(),
    "🌱 Yeni Vatandaş": discord.Colour.dark_grey(),
}

ALL_ROLE_NAMES = set(STAFF_ROLES) | set(RP_ROLES)

STAFF_NAMES = set(STAFF_ROLES.keys())

MANAGEMENT_NAMES = {
    "👑 Kurucu",
    "🛡️ Baş Yönetici",
    "🔧 Yönetici"
}


def has_role(member, role_names):
    return any(
        role.name in role_names
        for role in member.roles
    )


def is_staff(member):
    return (
        member.guild_permissions.administrator
        or has_role(member, STAFF_NAMES)
    )


def is_management(member):
    return (
        member.guild_permissions.administrator
        or has_role(member, MANAGEMENT_NAMES)
    )


# =========================================================
# KANALLAR
# =========================================================

CATEGORIES = {
    "📌 BİLGİ": [
        "📜・kurallar",
        "📢・duyurular",
        "🌍・ülke-bilgileri",
        "🪪・vatandaş-kayıt",
        "📋・yardım",
    ],

    "🏛️ DEVLET": [
        "👑・devlet",
        "🏛️・meclis",
        "📜・kanunlar",
        "🗳️・seçimler",
        "📋・devlet-kararları",
    ],

    "💰 EKONOMİ": [
        "💰・ekonomi",
        "🏦・banka",
        "🏢・şirketler",
        "💼・iş-ilanları",
        "🛒・pazar",
        "📈・borsa",
    ],

    "👥 HALK": [
        "💬・şehir-sohbeti",
        "🏙️・şehirler",
        "🏠・evler",
        "🎉・etkinlikler",
    ],

    "📰 MEDYA": [
        "📰・son-dakika",
        "🗞️・gazeteler",
        "📺・televizyon",
        "🎙️・basın",
    ],

    "🌎 DIŞ İLİŞKİLER": [
        "🌎・diplomasi",
        "🤝・antlaşmalar",
        "✈️・yurtdışı",
    ],

    "⚖️ HUKUK": [
        "⚖️・mahkeme",
        "📜・hukuk",
        "📋・dava-kayıtları",
    ],

    "👮 GÜVENLİK": [
        "👮・polis",
        "🚨・acil-durum",
        "🪖・ordu",
    ],

    "🏥 SAĞLIK": [
        "🏥・hastane",
        "🚑・ambulans",
    ],

    "🏢 ŞİRKETLER": [
        "🏢・şirketler",
        "💼・işe-alım",
        "📊・şirket-duyuruları",
    ],

    "🎭 RP": [
        "🎭・rp-sohbet",
        "📍・şehir-rp",
        "🚗・ulaşım-rp",
        "🏙️・sosyal-hayat",
    ],

    "🎫 DESTEK": [
        "🎫・destek",
        "📝・başvurular",
        "⚠️・şikayetler",
    ],

    "⚙️ YÖNETİM": [
        "🔐・yetkili-komutları",
        "📋・yönetim-log",
        "🛠️・bot-log",
    ],
}

READ_ONLY_CHANNELS = {
    "📜・kurallar",
    "📢・duyurular",
    "🌍・ülke-bilgileri",
    "📋・yardım",
    "📜・kanunlar",
    "📰・son-dakika",
    "📋・devlet-kararları",
    "📋・yönetim-log",
    "🛠️・bot-log",
}

STAFF_ONLY_CHANNELS = {
    "🔐・yetkili-komutları",
    "📋・yönetim-log",
    "🛠️・bot-log",
}


# =========================================================
# BOT HAZIR
# =========================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"BOT AKTİF: {bot.user}")
    print(f"SUNUCULAR: {len(bot.guilds)}")
    print("====================================")


# =========================================================
# YARDIM
# =========================================================

@bot.command()
async def yardım(ctx):

    embed = discord.Embed(
        title="🌍 ÜLKE RP BOT",
        description="Kullanılabilir komutlar:",
        colour=discord.Colour.blue()
    )

    embed.add_field(
        name="👤 VATANDAŞ",
        value=(
            "`.kayıt İsim`\n"
            "`.profil`\n"
            "`.para`\n"
            "`.öde @üye miktar`\n"
            "`.şehir`\n"
            "`.ülke`"
        ),
        inline=False
    )

    embed.add_field(
        name="💼 MESLEK",
        value=(
            "`.işler`\n"
            "`.iş meslek`\n"
            "`.çalış`"
        ),
        inline=False
    )

    embed.add_field(
        name="💰 EKONOMİ",
        value=(
            "`.banka yatır miktar`\n"
            "`.banka çek miktar`\n"
            "`.şirketkur isim`\n"
            "`.şirket`\n"
            "`.işeal @üye`\n"
            "`.ev al`"
        ),
        inline=False
    )

    embed.add_field(
        name="🗳️ SİYASET",
        value=(
            "`.adayol`\n"
            "`.adaylar`\n"
            "`.oyver @aday`\n"
            "`.seçim durum`"
        ),
        inline=False
    )

    if is_staff(ctx.author):

        embed.add_field(
            name="🔐 YETKİLİ",
            value=(
                "`.kur`\n"
                "`.söyle mesaj`\n"
                "`.duyuru mesaj`\n"
                "`.temizle sayı`\n"
                "`.embed Başlık | Mesaj`\n"
                "`.bilgi`"
            ),
            inline=False
        )

    await ctx.send(embed=embed)


# =========================================================
# .KUR
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
            "❌ Bu komutu sadece **Kurucu / Baş Yönetici / Yönetici** kullanabilir."
        )

    me = ctx.guild.me

    if not me.guild_permissions.manage_channels:
        return await ctx.send(
            "❌ Botta **Kanalları Yönet** izni yok."
        )

    if not me.guild_permissions.manage_roles:
        return await ctx.send(
            "❌ Botta **Rolleri Yönet** izni yok."
        )

    warning = await ctx.send(
        "⚠️ **DİKKAT! SUNUCU SIFIRLANACAK!**\n\n"
        "Bu işlem:\n"
        "🗑️ Tüm kanalları\n"
        "🗑️ Tüm kategorileri\n"
        "🗑️ Botun silebildiği rolleri\n\n"
        "silecek ve ülke RP sistemini baştan oluşturacak.\n\n"
        "**Devam etmek için 15 saniye içinde `onayla` yaz.**"
    )

    def check(message):
        return (
            message.author.id == ctx.author.id
            and message.channel.id == ctx.channel.id
            and message.content.lower().strip() == "onayla"
        )

    try:
        await bot.wait_for(
            "message",
            timeout=15,
            check=check
        )

    except asyncio.TimeoutError:
        return await ctx.send(
            "❌ Süre doldu. Kurulum iptal edildi."
        )

    msg = await ctx.send(
        "🧨 **SUNUCU SIFIRLANIYOR...**\n"
        "Lütfen işlem bitene kadar komut kullanma."
    )

    # =====================================================
    # TÜM KANALLARI SİL
    # =====================================================

    deleted_channels = 0

    for channel in list(ctx.guild.channels):

        try:

            await channel.delete(
                reason="Ülke RP tam sunucu sıfırlaması"
            )

            deleted_channels += 1

        except discord.Forbidden:

            print(
                f"[KANAL SİLİNEMEDİ] "
                f"{channel.name}: Yetki yok."
            )

        except discord.HTTPException as e:

            print(
                f"[KANAL SİLİNEMEDİ] "
                f"{channel.name}: {e}"
            )

    # =====================================================
    # ROLLERİ SİL
    # =====================================================

    await msg.edit(
        content=(
            "🧨 **SUNUCU SIFIRLANIYOR...**\n\n"
            f"🗑️ Silinen kanallar: `{deleted_channels}`\n"
            "🎭 Eski roller temizleniyor..."
        )
    )

    deleted_roles = 0

    for role in list(ctx.guild.roles):

        if role.is_default():
            continue

        # Discord, botun üstündeki rolleri sildirmez.
        if role >= me.top_role:
            print(
                f"[ROL SİLİNEMEDİ] {role.name}: "
                "Bot rolünün üstünde."
            )
            continue

        try:

            await role.delete(
                reason="Ülke RP tam sunucu sıfırlaması"
            )

            deleted_roles += 1

        except discord.Forbidden:

            print(
                f"[ROL SİLİNEMEDİ] {role.name}: Yetki yok."
            )

        except discord.HTTPException as e:

            print(
                f"[ROL SİLİNEMEDİ] {role.name}: {e}"
            )

    # =====================================================
    # ROLLERİ OLUŞTUR
    # =====================================================

    await msg.edit(
        content="🎭 **YENİ ROL SİSTEMİ OLUŞTURULUYOR...**"
    )

    roles = {}

    all_roles = {
        **STAFF_ROLES,
        **RP_ROLES
    }

    for name, colour in all_roles.items():

        try:

            role = await ctx.guild.create_role(
                name=name,
                colour=colour,
                mentionable=False,
                hoist=True,
                reason="Ülke RP rol sistemi"
            )

            roles[name] = role

        except discord.HTTPException as e:

            print(
                f"[ROL OLUŞTURULAMADI] "
                f"{name}: {e}"
            )

    # =====================================================
    # YETKİLİ ROL İZİNLERİ
    # =====================================================

    permission_map = {

        "👑 Kurucu": discord.Permissions(
            administrator=True
        ),

        "🛡️ Baş Yönetici": discord.Permissions(
            manage_guild=True,
            manage_channels=True,
            manage_roles=True,
            manage_messages=True,
            kick_members=True,
            ban_members=True,
            moderate_members=True,
            view_audit_log=True,
            manage_nicknames=True
        ),

        "🔧 Yönetici": discord.Permissions(
            manage_channels=True,
            manage_roles=True,
            manage_messages=True,
            kick_members=True,
            moderate_members=True,
            view_audit_log=True
        ),

        "🔨 Baş Moderatör": discord.Permissions(
            manage_messages=True,
            moderate_members=True,
            kick_members=True,
            view_audit_log=True
        ),

        "🛡️ Moderatör": discord.Permissions(
            manage_messages=True,
            moderate_members=True,
            view_audit_log=True
        ),
    }

    for role_name, permissions in permission_map.items():

        role = roles.get(role_name)

        if not role:
            continue

        try:

            await role.edit(
                permissions=permissions,
                reason="Ülke RP yetki sistemi"
            )

        except discord.HTTPException as e:

            print(
                f"[ROL İZNİ AYARLANAMADI] "
                f"{role_name}: {e}"
            )

    # =====================================================
    # KATEGORİLER
    # =====================================================

    await msg.edit(
        content="📁 **KATEGORİLER OLUŞTURULUYOR...**"
    )

    created_categories = {}

    for category_name in CATEGORIES:

        try:

            category = await ctx.guild.create_category(
                category_name,
                reason="Ülke RP kategori sistemi"
            )

            created_categories[category_name] = category

        except discord.HTTPException as e:

            print(
                f"[KATEGORİ OLUŞTURULAMADI] "
                f"{category_name}: {e}"
            )

    # =====================================================
    # KANALLAR
    # =====================================================

    await msg.edit(
        content="💬 **KANALLAR OLUŞTURULUYOR...**"
    )

    created_channels = 0

    for category_name, channel_names in CATEGORIES.items():

        category = created_categories.get(
            category_name
        )

        if not category:
            continue

        for channel_name in channel_names:

            try:

                channel = await ctx.guild.create_text_channel(
                    channel_name,
                    category=category,
                    reason="Ülke RP kanal sistemi"
                )

                created_channels += 1

            except discord.HTTPException as e:

                print(
                    f"[KANAL OLUŞTURULAMADI] "
                    f"{channel_name}: {e}"
                )

                continue

            # =================================================
            # @EVERYONE
            # =================================================

            everyone_permissions = discord.PermissionOverwrite(
                view_channel=True,
                read_message_history=True
            )

            if channel_name in STAFF_ONLY_CHANNELS:

                everyone_permissions.view_channel = False
                everyone_permissions.send_messages = False

            elif channel_name in READ_ONLY_CHANNELS:

                everyone_permissions.send_messages = False

            else:

                everyone_permissions.send_messages = True

            try:

                await channel.set_permissions(
                    ctx.guild.default_role,
                    overwrite=everyone_permissions,
                    reason="Ülke RP kanal izinleri"
                )

            except discord.HTTPException as e:

                print(
                    f"[KANAL İZNİ] "
                    f"{channel_name}: {e}"
                )

            # =================================================
            # STAFF
            # =================================================

            for staff_name in STAFF_NAMES:

                role = roles.get(staff_name)

                if not role:
                    continue

                staff_permissions = discord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True,
                    send_messages=True
                )

                if staff_name in {
                    "👑 Kurucu",
                    "🛡️ Baş Yönetici",
                    "🔧 Yönetici"
                }:
                    staff_permissions.manage_messages = True

                elif staff_name in {
                    "🔨 Baş Moderatör",
                    "🛡️ Moderatör"
                }:
                    staff_permissions.manage_messages = True

                try:

                    await channel.set_permissions(
                        role,
                        overwrite=staff_permissions,
                        reason="Ülke RP yetkili izinleri"
                    )

                except discord.HTTPException:
                    pass

    # =====================================================
    # ÜLKE VERİTABANI
    # =====================================================

    country = db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=?
        """,
        (ctx.guild.id,)
    ).fetchone()

    if not country:

        db.execute(
            """
            INSERT INTO countries
            (
                guild_id,
                name,
                capital,
                president_id,
                treasury,
                founded_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.guild.id,
                "Yeni Cumhuriyet",
                "Başkent",
                ctx.author.id,
                100000,
                now()
            )
        )

    else:

        db.execute(
            """
            UPDATE countries
            SET treasury=100000,
                president_id=?
            WHERE guild_id=?
            """,
            (
                ctx.author.id,
                ctx.guild.id
            )
        )

    db.commit()

    # =====================================================
    # KURALLAR MESAJI
    # =====================================================

    rules = discord.utils.get(
        ctx.guild.text_channels,
        name="📜・kurallar"
    )

    if rules:

        embed = discord.Embed(
            title="📜 ÜLKE RP KURALLARI",
            description=(
                "**1.** Saygılı davran.\n"
                "**2.** Spam/flood yapma.\n"
                "**3.** Reklam yapma.\n"
                "**4.** Meta Gaming yapma.\n"
                "**5.** Power Gaming yapma.\n"
                "**6.** Başka oyuncunun karakterini zorla yönetme.\n"
                "**7.** Yetkili kararlarına uy.\n"
                "**8.** Bugları kötüye kullanma.\n"
                "**9.** RP ile gerçek hayatı ayır.\n"
                "**10.** Kişisel bilgilerini paylaşma."
            ),
            colour=discord.Colour.blue()
        )

        await rules.send(embed=embed)

    # =====================================================
    # ÜLKE BİLGİLERİ
    # =====================================================

    info = discord.utils.get(
        ctx.guild.text_channels,
        name="🌍・ülke-bilgileri"
    )

    if info:

        embed = discord.Embed(
            title="🌍 ÜLKE RP SİSTEMİ",
            description=(
                "Ülke RP sunucusuna hoş geldiniz!\n\n"
                "🪪 `.kayıt İsim`\n"
                "👤 `.profil`\n"
                "💰 `.para`\n"
                "💼 `.işler`\n"
                "🏢 `.şirketkur isim`\n"
                "🗳️ `.adayol`\n"
                "🌍 `.ülke`\n\n"
                "📚 Tüm komutlar için `.yardım`"
            ),
            colour=discord.Colour.green()
        )

        await info.send(embed=embed)

    # =====================================================
    # DUYURU
    # =====================================================

    announcements = discord.utils.get(
        ctx.guild.text_channels,
        name="📢・duyurular"
    )

    if announcements:

        embed = discord.Embed(
            title="📢 SİSTEM KURULDU",
            description=(
                "🌍 Ülke RP sistemi başarıyla kuruldu.\n\n"
                "Vatandaş olmak için `.kayıt İsim` yaz."
            ),
            colour=discord.Colour.green()
        )

        await announcements.send(
            embed=embed
        )

    # =====================================================
    # BİTİŞ
    # =====================================================

    await msg.edit(
        content=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌍 **ÜLKE RP KURULUMU TAMAMLANDI!**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🗑️ Silinen kanallar: `{deleted_channels}`\n"
            f"🗑️ Silinen roller: `{deleted_roles}`\n"
            f"🎭 Yeni roller: `{len(roles)}`\n"
            f"📁 Kategoriler: `{len(created_categories)}`\n"
            f"💬 Kanallar: `{created_channels}`\n\n"
            "🔐 Yetki sistemi hazır.\n"
            "👥 Vatandaş sistemi hazır.\n"
            "💰 Ekonomi sistemi hazır.\n"
            "🏢 Şirket sistemi hazır.\n"
            "🗳️ Seçim sistemi hazır.\n"
            "🌍 Ülke sistemi hazır.\n\n"
            "📚 Komutlar: `.yardım`"
        )
    )


# =========================================================
# KAYIT
# =========================================================

@bot.command()
async def kayıt(ctx, *, isim=None):

    if not isim:
        return await ctx.send(
            "❌ Kullanım: `.kayıt Ahmet Yılmaz`"
        )

    if len(isim) > 40:
        return await ctx.send(
            "❌ İsim 40 karakterden uzun olamaz."
        )

    if get_user(
        ctx.guild.id,
        ctx.author.id
    ):
        return await ctx.send(
            "❌ Zaten kayıtlısın."
        )

    ensure_user(
        ctx.guild.id,
        ctx.author.id,
        isim
    )

    new_role = discord.utils.get(
        ctx.guild.roles,
        name="🌱 Yeni Vatandaş"
    )

    if new_role:

        try:

            await ctx.author.add_roles(
                new_role,
                reason="Yeni vatandaş kaydı"
            )

        except discord.HTTPException:
            pass

    await ctx.send(
        f"🪪 **{isim}**, vatandaş kaydın oluşturuldu!\n"
        "💰 Başlangıç paran: **₺1.000**"
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
            "❌ Bu kişinin kaydı bulunamadı."
        )

    embed = discord.Embed(
        title=f"🪪 {user['name']}",
        colour=discord.Colour.blue()
    )

    embed.add_field(
        name="💰 Cüzdan",
        value=f"₺{user['balance']:,}",
        inline=True
    )

    embed.add_field(
        name="🏦 Banka",
        value=f"₺{user['bank']:,}",
        inline=True
    )

    embed.add_field(
        name="💼 Meslek",
        value=user["job"],
        inline=True
    )

    embed.add_field(
        name="🏙️ Şehir",
        value=user["city"],
        inline=True
    )

    embed.add_field(
        name="🌍 Ülke",
        value=user["country"] or "Yok",
        inline=True
    )

    embed.add_field(
        name="🏠 Ev",
        value=user["house"] or "Yok",
        inline=True
    )

    embed.add_field(
        name="🏢 Şirket",
        value=user["company"] or "Yok",
        inline=True
    )

    await ctx.send(embed=embed)


# =========================================================
# PARA
# =========================================================

@bot.command()
async def para(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce `.kayıt İsim` yap."
        )

    await ctx.send(
        f"💰 Cüzdan: **₺{user['balance']:,}**\n"
        f"🏦 Banka: **₺{user['bank']:,}**"
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
            "❌ Kullanım: `.öde @üye 500`"
        )

    if member.bot or member.id == ctx.author.id:
        return await ctx.send(
            "❌ Geçerli bir vatandaş seç."
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
            "❌ İki kişinin de kayıtlı olması gerekiyor."
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
# MESLEKLER
# =========================================================

JOBS = {
    "doktor": ("Doktor", 900),
    "polis": ("Polis", 800),
    "öğretmen": ("Öğretmen", 700),
    "mühendis": ("Mühendis", 1000),
    "gazeteci": ("Gazeteci", 650),
    "işçi": ("İşçi", 500),
    "bankacı": ("Bankacı", 850),
    "asker": ("Asker", 800),
}


@bot.command()
async def işler(ctx):

    text = "\n".join(
        f"• `{key}` — {name} — ₺{salary:,}/çalışma"
        for key, (name, salary) in JOBS.items()
    )

    await ctx.send(
        "💼 **MESLEKLER**\n\n" + text
    )


@bot.command()
async def iş(ctx, meslek=None):

    if not meslek:
        return await ctx.send(
            "❌ `.işler` yazarak meslekleri gör."
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

    job_name, _ = JOBS[meslek]

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
        f"💼 Mesleğin artık **{job_name}**."
    )


@bot.command()
@commands.cooldown(
    1,
    30,
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

    job = next(
        (
            value
            for value in JOBS.values()
            if value[0] == user["job"]
        ),
        None
    )

    if not job:
        return await ctx.send(
            "❌ Önce `.iş meslek` ile meslek seç."
        )

    amount = job[1]

    db.execute(
        """
        UPDATE users
        SET balance=balance+?
        WHERE guild_id=? AND user_id=?
        """,
        (
            amount,
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.commit()

    await ctx.send(
        f"💼 Çalıştın ve **₺{amount:,}** kazandın."
    )


# =========================================================
# BANKA
# =========================================================

@bot.command()
async def banka(
    ctx,
    işlem=None,
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

    if işlem not in {"yatır", "çek"} or miktar <= 0:
        return await ctx.send(
            "❌ Kullanım:\n"
            "`.banka yatır 500`\n"
            "`.banka çek 500`"
        )

    if işlem == "yatır":

        if user["balance"] < miktar:
            return await ctx.send(
                "❌ Cüzdanda yeterli para yok."
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
                "❌ Bankada yeterli para yok."
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
        f"🏦 **₺{miktar:,}** {işlem} işlemi tamamlandı."
    )


# =========================================================
# ŞİRKET KUR
# =========================================================

@bot.command()
async def şirketkur(ctx, *, isim=None):

    if not isim:
        return await ctx.send(
            "❌ Kullanım: `.şirketkur Anadolu Teknoloji`"
        )

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    if user["company"]:
        return await ctx.send(
            "❌ Zaten bir şirketin var."
        )

    if user["balance"] < 5000:
        return await ctx.send(
            "❌ Şirket kurmak için **₺5.000** gerekiyor."
        )

    exists = db.execute(
        """
        SELECT 1
        FROM companies
        WHERE guild_id=? AND name=?
        """,
        (
            ctx.guild.id,
            isim
        )
    ).fetchone()

    if exists:
        return await ctx.send(
            "❌ Bu isimde şirket zaten var."
        )

    db.execute(
        """
        UPDATE users
        SET balance=balance-?,
            company=?
        WHERE guild_id=? AND user_id=?
        """,
        (
            5000,
            isim,
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.execute(
        """
        INSERT INTO companies
        (
            guild_id,
            owner_id,
            name
        )
        VALUES (?, ?, ?)
        """,
        (
            ctx.guild.id,
            ctx.author.id,
            isim
        )
    )

    db.commit()

    await ctx.send(
        f"🏢 **{isim}** şirketi kuruldu!\n"
        "💰 Kuruluş maliyeti: **₺5.000**"
    )


# =========================================================
# ŞİRKET
# =========================================================

@bot.command()
async def şirket(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user or not user["company"]:
        return await ctx.send(
            "❌ Bir şirketin yok."
        )

    company = db.execute(
        """
        SELECT *
        FROM companies
        WHERE guild_id=?
        AND owner_id=?
        AND name=?
        """,
        (
            ctx.guild.id,
            ctx.author.id,
            user["company"]
        )
    ).fetchone()

    if not company:
        return await ctx.send(
            "❌ Şirket verisi bulunamadı."
        )

    await ctx.send(
        f"🏢 **{company['name']}**\n"
        f"💰 Kasa: **₺{company['balance']:,}**\n"
        f"👥 Çalışan: **{company['employees']}**"
    )


# =========================================================
# İŞE AL
# =========================================================

@bot.command()
async def işeal(
    ctx,
    member: discord.Member = None
):

    if not member:
        return await ctx.send(
            "❌ Kullanım: `.işeal @üye`"
        )

    owner = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    employee = get_user(
        ctx.guild.id,
        member.id
    )

    if not owner or not owner["company"]:
        return await ctx.send(
            "❌ Bir şirket sahibi olmalısın."
        )

    if not employee:
        return await ctx.send(
            "❌ Bu kişi kayıtlı değil."
        )

    db.execute(
        """
        UPDATE companies
        SET employees=employees+1
        WHERE guild_id=?
        AND owner_id=?
        AND name=?
        """,
        (
            ctx.guild.id,
            ctx.author.id,
            owner["company"]
        )
    )

    db.execute(
        """
        UPDATE users
        SET company=?
        WHERE guild_id=? AND user_id=?
        """,
        (
            owner["company"],
            ctx.guild.id,
            member.id
        )
    )

    db.commit()

    await ctx.send(
        f"🏢 {member.mention} "
        f"**{owner['company']}** şirketine alındı."
    )


# =========================================================
# EV
# =========================================================

@bot.command()
async def ev(ctx, işlem=None):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    if işlem != "al":
        return await ctx.send(
            "❌ Kullanım: `.ev al`"
        )

    if user["house"]:
        return await ctx.send(
            "❌ Zaten evin var."
        )

    if user["balance"] < 10000:
        return await ctx.send(
            "❌ Ev için **₺10.000** gerekiyor."
        )

    db.execute(
        """
        UPDATE users
        SET balance=balance-?,
            house=?
        WHERE guild_id=? AND user_id=?
        """,
        (
            10000,
            "Standart Ev",
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.commit()

    await ctx.send(
        "🏠 Standart ev satın aldın.\n"
        "💰 Fiyat: **₺10.000**"
    )


# =========================================================
# ŞEHİR
# =========================================================

@bot.command()
async def şehir(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    await ctx.send(
        f"🏙️ Şehrin: **{user['city']}**"
    )


# =========================================================
# ÜLKE
# =========================================================

@bot.command()
async def ülke(ctx):

    country = db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=?
        """,
        (ctx.guild.id,)
    ).fetchone()

    if not country:
        return await ctx.send(
            "❌ Henüz ülke oluşturulmamış."
        )

    president = ctx.guild.get_member(
        country["president_id"]
    )

    president_text = (
        president.mention
        if president
        else "Belirlenmemiş"
    )

    await ctx.send(
        f"🌍 **{country['name']}**\n"
        f"🏛️ Başkent: **{country['capital']}**\n"
        f"👑 Başkan: {president_text}\n"
        f"💰 Hazine: **₺{country['treasury']:,}**"
    )


# =========================================================
# ÜLKE KUR
# =========================================================

@bot.command()
async def ülkekur(ctx, *, isim=None):

    if not is_management(ctx.author):
        return await ctx.send(
            "❌ Bu komutu sadece yönetim kullanabilir."
        )

    if not isim:
        return await ctx.send(
            "❌ Kullanım: `.ülkekur Türkiye`"
        )

    country = db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=?
        """,
        (ctx.guild.id,)
    ).fetchone()

    if country:

        db.execute(
            """
            UPDATE countries
            SET name=?,
                president_id=?
            WHERE guild_id=?
            """,
            (
                isim,
                ctx.author.id,
                ctx.guild.id
            )
        )

    else:

        db.execute(
            """
            INSERT INTO countries
            (
                guild_id,
                name,
                capital,
                president_id,
                treasury,
                founded_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.guild.id,
                isim,
                "Başkent",
                ctx.author.id,
                100000,
                now()
            )
        )

    db.commit()

    await ctx.send(
        f"🌍 Ülkenin adı **{isim}** olarak ayarlandı."
    )


# =========================================================
# ADAY OL
# =========================================================

@bot.command()
async def adayol(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    existing = db.execute(
        """
        SELECT 1
        FROM elections
        WHERE guild_id=?
        AND candidate_id=?
        AND active=1
        """,
        (
            ctx.guild.id,
            ctx.author.id
        )
    ).fetchone()

    if existing:
        return await ctx.send(
            "❌ Zaten adaysın."
        )

    db.execute(
        """
        INSERT INTO elections
        (
            guild_id,
            candidate_id
        )
        VALUES (?, ?)
        """,
        (
            ctx.guild.id,
            ctx.author.id
        )
    )

    db.commit()

    await ctx.send(
        "🗳️ Cumhurbaşkanlığı seçiminde aday oldun."
    )


# =========================================================
# ADAYLAR
# =========================================================

@bot.command()
async def adaylar(ctx):

    rows = db.execute(
        """
        SELECT *
        FROM elections
        WHERE guild_id=?
        AND active=1
        ORDER BY votes DESC
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "🗳️ Aktif aday yok."
        )

    lines = []

    for index, row in enumerate(rows, 1):

        member = ctx.guild.get_member(
            row["candidate_id"]
        )

        name = (
            member.mention
            if member
            else str(row["candidate_id"])
        )

        lines.append(
            f"**{index}.** {name} — `{row['votes']}` oy"
        )

    await ctx.send(
        "🗳️ **ADAYLAR**\n\n"
        + "\n".join(lines)
    )


# =========================================================
# OY VER
# =========================================================

@bot.command()
async def oyver(
    ctx,
    member: discord.Member = None
):

    if not member:
        return await ctx.send(
            "❌ Kullanım: `.oyver @aday`"
        )

    if not get_user(
        ctx.guild.id,
        ctx.author.id
    ):
        return await ctx.send(
            "❌ Önce kayıt ol."
        )

    candidate = db.execute(
        """
        SELECT *
        FROM elections
        WHERE guild_id=?
        AND candidate_id=?
        AND active=1
        """,
        (
            ctx.guild.id,
            member.id
        )
    ).fetchone()

    if not candidate:
        return await ctx.send(
            "❌ Bu kişi aktif aday değil."
        )

    used = db.execute(
        """
        SELECT 1
        FROM votes
        WHERE guild_id=?
        AND voter_id=?
        AND election_id=?
        """,
        (
            ctx.guild.id,
            ctx.author.id,
            candidate["id"]
        )
    ).fetchone()

    if used:
        return await ctx.send(
            "❌ Bu seçimde zaten oy kullandın."
        )

    db.execute(
        """
        UPDATE elections
        SET votes=votes+1
        WHERE id=?
        """,
        (candidate["id"],)
    )

    db.execute(
        """
        INSERT INTO votes
        (
            guild_id,
            voter_id,
            election_id
        )
        VALUES (?, ?, ?)
        """,
        (
            ctx.guild.id,
            ctx.author.id,
            candidate["id"]
        )
    )

    db.commit()

    await ctx.send(
        f"🗳️ Oyun **{member.display_name}** kişisine verildi."
    )


# =========================================================
# SEÇİM DURUM
# =========================================================

@bot.command()
async def seçim(ctx, işlem=None):

    if işlem != "durum":
        return await ctx.send(
            "❌ Kullanım: `.seçim durum`"
        )

    rows = db.execute(
        """
        SELECT *
        FROM elections
        WHERE guild_id=?
        AND active=1
        ORDER BY votes DESC
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "🗳️ Aktif seçim yok."
        )

    total = sum(
        row["votes"]
        for row in rows
    )

    lines = []

    for row in rows:

        member = ctx.guild.get_member(
            row["candidate_id"]
        )

        name = (
            member.mention
            if member
            else str(row["candidate_id"])
        )

        lines.append(
            f"• {name}: `{row['votes']}` oy"
        )

    await ctx.send(
        "🗳️ **SEÇİM DURUMU**\n\n"
        f"Toplam oy: `{total}`\n\n"
        + "\n".join(lines)
    )


# =========================================================
# SÖYLE
# =========================================================

@bot.command()
async def söyle(ctx, *, mesaj=None):

    if not is_staff(ctx.author):
        return await ctx.send(
            "❌ Bu komutu sadece yetkililer kullanabilir."
        )

    if not mesaj:
        return await ctx.send(
            "❌ Kullanım: `.söyle mesaj`"
        )

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    await ctx.send(mesaj)


# =========================================================
# DUYURU
# =========================================================

@bot.command()
async def duyuru(ctx, *, mesaj=None):

    if not is_staff(ctx.author):
        return await ctx.send(
            "❌ Bu komutu sadece yetkililer kullanabilir."
        )

    if not mesaj:
        return await ctx.send(
            "❌ Kullanım: `.duyuru mesaj`"
        )

    channel = discord.utils.get(
        ctx.guild.text_channels,
        name="📢・duyurular"
    )

    if not channel:
        return await ctx.send(
            "❌ Duyuru kanalı bulunamadı."
        )

    embed = discord.Embed(
        title="📢 DUYURU",
        description=mesaj,
        colour=discord.Colour.blue(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.set_footer(
        text=f"Yetkili: {ctx.author}"
    )

    await channel.send(
        embed=embed
    )

    await ctx.send(
        "✅ Duyuru gönderildi."
    )


# =========================================================
# TEMİZLE
# =========================================================

@bot.command()
async def temizle(
    ctx,
    miktar: int = 10
):

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
            f"🧹 `{max(0, len(deleted) - 1)}` "
            "mesaj temizlendi.",
            delete_after=3
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Mesajları silme iznim yok."
        )


# =========================================================
# EMBED
# =========================================================

@bot.command()
async def embed(ctx, *, veri=None):

    if not is_staff(ctx.author):
        return await ctx.send(
            "❌ Yetkin yok."
        )

    if not veri or "|" not in veri:
        return await ctx.send(
            "❌ Kullanım:\n"
            "`.embed Başlık | Mesaj`"
        )

    title, description = veri.split(
        "|",
        1
    )

    e = discord.Embed(
        title=title.strip(),
        description=description.strip(),
        colour=discord.Colour.blue()
    )

    e.set_footer(
        text=f"Gönderen: {ctx.author}"
    )

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    await ctx.send(
        embed=e
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

    embed = discord.Embed(
        title=f"📊 {ctx.guild.name}",
        colour=discord.Colour.blue()
    )

    embed.add_field(
        name="👥 Üye",
        value=str(ctx.guild.member_count),
        inline=True
    )

    embed.add_field(
        name="💬 Kanal",
        value=str(len(ctx.guild.channels)),
        inline=True
    )

    embed.add_field(
        name="🎭 Rol",
        value=str(len(ctx.guild.roles)),
        inline=True
    )

    embed.add_field(
        name="📡 Ping",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )

    await ctx.send(
        embed=embed
    )


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
        return await ctx.send(
            f"⏳ Biraz bekle: "
            f"`{error.retry_after:.1f}` saniye."
        )

    if isinstance(
        error,
        commands.BadArgument
    ):
        return await ctx.send(
            "❌ Kullanıcı veya sayı hatalı."
        )

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        return await ctx.send(
            "❌ Bu işlem için Discord yetkin yok."
        )

    print(
        f"[KOMUT HATASI] "
        f"{ctx.command}: {error}"
    )


# =========================================================
# BAŞLAT
# =========================================================

bot.run(TOKEN)
