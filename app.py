"""Геймификация обучения в СПО — приложение на customtkinter."""
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk
import psycopg2

from captcha import ImagePuzzleCaptcha
import db

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------
# Цвета (пары: светлая тема, тёмная тема)
# ---------------------------------------------------------------------
ACCENT = "#7c5cff"
ACCENT_HOVER = "#6a49f0"
GOLD = "#f5b942"
GREEN = "#2ecc71"
RED = "#e74c3c"
BLUE = "#3fa7ff"
WINDOW_BG = ("#eef0f6", "#1b1c22")
CARD = ("#ffffff", "#2a2b33")
CARD_INNER = ("#f2f3f8", "#33343e")
SIDEBAR = ("#ffffff", "#22232a")
MUTED = ("#6b6f7b", "#9a9eab")
TEXT = ("#1b1b1f", "#ececf1")

# ---------------------------------------------------------------------
# Подписи
# ---------------------------------------------------------------------
STATUS = {None: "Не сдано", "submitted": "Сдано", "on_review": "На проверке",
          "graded": "Оценено", "rejected": "Отклонено", "revision": "На доработку"}
TYPE = {"lab": "Лабораторная", "practice": "Практика", "test": "Тест",
        "homework": "Домашнее", "project": "Проект", "quiz": "Викторина"}
DIFF = {"easy": "Лёгкое", "medium": "Среднее", "hard": "Сложное", "expert": "Экспертное"}
COND = {"tasks_completed": "Выполнить заданий: {}", "total_xp": "Набрать XP: {}",
        "streak_days": "Серия дней: {}", "perfect_scores": "Работ на максимум: {}",
        "quests_completed": "Завершить квестов: {}", "manual": "Выдаётся преподавателем"}
ROLE = {"student": "Студент", "teacher": "Преподаватель", "admin": "Администратор"}
PURCHASE = {"pending": "Ждёт выдачи", "issued": "Выдано", "cancelled": "Отменено"}
QUEST_STATUS = {None: "Не начат", "in_progress": "В процессе", "completed": "Выполнен",
                "failed": "Провален"}


# ---------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------
def font(size=13, bold=False):
    return ctk.CTkFont(family="Segoe UI", size=size, weight="bold" if bold else "normal")


def fmt_dt(v):
    return v.strftime("%d.%m.%Y %H:%M") if v else "—"


def fmt_num(v):
    return "—" if v is None else f"{v:g}"


def cut(text, n):
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def db_safe(func, default):
    try:
        return func()
    except psycopg2.Error as e:
        messagebox.showerror("Ошибка БД", db.short_error(e))
        return default


def selected_id(tree):
    sel = tree.selection()
    return int(sel[0]) if sel else None


def button(parent, text, command, kind="primary", width=150, **kw):
    colors = {
        "primary": dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="white"),
        "danger": dict(fg_color=RED, hover_color="#c0392b", text_color="white"),
        "ghost": dict(fg_color=("#e3e5ee", "#383a45"), hover_color=("#d3d6e3", "#454857"),
                      text_color=TEXT),
    }[kind]
    return ctk.CTkButton(parent, text=text, command=command, width=width, height=36,
                         corner_radius=10, font=font(13, True), **colors, **kw)


def entry(parent, placeholder="", width=300, show=None):
    return ctk.CTkEntry(parent, width=width, height=36, corner_radius=10,
                        placeholder_text=placeholder, show=show)


def option_menu(parent, values, width=200, command=None):
    return ctk.CTkOptionMenu(parent, values=values, width=width, height=34, corner_radius=10,
                             fg_color=ACCENT, button_color=ACCENT_HOVER,
                             button_hover_color=ACCENT_HOVER, command=command)


def apply_tree_style():
    """Оформление таблиц ttk.Treeview под текущую тему."""
    dark = ctk.get_appearance_mode() == "Dark"
    bg = "#2a2b33" if dark else "#ffffff"
    fg = "#ececf1" if dark else "#1b1b1f"
    head = "#1e1f26" if dark else "#e3e5ee"
    st = ttk.Style()
    st.theme_use("clam")
    st.configure("App.Treeview", background=bg, fieldbackground=bg, foreground=fg,
                 rowheight=32, borderwidth=0, font=("Segoe UI", 10))
    st.map("App.Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])
    st.configure("App.Treeview.Heading", background=head, foreground=fg, relief="flat",
                 font=("Segoe UI", 10, "bold"), padding=(6, 6))
    st.map("App.Treeview.Heading", background=[("active", head)])


def make_table(parent, cols, height=12):
    """Таблица в карточке. cols = [(id, заголовок, ширина), ...]"""
    card = ctk.CTkFrame(parent, corner_radius=14, fg_color=CARD)
    tree = ttk.Treeview(card, columns=[c[0] for c in cols], show="headings", height=height,
                        selectmode="browse", style="App.Treeview")
    for cid, title, width in cols:
        tree.heading(cid, text=title, anchor="w")
        tree.column(cid, width=width, anchor="w")
    sb = ctk.CTkScrollbar(card, command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)
    sb.pack(side="right", fill="y", padx=(0, 12), pady=12)
    return card, tree


def stat_tile(parent, title, color):
    f = ctk.CTkFrame(parent, corner_radius=12, fg_color=CARD_INNER, width=120, height=84)
    f.pack_propagate(False)
    value = ctk.CTkLabel(f, text="—", font=font(24, True), text_color=color)
    value.pack(pady=(14, 0))
    ctk.CTkLabel(f, text=title, font=font(11), text_color=MUTED).pack()
    return f, value


def fill_list(frame, rows, empty="Пока пусто"):
    """rows = [(левый текст, правый текст, цвет правого текста), ...]"""
    for w in frame.winfo_children():
        w.destroy()
    if not rows:
        ctk.CTkLabel(frame, text=empty, text_color=MUTED, anchor="w").pack(fill="x", pady=4)
        return
    for left, right, color in rows:
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=right, text_color=color, font=font(12, True)).pack(side="right")
        ctk.CTkLabel(row, text=cut(left, 30), anchor="w").pack(side="left")


def make_dialog(owner, title, width, height):
    win = ctk.CTkToplevel(owner)
    win.title(title)
    win.geometry(f"{width}x{height}")
    win.resizable(False, False)
    win.transient(owner.winfo_toplevel())

    def _grab():
        try:
            win.grab_set()
            win.focus_force()
        except tk.TclError:
            pass

    win.after(200, _grab)
    return win


def set_text(box, text):
    box.configure(state="normal")
    box.delete("1.0", "end")
    box.insert("1.0", text)
    box.configure(state="disabled")


# ---------------------------------------------------------------------
# Окно приложения
# ---------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Геймификация обучения — СПО")
        self.geometry("1240x760")
        self.minsize(1080, 680)
        self.configure(fg_color=WINDOW_BG)
        apply_tree_style()
        self.user = None
        self.current = None
        self.show_login()

    def _switch(self, frame):
        if self.current is not None:
            self.current.destroy()
        self.current = frame
        frame.pack(fill="both", expand=True)

    def show_login(self):
        self.user = None
        self._switch(LoginFrame(self))

    def show_register(self):
        self._switch(RegisterFrame(self))

    def show_main(self, user):
        self.user = user
        shells = {"student": StudentShell, "teacher": TeacherShell, "admin": AdminShell}
        self._switch(shells[user["role"]](self))


# ---------------------------------------------------------------------
# Вход
# ---------------------------------------------------------------------
class LoginFrame(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self.captcha_passed = False

        card = ctk.CTkFrame(self, corner_radius=20, fg_color=CARD)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text="Геймификация обучения", font=font(26, True)).pack(padx=50, pady=(40, 2))
        ctk.CTkLabel(card, text="Учись, зарабатывай XP, расти в уровне",
                     text_color=MUTED).pack(pady=(0, 24))

        self.login = entry(card, "Логин")
        self.login.pack(pady=6)
        self.password = entry(card, "Пароль", show="•")
        self.password.pack(pady=6)

        self.captcha = ImagePuzzleCaptcha(card, on_success_callback=self.on_captcha_result)
        self.captcha.pack(pady=10)

        button(card, "Войти", self.do_login, width=300).pack(pady=(18, 8))
        button(card, "Создать аккаунт", app.show_register, kind="ghost", width=300).pack(pady=(0, 40))

        self.login.focus()
        self.login.bind("<Return>", lambda e: self.password.focus())
        self.password.bind("<Return>", lambda e: self.do_login())

    def on_captcha_result(self, result):
        self.captcha_passed = result

    def do_login(self):
        if not self.captcha_passed:
            messagebox.showwarning("Вход", "Пройдите капчу перед входом")
            return
        login, pw = self.login.get().strip(), self.password.get()
        if not login or not pw:
            messagebox.showwarning("Вход", "Введите логин и пароль")
            return
        try:
            user = db.authenticate(login, pw)
        except psycopg2.Error as e:
            messagebox.showerror("Ошибка БД", db.short_error(e))
            return
        if user is None:
            self.captcha_passed = False
            self.captcha.generate_captcha()
            messagebox.showerror("Вход", "Неверный логин или пароль")
            return
        if not user["is_active"]:
            messagebox.showerror("Вход", "Аккаунт отключён администратором")
            return
        self.app.show_main(user)


# ---------------------------------------------------------------------
# Регистрация
# ---------------------------------------------------------------------
class RegisterFrame(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        card = ctk.CTkFrame(self, corner_radius=20, fg_color=CARD)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text="Регистрация студента", font=font(24, True)).pack(padx=50, pady=(26, 4))
        ctk.CTkLabel(card, text="Аккаунты преподавателей создаёт администратор",
                     text_color=MUTED, font=font(12)).pack(pady=(0, 12))

        self.fields = {}
        for key, ph, secret in [("last_name", "Фамилия", False), ("first_name", "Имя", False),
                                ("middle_name", "Отчество (необязательно)", False),
                                ("email", "Email (необязательно)", False),
                                ("login", "Логин", False), ("password", "Пароль (от 6 символов)", True),
                                ("password2", "Повтор пароля", True)]:
            e = entry(card, ph, show="•" if secret else None)
            e.pack(pady=4)
            self.fields[key] = e

        self.groups = db_safe(db.get_groups, [])
        names = [g["name"] for g in self.groups] or ["Нет групп в БД"]
        self.group_menu = option_menu(card, names, width=300)
        self.group_menu.pack(pady=(10, 4))

        button(card, "Зарегистрироваться", self.do_register, width=300).pack(pady=(14, 6))
        button(card, "Назад ко входу", app.show_login, kind="ghost", width=300).pack(pady=(0, 26))

    def do_register(self):
        v = {k: e.get().strip() for k, e in self.fields.items()}
        v["password"], v["password2"] = self.fields["password"].get(), self.fields["password2"].get()
        if not (v["last_name"] and v["first_name"] and v["login"] and v["password"]):
            messagebox.showwarning("Регистрация", "Заполните фамилию, имя, логин и пароль")
            return
        if len(v["password"]) < 6:
            messagebox.showwarning("Регистрация", "Пароль должен быть не короче 6 символов")
            return
        if v["password"] != v["password2"]:
            messagebox.showwarning("Регистрация", "Пароли не совпадают")
            return
        by_name = {g["name"]: g["id"] for g in self.groups}
        group_id = by_name.get(self.group_menu.get())
        if group_id is None:
            messagebox.showwarning("Регистрация", "В БД нет групп. Выполните seed_demo.sql")
            return
        err = db.register_user(v["login"], v["password"], v["last_name"], v["first_name"],
                               v["middle_name"], v["email"], "student", group_id)
        if err:
            messagebox.showerror("Регистрация", err)
        else:
            messagebox.showinfo("Регистрация", "Аккаунт создан. Теперь можно войти.")
            self.app.show_login()


