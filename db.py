"""Работа с БД PostgreSQL (psycopg2). Настройки подключения — в файле db_config.py."""
import hashlib
import hmac
import os

import psycopg2
import psycopg2.errors
import psycopg2.extras

from db_config import DB_CONFIG


# ---------------------------------------------------------------------
# Базовые функции
# ---------------------------------------------------------------------
def _connect():
    try:
        return psycopg2.connect(client_encoding="utf8", **DB_CONFIG)
    except UnicodeDecodeError as e:
        # PostgreSQL на русской Windows присылает сообщение об ошибке в cp1251,
        # а psycopg2 пытается прочитать его как UTF-8. Достаём исходные байты сами.
        raw = e.object
        text = raw.decode("cp1251", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(e)
        raise psycopg2.OperationalError(
            "Не удалось подключиться к PostgreSQL: " + text.strip()
            + " (проверьте пароль, имя базы и порт в файле db_config.py)"
        ) from None


def fetch_all(sql, params=None):
    conn = _connect()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def fetch_one(sql, params=None):
    conn = _connect()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def run(sql, params=None):
    """Выполнить запрос без результата. Возвращает число затронутых строк."""
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount
    finally:
        conn.close()


def run_many(statements):
    """Несколько запросов в одной транзакции: [(sql, params), ...]."""
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            for sql, params in statements:
                cur.execute(sql, params)
    finally:
        conn.close()


def short_error(exc):
    """Первая строка текста ошибки PostgreSQL (без CONTEXT и т.п.)."""
    return str(exc).strip().splitlines()[0]


def _try(func, *args):
    """Выполнить действие; вернуть None при успехе или текст ошибки БД
    (в том числе сообщения из RAISE EXCEPTION в функциях PostgreSQL)."""
    try:
        func(*args)
        return None
    except psycopg2.Error as e:
        return short_error(e)


# ---------------------------------------------------------------------
# Пароли (PBKDF2 из стандартной библиотеки)
# ---------------------------------------------------------------------
def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex() + "$" + digest.hex()


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


# ---------------------------------------------------------------------
# Авторизация и регистрация
# ---------------------------------------------------------------------
def authenticate(login, password):
    """Возвращает данные пользователя, если пароль верный (иначе None).
    Проверку is_active (отключён ли аккаунт) делает вызывающий код."""
    row = fetch_one(
        """SELECT u.id, u.login, u.password_hash, u.last_name, u.first_name,
                  u.middle_name, u.group_id, u.is_active, r.code AS role,
                  g.name AS group_name
           FROM users u
           JOIN roles r ON r.id = u.role_id
           LEFT JOIN student_groups g ON g.id = u.group_id
           WHERE u.login = %s""",
        (login,),
    )
    if row and verify_password(password, row["password_hash"]):
        return row
    return None


def get_groups():
    return fetch_all("SELECT id, name FROM student_groups ORDER BY name")


def register_user(login, password, last_name, first_name, middle_name, email, role_code, group_id):
    """Возвращает None при успехе или текст ошибки."""
    try:
        run(
            """INSERT INTO users(login, password_hash, email, last_name, first_name,
                                 middle_name, role_id, group_id)
               VALUES (%s, %s, %s, %s, %s, %s,
                       (SELECT id FROM roles WHERE code = %s), %s)""",
            (login, hash_password(password), email or None, last_name, first_name,
             middle_name or None, role_code, group_id),
        )
        return None
    except psycopg2.errors.UniqueViolation:
        return "Пользователь с таким логином или email уже существует"
    except psycopg2.Error as e:
        return short_error(e)


# ---------------------------------------------------------------------
# Студент
# ---------------------------------------------------------------------
def get_profile(uid):
    return fetch_one(
        """SELECT p.total_xp, p.coins, p.level_no, p.current_streak, p.best_streak,
                  l.title AS level_title, l.xp_required AS level_start,
                  (SELECT MIN(xp_required) FROM levels WHERE xp_required > p.total_xp) AS next_xp
           FROM student_profiles p
           JOIN levels l ON l.level_no = p.level_no
           WHERE p.user_id = %s""",
        (uid,),
    )


def get_student_tasks(uid):
    """Задания, которые видит студент."""
    return fetch_all(
        """SELECT t.id, d.name AS discipline, t.title, t.description,
                  t.type::text AS type, t.difficulty::text AS difficulty,
                  t.max_score, t.xp_reward, t.deadline,
                  s.status::text AS status, s.score, s.teacher_comment
           FROM tasks t
           JOIN disciplines d ON d.id = t.discipline_id
           LEFT JOIN LATERAL (
               SELECT status, score, teacher_comment
               FROM submissions
               WHERE task_id = t.id AND student_id = %s
               ORDER BY attempt_no DESC LIMIT 1
           ) s ON TRUE
           WHERE t.is_active
           ORDER BY t.deadline NULLS LAST, t.id""",
        (uid,),
    )


def submit_work(task_id, uid, answer_text):
    run(
        """INSERT INTO submissions(task_id, student_id, attempt_no, answer_text)
           VALUES (%s, %s,
                   COALESCE((SELECT MAX(attempt_no) FROM submissions
                             WHERE task_id = %s AND student_id = %s), 0) + 1,
                   %s)""",
        (task_id, uid, task_id, uid, answer_text),
    )


def get_rating(group_name=None):
    if group_name:
        return fetch_all(
            """SELECT place, student_name, group_name, total_xp, level_no
               FROM v_rating_group WHERE group_name = %s ORDER BY place, student_name""",
            (group_name,),
        )
    return fetch_all(
        """SELECT place, student_name, group_name, total_xp, level_no
           FROM v_rating_global ORDER BY place, student_name"""
    )


def get_discipline_rating(discipline_id, group_name=None):
    """Рейтинг по дисциплине (представление v_rating_discipline);
    место пересчитывается среди выбранной группы, если она указана."""
    return fetch_all(
        """SELECT RANK() OVER (ORDER BY r.discipline_xp DESC) AS place,
                  r.student_name, g.name AS group_name,
                  r.discipline_xp AS total_xp, r.tasks_done
           FROM v_rating_discipline r
           JOIN users u ON u.id = r.student_id
           LEFT JOIN student_groups g ON g.id = u.group_id
           WHERE r.discipline_id = %s AND (%s::text IS NULL OR g.name = %s)
           ORDER BY place, r.student_name""",
        (discipline_id, group_name, group_name),
    )


def get_student_progress(uid):
    """Успеваемость студента по дисциплинам: представления v_student_progress
    и v_rating_discipline + число доступных заданий."""
    return fetch_all(
        """SELECT d.id, d.code, d.name,
                  COALESCE(p.tasks_graded, 0) AS tasks_graded,
                  p.avg_percent,
                  (SELECT COUNT(*) FROM tasks t
                    WHERE t.discipline_id = d.id AND t.is_active) AS tasks_total,
                  r.place,
                  (SELECT COUNT(*) FROM v_rating_discipline r2
                    WHERE r2.discipline_id = d.id) AS participants
           FROM disciplines d
           LEFT JOIN v_student_progress p ON p.student_id = %s AND p.discipline_id = d.id
           LEFT JOIN v_rating_discipline r ON r.student_id = %s AND r.discipline_id = d.id
           WHERE EXISTS (SELECT 1 FROM tasks t
                          WHERE t.discipline_id = d.id AND t.is_active)
           ORDER BY d.code""",
        (uid, uid),
    )


def get_student_quests(uid):
    return fetch_all(
        """SELECT q.id, q.title, q.description, q.ends_at, q.xp_reward, q.coin_reward,
                  d.name AS discipline,
                  COUNT(qt.task_id) AS total,
                  COUNT(*) FILTER (WHERE EXISTS (
                      SELECT 1 FROM submissions s
                       WHERE s.task_id = qt.task_id AND s.student_id = %s
                         AND s.status = 'graded')) AS done,
                  sq.status::text AS status, sq.completed_at
           FROM quests q
           JOIN quest_tasks qt ON qt.quest_id = q.id
           LEFT JOIN disciplines d ON d.id = q.discipline_id
           LEFT JOIN student_quests sq ON sq.quest_id = q.id AND sq.student_id = %s
           WHERE q.is_active
           GROUP BY q.id, d.name, sq.status, sq.completed_at
           ORDER BY (sq.status = 'completed') NULLS FIRST, q.ends_at NULLS LAST, q.id""",
        (uid, uid),
    )


def get_achievements(uid):
    return fetch_all(
        """SELECT a.title, a.description, a.condition_type::text AS condition_type,
                  a.condition_value, a.xp_bonus, ua.awarded_at
           FROM achievements a
           LEFT JOIN user_achievements ua
                  ON ua.achievement_id = a.id AND ua.student_id = %s
           ORDER BY (ua.awarded_at IS NULL), a.id""",
        (uid,),
    )


def get_rewards():
    return fetch_all(
        "SELECT id, title, description, cost_coins, stock FROM rewards WHERE is_active ORDER BY cost_coins"
    )


def buy_reward(uid, reward_id, cost_coins=None):
    """Покупка награды студентом. Возвращает None при успехе или текст ошибки."""
    conn = _connect()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, stock, cost_coins, is_active FROM rewards WHERE id = %s FOR UPDATE",
                (reward_id,),
            )
            r = cur.fetchone()
            if not r or not r["is_active"]:
                return "Награда недоступна"
            if r["stock"] is not None and r["stock"] <= 0:
                return "Награда закончилась"

            price = cost_coins if cost_coins is not None else r["cost_coins"]

            cur.execute(
                "SELECT coins FROM student_profiles WHERE user_id = %s FOR UPDATE",
                (uid,),
            )
            prof = cur.fetchone()
            if not prof or prof["coins"] < price:
                return "Недостаточно монет для покупки!"

            cur.execute(
                """INSERT INTO reward_purchases(student_id, reward_id, cost_coins)
                   VALUES (%s, %s, %s) RETURNING id""",
                (uid, reward_id, price),
            )
            purchase_id = cur.fetchone()["id"]

            cur.execute(
                """INSERT INTO xp_transactions(student_id, coin_amount, reason, source_id, comment)
                   VALUES (%s, %s, 'reward_purchase', %s, %s)""",
                (uid, -price, purchase_id, f"Покупка: {r['title']}"),
            )

            if r["stock"] is not None:
                cur.execute(
                    "UPDATE rewards SET stock = stock - 1 WHERE id = %s",
                    (reward_id,),
                )
        return None
    except psycopg2.Error as e:
        return short_error(e)
    finally:
        conn.close()


