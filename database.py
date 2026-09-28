import sqlite3
from datetime import datetime, timedelta

DB_NAME = "bot.db"


def create_database():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Foydalanuvchilar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            rank TEXT DEFAULT 'Bronze',
            subscription_start TEXT,
            subscription_end TEXT,
            is_active INTEGER DEFAULT 0
        )
    """)

    # Videolar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            title TEXT NOT NULL,
            rank TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # To‘lovlar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            rank TEXT NOT NULL,
            amount INTEGER NOT NULL,
            receipt_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)

    # Bir martalik invite linklar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invite_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            rank TEXT NOT NULL,
            days INTEGER DEFAULT 30,
            used INTEGER DEFAULT 0,
            used_by INTEGER,
            created_at TEXT NOT NULL,
            used_at TEXT
        )
    """)

    connection.commit()
    connection.close()


# =========================
# USERS
# =========================

def add_user(telegram_id, username, first_name):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (telegram_id, username, first_name)
        VALUES (?, ?, ?)
    """, (
        telegram_id,
        username,
        first_name
    ))

    connection.commit()
    connection.close()


def get_user(telegram_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT telegram_id,
               username,
               first_name,
               rank,
               subscription_start,
               subscription_end,
               is_active
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    user = cursor.fetchone()

    connection.close()

    return user


def get_all_users():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT telegram_id,
               username,
               first_name,
               rank,
               is_active
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()

    connection.close()

    return users


def update_user_rank(telegram_id, new_rank):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET rank = ?
        WHERE telegram_id = ?
    """, (
        new_rank,
        telegram_id
    ))

    connection.commit()
    connection.close()


# =========================
# SUBSCRIPTION
# =========================

def activate_subscription(telegram_id, days=30):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    now = datetime.now()

    cursor.execute("""
        SELECT subscription_end
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    result = cursor.fetchone()

    if result and result[0]:
        try:
            current_end = datetime.fromisoformat(result[0])
        except ValueError:
            current_end = now
    else:
        current_end = now

    # Agar eski obuna hali tugamagan bo‘lsa,
    # yangi kunlar eski tugash sanasiga qo‘shiladi.
    if current_end > now:
        start_date = now
        end_date = current_end + timedelta(days=days)
    else:
        # Obuna tugagan bo‘lsa, yangi muddat bugundan boshlanadi.
        start_date = now
        end_date = now + timedelta(days=days)

    cursor.execute("""
        UPDATE users
        SET subscription_start = ?,
            subscription_end = ?,
            is_active = 1
        WHERE telegram_id = ?
    """, (
        start_date.isoformat(),
        end_date.isoformat(),
        telegram_id
    ))

    connection.commit()
    connection.close()


def deactivate_subscription(telegram_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET is_active = 0
        WHERE telegram_id = ?
    """, (telegram_id,))

    connection.commit()
    connection.close()


def check_subscription(telegram_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT subscription_end,
               is_active
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    result = cursor.fetchone()

    connection.close()

    if not result:
        return False

    subscription_end = result[0]
    is_active = result[1]

    if not is_active or not subscription_end:
        return False

    end_date = datetime.fromisoformat(subscription_end)

    if datetime.now() >= end_date:
        deactivate_subscription(telegram_id)
        return False

    return True


def get_expired_users():
    """
    Muddati tugagan, lekin hali is_active = 1 bo‘lgan
    foydalanuvchilarni topadi.
    """

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        SELECT telegram_id,
               first_name,
               rank,
               subscription_end
        FROM users
        WHERE is_active = 1
        AND subscription_end IS NOT NULL
        AND subscription_end <= ?
    """, (now,))

    users = cursor.fetchall()

    connection.close()

    return users


def deactivate_expired_users():
    """
    Muddati tugagan foydalanuvchilarni inactive qiladi
    va ularning ma’lumotlarini qaytaradi.
    """

    expired_users = get_expired_users()

    if not expired_users:
        return []

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        UPDATE users
        SET is_active = 0
        WHERE is_active = 1
        AND subscription_end IS NOT NULL
        AND subscription_end <= ?
    """, (now,))

    connection.commit()
    connection.close()

    return expired_users


# =========================
# VIDEOS
# =========================

def add_video(file_id, title, rank):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO videos
        (file_id, title, rank, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        file_id,
        title,
        rank,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()


def get_videos_for_rank(rank):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    if rank == "Bronze":
        allowed_ranks = ("Bronze",)

    elif rank == "Silver":
        allowed_ranks = ("Bronze", "Silver")

    elif rank == "Gold":
        allowed_ranks = ("Bronze", "Silver", "Gold")

    else:
        connection.close()
        return []

    placeholders = ",".join(
        ["?"] * len(allowed_ranks)
    )

    cursor.execute(
        f"""
        SELECT id,
               file_id,
               title,
               rank,
               created_at
        FROM videos
        WHERE rank IN ({placeholders})
        ORDER BY id ASC
        """,
        allowed_ranks
    )

    videos = cursor.fetchall()

    connection.close()

    return videos


def get_all_videos():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               file_id,
               title,
               rank,
               created_at
        FROM videos
        ORDER BY id ASC
    """)

    videos = cursor.fetchall()

    connection.close()

    return videos


def delete_video(video_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM videos
        WHERE id = ?
    """, (video_id,))

    deleted_count = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted_count