# ---------------------------------------------------------------------
# Каркас с боковым меню
# ---------------------------------------------------------------------
class Shell(ctk.CTkFrame):
    role_label = ""

    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self.user = app.user
        self.uid = self.user["id"]
        self.fio = f"{self.user['last_name']} {self.user['first_name']}"
        self.pages = {}
        self.nav_buttons = {}
        self.nav_labels = {}
        self.current_key = None

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=SIDEBAR)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        for key, label, page_cls in self.pages_def():
            self.pages[key] = page_cls(self.content, self)
            self.nav_labels[key] = label
            b = ctk.CTkButton(self.sidebar, text=label, anchor="w", height=36, corner_radius=10,
                              fg_color="transparent", hover_color=CARD_INNER, text_color=TEXT,
                              font=font(14), command=lambda k=key: self.show_page(k))
            b.pack(fill="x", padx=14, pady=2)
            self.nav_buttons[key] = b
        self.show_page(self.pages_def()[0][0])

    def pages_def(self):
        return []

    def _build_sidebar(self):
        # нижняя часть (пакуется первой, чтобы прижаться к низу)
        button(self.sidebar, "Выйти", self.app.show_login, kind="ghost", width=200
               ).pack(side="bottom", padx=20, pady=(8, 20))
        sw = ctk.CTkSwitch(self.sidebar, text="Тёмная тема", progress_color=ACCENT,
                           command=lambda: self._toggle_theme(sw))
        if ctk.get_appearance_mode() == "Dark":
            sw.select()
        sw.pack(side="bottom", padx=24, pady=8, anchor="w")

        # верхняя часть: профиль
        initials = (self.user["first_name"][:1] + self.user["last_name"][:1]).upper()
        ctk.CTkLabel(self.sidebar, text=initials, width=60, height=60, corner_radius=30,
                     fg_color=ACCENT, text_color="white", font=font(20, True)
                     ).pack(pady=(20, 8))
        ctk.CTkLabel(self.sidebar, text=self.fio, font=font(15, True)).pack()
        sub = self.role_label
        if self.user.get("group_name"):
            sub += f" · {self.user['group_name']}"
        ctk.CTkLabel(self.sidebar, text=sub, text_color=MUTED, font=font(12)).pack(pady=(0, 14))

    def _toggle_theme(self, sw):
        ctk.set_appearance_mode("dark" if sw.get() else "light")
        apply_tree_style()

    def show_page(self, key):
        if self.current_key:
            self.pages[self.current_key].pack_forget()
            self.nav_buttons[self.current_key].configure(fg_color="transparent", text_color=TEXT)
        self.current_key = key
        page = self.pages[key]
        page.pack(fill="both", expand=True, padx=28, pady=22)
        self.nav_buttons[key].configure(fg_color=ACCENT, text_color="white")
        page.refresh()
        self.refresh_badge()

    def refresh_current(self):
        if self.current_key:
            self.pages[self.current_key].refresh()
        self.refresh_badge()

    def set_badge(self, key, n):
        text = self.nav_labels[key] + (f"   ({n})" if n else "")
        self.nav_buttons[key].configure(text=text)

    def refresh_badge(self):
        pass


class Page(ctk.CTkFrame):
    title = ""

    def __init__(self, parent, shell):
        super().__init__(parent, fg_color="transparent")
        self.shell = shell
        self.uid = shell.uid
        ctk.CTkLabel(self, text=self.get_title(), font=font(26, True), anchor="w"
                     ).pack(fill="x", pady=(0, 16))
        self.build()

    def get_title(self):
        return self.title

    def build(self):
        pass

    def refresh(self):
        pass


# ---------------------------------------------------------------------
# Рейтинг (общая страница)
# ---------------------------------------------------------------------
class RatingPage(Page):
    title = "Рейтинг"
    ALL_GROUPS = "Все студенты"
    ALL_DISC = "Все дисциплины (общий рейтинг)"

    def build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(top, text="Группа:", text_color=MUTED).pack(side="left", padx=(0, 8))
        groups = [g["name"] for g in db_safe(db.get_groups, [])]
        self.menu = option_menu(top, [self.ALL_GROUPS] + groups, width=190,
                                command=lambda _: self.refresh())
        default = self.shell.user.get("group_name")
        self.menu.set(default if default in groups else self.ALL_GROUPS)
        self.menu.pack(side="left")

        ctk.CTkLabel(top, text="Дисциплина:", text_color=MUTED).pack(side="left", padx=(20, 8))
        self.discs = db_safe(db.get_disciplines, [])
        self.disc_menu = option_menu(top, [self.ALL_DISC] + [d["name"] for d in self.discs],
                                     width=330, command=lambda _: self.refresh())
        self.disc_menu.set(self.ALL_DISC)
        self.disc_menu.pack(side="left")

        card, self.tree = make_table(self, [("place", "Место", 70), ("name", "Студент", 300),
                                            ("group", "Группа", 120), ("xp", "XP", 130),
                                            ("lvl", "Уровень", 100)], height=16)
        card.pack(fill="both", expand=True)
        self.tree.tag_configure("top", foreground=GOLD)
        self.tree.tag_configure("me", foreground=ACCENT)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        g = self.menu.get()
        group = None if g == self.ALL_GROUPS else g
        d = self.disc_menu.get()
        if d == self.ALL_DISC:
            rows = db_safe(lambda: db.get_rating(group), [])
            xp_title, extra_title, extra_key = "XP", "Уровень", "level_no"
        else:
            disc_id = {x["name"]: x["id"] for x in self.discs}[d]
            rows = db_safe(lambda: db.get_discipline_rating(disc_id, group), [])
            xp_title, extra_title, extra_key = "XP по дисциплине", "Заданий", "tasks_done"
        self.tree.heading("xp", text=xp_title)
        self.tree.heading("lvl", text=extra_title)
        for i, r in enumerate(rows):
            me = r["student_name"] == self.shell.fio
            tags = ("me",) if me else (("top",) if r["place"] <= 3 else ())
            self.tree.insert("", "end", iid=str(i), tags=tags, values=(
                r["place"], r["student_name"] + ("  (вы)" if me else ""),
                r["group_name"] or "—", r["total_xp"], r[extra_key]))


# =====================================================================
# СТУДЕНТ
# =====================================================================
class StudentDashboard(Page):
    def get_title(self):
        return f"Привет, {self.shell.user['first_name']}!"

    def build(self):
        top = ctk.CTkFrame(self, corner_radius=14, fg_color=CARD)
        top.pack(fill="x")
        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=24, pady=20)
        self.lbl_level = ctk.CTkLabel(left, text="", font=font(22, True), anchor="w")
        self.lbl_level.pack(fill="x")
        self.bar = ctk.CTkProgressBar(left, height=16, corner_radius=8, progress_color=ACCENT)
        self.bar.set(0)
        self.bar.pack(fill="x", pady=12)
        self.lbl_xp = ctk.CTkLabel(left, text="", text_color=MUTED, anchor="w")
        self.lbl_xp.pack(fill="x")

        tiles = ctk.CTkFrame(top, fg_color="transparent")
        tiles.pack(side="right", padx=16, pady=16)
        self.tiles = {}
        for i, (key, title, color) in enumerate([("xp", "Всего XP", ACCENT), ("coins", "Монеты", GOLD),
                                                 ("streak", "Серия, дн.", GREEN),
                                                 ("ach", "Достижения", BLUE)]):
            f, v = stat_tile(tiles, title, color)
            f.grid(row=0, column=i, padx=5)
            self.tiles[key] = v

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, pady=(16, 0))
        row.grid_rowconfigure(0, weight=1)
        for c in range(3):
            row.grid_columnconfigure(c, weight=1, uniform="col")
        self.lists = {}
        for c, (key, title) in enumerate([("tasks", "Ближайшие задания"),
                                          ("xp", "Последние начисления"),
                                          ("top", "Топ группы")]):
            card = ctk.CTkFrame(row, corner_radius=14, fg_color=CARD)
            card.grid(row=0, column=c, sticky="nsew",
                      padx=(0 if c == 0 else 8, 0 if c == 2 else 8))
            ctk.CTkLabel(card, text=title, font=font(16, True), anchor="w"
                         ).pack(fill="x", padx=18, pady=(16, 6))
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=18, pady=(0, 14))
            self.lists[key] = body

    def refresh(self):
        p = db_safe(lambda: db.get_profile(self.uid), None)
        if p:
            self.lbl_level.configure(text=f"Уровень {p['level_no']} · {p['level_title']}")
            if p["next_xp"] is None:
                self.bar.set(1)
                self.lbl_xp.configure(text=f"{p['total_xp']} XP — максимальный уровень")
            else:
                span = p["next_xp"] - p["level_start"]
                self.bar.set(max(0, min(1, (p["total_xp"] - p["level_start"]) / span)))
                self.lbl_xp.configure(
                    text=f"{p['total_xp']} / {p['next_xp']} XP до следующего уровня")
            self.tiles["xp"].configure(text=str(p["total_xp"]))
            self.tiles["coins"].configure(text=str(p["coins"]))
            self.tiles["streak"].configure(text=str(p["current_streak"]))

        ach = db_safe(lambda: db.get_achievements(self.uid), [])
        got = sum(1 for a in ach if a["awarded_at"])
        self.tiles["ach"].configure(text=f"{got}/{len(ach)}")

        tasks = db_safe(lambda: db.get_student_tasks(self.uid), [])
        rows = []
        for t in [t for t in tasks if t["status"] in (None, "revision")][:6]:
            dl = t["deadline"]
            overdue = bool(dl and dl < datetime.now(dl.tzinfo))
            right = (f"до {dl:%d.%m} · " if dl else "") + f"+{t['xp_reward']} XP"
            rows.append((t["title"], right, RED if overdue else MUTED))
        fill_list(self.lists["tasks"], rows, "Все задания выполнены")

        hist = db_safe(lambda: db.get_xp_history(self.uid), [])[:6]
        rows = []
        for h in hist:
            if h["xp_amount"]:
                rows.append((h["comment"], f"{h['xp_amount']:+d} XP", GREEN if h["xp_amount"] > 0 else RED))
            else:
                rows.append((h["comment"], f"{h['coin_amount']:+d} мон.", GOLD))
        fill_list(self.lists["xp"], rows, "Начислений пока нет")

        g = self.shell.user.get("group_name")
        top = db_safe(lambda: db.get_rating(g), [])[:6]
        rows = [(f"{r['place']}. {r['student_name']}", f"{r['total_xp']} XP",
                 ACCENT if r["student_name"] == self.shell.fio else TEXT) for r in top]
        fill_list(self.lists["top"], rows, "Рейтинг пуст")