def get_student_purchases(uid):
    return fetch_all(
        """SELECT p.id, r.title, p.cost_coins, p.status::text AS status,
                  p.purchased_at, p.issued_at
           FROM reward_purchases p JOIN rewards r ON r.id = p.reward_id
           WHERE p.student_id = %s
           ORDER BY p.purchased_at DESC, p.id DESC LIMIT 50""",
        (uid,),
    )


def get_xp_history(uid):
    return fetch_all(
        """SELECT created_at, xp_amount, coin_amount, comment
           FROM xp_transactions WHERE student_id = %s
           ORDER BY created_at DESC, id DESC LIMIT 100""",
        (uid,),
    )


def get_notifications(uid):
    return fetch_all(
        """SELECT id, title, body, is_read, created_at
           FROM notifications WHERE user_id = %s
           ORDER BY created_at DESC, id DESC LIMIT 100""",
        (uid,),
    )


def mark_notifications_read(uid):
    run("UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND NOT is_read", (uid,))


# ---------------------------------------------------------------------
# Преподаватель
# ---------------------------------------------------------------------
def get_pending_submissions(teacher_id):
    return fetch_all(
        """SELECT s.id, s.student_id, u.last_name || ' ' || u.first_name AS student,
                  g.name AS grp, t.title, t.description, t.max_score,
                  d.name AS discipline, s.attempt_no, s.submitted_at, s.answer_text
           FROM submissions s
           JOIN tasks t ON t.id = s.task_id
           JOIN disciplines d ON d.id = t.discipline_id
           JOIN users u ON u.id = s.student_id
           LEFT JOIN student_groups g ON g.id = u.group_id
           WHERE s.status IN ('submitted', 'on_review') AND t.author_id = %s
           ORDER BY s.submitted_at""",
        (teacher_id,),
    )


