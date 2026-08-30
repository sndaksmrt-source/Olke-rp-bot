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

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect(DB_PATH, check_same_thread=False)
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
    "👮 Polis": discord.Colour.dark_blue(),
    "📰 Gazeteci": discord.Colour.yellow(),
    "🏢 Şirket Sahibi": discord.Colour.green(),
    "💼 Çalışan": discord.Colour.teal(),
    "👤 Vatandaş": discord.Colour.light_grey(),
    "🌱 Yeni Vatandaş": discord.Colour.dark_grey(),
}

ALL_ROLE_NAMES = set(STAFF_ROLES) | set(RP_ROLES)


def is_staff(member):
    if member.guild_permissions.administrator:
        return True

    return any(
        role.name in STAFF_ROLES
        for role in member.roles
    )


def is_management(member):
    if member.guild_permissions.administrator:
        return True

    return any(
        role.name in {
            "👑 Kurucu",
            "🛡️ Baş Yönetici",
            "🔧 Yönetici"
        }
        for role in member.roles
    )


# =========================================================
# KANAL ŞABLONU
# =========================================================

CATEGORIES = {
    "📌 BİLGİ": [
        "📜・kurallar",
        "📢・duyurular",
        "🌍・ülke-bilgileri",
        "🪪・vatandaş-kayıt",
    ],

    "🏛️ DEVLET": [
        "👑・devlet",
        "🏛️・meclis",
        "📜・kanunlar",
        "🗳️・seçimler",
    ],

    "💰 EKONOMİ": [
        "💰・ekonomi",
        "🏦・banka",
        "🏢・şirketler",
        "💼・iş-ilanları",
        "🛒・market",
    ],

    "👥 HALK": [
        "💬・şehir-sohbeti",
        "🏙️・şehirler",
        "🏠・evler",
    ],

    "📰 MEDYA": [
        "📰・son-dakika",
        "🗞️・gazeteler",
    ],

    "🌎 DIŞ İLİŞKİLER": [
        "🌎・diplomasi",
        "⚔️・savaş",
    ],

    "⚙️ YÖNETİM": [
        "🔐・yetkili-komutları",
        "📋・başvurular",
        "📝・şikayetler",
        "📊・loglar",
    ],
}


# Sadece bu kanallarda normal vatandaş yazamaz.
READ_ONLY_CHANNELS = {
    "📜・kurallar",
    "📢・duyurular",
    "🌍・ülke-bilgileri",
    "📰・son-dakika",
    "🔐・yetkili-komutları",
    "📊・loglar",
}


# =========================================================
# BOT HAZIR
# =========================================================