class StudentTasksPage(Page):
    title = "Задания"

    def build(self):
        self.tasks = {}
        card, self.tree = make_table(self, [
            ("disc", "Дисциплина", 180), ("title", "Задание", 240), ("type", "Тип", 110),
            ("diff", "Сложность", 100), ("xp", "XP", 55), ("deadline", "Дедлайн", 130),
            ("status", "Статус", 120), ("score", "Балл", 80)], height=10)
        card.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._show_info)

        self.info = ctk.CTkTextbox(self, height=100, corner_radius=12, fg_color=CARD,
                                   wrap="word", state="disabled")
        self.info.pack(fill="x", pady=12)
        button(self, "Сдать работу", self.submit_dialog).pack(anchor="e")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.tasks = {}
        for t in db_safe(lambda: db.get_student_tasks(self.uid), []):
            self.tasks[t["id"]] = t
            score = (f"{fmt_num(t['score'])}/{fmt_num(t['max_score'])}"
                     if t["score"] is not None else "—")
            self.tree.insert("", "end", iid=str(t["id"]), values=(
                t["discipline"], t["title"], TYPE.get(t["type"], t["type"]),
                DIFF.get(t["difficulty"], t["difficulty"]), t["xp_reward"],
                fmt_dt(t["deadline"]), STATUS.get(t["status"], t["status"]), score))
        set_text(self.info, "Выберите задание, чтобы увидеть описание.")

    def _show_info(self, _=None):
        t = self.tasks.get(selected_id(self.tree))
        if not t:
            return
        text = t["description"] or "Описание не указано."
        if t["teacher_comment"]:
            text += f"\n\nКомментарий преподавателя: {t['teacher_comment']}"
        set_text(self.info, text)

    def submit_dialog(self):
        tid = selected_id(self.tree)
        if tid is None:
            messagebox.showinfo("Сдача работы", "Выберите задание в списке")
            return
        t = self.tasks[tid]
        if t["status"] in ("submitted", "on_review"):
            messagebox.showinfo("Сдача работы", "Работа уже отправлена и ждёт проверки")
            return
        if t["status"] == "graded":
            messagebox.showinfo("Сдача работы", "Задание уже оценено")
            return

        win = make_dialog(self, "Сдача работы", 600, 460)
        ctk.CTkLabel(win, text=t["title"], font=font(18, True), anchor="w"
                     ).pack(fill="x", padx=24, pady=(22, 2))
        ctk.CTkLabel(win, text=f"{t['discipline']} · награда {t['xp_reward']} XP",
                     text_color=MUTED, anchor="w").pack(fill="x", padx=24)
        ctk.CTkLabel(win, text="Ответ, ссылка на работу или комментарий:", anchor="w"
                     ).pack(fill="x", padx=24, pady=(16, 4))
        txt = ctk.CTkTextbox(win, height=200, corner_radius=10, wrap="word")
        txt.pack(fill="x", padx=24)

        def send():
            answer = txt.get("1.0", "end").strip()
            if not answer:
                messagebox.showwarning("Сдача работы", "Введите ответ", parent=win)
                return
            try:
                db.submit_work(tid, self.uid, answer)
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка БД", db.short_error(e), parent=win)
                return
            win.destroy()
            messagebox.showinfo("Сдача работы", "Работа отправлена преподавателю")
            self.shell.refresh_current()

        button(win, "Отправить", send).pack(pady=20)


class AchievementsPage(Page):
    title = "Достижения"

    def build(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)
        for c in range(3):
            self.scroll.grid_columnconfigure(c, weight=1, uniform="a")

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        for i, a in enumerate(db_safe(lambda: db.get_achievements(self.uid), [])):
            got = a["awarded_at"] is not None
            card = ctk.CTkFrame(self.scroll, corner_radius=14, fg_color=CARD)
            card.grid(row=i // 3, column=i % 3, padx=6, pady=6, sticky="nsew")
            ctk.CTkLabel(card, text="★" if got else "☆", font=font(34, True),
                         text_color=GOLD if got else MUTED).pack(pady=(16, 0))
            ctk.CTkLabel(card, text=a["title"], font=font(15, True),
                         text_color=TEXT if got else MUTED).pack(padx=14)
            ctk.CTkLabel(card, text=a["description"] or "", text_color=MUTED, wraplength=230,
                         justify="center").pack(padx=14, pady=(2, 6))
            ctk.CTkLabel(card, text=COND.get(a["condition_type"], "").format(a["condition_value"]),
                         font=font(11), text_color=MUTED).pack()
            ctk.CTkLabel(card, text=f"Награда: +{a['xp_bonus']} XP", font=font(12, True),
                         text_color=ACCENT).pack(pady=(4, 0))
            ctk.CTkLabel(card, text=f"Получено {fmt_dt(a['awarded_at'])}" if got else "Не получено",
                         font=font(11), text_color=GREEN if got else MUTED).pack(pady=(2, 16))


class ShopPage(Page):
    title = "Магазин наград"

    def build(self):
        self.lbl_coins = ctk.CTkLabel(self, text="", font=font(15, True), text_color=GOLD, anchor="w")
        self.lbl_coins.pack(fill="x", pady=(0, 10))

        # «Мои покупки» прижаты к низу страницы (пакуются до списка наград)
        card, self.buys = make_table(self, [("date", "Дата", 150), ("title", "Награда", 340),
                                            ("cost", "Цена", 90), ("status", "Статус", 150)],
                                     height=4)
        card.pack(side="bottom", fill="x")
        ctk.CTkLabel(self, text="Мои покупки", font=font(15, True), anchor="w"
                     ).pack(side="bottom", fill="x", pady=(12, 4))
        self.buys.tag_configure("pending", foreground=GOLD)
        self.buys.tag_configure("issued", foreground=GREEN)
        self.buys.tag_configure("cancelled", foreground="#6b6f7b")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def refresh(self):
        p = db_safe(lambda: db.get_profile(self.uid), None)
        coins = p["coins"] if p else 0
        self.lbl_coins.configure(text=f"Ваш баланс: {coins} монет")
        self.buys.delete(*self.buys.get_children())
        for p_ in db_safe(lambda: db.get_student_purchases(self.uid), []):
            self.buys.insert("", "end", iid=str(p_["id"]), tags=(p_["status"],), values=(
                fmt_dt(p_["purchased_at"]), p_["title"], p_["cost_coins"],
                PURCHASE.get(p_["status"], p_["status"])
                + (f" ({p_['issued_at']:%d.%m})" if p_["issued_at"] else "")))
        for w in self.scroll.winfo_children():
            w.destroy()
        for r in db_safe(db.get_rewards, []):
            card = ctk.CTkFrame(self.scroll, corner_radius=14, fg_color=CARD)
            card.pack(fill="x", pady=6)
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=20, pady=16)
            ctk.CTkLabel(left, text=r["title"], font=font(16, True), anchor="w").pack(fill="x")
            ctk.CTkLabel(left, text=r["description"] or "", text_color=MUTED, anchor="w"
                         ).pack(fill="x")
            stock = "без ограничений" if r["stock"] is None else f"осталось {r['stock']}"
            ctk.CTkLabel(left, text=stock, font=font(11), text_color=MUTED, anchor="w").pack(fill="x")
            right = ctk.CTkFrame(card, fg_color="transparent")
            right.pack(side="right", padx=20)
            ctk.CTkLabel(right, text=f"{r['cost_coins']} монет", font=font(16, True),
                         text_color=GOLD).pack(pady=(0, 6))
            b = button(right, "Купить", lambda rid=r["id"], cost=r["cost_coins"]: self.buy(rid, cost), width=120)
            if coins < r["cost_coins"]:
                b.configure(state="disabled")
            b.pack()

    def buy(self, reward_id, cost_coins):
        p = db_safe(lambda: db.get_profile(self.uid), None)
        coins = p["coins"] if p else 0
        if coins < cost_coins:
            messagebox.showerror("Ошибка", "Недостаточно монет для покупки!")
            return
        if not messagebox.askyesno("Магазин", "Купить выбранную награду?"):
            return
        err = db.buy_reward(self.uid, reward_id, cost_coins)
        if err:
            messagebox.showerror("Магазин", err)
        else:
            messagebox.showinfo("Магазин", "Покупка оформлена! Преподаватель выдаст награду.")
        self.shell.refresh_current()


class HistoryPage(Page):
    title = "История XP"

    def build(self):
        card, self.tree = make_table(self, [("date", "Дата", 150), ("xp", "XP", 80),
                                            ("coins", "Монеты", 80), ("comment", "Описание", 600)],
                                     height=16)
        card.pack(fill="both", expand=True)
        self.tree.tag_configure("plus", foreground=GREEN)
        self.tree.tag_configure("minus", foreground=RED)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, h in enumerate(db_safe(lambda: db.get_xp_history(self.uid), [])):
            neg = h["xp_amount"] < 0 or h["coin_amount"] < 0
            self.tree.insert("", "end", iid=str(i), tags=("minus" if neg else "plus",), values=(
                fmt_dt(h["created_at"]), f"{h['xp_amount']:+d}", f"{h['coin_amount']:+d}",
                h["comment"] or ""))


class NotificationsPage(Page):
    title = "Уведомления"

    def build(self):
        card, self.tree = make_table(self, [("new", "", 70), ("date", "Дата", 150),
                                            ("title", "Заголовок", 220), ("body", "Текст", 520)],
                                     height=14)
        card.pack(fill="both", expand=True)
        self.tree.tag_configure("new", foreground=ACCENT)
        button(self, "Отметить все прочитанными", self.read_all, kind="ghost", width=240
               ).pack(anchor="e", pady=(12, 0))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for n in db_safe(lambda: db.get_notifications(self.uid), []):
            self.tree.insert("", "end", iid=str(n["id"]), tags=() if n["is_read"] else ("new",),
                             values=("" if n["is_read"] else "новое", fmt_dt(n["created_at"]),
                                     n["title"], n["body"] or ""))

    def read_all(self):
        db_safe(lambda: db.mark_notifications_read(self.uid), None)
        self.refresh()
        self.shell.refresh_badge()


class StudentProgressPage(Page):
    title = "Успеваемость"

    def build(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    @staticmethod
    def _grade_color(avg):
        if avg is None:
            return MUTED
        return GREEN if avg >= 85 else (GOLD if avg >= 60 else RED)

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        rows = db_safe(lambda: db.get_student_progress(self.uid), [])
        if not rows:
            ctk.CTkLabel(self.scroll, text="Пока нет заданий по вашим дисциплинам",
                         text_color=MUTED).pack(pady=20)
            return
        for r in rows:
            card = ctk.CTkFrame(self.scroll, corner_radius=14, fg_color=CARD)
            card.pack(fill="x", pady=6)
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=20, pady=16)
            ctk.CTkLabel(left, text=r["name"], font=font(16, True), anchor="w").pack(fill="x")
            ctk.CTkLabel(left, text=r["code"], text_color=MUTED, font=font(11),
                         anchor="w").pack(fill="x")
            total, done = r["tasks_total"] or 0, r["tasks_graded"] or 0
            bar = ctk.CTkProgressBar(left, height=12, corner_radius=6, progress_color=ACCENT)
            bar.set(min(1, done / total) if total else 0)
            bar.pack(fill="x", pady=(10, 4))
            ctk.CTkLabel(left, text=f"Выполнено заданий: {done} из {total}",
                         text_color=MUTED, anchor="w").pack(fill="x")

            right = ctk.CTkFrame(card, fg_color="transparent")
            right.pack(side="right", padx=26)
            avg = r["avg_percent"]
            ctk.CTkLabel(right, text="—" if avg is None else f"{avg:g}%", font=font(26, True),
                         text_color=self._grade_color(avg)).pack()
            ctk.CTkLabel(right, text="средний балл", font=font(11), text_color=MUTED).pack()
            place = f"{r['place']} из {r['participants']}" if r["place"] else "—"
            ctk.CTkLabel(right, text=f"Место в дисциплине: {place}", font=font(12, True),
                         text_color=GOLD).pack(pady=(6, 0))