def grade_submission(sub_id, student_id, score, comment, teacher_id):
    """Оценить работу. Триггеры в БД сами начислят XP; затем проверяем достижения."""
    run_many([
        ("""UPDATE submissions
               SET status = 'graded', score = %s, teacher_comment = %s,
                   checked_by = %s, checked_at = now()
             WHERE id = %s""", (score, comment or None, teacher_id, sub_id)),
        ("SELECT check_achievements(%s)", (student_id,)),
    ])


def send_to_revision(sub_id, comment, teacher_id):
    run(
        """UPDATE submissions
              SET status = 'revision', teacher_comment = %s,
                  checked_by = %s, checked_at = now()
            WHERE id = %s""",
        (comment or None, teacher_id, sub_id),
    )


def get_disciplines():
    return fetch_all("SELECT id, code, name FROM disciplines ORDER BY code")


def get_teacher_disciplines(teacher_id):
    """Дисциплины, которые преподавателю назначил администратор."""
    return fetch_all(
        """SELECT DISTINCT d.id, d.code, d.name
           FROM teaching_assignments ta JOIN disciplines d ON d.id = ta.discipline_id
           WHERE ta.teacher_id = %s ORDER BY d.code""",
        (teacher_id,),
    )


def get_topics(discipline_id):
    return fetch_all(
        "SELECT id, title FROM topics WHERE discipline_id = %s ORDER BY order_no",
        (discipline_id,),
    )