@bot.event
async def on_ready():
    print("====================================")
    print(f"BOT AKTİF: {bot.user}")
    print(f"SUNUCU SAYISI: {len(bot.guilds)}")
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
                "`.kayıt @oyuncu İsim`\n"
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
@commands.cooldown(1, 60, commands.BucketType.guild)
async def kur(ctx):

    if not is_management(ctx.author):
        return await ctx.send(
            "❌ Bu komutu sadece **Kurucu / Baş Yönetici / Yönetici** kullanabilir."
        )

    guild = ctx.guild
    me = guild.me

    # -----------------------------------------------------
    # BOT İZİNLERİ
    # -----------------------------------------------------

    if not me.guild_permissions.administrator:
        missing = []

        if not me.guild_permissions.manage_channels:
            missing.append("Kanalları Yönet")

        if not me.guild_permissions.manage_roles:
            missing.append("Rolleri Yönet")

        if missing:
            return await ctx.send(
                "❌ Botun gerekli izinleri yok:\n"
                + "\n".join(f"• {x}" for x in missing)
                + "\n\nEn kolay çözüm: Bot rolüne **Yönetici** izni ver."
            )

    msg = await ctx.send(
        "🏗️ **ÜLKE RP KURULUYOR...**\n"
        "⚠️ Mevcut kanallar ve RP rolleri temizleniyor."
    )

    # =====================================================
    # 1 — TÜM KANALLARI SİL
    # =====================================================

    deleted_channels = 0

    # Kategoriler dahil bütün kanalları siliyoruz.
    # Discord kanal silindiğinde kategorinin altındaki
    # kanallar da ayrıca silinebilir; bu yüzden liste alıyoruz.

    for channel in list(guild.channels):

        try:
            await channel.delete(
                reason="Ülke RP tam sunucu kurulumu"
            )
            deleted_channels += 1

        except discord.Forbidden:
            print(
                f"[KANAL] Silinemedi (izin): {channel.name}"
            )

        except discord.HTTPException as e:
            print(
                f"[KANAL] Silinemedi: {channel.name} -> {e}"
            )

    # =====================================================
    # 2 — ESKİ RP ROLLERİNİ SİL
    # =====================================================

    deleted_roles = 0

    for role in list(guild.roles):

        # @everyone silinemez.
        if role.is_default():
            continue

        # Botun kendi rolü ve üstündeki roller silinemez.
        if role >= me.top_role:
            print(
                f"[ROL] Botun üstünde, silinemedi: {role.name}"
            )
            continue

        # Yönetici rolü dışında bütün eski roller silinir.
        try:
            await role.delete(
                reason="Ülke RP tam sunucu kurulumu"
            )
            deleted_roles += 1

        except discord.Forbidden:
            print(
                f"[ROL] Silinemedi: {role.name}"
            )

        except discord.HTTPException as e:
            print(
                f"[ROL] Hata: {role.name} -> {e}"
            )

    await msg.edit(
        content=(
            "🎭 **ROLLER OLUŞTURULUYOR...**\n"
            f"🗑️ Silinen kanallar: `{deleted_channels}`\n"
            f"🗑️ Silinen roller: `{deleted_roles}`"
        )
    )

    # =====================================================
    # 3 — YENİ ROLLER
    # =====================================================

    roles = {}

    all_roles = {}

    # Önce yetkili roller
    all_roles.update(STAFF_ROLES)

    # Sonra RP roller
    all_roles.update(RP_ROLES)

    for role_name, colour in all_roles.items():

        try:
            role = await guild.create_role(
                name=role_name,
                colour=colour,
                reason="Ülke RP rol kurulumu"
            )

            roles[role_name] = role

        except discord.Forbidden:
            print(
                f"[ROL] Oluşturulamadı: {role_name}"
            )

        except discord.HTTPException as e:
            print(
                f"[ROL] Hata: {role_name} -> {e}"
            )

    await msg.edit(
        content="📁 **KATEGORİLER VE KANALLAR OLUŞTURULUYOR...**"
    )

    # =====================================================
    # 4 — KANALLARI OLUŞTUR
    # =====================================================

    created_channels = 0

    for category_name, channel_names in CATEGORIES.items():

        try:
            category = await guild.create_category(
                category_name,
                reason="Ülke RP kategori kurulumu"
            )

        except discord.Forbidden:
            print(
                f"[KATEGORİ] Oluşturulamadı: {category_name}"
            )
            continue

        except discord.HTTPException as e:
            print(
                f"[KATEGORİ] Hata: {category_name} -> {e}"
            )
            continue

        for channel_name in channel_names:

            try:
                channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    reason="Ülke RP kanal kurulumu"
                )

                created_channels += 1

            except discord.Forbidden:
                print(
                    f"[KANAL] Oluşturulamadı: {channel_name}"
                )
                continue

            except discord.HTTPException as e:
                print(
                    f"[KANAL] Hata: {channel_name} -> {e}"
                )
                continue

            # =================================================
            # EVERYONE İZİNLERİ
            # =================================================

            everyone = discord.PermissionOverwrite()

            everyone.view_channel = True
            everyone.read_message_history = True

            if channel_name in READ_ONLY_CHANNELS:
                everyone.send_messages = False
            else:
                everyone.send_messages = True

            try:
                await channel.set_permissions(
                    guild.default_role,
                    overwrite=everyone,
                    reason="Ülke RP temel kanal izinleri"
                )

            except discord.HTTPException:
                pass

            # =================================================
            # YETKİLİ ROLLERİ
            # =================================================

            for staff_name in STAFF_ROLES:

                staff_role = roles.get(staff_name)

                if not staff_role:
                    continue

                overwrite = discord.PermissionOverwrite()

                overwrite.view_channel = True
                overwrite.read_message_history = True
                overwrite.send_messages = True
                overwrite.manage_messages = True

                # Yönetim kanallarında daha fazla yetki.
                if category_name == "⚙️ YÖNETİM":
                    overwrite.manage_channels = True

                try:
                    await channel.set_permissions(
                        staff_role,
                        overwrite=overwrite,
                        reason="Ülke RP yetkili izinleri"
                    )

                except discord.HTTPException:
                    pass

            # =================================================
            # KAYIT KANALI
            # =================================================

            if channel_name == "🪪・vatandaş-kayıt":

                for staff_name in STAFF_ROLES:

                    role = roles.get(staff_name)

                    if not role:
                        continue

                    try:
                        await channel.set_permissions(
                            role,
                            view_channel=True,
                            send_messages=True,
                            read_message_history=True,
                            manage_messages=True,
                            reason="Vatandaş kayıt izinleri"
                        )
                    except discord.HTTPException:
                        pass

    # =====================================================
    # 5 — ÜLKE VERİSİ
    # =====================================================

    country = db.execute(
        """
        SELECT *
        FROM countries
        WHERE guild_id=?
        """,
        (guild.id,)
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
                guild.id,
                "Yeni Cumhuriyet",
                "Başkent",
                ctx.author.id,
                100000,
                now()
            )
        )

        db.commit()

    # =====================================================
    # 6 — KURALLAR
    # =====================================================

    rules = discord.utils.get(
        guild.text_channels,
        name="📜・kurallar"
    )

    if rules:

        embed = discord.Embed(
            title="📜 ÜLKE RP KURALLARI",
            description=(
                "**1.** Saygılı davran.\n"
                "**2.** Spam ve flood yapma.\n"
                "**3.** Reklam yapma.\n"
                "**4.** Meta Gaming yapma.\n"
                "**5.** Power Gaming yapma.\n"
                "**6.** Başka oyuncunun karakterini zorla yönetme.\n"
                "**7.** Yetkili kararlarına uy.\n"
                "**8.** Bug veya açıkları kötüye kullanma.\n"
                "**9.** RP ile gerçek hayatı birbirinden ayır.\n"
                "**10.** Kişisel bilgilerini paylaşma."
            ),
            colour=discord.Colour.blue()
        )

        await rules.send(embed=embed)

    # =====================================================
    # 7 — BİLGİ KANALI
    # =====================================================

    info = discord.utils.get(
        guild.text_channels,
        name="🌍・ülke-bilgileri"
    )

    if info:

        embed = discord.Embed(
            title="🌍 ÜLKE RP SİSTEMİ",
            description=(
                "Ülke RP'ye hoş geldiniz!\n\n"
                "🪪 Vatandaş kaydını yetkililer yapar.\n"
                "💰 Ekonomi sistemi aktiftir.\n"
                "💼 Meslek sistemi aktiftir.\n"
                "🏢 Şirket sistemi aktiftir.\n"
                "🗳️ Seçim sistemi aktiftir.\n\n"
                "📌 Komutları görmek için `.yardım` yaz."
            ),
            colour=discord.Colour.green()
        )

        await info.send(embed=embed)

    # =====================================================
    # 8 — KURULUM SONU
    # =====================================================

    await msg.edit(
        content=(
            "✅ **ÜLKE RP KURULUMU TAMAMLANDI!**\n\n"
            f"🗑️ Silinen kanallar: `{deleted_channels}`\n"
            f"🗑️ Silinen roller: `{deleted_roles}`\n"
            f"🎭 Oluşturulan roller: `{len(roles)}`\n"
            f"📁 Oluşturulan kanallar: `{created_channels}`\n"
            "🔐 Kanal izinleri ayarlandı.\n"
            "🌍 Ülke sistemi hazır.\n"
            "💰 Ekonomi sistemi hazır.\n"
            "🗳️ Seçim sistemi hazır.\n\n"
            "📌 Vatandaş eklemek için:\n"
            "`.kayıt @oyuncu İsim Soyisim`"
        )
    )