class StudentQuestsPage(Page):
    title = "Квесты"

    def build(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        rows = db_safe(lambda: db.get_student_quests(self.uid), [])
        if not rows:
            ctk.CTkLabel(self.scroll, text="Квестов пока нет", text_color=MUTED).pack(pady=20)
            return
        colors = {"completed": GREEN, "failed": RED, "in_progress": ACCENT, None: MUTED}
        for q in rows:
            status = q["status"]
            ends = q["ends_at"]
            if status != "completed" and ends and ends < datetime.now(ends.tzinfo):
                status = "failed"
            elif status is None and q["done"] > 0:
                status = "in_progress"

            card = ctk.CTkFrame(self.scroll, corner_radius=14, fg_color=CARD)
            card.pack(fill="x", pady=6)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=20, pady=(16, 0))
            ctk.CTkLabel(head, text=QUEST_STATUS[status], font=font(12, True),
                         text_color=colors[status]).pack(side="right")
            ctk.CTkLabel(head, text=q["title"], font=font(16, True), anchor="w"
                         ).pack(side="left")
            if q["description"]:
                ctk.CTkLabel(card, text=q["description"], text_color=MUTED, anchor="w",
                             justify="left", wraplength=760).pack(fill="x", padx=20, pady=(2, 0))
            bar = ctk.CTkProgressBar(card, height=12, corner_radius=6,
                                     progress_color=colors[status])
            bar.set(q["done"] / q["total"] if q["total"] else 0)
            bar.pack(fill="x", padx=20, pady=(10, 4))
            info = [f"Выполнено заданий: {q['done']} из {q['total']}",
                    f"Награда: +{q['xp_reward']} XP, +{q['coin_reward']} монет",
                    f"до {ends:%d.%m.%Y}" if ends else "без срока"]
            if q["discipline"]:
                info.insert(0, q["discipline"])
            ctk.CTkLabel(card, text="  ·  ".join(info), text_color=MUTED, font=font(12),
                         anchor="w").pack(fill="x", padx=20, pady=(0, 16))


class StudentShell(Shell):
    role_label = "Студент"

    def pages_def(self):
        return [("home", "Главная", StudentDashboard), ("tasks", "Задания", StudentTasksPage),
                ("quests", "Квесты", StudentQuestsPage),
                ("progress", "Успеваемость", StudentProgressPage),
                ("rating", "Рейтинг", RatingPage), ("ach", "Достижения", AchievementsPage),
                ("shop", "Магазин", ShopPage), ("history", "История XP", HistoryPage),
                ("notif", "Уведомления", NotificationsPage)]

    def refresh_badge(self):
        rows = db_safe(lambda: db.get_notifications(self.uid), [])
        self.set_badge("notif", sum(1 for n in rows if not n["is_read"]))


# =====================================================================
# ПРЕПОДАВАТЕЛЬ
# =====================================================================
class TeacherDashboard(Page):
    def get_title(self):
        return f"Здравствуйте, {self.shell.user['first_name']}!"

    def build(self):
        tiles = ctk.CTkFrame(self, fg_color="transparent")
        tiles.pack(fill="x")
        self.tiles = {}
        for i, (key, title, color) in enumerate([("pending", "На проверку", RED),
                                                 ("rewards", "Наград к выдаче", GOLD),
                                                 ("tasks", "Моих заданий", ACCENT),
                                                 ("active", "Активных", GREEN)]):
            f, v = stat_tile(tiles, title, color)
            f.configure(width=190, height=100)
            f.grid(row=0, column=i, padx=(0, 12))
            self.tiles[key] = v

        card = ctk.CTkFrame(self, corner_radius=14, fg_color=CARD)
        card.pack(fill="both", expand=True, pady=(16, 0))
        ctk.CTkLabel(card, text="Ждут проверки", font=font(16, True), anchor="w"
                     ).pack(fill="x", padx=20, pady=(16, 6))
        self.body = ctk.CTkFrame(card, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(0, 14))

    def refresh(self):
        pending = db_safe(lambda: db.get_pending_submissions(self.uid), [])
        tasks = db_safe(lambda: db.get_teacher_tasks(self.uid), [])
        self.tiles["pending"].configure(text=str(len(pending)))
        self.tiles["tasks"].configure(text=str(len(tasks)))
        self.tiles["active"].configure(text=str(sum(1 for t in tasks if t["is_active"])))
        self.tiles["rewards"].configure(text=str(len(db_safe(db.get_pending_purchases, []))))
        fill_list(self.body, [(f"{s['student']} — {s['title']}", fmt_dt(s["submitted_at"]), MUTED)
                              for s in pending[:8]], "Все работы проверены")


class TeacherReviewPage(Page):
    title = "Работы на проверку"

    def build(self):
        self.pending = {}
        card, self.tree = make_table(self, [
            ("student", "Студент", 190), ("grp", "Группа", 90), ("task", "Задание", 250),
            ("disc", "Дисциплина", 180), ("att", "Попытка", 80), ("date", "Сдано", 140)], height=15)
        card.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.review_dialog())
        button(self, "Проверить выбранную работу", self.review_dialog, width=240
               ).pack(anchor="e", pady=(12, 0))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.pending = {}
        for s in db_safe(lambda: db.get_pending_submissions(self.uid), []):
            self.pending[s["id"]] = s
            self.tree.insert("", "end", iid=str(s["id"]), values=(
                s["student"], s["grp"] or "—", s["title"], s["discipline"],
                s["attempt_no"], fmt_dt(s["submitted_at"])))

    def review_dialog(self):
        sid = selected_id(self.tree)
        if sid is None:
            messagebox.showinfo("Проверка", "Выберите работу в списке")
            return
        s = self.pending[sid]
        win = make_dialog(self, "Проверка работы", 660, 680)
        ctk.CTkLabel(win, text=f"{s['student']} ({s['grp'] or '—'})", font=font(18, True),
                     anchor="w").pack(fill="x", padx=24, pady=(22, 0))
        ctk.CTkLabel(win, text=f"{s['discipline']} · {s['title']} · попытка {s['attempt_no']}",
                     text_color=MUTED, anchor="w").pack(fill="x", padx=24)
        ctk.CTkLabel(win, text="Ответ студента", font=font(13, True), anchor="w"
                     ).pack(fill="x", padx=24, pady=(14, 4))
        ans = ctk.CTkTextbox(win, height=170, corner_radius=10, wrap="word")
        ans.insert("1.0", s["answer_text"] or "")
        ans.configure(state="disabled")
        ans.pack(fill="x", padx=24)

        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=14)
        ctk.CTkLabel(row, text=f"Балл (макс. {fmt_num(s['max_score'])}):").pack(side="left")
        score = entry(row, width=110)
        score.pack(side="left", padx=10)

        ctk.CTkLabel(win, text="Комментарий", anchor="w").pack(fill="x", padx=24)
        comment = ctk.CTkTextbox(win, height=110, corner_radius=10, wrap="word")
        comment.pack(fill="x", padx=24, pady=(4, 0))

        def grade():
            try:
                val = float(score.get().replace(",", "."))
            except ValueError:
                messagebox.showwarning("Проверка", "Введите балл числом", parent=win)
                return
            if val < 0 or val > float(s["max_score"]):
                messagebox.showwarning("Проверка",
                                       f"Балл должен быть от 0 до {fmt_num(s['max_score'])}", parent=win)
                return
            try:
                db.grade_submission(sid, s["student_id"], val,
                                    comment.get("1.0", "end").strip(), self.uid)
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка БД", db.short_error(e), parent=win)
                return
            win.destroy()
            self.shell.refresh_current()

        def revision():
            text = comment.get("1.0", "end").strip()
            if not text:
                messagebox.showwarning("Проверка", "Напишите, что нужно исправить", parent=win)
                return
            try:
                db.send_to_revision(sid, text, self.uid)
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка БД", db.short_error(e), parent=win)
                return
            win.destroy()
            self.shell.refresh_current()

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(pady=18)
        button(btns, "Выставить оценку", grade, width=190).pack(side="left", padx=6)
        button(btns, "На доработку", revision, kind="ghost", width=170).pack(side="left", padx=6)


