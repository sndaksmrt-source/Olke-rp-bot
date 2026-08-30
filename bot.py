import os
import sqlite3
import asyncio
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
        "DISCORD_TOKEN bulunamadı! Railway > Variables kısmına ekle."
    )

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
    population INTEGER NOT NULL DEFAULT 0,
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
    "👑・Kurucu": discord.Colour.gold(),
    "🛡️・Baş Yönetici": discord.Colour.orange(),
    "🔧・Yönetici": discord.Colour.red(),
    "🔨・Baş Moderatör": discord.Colour.purple(),
    "🛡️・Moderatör": discord.Colour.blue(),
}

RP_ROLES = {
    "👑・Devlet Başkanı": discord.Colour.gold(),
    "⭐・Başkan Yardımcısı": discord.Colour.orange(),
    "🏛️・Başbakan": discord.Colour.red(),
    "🏢・Bakan": discord.Colour.blue(),
    "🗳️・Milletvekili": discord.Colour.purple(),
    "⚖️・Yargı": discord.Colour.dark_grey(),
    "👮・Polis": discord.Colour.dark_blue(),
    "📰・Gazeteci": discord.Colour.yellow(),
    "🏢・Şirket Sahibi": discord.Colour.green(),
    "💼・Çalışan": discord.Colour.teal(),
    "👤・Vatandaş": discord.Colour.light_grey(),
    "🌱・Yeni Vatandaş": discord.Colour.dark_grey(),
}

ALL_ROLE_NAMES = set(STAFF_ROLES) | set(RP_ROLES)


# =========================================================
# YETKİ SİSTEMİ
# =========================================================

MANAGEMENT_ROLES = {
    "👑・Kurucu",
    "🛡️・Baş Yönetici",
    "🔧・Yönetici",
}

STAFF_NAMES = set(STAFF_ROLES.keys())


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
        or has_role(member, MANAGEMENT_ROLES)
    )


def is_founder(member):
    return (
        member.guild_permissions.administrator
        or has_role(member, {"👑・Kurucu"})
    )


# =========================================================
# KANAL ŞABLONU
# =========================================================

CATEGORIES = {
    "📌・BİLGİ": [
        "📜・kurallar",
        "📢・duyurular",
        "🌍・ülke-bilgileri",
        "🪪・vatandaş-kayıt",
    ],

    "🏛️・DEVLET": [
        "👑・devlet",
        "🏛️・meclis",
        "📜・kanunlar",
        "🗳️・seçimler",
        "⚖️・mahkeme",
    ],

    "💰・EKONOMİ": [
        "💰・ekonomi",
        "🏦・banka",
        "🏢・şirketler",
        "💼・iş-ilanları",
        "🛒・pazar",
    ],

    "👥・HALK": [
        "💬・şehir-sohbeti",
        "🏙️・şehirler",
        "🏠・evler",
    ],

    "📰・MEDYA": [
        "📰・son-dakika",
        "🗞️・gazeteler",
    ],

    "🌎・DIŞ İLİŞKİLER": [
        "🌎・diplomasi",
        "🤝・ittifaklar",
    ],

    "🔐・YÖNETİM": [
        "🔐・yetkili-komutları",
        "📋・başvurular",
        "📝・şikayetler",
        "📊・loglar",
    ],
}


READ_ONLY_CHANNELS = {
    "📜・kurallar",
    "📢・duyurular",
    "🌍・ülke-bilgileri",
    "📰・son-dakika",
    "📊・loglar",
}


MANAGEMENT_CHANNELS = {
    "🔐・yetkili-komutları",
    "📋・başvurular",
    "📝・şikayetler",
    "📊・loglar",
}


# =========================================================
# KANAL İZİNLERİ
# =========================================================

def normal_channel_overwrite():
    return discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
        send_messages=True,
        add_reactions=True,
        embed_links=True,
        attach_files=True
    )


def readonly_overwrite():
    return discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
        send_messages=False,
        add_reactions=False,
        attach_files=False
    )


def staff_overwrite():
    return discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
        send_messages=True,
        manage_messages=True,
        embed_links=True,
        attach_files=True,
        add_reactions=True
    )


def management_overwrite():
    return discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
        send_messages=True,
        manage_messages=True,
        manage_channels=True,
        manage_permissions=True,
        embed_links=True,
        attach_files=True,
        add_reactions=True
    )


# =========================================================
# BOT HAZIR
# =========================================================