# =========================
# PAYMENTS
# =========================

def create_payment(
    telegram_id,
    rank,
    amount,
    receipt_file_id
):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO payments
        (
            telegram_id,
            rank,
            amount,
            receipt_file_id,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        telegram_id,
        rank,
        amount,
        receipt_file_id,
        "pending",
        datetime.now().isoformat()
    ))

    payment_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return payment_id


def get_payment(payment_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               telegram_id,
               rank,
               amount,
               receipt_file_id,
               status,
               created_at
        FROM payments
        WHERE id = ?
    """, (payment_id,))

    payment = cursor.fetchone()

    connection.close()

    return payment


def get_pending_payments():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               telegram_id,
               rank,
               amount,
               receipt_file_id,
               status,
               created_at
        FROM payments
        WHERE status = 'pending'
        ORDER BY id ASC
    """)

    payments = cursor.fetchall()

    connection.close()

    return payments


def update_payment_status(payment_id, status):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE payments
        SET status = ?
        WHERE id = ?
    """, (
        status,
        payment_id
    ))

    connection.commit()
    connection.close()


# =========================
# VIDEO NOTIFICATION
# =========================

def get_active_users_for_video_rank(video_rank):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    if video_rank == "Bronze":
        allowed_ranks = ("Bronze", "Silver", "Gold")

    elif video_rank == "Silver":
        allowed_ranks = ("Silver", "Gold")

    elif video_rank == "Gold":
        allowed_ranks = ("Gold",)

    else:
        connection.close()
        return []

    placeholders = ",".join(
        ["?"] * len(allowed_ranks)
    )

    cursor.execute(
        f"""
        SELECT telegram_id,
               first_name,
               rank
        FROM users
        WHERE is_active = 1
        AND rank IN ({placeholders})
        """,
        allowed_ranks
    )

    users = cursor.fetchall()

    connection.close()

    return users


# =========================
# INVITE LINKS
# =========================

def create_invite_link(token, rank, days=30):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO invite_links
        (
            token,
            rank,
            days,
            used,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        token,
        rank,
        days,
        0,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()


def get_invite_link(token):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               token,
               rank,
               days,
               used,
               used_by,
               created_at,
               used_at
        FROM invite_links
        WHERE token = ?
    """, (token,))

    invite = cursor.fetchone()

    connection.close()

    return invite


def use_invite_link(token, telegram_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               rank,
               days,
               used
        FROM invite_links
        WHERE token = ?
    """, (token,))

    invite = cursor.fetchone()

    if not invite:
        connection.close()
        return None

    invite_id = invite[0]
    rank = invite[1]
    days = invite[2]
    used = invite[3]

    if used:
        connection.close()
        return False

    cursor.execute("""
        UPDATE invite_links
        SET used = 1,
            used_by = ?,
            used_at = ?
        WHERE id = ?
        AND used = 0
    """, (
        telegram_id,
        datetime.now().isoformat(),
        invite_id
    ))

    if cursor.rowcount == 0:
        connection.close()
        return False

    connection.commit()
    connection.close()

    return {
        "rank": rank,
        "days": days
    }
# =========================
# STATISTICS
# =========================

def get_statistics():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    now = datetime.now().isoformat()

    # Jami foydalanuvchilar
    cursor.execute("""
        SELECT COUNT(*)
        FROM users
    """)
    total_users = cursor.fetchone()[0]

    # Faol obunalar
    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE is_active = 1
        AND subscription_end IS NOT NULL
        AND subscription_end > ?
    """, (now,))
    active_users = cursor.fetchone()[0]

    # Muddati tugagan obunalar
    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE subscription_end IS NOT NULL
        AND subscription_end <= ?
    """, (now,))
    expired_users = cursor.fetchone()[0]

    # Faol emas foydalanuvchilar
    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE is_active = 0
        AND (
            subscription_end IS NULL
            OR subscription_end > ?
        )
    """, (now,))
    inactive_users = cursor.fetchone()[0]

    # Bronze
    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE rank = 'Bronze'
    """)
    bronze_users = cursor.fetchone()[0]

    # Silver
    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE rank = 'Silver'
    """)
    silver_users = cursor.fetchone()[0]

    # Gold
    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE rank = 'Gold'
    """)
    gold_users = cursor.fetchone()[0]

    # Jami videolar
    cursor.execute("""
        SELECT COUNT(*)
        FROM videos
    """)
    total_videos = cursor.fetchone()[0]

    # Kutilayotgan to‘lovlar
    cursor.execute("""
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'pending'
    """)
    pending_payments = cursor.fetchone()[0]

    connection.close()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "expired_users": expired_users,
        "inactive_users": inactive_users,
        "bronze_users": bronze_users,
        "silver_users": silver_users,
        "gold_users": gold_users,
        "total_videos": total_videos,
        "pending_payments": pending_payments,
    }