# =========================================================
# YETKİLİ KAYIT
# =========================================================

@bot.command()
async def kayıt(
    ctx,
    member: discord.Member = None,
    *,
    isim=None
):

    # SADECE YETKİLİ
    if not is_staff(ctx.author):
        return await ctx.send(
            "❌ Bu komutu sadece yetkililer kullanabilir."
        )

    # ETİKET ZORUNLU
    if member is None:
        return await ctx.send(
            "❌ Kullanım:\n"
            "`.kayıt @oyuncu İsim Soyisim`"
        )

    # İSİM ZORUNLU
    if not isim:
        return await ctx.send(
            "❌ Oyuncunun RP ismini yazmalısın.\n"
            "Örnek:\n"
            "`.kayıt @Oyuncu Ahmet Yılmaz`"
        )

    isim = isim.strip()

    if len(isim) < 2:
        return await ctx.send(
            "❌ İsim çok kısa."
        )

    if len(isim) > 40:
        return await ctx.send(
            "❌ İsim 40 karakterden uzun olamaz."
        )

    # BOT KAYDI ENGELLE
    if member.bot:
        return await ctx.send(
            "❌ Botlar vatandaş olarak kaydedilemez."
        )

    # Zaten kayıtlı mı?
    existing = get_user(
        ctx.guild.id,
        member.id
    )

    if existing:
        return await ctx.send(
            f"❌ {member.mention} zaten kayıtlı.\n"
            f"🪪 Mevcut isim: **{existing['name']}**"
        )

    # KAYDET
    ensure_user(
        ctx.guild.id,
        member.id,
        isim
    )

    # =====================================================
    # VATANDAŞ ROLLERİ
    # =====================================================

    new_citizen = discord.utils.get(
        ctx.guild.roles,
        name="🌱 Yeni Vatandaş"
    )

    citizen = discord.utils.get(
        ctx.guild.roles,
        name="👤 Vatandaş"
    )

    # Yeni vatandaş varsa kaldır
    if new_citizen:

        if new_citizen < ctx.guild.me.top_role:

            try:
                await member.remove_roles(
                    new_citizen,
                    reason="Vatandaş kaydı tamamlandı"
                )
            except discord.HTTPException:
                pass

    # Vatandaş rolünü ver
    if citizen:

        if citizen < ctx.guild.me.top_role:

            try:
                await member.add_roles(
                    citizen,
                    reason="Yetkili tarafından vatandaş kaydı"
                )
            except discord.HTTPException:
                pass

    # =====================================================
    # NİCKNAME
    # =====================================================

    try:

        await member.edit(
            nick=isim,
            reason="Yetkili tarafından vatandaş kaydı"
        )

    except discord.Forbidden:
        pass

    except discord.HTTPException:
        pass

    # =====================================================
    # MESAJ
    # =====================================================

    embed = discord.Embed(
        title="🪪 VATANDAŞ KAYDI",
        colour=discord.Colour.green()
    )

    embed.add_field(
        name="👤 Oyuncu",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="🪪 RP İsmi",
        value=isim,
        inline=True
    )

    embed.add_field(
        name="💰 Başlangıç Parası",
        value="₺1.000",
        inline=True
    )

    embed.add_field(
        name="🔨 Kayıt Yapan",
        value=ctx.author.mention,
        inline=True
    )

    await ctx.send(embed=embed)


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
            "❌ Bu kişinin vatandaş kaydı bulunamadı."
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
            "❌ Vatandaş kaydın yok."
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
            "❌ Kullanım: `.öde @oyuncu 500`"
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

    if not meslek or meslek.lower() not in JOBS:
        return await ctx.send(
            "❌ `.işler` yazarak meslekleri gör."
        )

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Vatandaş kaydın yok."
        )

    job_name, _ = JOBS[meslek.lower()]

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
@commands.cooldown(1, 120, commands.BucketType.user)
async def çalış(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Vatandaş kaydın yok."
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
            "❌ Vatandaş kaydın yok."
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
            "❌ Vatandaş kaydın yok."
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
            "❌ Kullanım: `.işeal @oyuncu`"
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
            "❌ Vatandaş kaydın yok."
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
            "❌ Vatandaş kaydın yok."
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

    await ctx.send(
        f"🌍 **{country['name']}**\n"
        f"🏛️ Başkent: **{country['capital']}**\n"
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
# SEÇİM
# =========================================================

@bot.command()
async def adayol(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    if not user:
        return await ctx.send(
            "❌ Vatandaş kaydın yok."
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
            "❌ Önce vatandaş kaydın yapılmalı."
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
            "❌ Duyuru kanalı bulunamadı."
        )

    embed = discord.Embed(
        title="📢 DUYURU",
        description=mesaj,
        colour=discord.Colour.blue()
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
            f"🧹 `{max(0, len(deleted) - 1)}` mesaj temizlendi.",
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
        commands.MissingRequiredArgument
    ):
        return await ctx.send(
            "❌ Eksik bilgi girdin. `.yardım` yaz."
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
        f"[KOMUT HATASI] {ctx.command}: {error}"
    )


# =========================================================
# BAŞLAT
# =========================================================

bot.run(TOKEN)
