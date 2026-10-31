import os
import random
import customtkinter as ctk
from PIL import Image, ImageDraw


class ImagePuzzleCaptcha(ctk.CTkFrame):
    def __init__(self, master, on_success_callback, image_path="MM.jpg", **kwargs):
        super().__init__(master, **kwargs)

        self.on_success_callback = on_success_callback
        self.image_path = image_path
        self.tiles = []
        self.original_order = [0, 1, 2, 3]
        self.current_order = [0, 1, 2, 3]
        self.selected_tile = None

        self.setup_ui()
        self.generate_captcha()

    def setup_ui(self):
        # Контейнер для сетки картинок
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(pady=10, padx=10)

        self.label_info = ctk.CTkLabel(
            self,
            text="Защита от ботов: соберите пазл.\nКликните на две плитки, чтобы поменять их местами.",
            font=("Segoe UI", 14, "bold"),  # Размер 14 и стиль "bold" — точно как на кнопках!
            text_color=("#6b6f7b", "#9a9eab")  # Мягкий серый цвет MUTED
        )
        self.label_info.pack(pady=10)

        self.btn_reset = ctk.CTkButton(self, text="Обновить капчу", command=self.generate_captcha, width=120)
        self.btn_reset.pack(pady=5)

    def generate_captcha(self):
        # Загрузка изображения MM.jpg (или переданного пути)
        target_path = self.image_path
        if not os.path.exists(target_path):
            dir_path = os.path.join(os.path.dirname(__file__), self.image_path)
            if os.path.exists(dir_path):
                target_path = dir_path

        try:
            img = Image.open(target_path).resize((200, 200))
        except Exception:
            # Создаем динамический рисунок, если файл изображения недоступен
            img = Image.new("RGB", (200, 200), color="#2b2b2b")
            draw = ImageDraw.Draw(img)
            # Рисуем яркие фигуры, чтобы было понятно, как собирать
            draw.rectangle([10, 10, 100, 100], fill="#1f538d")
            draw.ellipse([100, 100, 190, 190], fill="#e67e22")
            draw.polygon([(20, 180), (100, 110), (180, 180)], fill="#2ecc71")

        w, h = img.size
        w_part, h_part = w // 2, h // 2

        self.image_parts = [
            img.crop((0, 0, w_part, h_part)),
            img.crop((w_part, 0, w, h_part)),
            img.crop((0, h_part, w_part, h)),
            img.crop((w_part, h_part, w, h))
        ]

        self.current_order = [0, 1, 2, 3]
        while self.current_order == self.original_order:
            random.shuffle(self.current_order)

        self.selected_tile = None
        if hasattr(self, "label_info"):
            self.label_info.configure(
                text="Защита от ботов: соберите пазл.\nКликните на две плитки, чтобы поменять их местами.",
                text_color=("#6b6f7b", "#9a9eab")
            )
        self.render_tiles()

    def render_tiles(self):
        for tile in self.tiles:
            tile.destroy()
        self.tiles.clear()

        for grid_index, img_index in enumerate(self.current_order):
            pil_img = self.image_parts[img_index]
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(90, 90))

            label = ctk.CTkLabel(self.grid_frame, image=ctk_img, text="", cursor="hand2")
            row = grid_index // 2
            col = grid_index % 2
            label.grid(row=row, column=col, padx=2, pady=2)

            # Эффект выделения рамкой
            if self.selected_tile == grid_index:
                label.configure(fg_color="#1f538d")

            label.bind("<Button-1>", lambda event, idx=grid_index: self.on_tile_click(idx))
            self.tiles.append(label)

    def on_tile_click(self, grid_index):
        if self.selected_tile is None:
            self.selected_tile = grid_index
            self.render_tiles()
        else:
            idx1, idx2 = self.selected_tile, grid_index
            self.current_order[idx1], self.current_order[idx2] = self.current_order[idx2], self.current_order[idx1]
            self.selected_tile = None
            self.render_tiles()

            # --- ИСПРАВЛЕННАЯ ЛОГИКА ПРОВЕРКИ ---
            if self.current_order == self.original_order:
                # Если собрано правильно — включаем зелёный текст успеха
                self.label_info.configure(
                    text="Капча успешно пройдена! ✓",
                    text_color="#2ecc71"
                )
                self.on_success_callback(True)
            else:
                # Если хоть одна картинка стоит не на своём месте —
                # возвращаем стандартную инструкцию и обычный цвет текста
                self.label_info.configure(
                    text="Защита от ботов: соберите пазл.\nКликните на две плитки, чтобы поменять их местами.",
                    text_color=("#1b1b1f", "#ececf1")  # Будет автоматически подстраиваться под тему
                )
                self.on_success_callback(False)