class TeacherTasksPage(Page):
    title = "Мои задания"

    def build(self):
        card, self.tree = make_table(self, [
            ("disc", "Дисциплина", 190), ("title", "Задание", 260), ("type", "Тип", 110),
            ("diff", "Сложность", 100), ("max", "Макс.", 60), ("xp", "XP", 55),
            ("deadline", "Дедлайн", 110), ("active", "Активно", 80)], height=15)
        card.pack(fill="both", expand=True)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(anchor="e", pady=(12, 0))
        button(btns, "Создать задание", self.create_dialog, width=180).pack(side="left", padx=5)
        button(btns, "Вкл / выкл", self.toggle, kind="ghost", width=130).pack(side="left", padx=5)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for t in db_safe(lambda: db.get_teacher_tasks(self.uid), []):
            self.tree.insert("", "end", iid=str(t["id"]), values=(
                t["discipline"], t["title"], TYPE.get(t["type"], t["type"]),
                DIFF.get(t["difficulty"], t["difficulty"]), fmt_num(t["max_score"]),
                t["xp_reward"], t["deadline"].strftime("%d.%m.%Y") if t["deadline"] else "—",
                "да" if t["is_active"] else "нет"))

    def toggle(self):
        tid = selected_id(self.tree)
        if tid is None:
            messagebox.showinfo("Задание", "Выберите задание в списке")
            return
        db_safe(lambda: db.toggle_task(tid), None)
        self.refresh()

    def create_dialog(self):
        discs = db_safe(lambda: db.get_teacher_disciplines(self.uid), [])
        if not discs:
            messagebox.showwarning(
                "Задание", "Администратор ещё не назначил вам дисциплины.\n"
                           "Задания можно создавать только по назначенным дисциплинам.")
            return
        win = make_dialog(self, "Новое задание", 600, 740)
        pad = dict(padx=24, pady=(10, 0))

        ctk.CTkLabel(win, text="Дисциплина", anchor="w").pack(fill="x", **pad)
        disc_names = [f"{d['code']} {d['name']}" for d in discs]
        disc = option_menu(win, disc_names, width=550)
        disc.pack(anchor="w", padx=24, pady=(4, 0))

        no_topic = "— без темы —"
        topics = {}
        ctk.CTkLabel(win, text="Тема (необязательно)", anchor="w").pack(fill="x", **pad)
        topic = option_menu(win, [no_topic], width=550)
        topic.pack(anchor="w", padx=24, pady=(4, 0))

        def load_topics(_=None):
            d = discs[disc_names.index(disc.get())]
            topics.clear()
            topics.update({t["title"]: t["id"] for t in db_safe(lambda: db.get_topics(d["id"]), [])})
            topic.configure(values=[no_topic] + list(topics))
            topic.set(no_topic)

        disc.configure(command=load_topics)
        load_topics()

        ctk.CTkLabel(win, text="Название", anchor="w").pack(fill="x", **pad)
        title = entry(win, width=550)
        title.pack(anchor="w", padx=24, pady=(4, 0))

        ctk.CTkLabel(win, text="Описание", anchor="w").pack(fill="x", **pad)
        desc = ctk.CTkTextbox(win, height=80, corner_radius=10, wrap="word")
        desc.pack(fill="x", padx=24, pady=(4, 0))

        type_keys, diff_keys = list(TYPE), list(DIFF)
        grid = ctk.CTkFrame(win, fg_color="transparent")
        grid.pack(fill="x", padx=24, pady=(14, 0))
        ctk.CTkLabel(grid, text="Тип").grid(row=0, column=0, sticky="w")
        ctype = option_menu(grid, [TYPE[k] for k in type_keys], width=240)
        ctype.set(TYPE["practice"])
        ctype.grid(row=1, column=0, sticky="w", padx=(0, 20), pady=(2, 10))
        ctk.CTkLabel(grid, text="Сложность").grid(row=0, column=1, sticky="w")
        cdiff = option_menu(grid, [DIFF[k] for k in diff_keys], width=240)
        cdiff.set(DIFF["medium"])
        cdiff.grid(row=1, column=1, sticky="w", pady=(2, 10))

        def field(label, default, row, col, width=240):
            ctk.CTkLabel(grid, text=label).grid(row=row, column=col, sticky="w")
            e = entry(grid, width=width)
            if default:
                e.insert(0, default)
            e.grid(row=row + 1, column=col, sticky="w", padx=(0, 20) if col == 0 else 0, pady=(2, 10))
            return e

        e_max = field("Макс. балл", "100", 2, 0)
        e_xp = field("Награда XP", "50", 2, 1)
        e_coin = field("Награда монетами", "5", 4, 0)
        e_dead = field("Дедлайн (ДД.ММ.ГГГГ)", "", 4, 1)

        def save():
            if not title.get().strip():
                messagebox.showwarning("Задание", "Введите название", parent=win)
                return
            try:
                mx = float(e_max.get().replace(",", "."))
                xp = int(e_xp.get())
                coins = int(e_coin.get())
                if mx <= 0 or xp < 0 or coins < 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Задание", "Проверьте числа: балл > 0, XP и монеты ≥ 0",
                                       parent=win)
                return
            deadline = None
            if e_dead.get().strip():
                try:
                    deadline = datetime.strptime(e_dead.get().strip(), "%d.%m.%Y").replace(
                        hour=23, minute=59)
                except ValueError:
                    messagebox.showwarning("Задание", "Дедлайн в формате ДД.ММ.ГГГГ", parent=win)
                    return
            try:
                db.create_task(discs[disc_names.index(disc.get())]["id"], self.uid,
                               title.get().strip(), desc.get("1.0", "end").strip(),
                               type_keys[[TYPE[k] for k in type_keys].index(ctype.get())],
                               diff_keys[[DIFF[k] for k in diff_keys].index(cdiff.get())],
                               mx, xp, coins, deadline, topic_id=topics.get(topic.get()))
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка БД", db.short_error(e), parent=win)
                return
            win.destroy()
            self.shell.refresh_current()

        button(win, "Создать задание", save, width=220).pack(pady=18)


class TeacherQuestsPage(Page):
    title = "Квесты"

    def build(self):
        card, self.tree = make_table(self, [
            ("title", "Квест", 240), ("disc", "Дисциплина", 200), ("tasks", "Заданий", 75),
            ("xp", "XP", 55), ("coins", "Монет", 65), ("ends", "Срок", 100),
            ("done", "Выполнили", 90), ("prog", "В процессе", 95), ("active", "Активен", 70)],
            height=15)
        card.pack(fill="both", expand=True)
        self.tree.tag_configure("off", foreground="#6b6f7b")
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(anchor="e", pady=(12, 0))
        button(btns, "Создать квест", self.create_dialog, width=170).pack(side="left", padx=5)
        button(btns, "Вкл / выкл", self.toggle, kind="ghost", width=130).pack(side="left", padx=5)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for q in db_safe(lambda: db.get_teacher_quests(self.uid), []):
            self.tree.insert("", "end", iid=str(q["id"]), tags=() if q["is_active"] else ("off",), values=(
                q["title"], q["discipline"] or "разные", q["tasks"], q["xp_reward"],
                q["coin_reward"], q["ends_at"].strftime("%d.%m.%Y") if q["ends_at"] else "—",
                q["completed"], q["in_progress"], "да" if q["is_active"] else "нет"))

    def toggle(self):
        qid = selected_id(self.tree)
        if qid is None:
            messagebox.showinfo("Квест", "Выберите квест в списке")
            return
        db_safe(lambda: db.toggle_quest(qid), None)
        self.refresh()

    def create_dialog(self):
        tasks = [t for t in db_safe(lambda: db.get_teacher_tasks(self.uid), []) if t["is_active"]]
        if len(tasks) < 2:
            messagebox.showinfo("Квест", "Для квеста нужно минимум два активных задания.\n"
                                         "Сначала создайте задания на вкладке «Мои задания».")
            return
        win = make_dialog(self, "Новый квест", 620, 730)
        pad = dict(padx=24, pady=(10, 0))

        ctk.CTkLabel(win, text="Название", anchor="w").pack(fill="x", **pad)
        title = entry(win, width=570)
        title.pack(anchor="w", padx=24, pady=(4, 0))
        ctk.CTkLabel(win, text="Описание", anchor="w").pack(fill="x", **pad)
        desc = ctk.CTkTextbox(win, height=80, corner_radius=10, wrap="word")
        desc.pack(fill="x", padx=24, pady=(4, 0))

        grid = ctk.CTkFrame(win, fg_color="transparent")
        grid.pack(fill="x", padx=24, pady=(12, 0))
        entries = {}
        for col, (key, label, default, width) in enumerate([
                ("xp", "Награда XP", "80", 130), ("coins", "Награда монетами", "15", 150),
                ("ends", "Срок (ДД.ММ.ГГГГ)", "", 180)]):
            ctk.CTkLabel(grid, text=label).grid(row=0, column=col, sticky="w")
            e = entry(grid, width=width)
            if default:
                e.insert(0, default)
            e.grid(row=1, column=col, sticky="w", padx=(0, 16), pady=(2, 0))
            entries[key] = e

        ctk.CTkLabel(win, text="Задания квеста (отметьте минимум два):", anchor="w"
                     ).pack(fill="x", **pad)
        box = ctk.CTkScrollableFrame(win, height=230, corner_radius=10)
        box.pack(fill="x", padx=24, pady=(4, 0))
        checks = []
        for t in tasks:
            var = tk.IntVar(value=0)
            ctk.CTkCheckBox(box, text=cut(f"{t['discipline']} — {t['title']}", 75), variable=var,
                            fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(anchor="w", pady=4)
            checks.append((t["id"], var))

        def save():
            if not title.get().strip():
                messagebox.showwarning("Квест", "Введите название", parent=win)
                return
            try:
                xp, coins = int(entries["xp"].get()), int(entries["coins"].get())
                if xp < 0 or coins < 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Квест", "XP и монеты — целые числа ≥ 0", parent=win)
                return
            ends = None
            if entries["ends"].get().strip():
                try:
                    ends = datetime.strptime(entries["ends"].get().strip(), "%d.%m.%Y").replace(
                        hour=23, minute=59)
                except ValueError:
                    messagebox.showwarning("Квест", "Срок в формате ДД.ММ.ГГГГ", parent=win)
                    return
                if ends < datetime.now():
                    messagebox.showwarning("Квест", "Срок не может быть в прошлом", parent=win)
                    return
            ids = [tid for tid, var in checks if var.get() == 1]
            if len(ids) < 2:
                messagebox.showwarning("Квест", "Отметьте минимум два задания", parent=win)
                return
            try:
                db.create_quest(title.get().strip(), desc.get("1.0", "end").strip(),
                                xp, coins, ends, ids)
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка БД", db.short_error(e), parent=win)
                return
            win.destroy()
            self.shell.refresh_current()

        button(win, "Создать квест", save, width=220).pack(pady=16)


class TeacherGroupsPage(Page):
    title = "Мои группы"

    def build(self):
        card, self.tree = make_table(self, [
            ("grp", "Группа", 100), ("disc", "Дисциплина", 300), ("year", "Учебный год", 110),
            ("sem", "Семестр", 80), ("students", "Студентов", 90),
            ("avg", "Средний балл", 110), ("pending", "Ждут проверки", 120)], height=15)
        card.pack(fill="both", expand=True)
        ctk.CTkLabel(self, text="Дисциплины и группы назначает администратор. "
                                "Средний балл считается по оценённым работам.",
                     text_color=MUTED, anchor="w").pack(fill="x", pady=(10, 0))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, g in enumerate(db_safe(lambda: db.get_teacher_groups_stats(self.uid), [])):
            avg = g["avg_percent"]
            self.tree.insert("", "end", iid=str(i), values=(
                g["grp"], g["discipline"], g["academic_year"], g["semester"], g["students"],
                "—" if avg is None else f"{avg:g}%", g["pending"]))


class TeacherRewardsPage(Page):
    title = "Выдача наград"

    def build(self):
        card, self.tree = make_table(self, [
            ("student", "Студент", 220), ("grp", "Группа", 90), ("title", "Награда", 290),
            ("cost", "Цена", 80), ("date", "Куплено", 140)], height=15)
        card.pack(fill="both", expand=True)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(anchor="e", pady=(12, 0))
        button(btns, "Отметить выданной", self.issue, width=200).pack(side="left", padx=5)
        button(btns, "Отменить, вернуть монеты", self.cancel, kind="danger",
               width=230).pack(side="left", padx=5)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for p in db_safe(db.get_pending_purchases, []):
            self.tree.insert("", "end", iid=str(p["id"]), values=(
                p["student"], p["grp"] or "—", p["title"], p["cost_coins"],
                fmt_dt(p["purchased_at"])))

    def _act(self, func, question=None):
        pid = selected_id(self.tree)
        if pid is None:
            messagebox.showinfo("Награды", "Выберите покупку в списке")
            return
        if question and not messagebox.askyesno("Награды", question):
            return
        err = func(pid)
        if err:
            messagebox.showerror("Награды", err)
        self.shell.refresh_current()

    def issue(self):
        self._act(db.issue_reward)

    def cancel(self):
        self._act(db.cancel_purchase, "Отменить покупку? Монеты вернутся студенту.")


class TeacherShell(Shell):
    role_label = "Преподаватель"

    def pages_def(self):
        return [("home", "Главная", TeacherDashboard), ("review", "На проверку", TeacherReviewPage),
                ("tasks", "Мои задания", TeacherTasksPage), ("quests", "Квесты", TeacherQuestsPage),
                ("groups", "Мои группы", TeacherGroupsPage),
                ("rewards", "Выдача наград", TeacherRewardsPage), ("rating", "Рейтинг", RatingPage)]

    def refresh_badge(self):
        rows = db_safe(lambda: db.get_pending_submissions(self.uid), [])
        self.set_badge("review", len(rows))
        self.set_badge("rewards", len(db_safe(db.get_pending_purchases, [])))


# =====================================================================
# АДМИНИСТРАТОР
# =====================================================================
def current_academic_year():
    """Учебный год и номер семестра по текущей дате (сентябрь — начало года)."""
    now = datetime.now()
    year = now.year if now.month >= 9 else now.year - 1
    return f"{year}/{year + 1}", (1 if now.month >= 9 else 2)


class AdminDashboard(Page):
    title = "Панель администратора"

    def build(self):
        tiles = ctk.CTkFrame(self, fg_color="transparent")
        tiles.pack(fill="x")
        tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="tile")
        
        self.tiles = {}
        tile_defs = [
            ("users", "Пользователи", ACCENT, 0, 0),
            ("active", "Активных", GREEN, 0, 1),
            ("academic", "Группы / Дисциплины", BLUE, 0, 2),
            ("tasks", "Заданий в системе", GOLD, 1, 0),
            ("submissions", "Сдач (ждут проверки)", RED, 1, 1),
            ("xp", "Начислено XP", GOLD, 1, 2),
        ]
        
        for key, heading, color, r, c in tile_defs:
            f, v = stat_tile(tiles, heading, color)
            f.configure(height=90)
            f.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            self.tiles[key] = v

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, pady=(16, 0))
        row.grid_rowconfigure(0, weight=1)
        row.grid_columnconfigure(0, weight=3, uniform="c")
        row.grid_columnconfigure(1, weight=2, uniform="c")

        # Левая колонка: Последние пользователи
        left_card = ctk.CTkFrame(row, corner_radius=14, fg_color=CARD)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(left_card, text="Недавно зарегистрированные", font=font(16, True), anchor="w"
                     ).pack(fill="x", padx=18, pady=(16, 6))
        self.recent_body = ctk.CTkFrame(left_card, fg_color="transparent")
        self.recent_body.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        # Правая колонка: Сводка и быстрые действия
        right_card = ctk.CTkFrame(row, corner_radius=14, fg_color=CARD)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(right_card, text="Сводка системы", font=font(16, True), anchor="w"
                     ).pack(fill="x", padx=18, pady=(16, 8))
        
        self.summary_box = ctk.CTkFrame(right_card, fg_color="transparent")
        self.summary_box.pack(fill="x", padx=18, pady=(0, 12))
        
        ctk.CTkLabel(right_card, text="Быстрые действия", font=font(15, True), anchor="w"
                     ).pack(fill="x", padx=18, pady=(8, 8))
        
        actions = ctk.CTkFrame(right_card, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 16))
        
        button(actions, "Управление пользователями", lambda: self.shell.show_page("users"), width=220
               ).pack(fill="x", pady=4)
        button(actions, "Управление группами", lambda: self.shell.show_page("groups"), kind="ghost", width=220
               ).pack(fill="x", pady=4)
        button(actions, "Назначения преподавателей", lambda: self.shell.show_page("assign"), kind="ghost", width=220
               ).pack(fill="x", pady=4)

    def refresh(self):
        stats = db_safe(db.get_admin_dashboard_stats, None)
        if not stats:
            return

        u = stats["users"]
        ac = stats["academic"]
        act = stats["activity"]

        self.tiles["users"].configure(text=f"{u['total_users'] or 0}")
        self.tiles["active"].configure(text=f"{u['active_users'] or 0} / {u['total_users'] or 0}")
        self.tiles["academic"].configure(text=f"{ac['groups_count'] or 0} / {ac['disciplines_count'] or 0}")
        self.tiles["tasks"].configure(text=f"{act['tasks_total'] or 0} ({act['tasks_active'] or 0})")
        self.tiles["submissions"].configure(text=f"{act['submissions_total'] or 0} ({act['submissions_pending'] or 0})")
        self.tiles["xp"].configure(text=f"{act['total_xp_awarded'] or 0}")

        # Список последних пользователей
        rows = []
        for ru in stats["recent_users"]:
            fio = f"{ru['last_name']} {ru['first_name']}"
            role_text = ROLE.get(ru["role"], ru["role"])
            if ru["group_name"]:
                role_text += f" ({ru['group_name']})"
            color = GREEN if ru["is_active"] else MUTED
            rows.append((f"{fio} · {ru['login']}", role_text, color))
        fill_list(self.recent_body, rows, "Пользователей пока нет")

        # Сводка системы
        for w in self.summary_box.winfo_children():
            w.destroy()
        
        items = [
            ("Студентов:", str(u["students"] or 0)),
            ("Преподавателей:", str(u["teachers"] or 0)),
            ("Администраторов:", str(u["admins"] or 0)),
            ("Специальностей:", str(ac["specialties_count"] or 0)),
            ("Назначений кафедры:", str(ac["assignments_count"] or 0)),
            ("Куплено наград в магазине:", str(act["rewards_purchased"] or 0)),
            ("Активных квестов:", str(act["active_quests"] or 0)),
        ]
        for label, val in items:
            r = ctk.CTkFrame(self.summary_box, fg_color="transparent")
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=label, text_color=MUTED, font=font(12)).pack(side="left")
            ctk.CTkLabel(r, text=val, font=font(12, True)).pack(side="right")