def get_teacher_tasks(teacher_id):
    return fetch_all(
        """SELECT t.id, d.name AS discipline, t.title, t.type::text AS type,
                  t.difficulty::text AS difficulty, t.max_score, t.xp_reward,
                  t.deadline, t.is_active
           FROM tasks t JOIN disciplines d ON d.id = t.discipline_id
           WHERE t.author_id = %s ORDER BY t.id DESC""",
        (teacher_id,),
    )


def create_task(discipline_id, author_id, title, description, task_type, difficulty,
                max_score, xp_reward, coin_reward, deadline, topic_id=None):
    run(
        """INSERT INTO tasks(discipline_id, topic_id, author_id, title, description, type,
                             difficulty, max_score, xp_reward, coin_reward, deadline)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (discipline_id, topic_id, author_id, title, description or None, task_type,
         difficulty, max_score, xp_reward, coin_reward, deadline),
    )


def toggle_task(task_id):
    run("UPDATE tasks SET is_active = NOT is_active WHERE id = %s", (task_id,))


def get_teacher_groups_stats(teacher_id):
    """Группы и дисциплины преподавателя со статистикой."""
    return fetch_all(
        """SELECT g.name AS grp, d.name AS discipline, ta.academic_year, ta.semester,
                  (SELECT COUNT(*) FROM users u JOIN roles r ON r.id = u.role_id
                    WHERE u.group_id = g.id AND r.code = 'student' AND u.is_active) AS students,
                  (SELECT ROUND(AVG(s.score / t.max_score * 100), 1)
                     FROM submissions s
                     JOIN tasks t ON t.id = s.task_id
                     JOIN users u ON u.id = s.student_id
                    WHERE s.status = 'graded' AND u.group_id = g.id
                      AND t.discipline_id = ta.discipline_id
                      AND t.author_id = ta.teacher_id) AS avg_percent,
                  (SELECT COUNT(*)
                     FROM submissions s
                     JOIN tasks t ON t.id = s.task_id
                     JOIN users u ON u.id = s.student_id
                    WHERE s.status IN ('submitted', 'on_review') AND u.group_id = g.id
                      AND t.discipline_id = ta.discipline_id
                      AND t.author_id = ta.teacher_id) AS pending
           FROM teaching_assignments ta
           JOIN student_groups g ON g.id = ta.group_id
           JOIN disciplines d ON d.id = ta.discipline_id
           WHERE ta.teacher_id = %s
           ORDER BY g.name, d.code""",
        (teacher_id,),
    )


# ----- квесты (преподаватель) -----
def create_quest(title, description, xp_reward, coin_reward, ends_at, task_ids):
    """Создать квест из выбранных заданий. Дисциплина квеста определяется
    автоматически: если все задания из одной дисциплины — она, иначе пусто."""
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO quests(discipline_id, title, description, starts_at, ends_at,
                                      xp_reward, coin_reward)
                   VALUES ((SELECT CASE WHEN COUNT(DISTINCT discipline_id) = 1
                                        THEN MIN(discipline_id) END
                              FROM tasks WHERE id = ANY(%s)),
                           %s, %s, now(), %s, %s, %s)
                   RETURNING id""",
                (list(task_ids), title, description or None, ends_at,
                 xp_reward, coin_reward),
            )
            quest_id = cur.fetchone()[0]
            for tid in task_ids:
                cur.execute("INSERT INTO quest_tasks(quest_id, task_id) VALUES (%s, %s)",
                            (quest_id, tid))
            return quest_id
    finally:
        conn.close()