@bot.event
async def on_ready():

    print("----------------------------------------")
    print(f"BOT: {bot.user}")
    print(f"ID: {bot.user.id}")
    print(f"SUNUCU SAYISI: {len(bot.guilds)}")
    print("----------------------------------------")

    try:
        await bot.change_presence(
            activity=discord.Game(
                name=".yardım | Ülke RP"
            )
        )
    except Exception:
        pass


# =========================================================
# YARDIM
# =========================================================

@bot.command()
async def yardım(ctx):

    embed = discord.Embed(
        title="🌍 ÜLKE RP BOT",
        description="Ülke RP komutları",
        colour=discord.Colour.blue()
    )

    embed.add_field(
        name="👤 Vatandaş",
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
        name="💼 Meslek",
        value=(
            "`.işler`\n"
            "`.iş meslek`\n"
            "`.çalış`"
        ),
        inline=False
    )

    embed.add_field(
        name="💰 Ekonomi",
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
        name="🗳️ Siyaset",
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
            name="🔐 Yetkili",
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
            "❌ Bu komutu sadece yönetim kullanabilir."
        )

    guild = ctx.guild
    me = guild.me

    if not me.guild_permissions.manage_channels:
        return await ctx.send(
            "❌ Botta **Kanalları Yönet** izni yok."
        )

    if not me.guild_permissions.manage_roles:
        return await ctx.send(
            "❌ Botta **Rolleri Yönet** izni yok."
        )

    # Komut kanalının silineceğini kullanıcıya DM ile bildir.
    try:
        await ctx.author.send(
            "🏗️ Ülke RP kurulumu başladı. "
            "Sunucudaki kanallar ve roller yeniden oluşturuluyor."
        )
    except Exception:
        pass

    print(f"[KUR] {guild.name} için kurulum başladı.")

    # =====================================================
    # 1 - TÜM KANALLARI SİL
    # =====================================================

    for channel in list(guild.channels):

        try:
            await channel.delete(
                reason="Ülke RP sıfırdan kurulum"
            )

            print(
                f"[KANAL SİLİNDİ] {channel.name}"
            )

            # Discord rate limitlerini zorlamamak için
            await asyncio.sleep(0.4)

        except discord.Forbidden:
            print(
                f"[KANAL SİLİNEMEDİ - YETKİ] "
                f"{channel.name}"
            )

        except discord.HTTPException as e:
            print(
                f"[KANAL SİLİNEMEDİ] "
                f"{channel.name}: {e}"
            )

    # =====================================================
    # 2 - TÜM SİLİNEBİLİR ROLLERİ SİL
    # =====================================================

    for role in list(guild.roles):

        # @everyone silinemez
        if role.is_default():
            continue

        # Discord tarafından yönetilen roller silinemez
        if role.managed:
            continue

        # Bot kendi rolünün üstündeki rolleri silemez
        if role >= me.top_role:
            print(
                f"[ROL SİLİNEMEDİ - HİYERARŞİ] "
                f"{role.name}"
            )
            continue

        try:
            await role.delete(
                reason="Ülke RP sıfırdan kurulum"
            )

            print(
                f"[ROL SİLİNDİ] {role.name}"
            )

            await asyncio.sleep(0.4)

        except discord.Forbidden:
            print(
                f"[ROL SİLİNEMEDİ - YETKİ] "
                f"{role.name}"
            )

        except discord.HTTPException as e:
            print(
                f"[ROL SİLİNEMEDİ] "
                f"{role.name}: {e}"
            )

    # =====================================================
    # 3 - YENİ ROLLERİ OLUŞTUR
    # =====================================================

    roles = {}

    all_roles = {}

    all_roles.update(STAFF_ROLES)
    all_roles.update(RP_ROLES)

    # Yönetim rolleri önce oluşturulur
    for role_name, colour in all_roles.items():

        try:

            role = await guild.create_role(
                name=role_name,
                colour=colour,
                mentionable=True,
                reason="Ülke RP rol kurulumu"
            )

            roles[role_name] = role

            print(
                f"[ROL OLUŞTURULDU] {role_name}"
            )

            await asyncio.sleep(0.5)

        except discord.Forbidden:
            print(
                f"[ROL OLUŞTURULAMADI] "
                f"{role_name}"
            )

        except discord.HTTPException as e:
            print(
                f"[ROL HATASI] "
                f"{role_name}: {e}"
            )

    # =====================================================
    # 4 - ROL HİYERARŞİSİ
    # =====================================================

    # En güçlüden daha aşağıya
    hierarchy = [
        "👑・Kurucu",
        "🛡️・Baş Yönetici",
        "🔧・Yönetici",
        "🔨・Baş Moderatör",
        "🛡️・Moderatör",
        "👑・Devlet Başkanı",
        "⭐・Başkan Yardımcısı",
        "🏛️・Başbakan",
        "🏢・Bakan",
        "🗳️・Milletvekili",
        "⚖️・Yargı",
        "👮・Polis",
        "📰・Gazeteci",
        "🏢・Şirket Sahibi",
        "💼・Çalışan",
        "👤・Vatandaş",
        "🌱・Yeni Vatandaş",
    ]

    # Discord rol pozisyonları oluşturulma sırasına göre
    # değişebileceği için üstten alta taşımaya çalışıyoruz.
    position = len(guild.roles) - 1

    for role_name in hierarchy:

        role = roles.get(role_name)

        if not role:
            continue

        try:
            await role.edit(
                position=position,
                reason="Ülke RP rol hiyerarşisi"
            )

            position -= 1

        except discord.HTTPException:
            pass

    # =====================================================
    # 5 - KATEGORİLERİ OLUŞTUR
    # =====================================================

    channels_created = {}

    for category_name, channel_names in CATEGORIES.items():

        try:

            category = await guild.create_category(
                category_name,
                reason="Ülke RP kategori kurulumu"
            )

            print(
                f"[KATEGORİ] {category_name}"
            )

        except discord.Forbidden:
            print(
                f"[KATEGORİ OLUŞTURULAMADI] "
                f"{category_name}"
            )
            continue

        except discord.HTTPException as e:
            print(
                f"[KATEGORİ HATASI] "
                f"{category_name}: {e}"
            )
            continue

        # =================================================
        # KANALLAR
        # =================================================

        for channel_name in channel_names:

            try:

                channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    reason="Ülke RP kanal kurulumu"
                )

                channels_created[channel_name] = channel

                # -----------------------------------------
                # EVERYONE İZNİ
                # -----------------------------------------

                if channel_name in MANAGEMENT_CHANNELS:

                    everyone = discord.PermissionOverwrite(
                        view_channel=False
                    )

                elif channel_name in READ_ONLY_CHANNELS:

                    everyone = discord.PermissionOverwrite(
                        view_channel=True,
                        read_message_history=True,
                        send_messages=False,
                        add_reactions=False,
                        attach_files=False
                    )

                else:

                    everyone = normal_channel_overwrite()

                await channel.set_permissions(
                    guild.default_role,
                    overwrite=everyone,
                    reason="Ülke RP kanal izinleri"
                )

                # -----------------------------------------
                # YETKİLİ İZİNLERİ
                # -----------------------------------------

                for staff_name, staff_role in roles.items():

                    if staff_name not in STAFF_NAMES:
                        continue

                    try:

                        if staff_name in {
                            "👑・Kurucu",
                            "🛡️・Baş Yönetici",
                            "🔧・Yönetici"
                        }:

                            overwrite = management_overwrite()

                        else:

                            overwrite = staff_overwrite()

                        await channel.set_permissions(
                            staff_role,
                            overwrite=overwrite,
                            reason="Yetkili kanal izinleri"
                        )

                    except discord.HTTPException:
                        pass

                # -----------------------------------------
                # RP ROLLERİ
                # -----------------------------------------

                for rp_name in [
                    "👑・Devlet Başkanı",
                    "⭐・Başkan Yardımcısı",
                    "🏛️・Başbakan",
                    "🏢・Bakan",
                    "🗳️・Milletvekili",
                    "⚖️・Yargı",
                    "👮・Polis",
                    "📰・Gazeteci",
                    "🏢・Şirket Sahibi",
                    "💼・Çalışan",
                    "👤・Vatandaş",
                    "🌱・Yeni Vatandaş",
                ]:

                    rp_role = roles.get(rp_name)

                    if not rp_role:
                        continue

                    try:

                        if channel_name in MANAGEMENT_CHANNELS:
                            overwrite = discord.PermissionOverwrite(
                                view_channel=False
                            )
                        else:
                            overwrite = discord.PermissionOverwrite(
                                view_channel=True,
                                read_message_history=True
                            )

                            if channel_name not in READ_ONLY_CHANNELS:
                                overwrite.send_messages = True

                        await channel.set_permissions(
                            rp_role,
                            overwrite=overwrite,
                            reason="RP rol izinleri"
                        )

                    except discord.HTTPException:
                        pass

                print(
                    f"[KANAL OLUŞTURULDU] "
                    f"{channel_name}"
                )

                await asyncio.sleep(0.5)

            except discord.Forbidden:
                print(
                    f"[KANAL OLUŞTURULAMADI] "
                    f"{channel_name}"
                )

            except discord.HTTPException as e:
                print(
                    f"[KANAL HATASI] "
                    f"{channel_name}: {e}"
                )

    # =====================================================
    # 6 - ÜLKEYİ VERİTABANINA EKLE
    # =====================================================

    country = db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=?
        """,
        (guild.id,)
    ).fetchone()

    if country is None:

        db.execute(
            """
            INSERT INTO countries
            (
                guild_id,
                name,
                capital,
                president_id,
                treasury,
                population,
                founded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild.id,
                "Yeni Cumhuriyet",
                "Başkent",
                None,
                100000,
                0,
                now()
            )
        )

    db.commit()

    # =====================================================
    # 7 - KURALLAR
    # =====================================================

    rules = channels_created.get("📜・kurallar")

    if rules:

        embed = discord.Embed(
            title="📜 ÜLKE RP KURALLARI",
            description=(
                "**1.** Herkese saygılı davran.\n"
                "**2.** Spam ve flood yasaktır.\n"
                "**3.** Reklam yasaktır.\n"
                "**4.** Meta Gaming yasaktır.\n"
                "**5.** Power Gaming yasaktır.\n"
                "**6.** Başka oyuncunun karakterini zorla yönetme.\n"
                "**7.** Yetkili kararlarına uy.\n"
                "**8.** Bug ve açıkları kullanma.\n"
                "**9.** RP ile gerçek hayatı birbirine karıştırma.\n"
                "**10.** Kişisel bilgilerini paylaşma.\n"
                "**11.** Dolandırıcılık ve spam yapma.\n"
                "**12.** Sunucu düzenini bozacak davranışlardan kaçın."
            ),
            colour=discord.Colour.blue()
        )

        await rules.send(embed=embed)

    # =====================================================
    # 8 - ÜLKE BİLGİLERİ
    # =====================================================

    info = channels_created.get("🌍・ülke-bilgileri")

    if info:

        embed = discord.Embed(
            title="🌍 ÜLKE RP",
            description=(
                "Ülke RP sistemine hoş geldiniz!\n\n"
                "🪪 `.kayıt İsim`\n"
                "👤 `.profil`\n"
                "💰 `.para`\n"
                "💼 `.işler`\n"
                "🏢 `.şirketkur isim`\n"
                "🗳️ `.adayol`\n\n"
                "📌 Tüm komutlar için `.yardım`"
            ),
            colour=discord.Colour.green()
        )

        await info.send(embed=embed)

    # =====================================================
    # 9 - DUYURU KANALI
    # =====================================================

    announcements = channels_created.get(
        "📢・duyurular"
    )

    if announcements:

        embed = discord.Embed(
            title="📢 SİSTEM KURULDU",
            description=(
                "Ülke RP sistemi başarıyla oluşturuldu.\n\n"
                "Vatandaş olmak için `.kayıt İsim` kullan."
            ),
            colour=discord.Colour.green()
        )

        await announcements.send(embed=embed)

    # =====================================================
    # 10 - LOG
    # =====================================================

    logs = channels_created.get("📊・loglar")

    if logs:

        await logs.send(
            "✅ **Ülke RP kurulumu tamamlandı.**\n"
            f"👤 Kurucu: {ctx.author.mention}\n"
            f"🕐 Zaman: <t:{int(datetime.now().timestamp())}:F>"
        )

    print(
        f"[KUR] {guild.name} kurulumu tamamlandı."
    )

    # Kullanıcıya DM
    try:

        await ctx.author.send(
            "✅ **ÜLKE RP KURULUMU TAMAMLANDI!**\n\n"
            "🗑️ Eski kanallar temizlendi.\n"
            "🗑️ Silinebilir eski roller temizlendi.\n"
            "🎭 Yeni roller oluşturuldu.\n"
            "📁 Yeni kategoriler oluşturuldu.\n"
            "💬 Yeni kanallar oluşturuldu.\n"
            "🔐 Kanal izinleri ayarlandı.\n"
            "🌍 Ülke sistemi hazır.\n"
            "💰 Ekonomi sistemi hazır.\n"
            "🗳️ Seçim sistemi hazır."
        )

    except Exception:
        pass


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

    if get_user(ctx.guild.id, ctx.author.id):
        return await ctx.send(
            "❌ Zaten kayıtlısın."
        )

    ensure_user(
        ctx.guild.id,
        ctx.author.id,
        isim
    )

    role = discord.utils.get(
        ctx.guild.roles,
        name="🌱・Yeni Vatandaş"
    )

    if role and role < ctx.guild.me.top_role:

        try:
            await ctx.author.add_roles(
                role,
                reason="Vatandaş kaydı"
            )
        except discord.HTTPException:
            pass

    # Ülke nüfusu
    db.execute(
        """
        UPDATE countries
        SET population=population+1
        WHERE guild_id=?
        """,
        (ctx.guild.id,)
    )

    db.commit()

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
            "❌ Önce `.iş meslek` seç."
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
            "❌ Şirket kurmak için ₺5.000 gerekiyor."
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
            "❌ Ev için ₺10.000 gerekiyor."
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

    president = "Yok"

    if country["president_id"]:
        member = ctx.guild.get_member(
            country["president_id"]
        )

        if member:
            president = member.mention

    await ctx.send(
        f"🌍 **{country['name']}**\n"
        f"🏛️ Başkent: **{country['capital']}**\n"
        f"👑 Başkan: {president}\n"
        f"👥 Nüfus: **{country['population']}**\n"
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
                population,
                founded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.guild.id,
                isim,
                "Başkent",
                ctx.author.id,
                100000,
                0,
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

    if not get_user(
        ctx.guild.id,
        ctx.author.id
    ):
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
# SEÇİM
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
            "❌ Yetkin yok."
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
            "❌ Yetkin yok."
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
            "❌ Duyuru kanalı bulunamadı. `.kur` kullan."
        )

    embed = discord.Embed(
        title="📢 DUYURU",
        description=mesaj,
        colour=discord.Colour.blue()
    )

    embed.set_footer(
        text=f"Yetkili: {ctx.author.display_name}"
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
        text=f"Gönderen: {ctx.author.display_name}"
    )

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    await ctx.send(embed=e)


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

    await ctx.send(embed=embed)