class AdminUsersPage(Page):
    title = "Управление пользователями"

    def build(self):
        self.users = {}
        self.groups = []

        # Панель поиска и фильтров
        filter_card = ctk.CTkFrame(self, corner_radius=12, fg_color=CARD)
        filter_card.pack(fill="x", pady=(0, 10))

        top_row = ctk.CTkFrame(filter_card, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(top_row, text="Поиск:", text_color=MUTED).pack(side="left", padx=(0, 6))
        self.search_entry = entry(top_row, "Логин, ФИО, email, группа...", width=240)
        self.search_entry.pack(side="left", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda e: self.refresh())

        button(top_row, "Найти", self.refresh, width=80).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(top_row, text="Роль:", text_color=MUTED).pack(side="left", padx=(0, 6))
        self.role_filter = option_menu(top_row, ["Все роли", "Студент", "Преподаватель", "Администратор"],
                                       width=140, command=lambda _: self.refresh())
        self.role_filter.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(top_row, text="Группа:", text_color=MUTED).pack(side="left", padx=(0, 6))
        self.group_filter = option_menu(top_row, ["Все группы"], width=130, command=lambda _: self.refresh())
        self.group_filter.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(top_row, text="Статус:", text_color=MUTED).pack(side="left", padx=(0, 6))
        self.status_filter = option_menu(top_row, ["Все статусы", "Активные", "Отключённые"],
                                         width=130, command=lambda _: self.refresh())
        self.status_filter.pack(side="left", padx=(0, 8))

        button(top_row, "Сбросить", self.reset_filters, kind="ghost", width=90).pack(side="left")

        # Таблица пользователей
        card, self.tree = make_table(self, [
            ("id", "ID", 45), ("login", "Логин", 115), ("fio", "ФИО", 220),
            ("role", "Роль", 110), ("grp", "Группа", 80), ("email", "Email", 170),
            ("balance", "XP / Монеты", 110), ("active", "Активен", 75),
            ("created", "Создан", 120)], height=13)
        card.pack(fill="both", expand=True)

        self.tree.tag_configure("admin", foreground=GOLD)
        self.tree.tag_configure("teacher", foreground=BLUE)
        self.tree.tag_configure("off", foreground="#6b6f7b")
        self.tree.bind("<Double-1>", lambda e: self.details_dialog())

        # Панель действий
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", pady=(10, 0))

        left_btns = ctk.CTkFrame(btns, fg_color="transparent")
        left_btns.pack(side="left")
        button(left_btns, "Создать пользователя", self.create_dialog, width=175).pack(side="left", padx=(0, 6))
        button(left_btns, "Редактировать", self.edit_dialog, width=135).pack(side="left", padx=(0, 6))
        button(left_btns, "Сменить пароль", self.reset_password_dialog, kind="ghost", width=135).pack(side="left", padx=(0, 6))
        button(left_btns, "Вкл / Выкл", self.toggle, kind="ghost", width=105).pack(side="left", padx=(0, 6))
        button(left_btns, "Баланс XP/монет", self.balance_dialog, kind="ghost", width=145).pack(side="left", padx=(0, 6))

        right_btns = ctk.CTkFrame(btns, fg_color="transparent")
        right_btns.pack(side="right")
        button(right_btns, "Подробнее", self.details_dialog, kind="ghost", width=110).pack(side="left", padx=(0, 6))
        button(right_btns, "Удалить", self.delete_user_dialog, kind="danger", width=100).pack(side="left")

    def reset_filters(self):
        self.search_entry.delete(0, "end")
        self.role_filter.set("Все роли")
        self.group_filter.set("Все группы")
        self.status_filter.set("Все статусы")
        self.refresh()

    def refresh(self):
        self.groups = db_safe(db.get_groups, [])
        grp_names = ["Все группы"] + [g["name"] for g in self.groups]
        current_grp = self.group_filter.get()
        self.group_filter.configure(values=grp_names)
        self.group_filter.set(current_grp if current_grp in grp_names else "Все группы")

        search = self.search_entry.get().strip() or None
        
        role_map = {"Все роли": None, "Студент": "student", "Преподаватель": "teacher", "Администратор": "admin"}
        role = role_map.get(self.role_filter.get())

        group_id = None
        if self.group_filter.get() != "Все группы":
            for g in self.groups:
                if g["name"] == self.group_filter.get():
                    group_id = g["id"]
                    break

        status_map = {"Все статусы": None, "Активные": True, "Отключённые": False}
        is_active = status_map.get(self.status_filter.get())

        self.tree.delete(*self.tree.get_children())
        self.users = {}
        users_list = db_safe(lambda: db.get_all_users(search, role, group_id, is_active), [])

        for u in users_list:
            self.users[u["id"]] = u
            fio = f"{u['last_name']} {u['first_name']} {u['middle_name'] or ''}".strip()
            
            tag = "off" if not u["is_active"] else (u["role"] if u["role"] in ("admin", "teacher") else "")
            tags = (tag,) if tag else ()

            balance_str = f"{u['total_xp']} XP / {u['coins']} м." if u["role"] == "student" and u["total_xp"] is not None else "—"
            created_str = u["created_at"].strftime("%d.%m.%Y") if u.get("created_at") else "—"

            self.tree.insert("", "end", iid=str(u["id"]), tags=tags, values=(
                u["id"], u["login"], fio, ROLE.get(u["role"], u["role"]),
                u["group_name"] or "—", u["email"] or "—", balance_str,
                "да" if u["is_active"] else "нет", created_str))

    def _selected_user(self):
        uid = selected_id(self.tree)
        if uid is None:
            messagebox.showinfo("Пользователи", "Выберите пользователя в списке")
            return None
        return self.users.get(uid)

    def toggle(self):
        u = self._selected_user()
        if not u:
            return
        if u["id"] == self.uid:
            messagebox.showwarning("Пользователи", "Нельзя отключить собственный аккаунт администратора")
            return
        db_safe(lambda: db.set_user_active(u["id"], not u["is_active"]), None)
        self.refresh()

    def reset_password_dialog(self):
        u = self._selected_user()
        if not u:
            return
        
        fio = f"{u['last_name']} {u['first_name']}"
        win = make_dialog(self, "Смена пароля", 440, 320)
        
        ctk.CTkLabel(win, text=f"Смена пароля", font=font(18, True)).pack(pady=(18, 2))
        ctk.CTkLabel(win, text=f"Пользователь: {fio} ({u['login']})", text_color=MUTED).pack(pady=(0, 14))

        p1 = entry(win, "Новый пароль (от 6 символов)", width=320, show="•")
        p1.pack(pady=6)
        p2 = entry(win, "Повторите новый пароль", width=320, show="•")
        p2.pack(pady=6)

        def save():
            pw = p1.get()
            if len(pw) < 6:
                messagebox.showwarning("Пароль", "Пароль должен быть не короче 6 символов", parent=win)
                return
            if pw != p2.get():
                messagebox.showwarning("Пароль", "Пароли не совпадают", parent=win)
                return
            if db_safe(lambda: db.reset_password(u["id"], pw) or True, False):
                win.destroy()
                messagebox.showinfo("Пароль", f"Пароль для «{u['login']}» успешно изменён")

        button(win, "Сохранить пароль", save, width=220).pack(pady=18)

    def balance_dialog(self):
        u = self._selected_user()
        if not u:
            return
        if u["role"] != "student":
            messagebox.showinfo("Баланс", "Управление балансом XP и монет применимо только к студентам")
            return

        win = make_dialog(self, "Баланс студента", 480, 420)
        fio = f"{u['last_name']} {u['first_name']}"
        
        ctk.CTkLabel(win, text="Управление балансом", font=font(18, True)).pack(pady=(18, 2))
        ctk.CTkLabel(win, text=f"Студент: {fio} ({u['group_name'] or 'без группы'})", text_color=MUTED).pack(pady=(0, 8))

        curr_frame = ctk.CTkFrame(win, fg_color=CARD_INNER, corner_radius=10)
        curr_frame.pack(fill="x", padx=30, pady=8)
        ctk.CTkLabel(curr_frame, text=f"Текущий баланс:  {u['total_xp'] or 0} XP  ·  {u['coins'] or 0} монет",
                     font=font(14, True), text_color=GOLD).pack(pady=10)

        grid = ctk.CTkFrame(win, fg_color="transparent")
        grid.pack(fill="x", padx=30, pady=6)
        
        ctk.CTkLabel(grid, text="Изменение XP (+/-):").grid(row=0, column=0, sticky="w", pady=4)
        e_xp = entry(grid, "0", width=180)
        e_xp.insert(0, "0")
        e_xp.grid(row=0, column=1, sticky="e", pady=4)

        ctk.CTkLabel(grid, text="Изменение монет (+/-):").grid(row=1, column=0, sticky="w", pady=4)
        e_coins = entry(grid, "0", width=180)
        e_coins.insert(0, "0")
        e_coins.grid(row=1, column=1, sticky="e", pady=4)

        ctk.CTkLabel(win, text="Причина корректировки:", anchor="w").pack(fill="x", padx=30, pady=(8, 2))
        e_comment = entry(win, "Корректировка администратором", width=420)
        e_comment.insert(0, "Корректировка администратором")
        e_comment.pack(padx=30, pady=(0, 10))

        def save():
            try:
                xp_val = int(e_xp.get().strip())
                coin_val = int(e_coins.get().strip())
            except ValueError:
                messagebox.showwarning("Баланс", "Введите целые числа для XP и монет", parent=win)
                return
            if xp_val == 0 and coin_val == 0:
                messagebox.showwarning("Баланс", "Укажите ненулевое изменение XP или монет", parent=win)
                return
            comment = e_comment.get().strip() or "Корректировка администратором"
            err = db.adjust_student_balance(u["id"], xp_val, coin_val, comment)
            if err:
                messagebox.showerror("Ошибка", err, parent=win)
                return
            win.destroy()
            messagebox.showinfo("Баланс", "Баланс студента успешно обновлён")
            self.refresh()

        button(win, "Применить изменения", save, width=220).pack(pady=12)

    def details_dialog(self):
        u = self._selected_user()
        if not u:
            return
        
        details = db_safe(lambda: db.get_user_details(u["id"]), None)
        if not details:
            messagebox.showerror("Ошибка", "Не удалось загрузить данные пользователя")
            return

        win = make_dialog(self, f"Профиль: {details['login']}", 580, 560)
        fio = f"{details['last_name']} {details['first_name']} {details['middle_name'] or ''}".strip()
        
        ctk.CTkLabel(win, text=fio, font=font(20, True)).pack(pady=(20, 2))
        role_title = ROLE.get(details["role"], details["role"])
        status_text = "Активен" if details["is_active"] else "Заблокирован"
        ctk.CTkLabel(win, text=f"{role_title}  ·  Статус: {status_text}",
                     text_color=GREEN if details["is_active"] else RED).pack(pady=(0, 14))

        box = ctk.CTkScrollableFrame(win, corner_radius=12, fg_color=CARD)
        box.pack(fill="both", expand=True, padx=24, pady=(0, 18))

        def add_info_row(title, val, val_color=TEXT):
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack(fill="x", pady=4)
            ctk.CTkLabel(r, text=title, text_color=MUTED, font=font(12)).pack(side="left")
            ctk.CTkLabel(r, text=str(val), font=font(13, True), text_color=val_color).pack(side="right")

        add_info_row("ID пользователя:", details["id"])
        add_info_row("Логин:", details["login"])
        add_info_row("Email:", details["email"] or "не указан")
        add_info_row("Дата регистрации:", fmt_dt(details.get("created_at")))
        
        if details["role"] == "student":
            add_info_row("Группа:", details["group_name"] or "не назначена")
            add_info_row("Текущий уровень:", f"Уровень {details.get('level_no', 1)} ({details.get('level_title', 'Новичок')})", ACCENT)
            add_info_row("Всего XP:", details.get("total_xp", 0), GOLD)
            add_info_row("Баланс монет:", details.get("coins", 0), GOLD)
            add_info_row("Серия дней:", f"{details.get('current_streak', 0)} (лучшая: {details.get('best_streak', 0)})", GREEN)
            add_info_row("Всего сдач работ:", details.get("total_submissions", 0))
            add_info_row("Оценённых работ:", details.get("graded_count", 0))
            add_info_row("Работ на максимум (100%):", details.get("perfect_count", 0))
            avg = details.get("avg_score")
            add_info_row("Средний балл:", f"{avg:.1f}" if avg is not None else "—", GREEN if avg and avg >= 80 else TEXT)
            add_info_row("Получено достижений:", details.get("achievements_count", 0), BLUE)
            add_info_row("Покупок в магазине:", details.get("purchases_count", 0))
        elif details["role"] == "teacher":
            add_info_row("Создано заданий:", f"{details.get('tasks_count', 0)} (активных: {details.get('active_tasks_count', 0)})", ACCENT)
            add_info_row("Назначено групп:", details.get("groups_count", 0))
            add_info_row("Назначено дисциплин:", details.get("disciplines_count", 0))
            add_info_row("Проверено работ студентов:", details.get("checked_submissions", 0), GREEN)

        button(win, "Закрыть", win.destroy, kind="ghost", width=140).pack(pady=(0, 16))

    def create_dialog(self):
        groups = db_safe(db.get_groups, [])
        by_name = {g["name"]: g["id"] for g in groups}
        win = make_dialog(self, "Новый пользователь", 480, 700)
        ctk.CTkLabel(win, text="Создание пользователя", font=font(18, True)).pack(pady=(18, 8))

        fields = {}
        for key, ph, secret in [("last_name", "Фамилия *", False), ("first_name", "Имя *", False),
                                ("middle_name", "Отчество", False),
                                ("email", "Email", False),
                                ("login", "Логин *", False),
                                ("password", "Пароль (от 6 символов) *", True)]:
            e = entry(win, ph, width=380, show="•" if secret else None)
            e.pack(pady=4)
            fields[key] = e

        def role_changed(value):
            group_menu.configure(state="normal" if value == ROLE["student"] else "disabled")

        ctk.CTkLabel(win, text="Роль пользователя:", text_color=MUTED, font=font(12), anchor="w").pack(fill="x", padx=50, pady=(6, 2))
        role_menu = option_menu(win, list(ROLE.values()), width=380, command=role_changed)
        role_menu.pack(pady=2)

        ctk.CTkLabel(win, text="Учебная группа (для студентов):", text_color=MUTED, font=font(12), anchor="w").pack(fill="x", padx=50, pady=(6, 2))
        group_menu = option_menu(win, list(by_name) or ["Нет групп в БД"], width=380)
        group_menu.pack(pady=2)

        def save():
            v = {k: e.get().strip() for k, e in fields.items()}
            v["password"] = fields["password"].get()
            if not (v["last_name"] and v["first_name"] and v["login"] and v["password"]):
                messagebox.showwarning("Пользователь", "Заполните обязательные поля: фамилию, имя, логин и пароль",
                                       parent=win)
                return
            if len(v["password"]) < 6:
                messagebox.showwarning("Пользователь", "Пароль должен быть не короче 6 символов", parent=win)
                return
            role_code = {name: code for code, name in ROLE.items()}[role_menu.get()]
            group_id = None
            if role_code == "student":
                group_id = by_name.get(group_menu.get())
                if group_id is None:
                    messagebox.showwarning("Пользователь", "Выберите группу студента", parent=win)
                    return
            err = db.register_user(v["login"], v["password"], v["last_name"], v["first_name"],
                                   v["middle_name"], v["email"], role_code, group_id)
            if err:
                messagebox.showerror("Ошибка", err, parent=win)
                return
            win.destroy()
            messagebox.showinfo("Успех", f"Пользователь «{v['login']}» успешно создан")
            self.refresh()

        button(win, "Создать аккаунт", save, width=220).pack(pady=18)

    def edit_dialog(self):
        u = self._selected_user()
        if not u:
            return

        groups = db_safe(db.get_groups, [])
        by_name = {g["name"]: g["id"] for g in groups}
        by_id = {g["id"]: g["name"] for g in groups}

        win = make_dialog(self, f"Редактирование: {u['login']}", 480, 680)
        ctk.CTkLabel(win, text="Редактирование пользователя", font=font(18, True)).pack(pady=(18, 8))

        fields = {}
        for key, label, val in [("last_name", "Фамилия *", u["last_name"]),
                                ("first_name", "Имя *", u["first_name"]),
                                ("middle_name", "Отчество", u["middle_name"] or ""),
                                ("email", "Email", u["email"] or ""),
                                ("login", "Логин *", u["login"])]:
            ctk.CTkLabel(win, text=label, text_color=MUTED, font=font(12), anchor="w").pack(fill="x", padx=50, pady=(4, 1))
            e = entry(win, "", width=380)
            e.insert(0, val)
            e.pack(pady=(0, 4))
            fields[key] = e

        def role_changed(value):
            group_menu.configure(state="normal" if value == ROLE["student"] else "disabled")

        ctk.CTkLabel(win, text="Роль:", text_color=MUTED, font=font(12), anchor="w").pack(fill="x", padx=50, pady=(4, 1))
        role_menu = option_menu(win, list(ROLE.values()), width=380, command=role_changed)
        role_menu.set(ROLE.get(u["role"], u["role"]))
        role_menu.pack(pady=(0, 4))

        ctk.CTkLabel(win, text="Группа:", text_color=MUTED, font=font(12), anchor="w").pack(fill="x", padx=50, pady=(4, 1))
        group_menu = option_menu(win, list(by_name) or ["Нет групп в БД"], width=380)
        default_grp = by_id.get(u["group_id"], list(by_name)[0] if by_name else "Нет групп в БД")
        group_menu.set(default_grp)
        group_menu.configure(state="normal" if u["role"] == "student" else "disabled")
        group_menu.pack(pady=(0, 8))

        sw_active = ctk.CTkSwitch(win, text="Аккаунт активен", progress_color=GREEN)
        if u["is_active"]:
            sw_active.select()
        sw_active.pack(padx=50, pady=4, anchor="w")

        def save():
            v = {k: e.get().strip() for k, e in fields.items()}
            if not (v["last_name"] and v["first_name"] and v["login"]):
                messagebox.showwarning("Пользователь", "Заполните фамилию, имя и логин", parent=win)
                return
            
            role_code = {name: code for code, name in ROLE.items()}[role_menu.get()]
            group_id = by_name.get(group_menu.get()) if role_code == "student" else None

            if u["id"] == self.uid:
                if role_code != "admin":
                    messagebox.showwarning("Пользователь", "Нельзя понизить роль собственного аккаунта администратора", parent=win)
                    return
                if not sw_active.get():
                    messagebox.showwarning("Пользователь", "Нельзя отключить собственный аккаунт", parent=win)
                    return

            err = db.update_user(u["id"], v["login"], v["last_name"], v["first_name"],
                                 v["middle_name"], v["email"], role_code, group_id, bool(sw_active.get()))
            if err:
                messagebox.showerror("Ошибка", err, parent=win)
                return
            win.destroy()
            messagebox.showinfo("Успех", "Данные пользователя успешно обновлены")
            self.refresh()

        button(win, "Сохранить изменения", save, width=220).pack(pady=16)

    def delete_user_dialog(self):
        u = self._selected_user()
        if not u:
            return
        if u["id"] == self.uid:
            messagebox.showwarning("Удаление", "Нельзя удалить собственный аккаунт администратора")
            return
        
        fio = f"{u['last_name']} {u['first_name']}"
        if not messagebox.askyesno("Удаление пользователя",
                                   f"Вы действительно хотите удалить пользователя «{fio} ({u['login']})»?\n\n"
                                   "Это действие необратимо и удалит все связанные данные (профиль, сдачи, достижения)."):
            return

        err = db.delete_user(u["id"])
        if err:
            messagebox.showerror("Удаление", err)
            return
        messagebox.showinfo("Удаление", "Пользователь успешно удалён")
        self.refresh()


class AdminGroupsPage(Page):
    title = "Группы и специальности"

    def build(self):
        card, self.tree = make_table(self, [
            ("name", "Группа", 110), ("spec", "Специальность", 340), ("course", "Курс", 70),
            ("year", "Год набора", 110), ("curator", "Куратор", 220), ("students", "Студентов", 95)],
            height=15)
        card.pack(fill="both", expand=True)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(anchor="e", pady=(12, 0))
        button(btns, "Создать группу", self.create_dialog, width=170).pack(side="left", padx=5)
        button(btns, "Удалить группу", self.delete_group, kind="danger", width=150).pack(side="left", padx=5)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for g in db_safe(db.get_groups_detailed, []):
            self.tree.insert("", "end", iid=str(g["id"]), values=(
                g["name"], f"{g['spec_code']} {g['spec_name']}", g["course"],
                g["admission_year"], g["curator"] or "—", g["students_count"]))

    def create_dialog(self):
        specs = db_safe(db.get_specialties, [])
        teachers = db_safe(db.get_teachers, [])
        if not specs:
            messagebox.showwarning("Группы", "В базе нет специальностей")
            return

        spec_map = {f"{s['code']} {s['name']}": s["id"] for s in specs}
        teacher_map = {"Без куратора": None}
        teacher_map.update({f"{t['last_name']} {t['first_name']} {t['middle_name'] or ''}".strip(): t["id"]
                            for t in teachers})

        win = make_dialog(self, "Новая группа", 480, 520)
        ctk.CTkLabel(win, text="Создание учебной группы", font=font(18, True)).pack(pady=(18, 12))

        ctk.CTkLabel(win, text="Название группы (например, ИС-11):", text_color=MUTED, font=font(12), anchor="w").pack(fill="x", padx=40, pady=(4, 1))
        e_name = entry(win, "Название группы", width=400)
        e_name.pack(pady=(0, 8))

        ctk.CTkLabel(win, text="Специальность:", text_color=MUTED, font=font(12), anchor="w").pack(fill="x", padx=40, pady=(4, 1))
        menu_spec = option_menu(win, list(spec_map), width=400)
        menu_spec.pack(pady=(0, 8))

        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=40, pady=4)
        ctk.CTkLabel(row, text="Курс:").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row, text="Год набора:").grid(row=0, column=1, sticky="w", padx=(20, 0))
        
        course_menu = option_menu(row, ["1", "2", "3", "4"], width=180)
        course_menu.grid(row=1, column=0, sticky="w", pady=(2, 0))

        e_year = entry(row, str(datetime.now().year), width=190)
        e_year.insert(0, str(datetime.now().year))
        e_year.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=(2, 0))

        ctk.CTkLabel(win, text="Куратор группы:", text_color=MUTED, font=font(12), anchor="w").pack(fill="x", padx=40, pady=(12, 1))
        menu_curator = option_menu(win, list(teacher_map), width=400)
        menu_curator.pack(pady=(0, 16))

        def save():
            name = e_name.get().strip()
            if not name:
                messagebox.showwarning("Группа", "Введите название группы", parent=win)
                return
            try:
                year = int(e_year.get().strip())
                course = int(course_menu.get())
                if year < 2000 or year > 2100:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Группа", "Укажите корректный год набора (например, 2026)", parent=win)
                return
            
            spec_id = spec_map[menu_spec.get()]
            curator_id = teacher_map[menu_curator.get()]

            err = db.create_group(name, spec_id, course, year, curator_id)
            if err:
                messagebox.showerror("Ошибка", err, parent=win)
                return
            win.destroy()
            messagebox.showinfo("Успех", f"Группа «{name}» успешно создана")
            self.refresh()

        button(win, "Создать группу", save, width=220).pack(pady=10)

    def delete_group(self):
        gid = selected_id(self.tree)
        if gid is None:
            messagebox.showinfo("Группы", "Выберите группу в списке")
            return
        if not messagebox.askyesno("Удаление группы", "Удалить выбранную группу?"):
            return
        err = db.delete_group(gid)
        if err:
            messagebox.showerror("Удаление", err)
            return
        messagebox.showinfo("Успех", "Группа успешно удалена")
        self.refresh()