def get_teacher_quests(teacher_id=None):
    return fetch_all(
        """SELECT q.id, q.title, d.name AS discipline, q.xp_reward, q.coin_reward,
                  q.ends_at, q.is_active,
                  (SELECT COUNT(*) FROM quest_tasks qt WHERE qt.quest_id = q.id) AS tasks,
                  (SELECT COUNT(*) FROM student_quests sq
                    WHERE sq.quest_id = q.id AND sq.status = 'completed') AS completed,
                  (SELECT COUNT(*) FROM student_quests sq
                    WHERE sq.quest_id = q.id AND sq.status = 'in_progress') AS in_progress
           FROM quests q
           LEFT JOIN disciplines d ON d.id = q.discipline_id
           ORDER BY q.id DESC"""
    )


def toggle_quest(quest_id):
    run("UPDATE quests SET is_active = NOT is_active WHERE id = %s", (quest_id,))


# ----- выдача наград (преподаватель) -----
def get_pending_purchases():
    return fetch_all(
        """SELECT p.id, u.last_name || ' ' || u.first_name AS student, g.name AS grp,
                  r.title, p.cost_coins, p.purchased_at
           FROM reward_purchases p
           JOIN users u ON u.id = p.student_id
           LEFT JOIN student_groups g ON g.id = u.group_id
           JOIN rewards r ON r.id = p.reward_id
           WHERE p.status = 'pending'
           ORDER BY p.purchased_at, p.id"""
    )


def issue_reward(purchase_id):
    """Отметить награду выданной. None при успехе или текст ошибки."""
    try:
        run(
            "UPDATE reward_purchases SET status = 'issued', issued_at = now() WHERE id = %s AND status = 'pending'",
            (purchase_id,),
        )
        return None
    except psycopg2.Error as e:
        return short_error(e)