# =========================================================
# YETKİLİ ROL VERME
# =========================================================

@bot.command()
async def yetki(ctx, üye: discord.Member = None, *, rol_adi=None):

    if not is_management(ctx.author):
        return await ctx.send(
            "❌ Bu komutu sadece yönetim kullanabilir."
        )

    if not üye or not rol_adi:
        return await ctx.send(
            "❌ Kullanım:\n"
            "`.yetki @üye Moderatör`"
        )

    role = None

    for r in ctx.guild.roles:

        if r.name.lower() == rol_adi.lower():
            role = r
            break

    if not role:
        return await ctx.send(
            "❌ Böyle bir rol bulunamadı."
        )

    if role >= ctx.guild.me.top_role:
        return await ctx.send(
            "❌ Bu rol botun rolünün üstünde."
        )

    try:

        await üye.add_roles(
            role,
            reason=f"Yetkili: {ctx.author}"
        )

        await ctx.send(
            f"✅ {üye.mention} kişisine "
            f"**{role.name}** verildi."
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Bu rolü veremiyorum. "
            "Botun rolünü daha yukarı taşı."
        )


# =========================================================
# YETKİLİ ROLLER
# =========================================================

@bot.command()
async def yetkililer(ctx):

    embed = discord.Embed(
        title="🔐 YETKİLİ ROLLERİ",
        description=(
            "👑 Kurucu — Tam yetki\n"
            "🛡️ Baş Yönetici — Yönetim\n"
            "🔧 Yönetici — Yönetim\n"
            "🔨 Baş Moderatör — Moderasyon\n"
            "🛡️ Moderatör — Moderasyon"
        ),
        colour=discord.Colour.blue()
    )

    await ctx.send(embed=embed)


# =========================================================
# HATA SİSTEMİ
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
        commands.MissingRequiredArgument
    ):

        return await ctx.send(
            "❌ Eksik bilgi girdin."
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
        commands.CommandInvokeError
    ):

        original = error.original

        print(
            f"[KOMUT HATASI] "
            f"{ctx.command}: {original}"
        )

        try:
            await ctx.send(
                "❌ Komut çalışırken bir hata oluştu. "
                "Railway Console'u kontrol et."
            )
        except Exception:
            pass

        return

    print(
        f"[HATA] {ctx.command}: {error}"
    )


# =========================================================
# BAŞLAT
# =========================================================

print("🚀 Ülke RP Bot başlatılıyor...")

bot.run(TOKEN)