class AdminAssignmentsPage(Page):
    title = "Назначения преподавателей"

    def build(self):
        card, self.tree = make_table(self, [
            ("grp", "Группа", 90), ("disc", "Дисциплина", 330), ("teacher", "Преподаватель", 220),
            ("year", "Учебный год", 110), ("sem", "Семестр", 80)], height=15)
        card.pack(fill="both", expand=True)
        ctk.CTkLabel(self, text="Преподаватель создаёт задания только по назначенным ему "
                                "дисциплинам, и их видят студенты назначенной группы.",
                     text_color=MUTED, anchor="w").pack(fill="x", pady=(10, 0))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(anchor="e", pady=(8, 0))
        button(btns, "Назначить", self.add_dialog, width=160).pack(side="left", padx=5)
        button(btns, "Удалить назначение", self.delete, kind="danger",
               width=200).pack(side="left", padx=5)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for a in db_safe(db.get_assignments, []):
            self.tree.insert("", "end", iid=str(a["id"]), values=(
                a["grp"], f"{a['code']} {a['discipline']}", a["teacher"],
                a["academic_year"], a["semester"]))

    def delete(self):
        aid = selected_id(self.tree)
        if aid is None:
            messagebox.showinfo("Назначения", "Выберите назначение в списке")
            return
        if not messagebox.askyesno("Назначения", "Удалить назначение?\nЗадания останутся в БД, "
                                   "но студенты группы перестанут их видеть."):
            return
        db_safe(lambda: db.delete_assignment(aid), None)
        self.refresh()

    def add_dialog(self):
        groups = db_safe(db.get_groups, [])
        teachers = db_safe(db.get_teachers, [])
        if not groups:
            messagebox.showwarning("Назначения", "В БД нет групп. Создайте их на вкладке «Группы».")
            return
        if not teachers:
            messagebox.showwarning("Назначения", "Нет преподавателей. Создайте их на вкладке «Пользователи».")
            return
        group_ids = {g["name"]: g["id"] for g in groups}
        teacher_ids = {f"{t['last_name']} {t['first_name']} {t['middle_name'] or ''}".strip(): t["id"]
                       for t in teachers}
        disc_ids = {}

        win = make_dialog(self, "Новое назначение", 520, 560)
        pad = dict(padx=24, pady=(12, 0))
        ctk.CTkLabel(win, text="Группа", anchor="w").pack(fill="x", **pad)
        group_menu = option_menu(win, list(group_ids), width=470)
        group_menu.pack(anchor="w", padx=24, pady=(4, 0))

        ctk.CTkLabel(win, text="Дисциплина (из специальности группы)", anchor="w"
                     ).pack(fill="x", **pad)
        disc_menu = option_menu(win, ["—"], width=470)
        disc_menu.pack(anchor="w", padx=24, pady=(4, 0))

        def load_disciplines(_=None):
            rows = db_safe(lambda: db.get_group_disciplines(group_ids[group_menu.get()]), [])
            disc_ids.clear()
            disc_ids.update({f"{d['code']} {d['name']}": d["id"] for d in rows})
            names = list(disc_ids) or ["— нет дисциплин —"]
            disc_menu.configure(values=names)
            disc_menu.set(names[0])

        group_menu.configure(command=load_disciplines)
        load_disciplines()

        ctk.CTkLabel(win, text="Преподаватель", anchor="w").pack(fill="x", **pad)
        teacher_menu = option_menu(win, list(teacher_ids), width=470)
        teacher_menu.pack(anchor="w", padx=24, pady=(4, 0))

        year, sem = current_academic_year()
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(12, 0))
        ctk.CTkLabel(row, text="Учебный год").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row, text="Семестр").grid(row=0, column=1, sticky="w", padx=(20, 0))
        e_year = entry(row, width=150)
        e_year.insert(0, year)
        e_year.grid(row=1, column=0, sticky="w", pady=(2, 0))
        sem_menu = option_menu(row, [str(i) for i in range(1, 11)], width=100)
        sem_menu.set(str(sem))
        sem_menu.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=(2, 0))

        def save():
            if group_menu.get() not in group_ids or disc_menu.get() not in disc_ids:
                messagebox.showwarning("Назначения", "Выберите группу и дисциплину", parent=win)
                return
            y = e_year.get().strip()
            parts = y.split("/")
            if not (len(parts) == 2 and all(p.isdigit() for p in parts)
                    and int(parts[1]) == int(parts[0]) + 1):
                messagebox.showwarning("Назначения", "Учебный год в формате 2026/2027", parent=win)
                return
            err = db.add_assignment(disc_ids[disc_menu.get()], group_ids[group_menu.get()],
                                    teacher_ids[teacher_menu.get()], y, int(sem_menu.get()))
            if err:
                messagebox.showerror("Назначения", err, parent=win)
                return
            win.destroy()
            self.refresh()

        button(win, "Назначить", save, width=200).pack(pady=22)


class AdminShell(Shell):
    role_label = "Администратор"

    def pages_def(self):
        return [
            ("dashboard", "Главная", AdminDashboard),
            ("users", "Пользователи", AdminUsersPage),
            ("groups", "Группы", AdminGroupsPage),
            ("assign", "Назначения", AdminAssignmentsPage),
            ("rating", "Рейтинг", RatingPage),
        ]


if __name__ == "__main__":
    App().mainloop()