def cancel_purchase(purchase_id):
    """Отменить покупку (монеты возвращаются студенту). None или текст ошибки."""
    conn = _connect()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT p.id, p.student_id, p.reward_id, p.cost_coins, p.status, r.title
                   FROM reward_purchases p
                   JOIN rewards r ON r.id = p.reward_id
                   WHERE p.id = %s FOR UPDATE""",
                (purchase_id,),
            )
            p = cur.fetchone()
            if not p:
                return "Покупка не найдена"
            if p["status"] != "pending":
                return "Можно отменить только покупки в статусе ожидания"
            cur.execute(
                "UPDATE reward_purchases SET status = 'cancelled' WHERE id = %s",
                (purchase_id,),
            )
            cur.execute(
                """INSERT INTO xp_transactions(student_id, coin_amount, reason, source_id, comment)
                   VALUES (%s, %s, 'manual', %s, %s)""",
                (p["student_id"], p["cost_coins"], purchase_id, f"Возврат монет за награду: {p['title']}"),
            )
            cur.execute(
                "UPDATE rewards SET stock = stock + 1 WHERE id = %s AND stock IS NOT NULL",
                (p["reward_id"],),
            )
        return None
    except psycopg2.Error as e:
        return short_error(e)
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Администратор
# ---------------------------------------------------------------------
def get_all_users(search=None, role=None, group_id=None, is_active=None):
    sql = """SELECT u.id, u.login, u.last_name, u.first_name, u.middle_name, u.email,
                    r.code AS role, r.name AS role_name, u.group_id, g.name AS group_name,
                    u.is_active, u.created_at,
                    p.total_xp, p.coins, p.level_no, p.current_streak
             FROM users u
             JOIN roles r ON r.id = u.role_id
             LEFT JOIN student_groups g ON g.id = u.group_id
             LEFT JOIN student_profiles p ON p.user_id = u.id
             WHERE 1=1"""
    params = []
    if search:
        s = f"%{search.strip()}%"
        sql += """ AND (u.login ILIKE %s OR u.last_name ILIKE %s OR u.first_name ILIKE %s 
                   OR u.middle_name ILIKE %s OR u.email ILIKE %s OR g.name ILIKE %s)"""
        params.extend([s, s, s, s, s, s])
    if role and role != "all":
        sql += " AND r.code = %s"
        params.append(role)
    if group_id is not None and group_id != "all":
        sql += " AND u.group_id = %s"
        params.append(group_id)
    if is_active is not None and is_active != "all":
        sql += " AND u.is_active = %s"
        params.append(bool(is_active))
    sql += """ ORDER BY CASE r.code WHEN 'admin' THEN 0 WHEN 'teacher' THEN 1 ELSE 2 END,
                        u.last_name, u.first_name"""
    return fetch_all(sql, params if params else None)


def get_user_details(user_id):
    user = fetch_one(
        """SELECT u.id, u.login, u.last_name, u.first_name, u.middle_name, u.email,
                  r.code AS role, r.name AS role_name, u.group_id, g.name AS group_name,
                  u.is_active, u.created_at,
                  p.total_xp, p.coins, p.level_no, p.current_streak, p.best_streak,
                  l.title AS level_title
           FROM users u
           JOIN roles r ON r.id = u.role_id
           LEFT JOIN student_groups g ON g.id = u.group_id
           LEFT JOIN student_profiles p ON p.user_id = u.id
           LEFT JOIN levels l ON l.level_no = p.level_no
           WHERE u.id = %s""",
        (user_id,),
    )
    if not user:
        return None

    stats = dict(user)
    if user["role"] == "student":
        sub_stats = fetch_one(
            """SELECT COUNT(*) AS total_submissions,
                      COUNT(*) FILTER (WHERE status = 'graded') AS graded_count,
                      COUNT(*) FILTER (WHERE status = 'graded' AND score >= 100) AS perfect_count,
                      AVG(score) FILTER (WHERE status = 'graded') AS avg_score
               FROM submissions WHERE student_id = %s""",
            (user_id,),
        )
        ach_count = fetch_one(
            "SELECT COUNT(*) AS count FROM user_achievements WHERE student_id = %s",
            (user_id,),
        )["count"]
        purchases_count = fetch_one(
            "SELECT COUNT(*) AS count FROM reward_purchases WHERE student_id = %s",
            (user_id,),
        )["count"]
        stats.update({
            "total_submissions": sub_stats["total_submissions"] or 0,
            "graded_count": sub_stats["graded_count"] or 0,
            "perfect_count": sub_stats["perfect_count"] or 0,
            "avg_score": sub_stats["avg_score"],
            "achievements_count": ach_count,
            "purchases_count": purchases_count,
        })
    elif user["role"] == "teacher":
        tasks_count = fetch_one(
            "SELECT COUNT(*) AS count, COUNT(*) FILTER (WHERE is_active) AS active_count FROM tasks WHERE author_id = %s",
            (user_id,),
        )
        assign_count = fetch_one(
            "SELECT COUNT(DISTINCT group_id) AS groups_count, COUNT(DISTINCT discipline_id) AS disc_count FROM teaching_assignments WHERE teacher_id = %s",
            (user_id,),
        )
        checked_count = fetch_one(
            "SELECT COUNT(*) AS count FROM submissions WHERE checked_by = %s",
            (user_id,),
        )["count"]
        stats.update({
            "tasks_count": tasks_count["count"] or 0,
            "active_tasks_count": tasks_count["active_count"] or 0,
            "groups_count": assign_count["groups_count"] or 0,
            "disciplines_count": assign_count["disc_count"] or 0,
            "checked_submissions": checked_count,
        })
    return stats


def update_user(user_id, login, last_name, first_name, middle_name, email, role_code, group_id, is_active):
    """Обновляет данные пользователя. None при успехе или текст ошибки."""
    try:
        conn = _connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    """UPDATE users
                       SET login = %s,
                           last_name = %s,
                           first_name = %s,
                           middle_name = %s,
                           email = %s,
                           role_id = (SELECT id FROM roles WHERE code = %s),
                           group_id = %s,
                           is_active = %s
                       WHERE id = %s""",
                    (login, last_name, first_name, middle_name or None, email or None,
                     role_code, group_id if role_code == "student" else None, is_active, user_id),
                )
                if role_code == "student":
                    cur.execute(
                        "INSERT INTO student_profiles(user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                        (user_id,),
                    )
            return None
        finally:
            conn.close()
    except psycopg2.errors.UniqueViolation:
        return "Пользователь с таким логином или email уже существует"
    except psycopg2.Error as e:
        return short_error(e)


def delete_user(user_id):
    """Удаляет пользователя. None при успехе или текст ошибки."""
    try:
        tasks_count = fetch_one("SELECT COUNT(*) AS c FROM tasks WHERE author_id = %s", (user_id,))
        if tasks_count and tasks_count["c"] > 0:
            return "Нельзя удалить преподавателя, создавшего задания. Сначала удалите задания или деактивируйте аккаунт."
        assigns_count = fetch_one("SELECT COUNT(*) AS c FROM teaching_assignments WHERE teacher_id = %s", (user_id,))
        if assigns_count and assigns_count["c"] > 0:
            return "Нельзя удалить преподавателя с активными назначениями. Сначала удалите назначения."
        
        run("UPDATE submissions SET checked_by = NULL WHERE checked_by = %s", (user_id,))
        run("DELETE FROM users WHERE id = %s", (user_id,))
        return None
    except psycopg2.Error as e:
        return short_error(e)


def adjust_student_balance(student_id, xp_amount, coin_amount, comment="Корректировка администратором"):
    """Начисление или списание XP и монет студенту администратором."""
    try:
        if xp_amount == 0 and coin_amount == 0:
            return "Сумма изменения должна быть отлична от нуля"
        run(
            """INSERT INTO xp_transactions(student_id, xp_amount, coin_amount, reason, comment)
               VALUES (%s, %s, %s, 'manual', %s)""",
            (student_id, xp_amount, coin_amount, comment),
        )
        return None
    except psycopg2.Error as e:
        return short_error(e)


def get_admin_dashboard_stats():
    """Сводные статистические показатели для дашборда администратора."""
    user_counts = fetch_one(
        """SELECT COUNT(*) AS total_users,
                  COUNT(*) FILTER (WHERE r.code = 'student') AS students,
                  COUNT(*) FILTER (WHERE r.code = 'teacher') AS teachers,
                  COUNT(*) FILTER (WHERE r.code = 'admin') AS admins,
                  COUNT(*) FILTER (WHERE u.is_active) AS active_users,
                  COUNT(*) FILTER (WHERE NOT u.is_active) AS inactive_users
           FROM users u
           JOIN roles r ON r.id = u.role_id"""
    )
    academic_counts = fetch_one(
        """SELECT (SELECT COUNT(*) FROM student_groups) AS groups_count,
                  (SELECT COUNT(*) FROM disciplines) AS disciplines_count,
                  (SELECT COUNT(*) FROM teaching_assignments) AS assignments_count,
                  (SELECT COUNT(*) FROM specialties) AS specialties_count"""
    )
    activity_counts = fetch_one(
        """SELECT (SELECT COUNT(*) FROM tasks) AS tasks_total,
                  (SELECT COUNT(*) FROM tasks WHERE is_active) AS tasks_active,
                  (SELECT COUNT(*) FROM submissions) AS submissions_total,
                  (SELECT COUNT(*) FROM submissions WHERE status = 'submitted') AS submissions_pending,
                  (SELECT COUNT(*) FROM submissions WHERE status = 'graded') AS submissions_graded,
                  (SELECT COALESCE(SUM(xp_amount), 0) FROM xp_transactions WHERE xp_amount > 0) AS total_xp_awarded,
                  (SELECT COUNT(*) FROM reward_purchases) AS rewards_purchased,
                  (SELECT COUNT(*) FROM quests WHERE is_active) AS active_quests"""
    )
    recent_users = fetch_all(
        """SELECT u.id, u.login, u.last_name, u.first_name, u.email,
                  r.code AS role, g.name AS group_name, u.is_active, u.created_at
           FROM users u
           JOIN roles r ON r.id = u.role_id
           LEFT JOIN student_groups g ON g.id = u.group_id
           ORDER BY u.created_at DESC, u.id DESC
           LIMIT 6"""
    )
    return {
        "users": user_counts,
        "academic": academic_counts,
        "activity": activity_counts,
        "recent_users": recent_users,
    }


def get_specialties():
    return fetch_all("SELECT id, code, name, qualification FROM specialties ORDER BY code")


def get_groups_detailed():
    return fetch_all(
        """SELECT g.id, g.name, g.course, g.admission_year,
                  s.code AS spec_code, s.name AS spec_name,
                  u.last_name || ' ' || u.first_name AS curator,
                  COUNT(u2.id) AS students_count
           FROM student_groups g
           JOIN specialties s ON s.id = g.specialty_id
           LEFT JOIN users u ON u.id = g.curator_id
           LEFT JOIN users u2 ON u2.group_id = g.id AND u2.is_active
           GROUP BY g.id, g.name, g.course, g.admission_year, s.code, s.name, u.last_name, u.first_name
           ORDER BY g.name"""
    )


def create_group(name, specialty_id, course, admission_year, curator_id=None):
    try:
        run(
            """INSERT INTO student_groups(name, specialty_id, course, admission_year, curator_id)
               VALUES (%s, %s, %s, %s, %s)""",
            (name, specialty_id, course, admission_year, curator_id),
        )
        return None
    except psycopg2.errors.UniqueViolation:
        return "Группа с таким названием уже существует"
    except psycopg2.Error as e:
        return short_error(e)


def delete_group(group_id):
    try:
        cnt = fetch_one("SELECT COUNT(*) AS c FROM users WHERE group_id = %s", (group_id,))["c"]
        if cnt > 0:
            return f"Нельзя удалить группу: в ней состоит {cnt} студентов. Сначала переведите их в другую группу."
        run("DELETE FROM student_groups WHERE id = %s", (group_id,))
        return None
    except psycopg2.Error as e:
        return short_error(e)


def set_user_active(user_id, active):
    run("UPDATE users SET is_active = %s WHERE id = %s", (active, user_id))


def reset_password(user_id, new_password):
    run("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(new_password), user_id))


def get_teachers():
    return fetch_all(
        """SELECT u.id, u.last_name, u.first_name, u.middle_name
           FROM users u JOIN roles r ON r.id = u.role_id
           WHERE r.code = 'teacher' AND u.is_active
           ORDER BY u.last_name, u.first_name"""
    )


def get_assignments():
    return fetch_all(
        """SELECT ta.id, d.code, d.name AS discipline, g.name AS grp,
                  u.last_name || ' ' || u.first_name AS teacher,
                  ta.academic_year, ta.semester
           FROM teaching_assignments ta
           JOIN disciplines d ON d.id = ta.discipline_id
           JOIN student_groups g ON g.id = ta.group_id
           JOIN users u ON u.id = ta.teacher_id
           ORDER BY g.name, d.code, ta.academic_year, ta.semester"""
    )


def get_group_disciplines(group_id):
    """Дисциплины специальности группы (specialty_disciplines)."""
    return fetch_all(
        """SELECT d.id, d.code, d.name
           FROM student_groups g
           JOIN specialty_disciplines sd ON sd.specialty_id = g.specialty_id
           JOIN disciplines d ON d.id = sd.discipline_id
           WHERE g.id = %s ORDER BY d.code""",
        (group_id,),
    )


def add_assignment(discipline_id, group_id, teacher_id, academic_year, semester):
    """Назначить преподавателя на дисциплину у группы. None или текст ошибки."""
    try:
        ok = fetch_one(
            """SELECT EXISTS (SELECT 1 FROM student_groups g
                               JOIN specialty_disciplines sd ON sd.specialty_id = g.specialty_id
                              WHERE g.id = %s AND sd.discipline_id = %s) AS ok""",
            (group_id, discipline_id),
        )["ok"]
        if not ok:
            return "Эта дисциплина не входит в специальность выбранной группы"
        run(
            """INSERT INTO teaching_assignments(discipline_id, group_id, teacher_id,
                                                academic_year, semester)
               VALUES (%s, %s, %s, %s, %s)""",
            (discipline_id, group_id, teacher_id, academic_year, semester),
        )
        return None
    except psycopg2.errors.UniqueViolation:
        return "На эту дисциплину, группу и семестр преподаватель уже назначен"
    except psycopg2.Error as e:
        return short_error(e)


def delete_assignment(assignment_id):
    run("DELETE FROM teaching_assignments WHERE id = %s", (assignment_id,))
