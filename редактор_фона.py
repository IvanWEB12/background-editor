# редактор_фона.py - ПОЛНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ v5.0
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, scrolledtext, simpledialog
from PIL import Image, ImageTk, ImageFilter, ImageEnhance, ImageOps, ImageDraw
import os
import json
import copy
import threading
import queue
import time
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime
import math
import random

# === ПРОВЕРКА БИБЛИОТЕК ===
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from skimage import exposure, filters, measure
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False

try:
    from rembg import remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import cairosvg
    HAS_SVG = True
except ImportError:
    HAS_SVG = False

HAS_AI = HAS_CV2 and HAS_SKIMAGE and HAS_REMBG

# === КЛАСС АВТООБНОВЛЕНИЯ ===
class Updater:
    def __init__(self, current_version="5.0"):
        self.version = current_version
        self.update_url = "https://raw.githubusercontent.com/ваш_логин/редактор_фона/main/version.json"
        self.download_url = "https://raw.githubusercontent.com/ваш_логин/редактор_фона/main/Редактор_фона.exe"
        self.owner = "ваш_логин"
        self.repo = "редактор_фона"
    
    def check_for_updates(self):
        if not HAS_REQUESTS:
            return False, None, "Установите requests: pip install requests"
        
        try:
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get('tag_name', '').replace('v', '')
                download_url = data.get('assets', [{}])[0].get('browser_download_url', '')
                
                if latest_version > self.version:
                    return True, latest_version, download_url
                return False, None, None
            
            response = requests.get(self.update_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get('version', '0.0')
                download_url = data.get('download_url', '')
                
                if latest_version > self.version:
                    return True, latest_version, download_url
                return False, None, None
            
            return False, None, "Не удалось проверить обновления"
        except Exception as e:
            return False, None, f"Ошибка: {str(e)}"
    
    def download_update(self, url=None):
        if not HAS_REQUESTS:
            return None, "Установите requests"
        
        try:
            download_url = url or self.download_url
            
            if download_url.startswith('file://'):
                local_path = download_url.replace('file://', '')
                if os.path.exists(local_path):
                    temp_path = os.path.join(tempfile.gettempdir(), "Редактор_фона_new.exe")
                    shutil.copy2(local_path, temp_path)
                    return temp_path, None
                return None, "Локальный файл не найден"
            
            response = requests.get(download_url, stream=True, timeout=30)
            
            if response.status_code != 200:
                return None, f"Ошибка: {response.status_code}"
            
            temp_path = os.path.join(tempfile.gettempdir(), "Редактор_фона_new.exe")
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return temp_path, None
        except Exception as e:
            return None, f"Ошибка: {str(e)}"
    
    def apply_update(self, new_exe_path):
        if not os.path.exists(new_exe_path):
            return False, "Файл не найден"
        
        current_exe = sys.executable
        
        if os.path.samefile(new_exe_path, current_exe):
            return False, "Файл совпадает с текущим"
        
        try:
            bat_content = f"""@echo off
echo Обновление Редактора фона...
timeout /t 2 /nobreak >nul
copy /y "{new_exe_path}" "{current_exe}"
if errorlevel 1 (
    echo Ошибка замены!
    pause
    exit
)
start "" "{current_exe}"
del "{new_exe_path}" 2>nul
exit
"""
            bat_path = os.path.join(tempfile.gettempdir(), "update_editor.bat")
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            
            subprocess.Popen([bat_path], shell=True, 
                           creationflags=subprocess.CREATE_NO_WINDOW)
            
            return True, "Обновление применено"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


# === ОСНОВНАЯ ПРОГРАММА ===
class BackgroundEditorUltimate:
    def __init__(self, root):
        self.root = root
        self.root.title("🎨 Редактор Фона Ultimate v5.0")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 700)
        
        # === ВЕРСИЯ ===
        self.version = "5.0"
        self.updater = Updater(self.version)
        
        # === ОСНОВНЫЕ ПЕРЕМЕННЫЕ ===
        self.current_language = 'ru'
        self.project_path = None
        self.project_folder = None
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_batch_mode = False
        self.batch_target_var = tk.StringVar(value="all")
        self.grid_visible = False
        self.rules_visible = False
        self.auto_save_enabled = True
        self.auto_save_interval = 300
        self.last_auto_save = time.time()
        self.resize_handles_var = tk.BooleanVar(value=True)
        self.dark_mode = tk.BooleanVar(value=True)
        self.show_tooltips = tk.BooleanVar(value=True)
        
        # === ДАННЫЕ ПРОЕКТА ===
        self.backgrounds = []
        self.current_background = None
        self.current_bg_index = 0
        self.objects = []
        self.selected_objects = []
        self.layers = []
        self.current_layer_index = 0
        self.recent_projects = []
        self.max_recent = 10
        self.clipboard = []
        self.clipboard_objects = []
        
        # === ИСТОРИЯ ===
        self.history = []
        self.history_index = -1
        self.max_history = 100
        
        # === ПАКЕТНАЯ ОБРАБОТКА ===
        self.batch_templates = {}
        self.batch_operations = []
        
        # === ЭКСПОРТ ===
        self.export_formats = ['PNG', 'JPG', 'BMP', 'WEBP', 'PDF', 'PSD']
        if HAS_SVG:
            self.export_formats.append('SVG')
        self.export_quality = 90
        
        # === ПРЕСЕТЫ ===
        self.custom_presets = {}
        
        # === НАСТРОЙКИ ===
        self.config = {
            'auto_save': True,
            'confirm_delete': True,
            'theme': 'dark',
            'language': 'ru',
            'check_updates': True,
            'quality': 90,
            'last_update_check': 0
        }
        
        # === КЭШ ===
        self.preview_cache = None
        self.preview_cache_time = 0
        self.cache_duration = 0.3
        
        # === ПРОВЕРКА БИБЛИОТЕК ===
        self.check_libraries()
        
        # === СОЗДАНИЕ ИНТЕРФЕЙСА ===
        self.setup_ui()
        self.setup_menu()
        self.setup_hotkeys()
        self.setup_tooltips()
        self.apply_theme()
        self.load_recent_projects()
        self.start_auto_save()
        self.setup_drag_drop()
        
        # === ПРОВЕРКА ОБНОВЛЕНИЙ ===
        if self.config.get('check_updates', True):
            self.root.after(3000, self.check_updates_auto)
        
        # === СТАТУС ===
        self.update_status()
    
    def check_libraries(self):
        self.has_cv2 = HAS_CV2
        self.has_skimage = HAS_SKIMAGE
        self.has_rembg = HAS_REMBG
        self.has_sklearn = HAS_SKLEARN
        self.has_ai = HAS_AI
        self.has_requests = HAS_REQUESTS
        self.has_svg = HAS_SVG
    
    def update_status(self):
        status = "✅ Готов к работе"
        if self.has_ai:
            status += " | 🤖 ИИ доступен"
        else:
            status += " | ⚠️ ИИ не доступен"
        if self.has_svg:
            status += " | 📤 SVG доступен"
        self.info_label.config(text=status)
    
    def setup_ui(self):
        """Создание интерфейса"""
        # Основной контейнер
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель
        left_container = ttk.Frame(main_paned)
        main_paned.add(left_container, weight=1)
        
        # Панель инструментов с вкладками
        tool_notebook = ttk.Notebook(left_container)
        tool_notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.setup_tools_tab(tool_notebook)
        self.setup_layers_tab(tool_notebook)
        self.setup_filters_tab(tool_notebook)
        self.setup_presets_tab(tool_notebook)
        self.setup_batch_tab(tool_notebook)
        self.setup_analysis_tab(tool_notebook)
        self.setup_history_tab(tool_notebook)
        self.setup_settings_tab(tool_notebook)
        
        # Центр - предпросмотр
        preview_container = ttk.Frame(main_paned)
        main_paned.add(preview_container, weight=3)
        self.setup_preview(preview_container)
        
        # Правая панель
        right_container = ttk.Frame(main_paned)
        main_paned.add(right_container, weight=1)
        self.setup_properties_panel(right_container)
    
    def setup_tools_tab(self, notebook):
        """Вкладка Инструменты"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🔧 Инструменты")
        
        # === ФОН ===
        bg_frame = ttk.LabelFrame(tab, text="📁 Фон")
        bg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(bg_frame, text="📂 Добавить фон", command=self.add_background).pack(fill=tk.X, pady=2)
        btn_frame = ttk.Frame(bg_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="◄", command=self.prev_background, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="►", command=self.next_background, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🎲", command=self.random_background, width=5).pack(side=tk.LEFT, padx=2)
        
        # === УДАЛЕНИЕ ФОНА ===
        remove_frame = ttk.LabelFrame(tab, text="🧹 Удаление фона")
        remove_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(remove_frame, text="🎯 По цвету", command=self.remove_by_color).pack(fill=tk.X, pady=2)
        ttk.Button(remove_frame, text="🤖 ИИ удаление", command=self.remove_ai).pack(fill=tk.X, pady=2)
        ttk.Button(remove_frame, text="✂️ Обрезка краёв", command=self.remove_edges).pack(fill=tk.X, pady=2)
        
        # === ОБЪЕКТЫ ===
        obj_frame = ttk.LabelFrame(tab, text="📦 Объекты")
        obj_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(obj_frame, text="➕ Добавить", command=self.add_object).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="📋 Дублировать", command=self.duplicate_objects).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="🗑 Удалить", command=self.delete_objects).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="🔀 Выровнять", command=self.align_objects).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="📐 Изменить размер", command=self.resize_dialog).pack(fill=tk.X, pady=2)
        
        # === ДЕЙСТВИЯ ===
        action_frame = ttk.LabelFrame(tab, text="⚡ Действия")
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        action_btns = ttk.Frame(action_frame)
        action_btns.pack(fill=tk.X, pady=2)
        ttk.Button(action_btns, text="↩ Отмена", command=self.undo, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_btns, text="↪ Повтор", command=self.redo, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_btns, text="⟳ Сброс", command=self.reset, width=10).pack(side=tk.LEFT, padx=2)
        
        # === МАРКЕРЫ ===
        resize_frame = ttk.LabelFrame(tab, text="📐 Ресайз маркеры")
        resize_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Checkbutton(resize_frame, text="Показывать маркеры", 
                       variable=self.resize_handles_var,
                       command=self.update_preview).pack(fill=tk.X, pady=2)
    
    def setup_layers_tab(self, notebook):
        """Вкладка Слои"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📚 Слои")
        
        # Список слоёв
        self.layer_listbox = tk.Listbox(tab, height=14, selectmode=tk.SINGLE)
        self.layer_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.layer_listbox.bind('<<ListboxSelect>>', self.on_layer_select)
        
        # Кнопки управления
        layer_btns = ttk.Frame(tab)
        layer_btns.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(layer_btns, text="➕ Новый", command=self.add_layer).pack(side=tk.LEFT, padx=2)
        ttk.Button(layer_btns, text="🗑 Удалить", command=self.delete_layer).pack(side=tk.LEFT, padx=2)
        ttk.Button(layer_btns, text="⬆", command=self.layer_up, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(layer_btns, text="⬇", command=self.layer_down, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(layer_btns, text="🔗", command=self.merge_layers, width=3).pack(side=tk.LEFT, padx=2)
        
        # Настройки слоя
        settings_frame = ttk.LabelFrame(tab, text="⚙️ Настройки слоя")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.layer_name_entry = ttk.Entry(settings_frame)
        self.layer_name_entry.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(settings_frame, text="Переименовать", command=self.rename_layer).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(settings_frame, text="Прозрачность:").pack(anchor=tk.W, padx=5)
        self.layer_opacity_scale = ttk.Scale(settings_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                            command=self.change_layer_opacity)
        self.layer_opacity_scale.pack(fill=tk.X, padx=5, pady=2)
        self.layer_opacity_label = ttk.Label(settings_frame, text="100%")
        self.layer_opacity_label.pack(pady=2)
        
        # Режим наложения
        ttk.Label(settings_frame, text="Режим наложения:").pack(anchor=tk.W, padx=5)
        blend_modes = ['normal', 'multiply', 'screen', 'overlay', 'soft_light', 
                      'hard_light', 'difference', 'exclusion', 'color_dodge', 'color_burn']
        self.blend_mode_var = tk.StringVar(value="normal")
        self.blend_combo = ttk.Combobox(settings_frame, textvariable=self.blend_mode_var,
                                        values=blend_modes, state='readonly')
        self.blend_combo.pack(fill=tk.X, padx=5, pady=2)
        self.blend_combo.bind('<<ComboboxSelected>>', self.change_blend_mode)
        
        # Видимость
        self.layer_visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="👁 Видимый", 
                       variable=self.layer_visible_var,
                       command=self.toggle_layer_visibility).pack(anchor=tk.W, padx=5, pady=2)
    
    def setup_filters_tab(self, notebook):
        """Вкладка Фильтры"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🎨 Фильтры")
        
        filter_notebook = ttk.Notebook(tab)
        filter_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === РАЗМЫТИЕ ===
        blur_tab = ttk.Frame(filter_notebook)
        filter_notebook.add(blur_tab, text="Размытие")
        
        ttk.Label(blur_tab, text="Размытие по Гауссу").pack(pady=5)
        self.blur_scale = ttk.Scale(blur_tab, from_=0, to=10, orient=tk.HORIZONTAL, length=250)
        self.blur_scale.set(2)
        self.blur_scale.pack(pady=5)
        ttk.Button(blur_tab, text="Применить", 
                  command=lambda: self.apply_filter('gaussian_blur', self.blur_scale.get())).pack(pady=5)
        
        for text, cmd in [("Сглаживание", 'smooth'), ("Резкость", 'sharpen'), 
                         ("Тиснение", 'emboss'), ("Размытие по краям", 'edge_blur')]:
            ttk.Button(blur_tab, text=text, command=lambda c=cmd: self.apply_filter(c)).pack(fill=tk.X, pady=2)
        
        # === КОРРЕКЦИЯ ===
        corr_tab = ttk.Frame(filter_notebook)
        filter_notebook.add(corr_tab, text="Коррекция")
        
        ttk.Label(corr_tab, text="Яркость").pack(pady=2)
        self.brightness_scale = ttk.Scale(corr_tab, from_=0, to=2, orient=tk.HORIZONTAL, length=250)
        self.brightness_scale.set(1.0)
        self.brightness_scale.pack(pady=2)
        
        ttk.Label(corr_tab, text="Контраст").pack(pady=2)
        self.contrast_scale = ttk.Scale(corr_tab, from_=0, to=2, orient=tk.HORIZONTAL, length=250)
        self.contrast_scale.set(1.0)
        self.contrast_scale.pack(pady=2)
        
        ttk.Label(corr_tab, text="Насыщенность").pack(pady=2)
        self.saturation_scale = ttk.Scale(corr_tab, from_=0, to=2, orient=tk.HORIZONTAL, length=250)
        self.saturation_scale.set(1.0)
        self.saturation_scale.pack(pady=2)
        
        ttk.Button(corr_tab, text="Применить коррекцию", command=self.apply_correction).pack(pady=5)
        
        # === ЭФФЕКТЫ ===
        eff_tab = ttk.Frame(filter_notebook)
        filter_notebook.add(eff_tab, text="Эффекты")
        
        for text, cmd in [("Ч/б", 'grayscale'), ("Сепия", 'sepia'), ("Инверсия", 'invert'),
                         ("Постеризация", 'posterize'), ("Соляризация", 'solarize'),
                         ("Виньетка", 'vignette'), ("Пикселизация", 'pixelate')]:
            ttk.Button(eff_tab, text=text, command=lambda c=cmd: self.apply_effect(c)).pack(fill=tk.X, pady=2)
        
        # === СПЕЦИАЛЬНЫЕ ===
        spec_tab = ttk.Frame(filter_notebook)
        filter_notebook.add(spec_tab, text="Специальные")
        
        ttk.Button(spec_tab, text="🔍 Автоконтраст", command=lambda: self.apply_auto('autocontrast')).pack(fill=tk.X, pady=2)
        ttk.Button(spec_tab, text="⚖️ Баланс белого", command=lambda: self.apply_auto('white_balance')).pack(fill=tk.X, pady=2)
        ttk.Button(spec_tab, text="✨ Улучшение деталей", command=lambda: self.apply_auto('detail_enhance')).pack(fill=tk.X, pady=2)
        ttk.Button(spec_tab, text="🧹 Шумоподавление", command=lambda: self.apply_auto('denoise')).pack(fill=tk.X, pady=2)
    
    def setup_presets_tab(self, notebook):
        """Вкладка Пресеты - ИСПРАВЛЕННАЯ"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⚡ Пресеты")
        
        ttk.Label(tab, text="🚀 Быстрые пресеты", font=("Arial", 10, "bold")).pack(pady=10)
        
        presets = [
            ("🎨 Vintage", self.preset_vintage),
            ("🎬 Cinematic", self.preset_cinematic),
            ("⚫ B&W", self.preset_bw),
            ("🔥 Warm", self.preset_warm),
            ("❄️ Cool", self.preset_cool),
            ("🌈 HDR", self.preset_hdr),
            ("🎭 Dramatic", self.preset_dramatic),
            ("✨ Soft Glow", self.preset_soft_glow),
            ("📷 Film Grain", self.preset_film_grain),
        ]
        
        # Создаём фрейм для кнопок
        presets_frame = ttk.Frame(tab)
        presets_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Размещаем кнопки в grid
        for i, (name, cmd) in enumerate(presets):
            row = i // 3
            col = i % 3
            btn = ttk.Button(presets_frame, text=name, command=cmd, width=14)
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        # Настройка колонок, чтобы растягивались
        for col in range(3):
            presets_frame.columnconfigure(col, weight=1)
        
        # --- ПОЛЬЗОВАТЕЛЬСКИЕ ПРЕСЕТЫ ---
        ttk.Label(tab, text="💾 Пользовательские пресеты", font=("Arial", 10, "bold")).pack(pady=(20, 10))
        
        custom_frame = ttk.Frame(tab)
        custom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.custom_preset_entry = ttk.Entry(custom_frame)
        self.custom_preset_entry.pack(fill=tk.X, pady=5)
        
        ttk.Button(custom_frame, text="💾 Сохранить как пресет",
                   command=self.save_custom_preset).pack(fill=tk.X, pady=2)
        
        self.custom_preset_list = tk.Listbox(custom_frame, height=4)
        self.custom_preset_list.pack(fill=tk.X, pady=5)
        
        btn_frame = ttk.Frame(custom_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(btn_frame, text="📂 Применить выбранный",
                   command=self.apply_custom_preset).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="🗑 Удалить",
                   command=self.delete_custom_preset).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        self.update_custom_preset_list()
    
    def setup_batch_tab(self, notebook):
        """Вкладка Пакетная обработка"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📦 Пакетная")
        
        # === ШАБЛОНЫ ===
        template_frame = ttk.LabelFrame(tab, text="📋 Шаблоны")
        template_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.template_listbox = tk.Listbox(template_frame, height=4)
        self.template_listbox.pack(fill=tk.X, padx=5, pady=5)
        self.template_listbox.bind('<<ListboxSelect>>', self.on_template_select)
        
        template_btns = ttk.Frame(template_frame)
        template_btns.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(template_btns, text="💾 Сохранить", command=self.save_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_btns, text="📂 Загрузить", command=self.load_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_btns, text="🗑 Удалить", command=self.delete_template).pack(side=tk.LEFT, padx=2)
        
        # === ОПЕРАЦИИ ===
        ops_frame = ttk.LabelFrame(tab, text="⚙️ Операции")
        ops_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.batch_ops_listbox = tk.Listbox(ops_frame, height=6)
        self.batch_ops_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ops_btns = ttk.Frame(ops_frame)
        ops_btns.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(ops_btns, text="➕ Добавить", command=self.add_batch_op).pack(side=tk.LEFT, padx=2)
        ttk.Button(ops_btns, text="🗑 Удалить", command=self.remove_batch_op).pack(side=tk.LEFT, padx=2)
        ttk.Button(ops_btns, text="⬆", width=3, command=self.batch_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(ops_btns, text="⬇", width=3, command=self.batch_down).pack(side=tk.LEFT, padx=2)
        
        # === ВЫПОЛНЕНИЕ ===
        exec_frame = ttk.Frame(tab)
        exec_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(exec_frame, text="Применить к:").pack(side=tk.LEFT)
        for text, value in [("Всем", "all"), ("Выбранным", "selected"), ("Слою", "layer")]:
            ttk.Radiobutton(exec_frame, text=text, variable=self.batch_target_var, 
                           value=value).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(tab, text="▶ ВЫПОЛНИТЬ", command=self.execute_batch,
                  style="Accent.TButton").pack(fill=tk.X, padx=5, pady=5)
        
        self.batch_progress = ttk.Progressbar(tab, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.batch_progress.pack(fill=tk.X, padx=5, pady=5)
        self.batch_status = ttk.Label(tab, text="✅ Готов к работе")
        self.batch_status.pack(pady=2)
    
    def setup_analysis_tab(self, notebook):
        """Вкладка Анализ"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📊 Анализ")
        
        analysis_frame = ttk.Frame(tab)
        analysis_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(analysis_frame, text="📊 Гистограмма", command=self.analyze_histogram).pack(fill=tk.X, pady=2)
        ttk.Button(analysis_frame, text="🎨 Цветовая палитра", command=self.analyze_colors).pack(fill=tk.X, pady=2)
        ttk.Button(analysis_frame, text="🔍 Детекция краёв", command=self.analyze_edges).pack(fill=tk.X, pady=2)
        ttk.Button(analysis_frame, text="📐 Качество", command=self.analyze_quality).pack(fill=tk.X, pady=2)
        ttk.Button(analysis_frame, text="🧬 Сравнить", command=self.compare_images).pack(fill=tk.X, pady=2)
        
        results_frame = ttk.LabelFrame(tab, text="📋 Результаты")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.analysis_text = scrolledtext.ScrolledText(results_frame, height=12, width=30)
        self.analysis_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def setup_history_tab(self, notebook):
        """Вкладка История"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⏳ История")
        
        self.history_listbox = tk.Listbox(tab, height=14)
        self.history_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.history_listbox.bind('<<ListboxSelect>>', self.on_history_select)
        
        hist_btns = ttk.Frame(tab)
        hist_btns.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(hist_btns, text="↩ Отменить", command=self.undo).pack(side=tk.LEFT, padx=2)
        ttk.Button(hist_btns, text="↪ Повторить", command=self.redo).pack(side=tk.LEFT, padx=2)
        ttk.Button(hist_btns, text="🧹 Очистить", command=self.clear_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(hist_btns, text="📸 Снимок", command=self.take_snapshot).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(tab, text=f"Всего шагов: ", font=("Arial", 8)).pack(pady=2)
        self.history_count_label = ttk.Label(tab, text="0")
        self.history_count_label.pack(pady=2)
    
    def setup_settings_tab(self, notebook):
        """Вкладка Настройки"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⚙️ Настройки")
        
        # === ОБЩИЕ ===
        general_frame = ttk.LabelFrame(tab, text="Общие")
        general_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(general_frame, text="Язык:").pack(anchor=tk.W, padx=5, pady=2)
        lang_frame = ttk.Frame(general_frame)
        lang_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(lang_frame, text="🇷🇺 Русский", command=lambda: self.set_language('ru')).pack(side=tk.LEFT, padx=2)
        ttk.Button(lang_frame, text="🇬🇧 English", command=lambda: self.set_language('en')).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(general_frame, text="Тема:").pack(anchor=tk.W, padx=5, pady=2)
        theme_frame = ttk.Frame(general_frame)
        theme_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(theme_frame, text="🌙 Тёмная", command=lambda: self.set_theme('dark')).pack(side=tk.LEFT, padx=2)
        ttk.Button(theme_frame, text="☀️ Светлая", command=lambda: self.set_theme('light')).pack(side=tk.LEFT, padx=2)
        
        ttk.Checkbutton(general_frame, text="Показывать подсказки", 
                       variable=self.show_tooltips,
                       command=self.toggle_tooltips).pack(anchor=tk.W, padx=5, pady=2)
        
        # === СОХРАНЕНИЕ ===
        save_frame = ttk.LabelFrame(tab, text="Сохранение")
        save_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.auto_save_var = tk.BooleanVar(value=self.auto_save_enabled)
        ttk.Checkbutton(save_frame, text="Автосохранение", 
                       variable=self.auto_save_var,
                       command=self.toggle_auto_save).pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(save_frame, text="Интервал (сек):").pack(anchor=tk.W, padx=5, pady=2)
        self.interval_entry = ttk.Entry(save_frame, width=10)
        self.interval_entry.insert(0, str(self.auto_save_interval))
        self.interval_entry.pack(anchor=tk.W, padx=5, pady=2)
        ttk.Button(save_frame, text="Обновить интервал", 
                  command=self.update_interval).pack(fill=tk.X, padx=5, pady=2)
        
        # === ОБНОВЛЕНИЯ ===
        update_frame = ttk.LabelFrame(tab, text="Обновления")
        update_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.check_updates_var = tk.BooleanVar(value=self.config.get('check_updates', True))
        ttk.Checkbutton(update_frame, text="Проверять обновления при запуске", 
                       variable=self.check_updates_var,
                       command=self.toggle_update_check).pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(update_frame, text=f"Текущая версия: {self.version}").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Button(update_frame, text="🔄 Проверить обновления сейчас", 
                  command=self.check_updates_manual).pack(fill=tk.X, padx=5, pady=2)
        
        # === ПРОГРАММА ===
        info_frame = ttk.LabelFrame(tab, text="О программе")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(info_frame, text=f"Редактор Фона Ultimate v{self.version}").pack(pady=5)
        
        status_text = "✅ ИИ доступен" if self.has_ai else "⚠️ ИИ не доступен"
        ttk.Label(info_frame, text=f"Статус: {status_text}").pack(pady=2)
        
        ttk.Button(info_frame, text="📖 О программе", command=self.show_about).pack(fill=tk.X, padx=5, pady=5)
    
    def setup_preview(self, container):
        """Область предпросмотра"""
        # Панель инструментов
        toolbar = ttk.Frame(container)
        toolbar.pack(fill=tk.X, pady=2)
        
        ttk.Button(toolbar, text="🔍 +", command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔍 -", command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⟳", command=self.reset_view, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⬡", command=self.toggle_grid, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✚", command=self.fit_to_window, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📐", command=self.toggle_rules, width=3).pack(side=tk.LEFT, padx=2)
        
        self.zoom_label = ttk.Label(toolbar, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=10)
        
        # Холст
        canvas_frame = ttk.Frame(container)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#2b2b2b', highlightthickness=1,
                               highlightbackground='#555', cursor='cross')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Скроллы
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Информация
        info_frame = ttk.Frame(container)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.info_label = ttk.Label(info_frame, text="✅ Готов к работе")
        self.info_label.pack(side=tk.LEFT)
        
        self.coord_label = ttk.Label(info_frame, text="X: 0 Y: 0")
        self.coord_label.pack(side=tk.RIGHT)
        
        self.size_label = ttk.Label(info_frame, text="")
        self.size_label.pack(side=tk.RIGHT, padx=10)
        
        # События
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        
        self.drag_objects = []
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
        self.resize_mode = False
        self.resize_handle = None
    
    def setup_properties_panel(self, container):
        """Панель свойств"""
        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # === СВОЙСТВА ===
        props_tab = ttk.Frame(notebook)
        notebook.add(props_tab, text="📐 Свойства")
        
        # Позиция
        pos_frame = ttk.LabelFrame(props_tab, text="📍 Позиция")
        pos_frame.pack(fill=tk.X, padx=5, pady=5)
        
        coord_grid = ttk.Frame(pos_frame)
        coord_grid.pack(fill=tk.X, pady=2)
        ttk.Label(coord_grid, text="X:").pack(side=tk.LEFT)
        self.x_entry = ttk.Entry(coord_grid, width=10)
        self.x_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(coord_grid, text="Y:").pack(side=tk.LEFT, padx=5)
        self.y_entry = ttk.Entry(coord_grid, width=10)
        self.y_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(coord_grid, text="Прим", command=self.apply_position, width=5).pack(side=tk.LEFT, padx=2)
        
        # Размер
        size_frame = ttk.LabelFrame(props_tab, text="📏 Размер")
        size_frame.pack(fill=tk.X, padx=5, pady=5)
        
        size_grid = ttk.Frame(size_frame)
        size_grid.pack(fill=tk.X, pady=2)
        ttk.Label(size_grid, text="Ш:").pack(side=tk.LEFT)
        self.width_entry = ttk.Entry(size_grid, width=10)
        self.width_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(size_grid, text="В:").pack(side=tk.LEFT, padx=5)
        self.height_entry = ttk.Entry(size_grid, width=10)
        self.height_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(size_grid, text="Прим", command=self.apply_size, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(size_frame, text="🔒 Сохранить пропорции", 
                  command=self.lock_aspect).pack(fill=tk.X, pady=2)
        
        # Поворот
        rot_frame = ttk.LabelFrame(props_tab, text="🔄 Поворот")
        rot_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.angle_scale = ttk.Scale(rot_frame, from_=0, to=360, orient=tk.HORIZONTAL,
                                     command=self.apply_angle)
        self.angle_scale.pack(fill=tk.X, padx=5, pady=2)
        self.angle_label = ttk.Label(rot_frame, text="0°")
        self.angle_label.pack(pady=2)
        
        angle_btns = ttk.Frame(rot_frame)
        angle_btns.pack(fill=tk.X, pady=2)
        for angle in [0, 90, 180, 270]:
            ttk.Button(angle_btns, text=f"{angle}°", width=5,
                      command=lambda a=angle: self.set_angle(a)).pack(side=tk.LEFT, padx=2)
        
        # Прозрачность
        opacity_frame = ttk.LabelFrame(props_tab, text="👁 Прозрачность")
        opacity_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.opacity_scale = ttk.Scale(opacity_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                       command=self.apply_opacity)
        self.opacity_scale.pack(fill=tk.X, padx=5, pady=2)
        self.opacity_label = ttk.Label(opacity_frame, text="100%")
        self.opacity_label.pack(pady=2)
        
        # Отражение
        mirror_frame = ttk.LabelFrame(props_tab, text="🔄 Отражение")
        mirror_frame.pack(fill=tk.X, padx=5, pady=5)
        
        mirror_btns = ttk.Frame(mirror_frame)
        mirror_btns.pack(fill=tk.X, pady=2)
        ttk.Button(mirror_btns, text="↔ X", width=8,
                  command=lambda: self.apply_mirror('x')).pack(side=tk.LEFT, padx=2)
        ttk.Button(mirror_btns, text="↕ Y", width=8,
                  command=lambda: self.apply_mirror('y')).pack(side=tk.LEFT, padx=2)
        ttk.Button(mirror_btns, text="🔄 Both", width=8,
                  command=lambda: self.apply_mirror('both')).pack(side=tk.LEFT, padx=2)
    
    def setup_menu(self):
        """Главное меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 Файл", menu=file_menu)
        file_menu.add_command(label="📄 Новый проект", command=self.new_project, accelerator="Ctrl+N")
        file_menu.add_command(label="📂 Открыть", command=self.open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="💾 Сохранить", command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="💾 Сохранить как", command=self.save_project_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="📤 Экспорт", command=self.export_dialog, accelerator="Ctrl+E")
        file_menu.add_command(label="📥 Импорт", command=self.import_file, accelerator="Ctrl+I")
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Выход", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Правка
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="✏️ Правка", menu=edit_menu)
        edit_menu.add_command(label="↩ Отмена", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="↪ Повтор", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="✂️ Вырезать", command=self.cut_objects, accelerator="Ctrl+X")
        edit_menu.add_command(label="📋 Копировать", command=self.copy_objects, accelerator="Ctrl+C")
        edit_menu.add_command(label="📋 Вставить", command=self.paste_objects, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="🎯 Выделить всё", command=self.select_all, accelerator="Ctrl+A")
        edit_menu.add_command(label="❌ Снять выделение", command=self.deselect_all, accelerator="Esc")
        
        # Вид
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁 Вид", menu=view_menu)
        view_menu.add_command(label="🔍 Увеличить", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="🔍 Уменьшить", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="⟳ Сбросить вид", command=self.reset_view)
        view_menu.add_separator()
        view_menu.add_command(label="⬡ Сетка", command=self.toggle_grid)
        view_menu.add_command(label="📐 Правило третей", command=self.toggle_rules)
        view_menu.add_command(label="📐 Маркеры ресайза", command=self.toggle_resize_handles)
        
        # Обновление
        update_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🔄 Обновление", menu=update_menu)
        update_menu.add_command(label="🔄 Проверить обновления", command=self.check_updates_manual)
        update_menu.add_command(label="⚙️ Настройки обновлений", command=self.update_settings)
        
        # Помощь
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Помощь", menu=help_menu)
        help_menu.add_command(label="📖 Справка", command=self.show_help)
        help_menu.add_command(label="⌨️ Горячие клавиши", command=self.show_hotkeys)
        help_menu.add_command(label="ℹ️ О программе", command=self.show_about)
    
    def setup_hotkeys(self):
        """Горячие клавиши"""
        self.root.bind('<Control-n>', lambda e: self.new_project())
        self.root.bind('<Control-o>', lambda e: self.open_project())
        self.root.bind('<Control-s>', lambda e: self.save_project())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_project_as())
        self.root.bind('<Control-e>', lambda e: self.export_dialog())
        self.root.bind('<Control-i>', lambda e: self.import_file())
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Control-x>', lambda e: self.cut_objects())
        self.root.bind('<Control-c>', lambda e: self.copy_objects())
        self.root.bind('<Control-v>', lambda e: self.paste_objects())
        self.root.bind('<Control-plus>', lambda e: self.zoom_in())
        self.root.bind('<Control-minus>', lambda e: self.zoom_out())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<Delete>', lambda e: self.delete_objects())
        self.root.bind('<Escape>', lambda e: self.deselect_all())
        self.root.bind('<F2>', lambda e: self.rename_layer())
        self.root.bind('<Tab>', lambda e: self.select_next_object())
        self.root.bind('<Shift-Tab>', lambda e: self.select_prev_object())
    
    def setup_tooltips(self):
        """Подсказки"""
        self.tooltips = {}
    
    def setup_drag_drop(self):
        """Drag & Drop"""
        try:
            self.root.tk.call('package', 'require', 'tkdnd')
            self.root.drop_target_register('DND_Files')
            self.root.dnd_bind('<<Drop>>', self.on_drop)
        except:
            pass
    
    # === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    
    def get_layer_objects(self, layer_index):
        """Получить объекты слоя"""
        if layer_index < len(self.layers):
            return self.layers[layer_index]['objects']
        return []
    
    def add_to_history(self, action_name):
        """Добавить действие в историю"""
        state = self.get_current_state()
        
        self.history = self.history[:self.history_index + 1]
        
        snapshot = {
            'name': action_name,
            'time': datetime.now().isoformat(),
            'state': state
        }
        
        self.history.append(snapshot)
        self.history_index += 1
        
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1
        
        self.update_history_list()
        self.history_count_label.config(text=f"{len(self.history)}")
    
    def get_current_state(self):
        """Получить текущее состояние"""
        return {
            'objects': copy.deepcopy(self.objects),
            'layers': copy.deepcopy(self.layers),
            'background': self.current_background.copy() if self.current_background else None,
            'selected': [self.objects.index(obj) for obj in self.selected_objects if obj in self.objects]
        }
    
    def restore_state(self, state):
        """Восстановить состояние"""
        self.objects = copy.deepcopy(state['objects'])
        self.layers = copy.deepcopy(state['layers'])
        if state['background']:
            self.current_background = state['background'].copy()
        self.selected_objects = [self.objects[i] for i in state['selected'] if i < len(self.objects)]
        
        self.update_layer_list()
        self.update_preview()
        self.update_properties_panel()
    
    def update_layer_list(self):
        """Обновить список слоёв"""
        self.layer_listbox.delete(0, tk.END)
        for i, layer in enumerate(reversed(self.layers)):
            visible = "👁" if layer['visible'] else "👁‍🗨"
            name = layer['name']
            count = len(layer['objects'])
            blend = f" [{layer.get('blend_mode', 'normal')}]" if layer.get('blend_mode') != 'normal' else ""
            self.layer_listbox.insert(tk.END, f"{visible} {name}{blend} ({count})")
            if i == len(self.layers) - 1 - self.current_layer_index:
                self.layer_listbox.selection_set(i)
    
    def update_history_list(self):
        """Обновить список истории"""
        self.history_listbox.delete(0, tk.END)
        for i, item in enumerate(self.history):
            prefix = "▶ " if i == self.history_index else "  "
            self.history_listbox.insert(tk.END, f"{prefix}{item['name']}")
            if i == self.history_index:
                self.history_listbox.selection_set(i)
    
    def update_properties_panel(self):
        """Обновить панель свойств"""
        if self.selected_objects:
            obj = self.selected_objects[0]
            self.x_entry.delete(0, tk.END)
            self.x_entry.insert(0, str(int(obj['x'])))
            self.y_entry.delete(0, tk.END)
            self.y_entry.insert(0, str(int(obj['y'])))
            self.width_entry.delete(0, tk.END)
            self.width_entry.insert(0, str(obj['width']))
            self.height_entry.delete(0, tk.END)
            self.height_entry.insert(0, str(obj['height']))
            self.angle_scale.set(obj['angle'])
            self.angle_label.config(text=f"{int(obj['angle'])}°")
            self.opacity_scale.set(obj['opacity'])
            self.opacity_label.config(text=f"{int(obj['opacity'])}%")
    
    def update_custom_preset_list(self):
        """Обновить список пользовательских пресетов"""
        self.custom_preset_list.delete(0, tk.END)
        for name in self.custom_presets.keys():
            self.custom_preset_list.insert(tk.END, name)
    
    def apply_theme(self):
        """Применить тему"""
        if self.config.get('theme', 'dark') == 'dark':
            self.root.configure(bg='#2b2b2b')
            self.canvas.configure(bg='#2b2b2b')
        else:
            self.root.configure(bg='#f0f0f0')
            self.canvas.configure(bg='#f0f0f0')
    
    def set_theme(self, theme):
        """Установить тему"""
        self.config['theme'] = theme
        self.apply_theme()
        self.info_label.config(text=f"✅ Тема: {theme}")
    
    def set_language(self, lang):
        """Установить язык"""
        self.current_language = lang
        self.info_label.config(text=f"✅ Язык: {lang}")
    
    def toggle_tooltips(self):
        """Переключить подсказки"""
        pass
    
    def toggle_auto_save(self):
        """Переключить автосохранение"""
        self.auto_save_enabled = self.auto_save_var.get()
        self.info_label.config(text=f"✅ Автосохранение: {'Вкл' if self.auto_save_enabled else 'Выкл'}")
    
    def update_interval(self):
        """Обновить интервал автосохранения"""
        try:
            interval = int(self.interval_entry.get())
            self.auto_save_interval = interval
            self.info_label.config(text=f"✅ Интервал: {interval} сек")
        except:
            pass
    
    def toggle_update_check(self):
        """Переключить проверку обновлений"""
        self.config['check_updates'] = self.check_updates_var.get()
    
    # === ОБНОВЛЕНИЯ ===
    
    def check_updates_auto(self):
        """Автоматическая проверка обновлений"""
        if not self.config.get('check_updates', True):
            return
        
        try:
            has_update, version, url = self.updater.check_for_updates()
            if has_update:
                if messagebox.askyesno("🔄 Обновление", 
                    f"Доступна новая версия {version}!\n\n"
                    f"Текущая: {self.version}\n"
                    f"Новая: {version}\n\n"
                    "Скачать обновление?"):
                    self.download_update(url)
        except:
            pass
    
    def check_updates_manual(self):
        """Ручная проверка обновлений"""
        self.info_label.config(text="🔄 Проверка обновлений...")
        
        def check():
            try:
                has_update, version, url = self.updater.check_for_updates()
                if has_update:
                    self.root.after(0, lambda: messagebox.askyesno("🔄 Обновление",
                        f"Доступна новая версия {version}!\n\nОбновить?"))
                    self.root.after(0, lambda: self.info_label.config(text="✅ Обновление доступно!"))
                else:
                    self.root.after(0, lambda: self.info_label.config(text="✅ Обновлений нет"))
            except Exception as e:
                self.root.after(0, lambda: self.info_label.config(text=f"⚠️ {str(e)}"))
        
        threading.Thread(target=check, daemon=True).start()
    
    def download_update(self, url):
        """Скачать обновление"""
        self.info_label.config(text="📥 Скачивание...")
        
        def download():
            new_exe, error = self.updater.download_update(url)
            if new_exe:
                self.root.after(0, lambda: self.apply_update(new_exe))
            else:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", error))
                self.root.after(0, lambda: self.info_label.config(text="⚠️ Ошибка скачивания"))
        
        threading.Thread(target=download, daemon=True).start()
    
    def apply_update(self, new_exe):
        """Применить обновление"""
        success, msg = self.updater.apply_update(new_exe)
        if success:
            messagebox.showinfo("✅ Обновление", "Программа перезапустится")
            self.root.quit()
        else:
            messagebox.showerror("Ошибка", msg)
    
    def update_settings(self):
        """Настройки обновлений"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки обновлений")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text=f"Текущая версия: {self.version}", font=("Arial", 10)).pack(pady=10)
        
        check_var = tk.BooleanVar(value=self.config.get('check_updates', True))
        ttk.Checkbutton(dialog, text="Проверять при запуске", 
                       variable=check_var,
                       command=lambda: self.config.update({'check_updates': check_var.get()})).pack(pady=5)
        
        ttk.Button(dialog, text="🔄 Проверить сейчас", 
                  command=lambda: [dialog.destroy(), self.check_updates_manual()]).pack(pady=10)
        
        ttk.Button(dialog, text="Закрыть", command=dialog.destroy).pack(pady=5)
    
    # === ОСНОВНЫЕ ФУНКЦИИ ===
    
    def add_background(self):
        """Добавить фон"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )
        if file_path:
            try:
                img = Image.open(file_path)
                self.backgrounds.append(img)
                self.current_bg_index = len(self.backgrounds) - 1
                self.current_background = img.copy()
                self.update_preview()
                self.add_to_history("Добавлен фон")
                self.info_label.config(text=f"✅ Фон добавлен: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
    
    def add_object(self):
        """Добавить объект"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )
        if file_path:
            try:
                img = Image.open(file_path)
                obj = {
                    'image': img,
                    'x': 100 + len(self.objects) * 20,
                    'y': 100 + len(self.objects) * 20,
                    'width': img.width,
                    'height': img.height,
                    'angle': 0,
                    'opacity': 100,
                    'mirror_x': False,
                    'mirror_y': False,
                    'path': file_path,
                    'layer': self.current_layer_index
                }
                self.objects.append(obj)
                if self.current_layer_index < len(self.layers):
                    self.layers[self.current_layer_index]['objects'].append(obj)
                self.selected_objects = [obj]
                self.update_preview()
                self.add_to_history("Добавлен объект")
                self.info_label.config(text=f"✅ Объект добавлен: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
    
    def add_layer(self):
        """Добавить слой"""
        name = f"Слой {len(self.layers) + 1}"
        layer = {
            'name': name,
            'visible': True,
            'opacity': 100,
            'blend_mode': 'normal',
            'objects': []
        }
        self.layers.append(layer)
        self.current_layer_index = len(self.layers) - 1
        self.update_layer_list()
        self.add_to_history("Добавлен слой")
        self.info_label.config(text=f"✅ Добавлен слой: {name}")
    
    def delete_layer(self):
        """Удалить слой"""
        if len(self.layers) <= 1:
            messagebox.showwarning("Предупреждение", "Нельзя удалить последний слой")
            return
        
        selected = self.layer_listbox.curselection()
        if selected:
            index = len(self.layers) - 1 - selected[0]
            if messagebox.askyesno("Удаление", f"Удалить слой '{self.layers[index]['name']}'?"):
                for obj in self.layers[index]['objects']:
                    if obj in self.objects:
                        self.objects.remove(obj)
                del self.layers[index]
                if self.current_layer_index >= len(self.layers):
                    self.current_layer_index = len(self.layers) - 1
                self.update_layer_list()
                self.update_preview()
                self.add_to_history("Удалён слой")
    
    def on_layer_select(self, event):
        """Выбор слоя"""
        selected = self.layer_listbox.curselection()
        if selected:
            self.current_layer_index = len(self.layers) - 1 - selected[0]
            layer = self.layers[self.current_layer_index]
            self.layer_name_entry.delete(0, tk.END)
            self.layer_name_entry.insert(0, layer['name'])
            self.layer_opacity_scale.set(layer['opacity'])
            self.layer_opacity_label.config(text=f"{int(layer['opacity'])}%")
            self.layer_visible_var.set(layer['visible'])
            self.blend_mode_var.set(layer.get('blend_mode', 'normal'))
            self.selected_objects = layer['objects'].copy()
            self.update_properties_panel()
            self.update_preview()
    
    def rename_layer(self):
        """Переименовать слой"""
        name = self.layer_name_entry.get()
        if name and self.current_layer_index < len(self.layers):
            self.layers[self.current_layer_index]['name'] = name
            self.update_layer_list()
            self.info_label.config(text=f"✅ Слой переименован: {name}")
    
    def change_layer_opacity(self, value):
        """Изменить прозрачность слоя"""
        opacity = float(value)
        self.layer_opacity_label.config(text=f"{int(opacity)}%")
        if self.current_layer_index < len(self.layers):
            self.layers[self.current_layer_index]['opacity'] = opacity
            self.update_preview()
    
    def toggle_layer_visibility(self):
        """Переключить видимость слоя"""
        if self.current_layer_index < len(self.layers):
            self.layers[self.current_layer_index]['visible'] = self.layer_visible_var.get()
            self.update_layer_list()
            self.update_preview()
    
    def change_blend_mode(self, event):
        """Изменить режим наложения"""
        if self.current_layer_index < len(self.layers):
            self.layers[self.current_layer_index]['blend_mode'] = self.blend_mode_var.get()
            self.update_layer_list()
            self.update_preview()
            self.add_to_history("Изменён режим наложения")
    
    def layer_up(self):
        """Поднять слой"""
        if self.current_layer_index < len(self.layers) - 1:
            self.layers[self.current_layer_index], self.layers[self.current_layer_index + 1] = \
                self.layers[self.current_layer_index + 1], self.layers[self.current_layer_index]
            self.current_layer_index += 1
            self.update_layer_list()
            self.update_preview()
            self.add_to_history("Слой поднят")
    
    def layer_down(self):
        """Опустить слой"""
        if self.current_layer_index > 0:
            self.layers[self.current_layer_index], self.layers[self.current_layer_index - 1] = \
                self.layers[self.current_layer_index - 1], self.layers[self.current_layer_index]
            self.current_layer_index -= 1
            self.update_layer_list()
            self.update_preview()
            self.add_to_history("Слой опущен")
    
    def merge_layers(self):
        """Объединить слои"""
        if len(self.layers) <= 1:
            return
        if self.current_layer_index < len(self.layers) - 1:
            layer1 = self.layers[self.current_layer_index]
            layer2 = self.layers[self.current_layer_index + 1]
            layer1['objects'].extend(layer2['objects'])
            del self.layers[self.current_layer_index + 1]
            self.update_layer_list()
            self.update_preview()
            self.add_to_history("Слои объединены")
            self.info_label.config(text="✅ Слои объединены")
    
    # === ПРЕДПРОСМОТР ===
    
    def update_preview(self):
        """Обновить предпросмотр"""
        self.canvas.delete("all")
        
        if self.current_background is None:
            self.canvas.create_text(400, 300, 
                text="📂 Добавьте фон или перетащите файлы",
                fill="white", font=("Arial", 16))
            return
        
        try:
            img = self.current_background.copy()
            
            # Рендерим слои
            for layer in self.layers:
                if not layer['visible']:
                    continue
                layer_img = self.render_layer(layer)
                if layer_img:
                    img = Image.alpha_composite(img.convert('RGBA'), layer_img)
            
            # Размеры холста
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width < 10 or canvas_height < 10:
                canvas_width = 800
                canvas_height = 600
            
            # Масштабирование
            img_ratio = img.width / img.height
            canvas_ratio = canvas_width / canvas_height
            
            if img_ratio > canvas_ratio:
                display_width = canvas_width - 20
                display_height = int(display_width / img_ratio)
            else:
                display_height = canvas_height - 20
                display_width = int(display_height * img_ratio)
            
            display_width = int(display_width * self.zoom_level)
            display_height = int(display_height * self.zoom_level)
            
            # Ресайз
            img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img_resized)
            
            # Центрирование
            x_offset = (canvas_width - display_width) // 2
            y_offset = (canvas_height - display_height) // 2
            
            self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.photo)
            
            # Выделение объектов
            for obj in self.selected_objects:
                self.draw_selection(obj, x_offset, y_offset, display_width, display_height, img.width, img.height)
            
            # Сетка
            if self.grid_visible:
                self.draw_grid(canvas_width, canvas_height)
            
            # Правило третей
            if self.rules_visible:
                self.draw_rules(canvas_width, canvas_height)
            
            # Обновление информации о размере
            self.size_label.config(text=f"{img.width}x{img.height}")
            
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            print(f"Preview error: {e}")
    
    def render_layer(self, layer):
        """Рендеринг слоя"""
        if not layer['objects']:
            return None
        
        layer_img = Image.new('RGBA', self.current_background.size, (0,0,0,0))
        
        for obj in layer['objects']:
            obj_img = self.render_object(obj)
            if obj_img:
                x = int(obj['x'])
                y = int(obj['y'])
                layer_img.paste(obj_img, (x, y), obj_img)
        
        if layer['opacity'] < 100:
            alpha = layer_img.split()[3]
            alpha = alpha.point(lambda p: int(p * layer['opacity'] / 100))
            layer_img.putalpha(alpha)
        
        return layer_img
    
    def render_object(self, obj):
        """Рендеринг объекта"""
        img = obj['image'].copy()
        
        if obj['opacity'] < 100:
            img = img.convert('RGBA')
            alpha = img.split()[3]
            alpha = alpha.point(lambda p: int(p * obj['opacity'] / 100))
            img.putalpha(alpha)
        
        if obj['angle'] != 0:
            img = img.rotate(obj['angle'], expand=True)
        
        if obj.get('mirror_x', False):
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if obj.get('mirror_y', False):
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        
        return img
    
    def draw_selection(self, obj, x_offset, y_offset, display_width, display_height, img_width, img_height):
        """Рисование выделения объекта"""
        x = obj['x']
        y = obj['y']
        w = obj['width']
        h = obj['height']
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        x1 = x_offset + x * scale_x - 2
        y1 = y_offset + y * scale_y - 2
        x2 = x_offset + (x + w) * scale_x + 2
        y2 = y_offset + (y + h) * scale_y + 2
        
        self.canvas.create_rectangle(x1, y1, x2, y2, outline='cyan', width=2, dash=(4, 4))
        
        if self.resize_handles_var.get():
            size = 7
            handles = [(x1, y1, 'nw'), (x2, y1, 'ne'), (x1, y2, 'sw'), (x2, y2, 'se'),
                      ((x1+x2)/2, y1, 'n'), ((x1+x2)/2, y2, 's'), (x1, (y1+y2)/2, 'w'), (x2, (y1+y2)/2, 'e')]
            for hx, hy, _ in handles:
                self.canvas.create_rectangle(hx - size//2, hy - size//2,
                                            hx + size//2, hy + size//2,
                                            fill='white', outline='cyan', width=1.5)
    
    def draw_grid(self, width, height):
        """Рисование сетки"""
        step = 50
        for x in range(0, width, step):
            self.canvas.create_line(x, 0, x, height, fill='#444', tags="grid")
        for y in range(0, height, step):
            self.canvas.create_line(0, y, width, y, fill='#444', tags="grid")
    
    def draw_rules(self, width, height):
        """Рисование правила третей"""
        x1 = width / 3
        x2 = width * 2 / 3
        y1 = height / 3
        y2 = height * 2 / 3
        
        self.canvas.create_line(x1, 0, x1, height, fill='white', dash=(5, 5), tags="rules")
        self.canvas.create_line(x2, 0, x2, height, fill='white', dash=(5, 5), tags="rules")
        self.canvas.create_line(0, y1, width, y1, fill='white', dash=(5, 5), tags="rules")
        self.canvas.create_line(0, y2, width, y2, fill='white', dash=(5, 5), tags="rules")
        
        for px, py in [(x1, y1), (x1, y2), (x2, y1), (x2, y2)]:
            self.canvas.create_oval(px-5, py-5, px+5, py+5, fill='red', outline='red', tags="rules")
    
    def toggle_grid(self):
        """Переключить сетку"""
        self.grid_visible = not self.grid_visible
        self.update_preview()
    
    def toggle_rules(self):
        """Переключить правило третей"""
        self.rules_visible = not self.rules_visible
        self.update_preview()
    
    def toggle_resize_handles(self):
        """Переключить маркеры ресайза"""
        self.update_preview()
    
    def fit_to_window(self):
        """Подогнать под окно"""
        self.zoom_level = 1.0
        self.update_preview()
    
    # === МАСШТАБ ===
    
    def zoom_in(self):
        self.zoom_level *= 1.1
        if self.zoom_level > 5.0:
            self.zoom_level = 5.0
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        self.update_preview()
    
    def zoom_out(self):
        self.zoom_level /= 1.1
        if self.zoom_level < 0.1:
            self.zoom_level = 0.1
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        self.update_preview()
    
    def reset_view(self):
        self.zoom_level = 1.0
        self.zoom_label.config(text="100%")
        self.update_preview()
    
    # === ОБРАБОТКА СОБЫТИЙ ===
    
    def on_mouse_down(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.drag_objects = []
        self.is_dragging = False
        
        # Проверка попадания в объекты
        canvas_coords = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        for obj in reversed(self.objects):
            x, y = obj['x'], obj['y']
            w, h = obj['width'], obj['height']
            
            scale = self.zoom_level
            x1 = x * scale
            y1 = y * scale
            x2 = (x + w) * scale
            y2 = (y + h) * scale
            
            if x1 <= canvas_coords[0] <= x2 and y1 <= canvas_coords[1] <= y2:
                if event.state & 0x0001:  # Shift
                    if obj not in self.selected_objects:
                        self.selected_objects.append(obj)
                else:
                    self.selected_objects = [obj]
                self.drag_objects = self.selected_objects.copy()
                self.update_preview()
                self.update_properties_panel()
                return
        
        if not (event.state & 0x0001):
            self.selected_objects = []
            self.update_preview()
            self.update_properties_panel()
    
    def on_mouse_drag(self, event):
        if self.drag_objects:
            self.is_dragging = True
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            
            scale = self.zoom_level
            dx = dx / scale
            dy = dy / scale
            
            for obj in self.drag_objects:
                obj['x'] += dx
                obj['y'] += dy
            
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.update_preview()
    
    def on_mouse_up(self, event):
        if self.drag_objects and self.is_dragging:
            self.add_to_history("Перемещение объектов")
            self.drag_objects = []
            self.is_dragging = False
    
    def on_mouse_move(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.coord_label.config(text=f"X: {int(x)} Y: {int(y)}")
    
    def on_mouse_wheel(self, event):
        if event.state & 0x0004:  # Ctrl
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            if event.delta > 0:
                self.canvas.yview_scroll(-1, "units")
            else:
                self.canvas.yview_scroll(1, "units")
    
    def on_double_click(self, event):
        """Двойной клик - сброс выделения"""
        self.deselect_all()
        self.info_label.config(text="✅ Выделение снято")
    
    def on_drop(self, event):
        """Drop файлов"""
        files = self.root.tk.splitlist(event.data)
        for file_path in files:
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                self.add_object_from_path(file_path)
        self.info_label.config(text=f"✅ Загружено: {len(files)}")
    
    def add_object_from_path(self, file_path):
        """Добавить объект из пути"""
        try:
            img = Image.open(file_path)
            obj = {
                'image': img,
                'x': 100 + len(self.objects) * 20,
                'y': 100 + len(self.objects) * 20,
                'width': img.width,
                'height': img.height,
                'angle': 0,
                'opacity': 100,
                'mirror_x': False,
                'mirror_y': False,
                'path': file_path,
                'layer': self.current_layer_index
            }
            self.objects.append(obj)
            if self.current_layer_index < len(self.layers):
                self.layers[self.current_layer_index]['objects'].append(obj)
            self.selected_objects = [obj]
            self.update_preview()
            self.add_to_history("Добавлен объект")
            self.info_label.config(text=f"✅ Объект добавлен: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    # === ПРЕДЫДУЩИЙ/СЛЕДУЮЩИЙ ФОН ===
    
    def next_background(self):
        if self.backgrounds:
            self.current_bg_index = (self.current_bg_index + 1) % len(self.backgrounds)
            self.current_background = self.backgrounds[self.current_bg_index].copy()
            self.update_preview()
    
    def prev_background(self):
        if self.backgrounds:
            self.current_bg_index = (self.current_bg_index - 1) % len(self.backgrounds)
            self.current_background = self.backgrounds[self.current_bg_index].copy()
            self.update_preview()
    
    def random_background(self):
        if self.backgrounds:
            idx = random.randint(0, len(self.backgrounds) - 1)
            self.current_bg_index = idx
            self.current_background = self.backgrounds[idx].copy()
            self.update_preview()
            self.info_label.config(text="🎲 Случайный фон выбран")
    
    # === УДАЛЕНИЕ ФОНА ===
    
    def remove_by_color(self):
        """Удаление фона по цвету"""
        if not self.current_background:
            return
        
        color = colorchooser.askcolor()[1]
        if color:
            try:
                import numpy as np
                img = self.current_background.convert('RGBA')
                data = np.array(img)
                
                target = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
                distance = np.linalg.norm(data[:,:,:3] - target, axis=2)
                mask = distance < 30
                data[mask] = [0, 0, 0, 0]
                result = Image.fromarray(data, 'RGBA')
                
                self.current_background = result
                self.update_preview()
                self.add_to_history("Удалён фон по цвету")
                self.info_label.config(text="✅ Фон удалён по цвету")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
    
    def remove_ai(self):
        """ИИ удаление фона"""
        if not self.current_background:
            messagebox.showinfo("Информация", "Нет изображения")
            return
        
        if not HAS_REMBG:
            messagebox.showinfo("Информация", "Установите: pip install rembg onnxruntime")
            return
        
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Обработка")
        progress_dialog.geometry("300x100")
        progress_dialog.transient(self.root)
        
        ttk.Label(progress_dialog, text="🤖 ИИ удаляет фон...").pack(pady=10)
        progress_bar = ttk.Progressbar(progress_dialog, orient=tk.HORIZONTAL, 
                                      length=250, mode='indeterminate')
        progress_bar.pack(pady=10)
        progress_bar.start()
        
        def process():
            try:
                from rembg import remove
                result = remove(self.current_background)
                self.root.after(0, lambda: self.finish_ai_remove(progress_dialog, result))
            except Exception as e:
                self.root.after(0, lambda: self.handle_ai_error(progress_dialog, str(e)))
        
        threading.Thread(target=process, daemon=True).start()
    
    def finish_ai_remove(self, dialog, result):
        dialog.destroy()
        self.current_background = result
        self.update_preview()
        self.add_to_history("ИИ удаление фона")
        self.info_label.config(text="✅ ИИ удалил фон")
    
    def handle_ai_error(self, dialog, error):
        dialog.destroy()
        messagebox.showerror("Ошибка", f"Не удалось удалить фон:\n{error}")
    
    def remove_edges(self):
        """Обрезка краёв"""
        if not self.current_background:
            return
        
        try:
            img = self.current_background.convert('RGBA')
            bbox = img.getbbox()
            if bbox:
                cropped = img.crop(bbox)
                self.current_background = cropped
                self.update_preview()
                self.add_to_history("Обрезка краёв")
                self.info_label.config(text="✅ Края обрезаны")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    # === ФИЛЬТРЫ ===
    
    def apply_filter(self, filter_type, value=1):
        if not self.selected_objects:
            messagebox.showinfo("Информация", "Выберите объекты")
            return
        
        for obj in self.selected_objects:
            img = obj['image'].copy()
            
            if filter_type == 'gaussian_blur':
                img = img.filter(ImageFilter.GaussianBlur(radius=float(value)))
            elif filter_type == 'smooth':
                img = img.filter(ImageFilter.SMOOTH_MORE)
            elif filter_type == 'sharpen':
                img = img.filter(ImageFilter.SHARPEN)
            elif filter_type == 'emboss':
                img = img.filter(ImageFilter.EMBOSS)
            elif filter_type == 'edge_blur':
                img = img.filter(ImageFilter.EDGE_ENHANCE)
                img = img.filter(ImageFilter.GaussianBlur(radius=1))
            
            obj['image'] = img
            obj['width'], obj['height'] = img.size
        
        self.update_preview()
        self.add_to_history(f"Фильтр: {filter_type}")
        self.info_label.config(text=f"✅ Фильтр применён")
    
    def apply_correction(self):
        if not self.selected_objects:
            return
        
        for obj in self.selected_objects:
            img = obj['image'].copy()
            
            brightness = float(self.brightness_scale.get())
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
            
            contrast = float(self.contrast_scale.get())
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
            
            saturation = float(self.saturation_scale.get())
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation)
            
            obj['image'] = img
            obj['width'], obj['height'] = img.size
        
        self.update_preview()
        self.add_to_history("Коррекция")
        self.info_label.config(text="✅ Коррекция применена")
    
    def apply_effect(self, effect_type):
        if not self.selected_objects:
            return
        
        for obj in self.selected_objects:
            img = obj['image'].copy()
            
            if effect_type == 'grayscale':
                img = ImageOps.grayscale(img)
                img = img.convert('RGBA')
            elif effect_type == 'sepia':
                img = self.apply_sepia(img)
            elif effect_type == 'invert':
                img = ImageOps.invert(img.convert('RGB'))
                img = img.convert('RGBA')
            elif effect_type == 'posterize':
                img = ImageOps.posterize(img, 4)
            elif effect_type == 'solarize':
                img = ImageOps.solarize(img, 128)
            elif effect_type == 'vignette':
                img = self.apply_vignette(img)
            elif effect_type == 'pixelate':
                small = img.resize((img.width // 10, img.height // 10), Image.Resampling.NEAREST)
                img = small.resize(img.size, Image.Resampling.NEAREST)
            
            obj['image'] = img
            obj['width'], obj['height'] = img.size
        
        self.update_preview()
        self.add_to_history(f"Эффект: {effect_type}")
        self.info_label.config(text=f"✅ Эффект применён")
    
    def apply_sepia(self, img):
        img = img.convert('RGB')
        width, height = img.size
        pixels = img.load()
        
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                pixels[x, y] = (min(255, tr), min(255, tg), min(255, tb))
        
        return img.convert('RGBA')
    
    def apply_vignette(self, img):
        img = img.convert('RGBA')
        width, height = img.size
        center_x, center_y = width // 2, height // 2
        max_radius = min(width, height) // 2
        
        pixels = img.load()
        for y in range(height):
            for x in range(width):
                dx = x - center_x
                dy = y - center_y
                distance = (dx ** 2 + dy ** 2) ** 0.5
                vignette = max(0, 1 - (distance / max_radius) ** 0.5)
                r, g, b, a = pixels[x, y]
                pixels[x, y] = (int(r * vignette), int(g * vignette), int(b * vignette), a)
        
        return img
    
    def apply_auto(self, filter_type):
        if not self.selected_objects:
            return
        
        for obj in self.selected_objects:
            img = obj['image'].copy()
            
            if filter_type == 'autocontrast':
                img = ImageOps.autocontrast(img)
            elif filter_type == 'white_balance':
                img = self.apply_white_balance(img)
            elif filter_type == 'detail_enhance' and HAS_CV2:
                import cv2
                import numpy as np
                arr = np.array(img)
                enhanced = cv2.detailEnhance(arr, sigma_s=10, sigma_r=0.15)
                img = Image.fromarray(enhanced)
            elif filter_type == 'denoise' and HAS_CV2:
                import cv2
                import numpy as np
                arr = np.array(img)
                denoised = cv2.fastNlMeansDenoisingColored(arr, None, 10, 10, 7, 21)
                img = Image.fromarray(denoised)
            
            obj['image'] = img
            obj['width'], obj['height'] = img.size
        
        self.update_preview()
        self.add_to_history(f"Автофильтр: {filter_type}")
        self.info_label.config(text=f"✅ Автофильтр применён")
    
    def apply_white_balance(self, img):
        img = img.convert('RGB')
        r, g, b = img.split()
        r_mean = r.getextrema()[1]
        g_mean = g.getextrema()[1]
        b_mean = b.getextrema()[1]
        avg = (r_mean + g_mean + b_mean) / 3
        r = r.point(lambda i: min(255, int(i * avg / r_mean)) if r_mean > 0 else i)
        g = g.point(lambda i: min(255, int(i * avg / g_mean)) if g_mean > 0 else i)
        b = b.point(lambda i: min(255, int(i * avg / b_mean)) if b_mean > 0 else i)
        return Image.merge('RGB', (r, g, b)).convert('RGBA')
    
    # === ПРЕСЕТЫ ===
    
    def preset_vintage(self):
        if self.selected_objects:
            self.apply_effect('sepia')
            self.apply_filter('gaussian_blur', 0.5)
            self.info_label.config(text="✅ Пресет: Vintage")
    
    def preset_cinematic(self):
        if self.selected_objects:
            self.brightness_scale.set(1.1)
            self.contrast_scale.set(1.2)
            self.apply_correction()
            self.apply_filter('sharpen')
            self.info_label.config(text="✅ Пресет: Cinematic")
    
    def preset_bw(self):
        if self.selected_objects:
            self.apply_effect('grayscale')
            self.info_label.config(text="✅ Пресет: Black & White")
    
    def preset_warm(self):
        if self.selected_objects:
            self.apply_effect('sepia')
            self.brightness_scale.set(1.1)
            self.apply_correction()
            self.info_label.config(text="✅ Пресет: Warm")
    
    def preset_cool(self):
        if self.selected_objects:
            self.brightness_scale.set(0.9)
            self.apply_correction()
            self.info_label.config(text="✅ Пресет: Cool")
    
    def preset_hdr(self):
        if self.selected_objects:
            self.contrast_scale.set(1.3)
            self.brightness_scale.set(1.1)
            self.apply_correction()
            self.apply_filter('sharpen')
            self.info_label.config(text="✅ Пресет: HDR")
    
    def preset_dramatic(self):
        if self.selected_objects:
            self.contrast_scale.set(1.5)
            self.brightness_scale.set(0.8)
            self.apply_correction()
            self.apply_effect('vignette')
            self.info_label.config(text="✅ Пресет: Dramatic")
    
    def preset_soft_glow(self):
        if self.selected_objects:
            self.apply_filter('gaussian_blur', 1.5)
            self.brightness_scale.set(1.1)
            self.apply_correction()
            self.info_label.config(text="✅ Пресет: Soft Glow")
    
    def preset_film_grain(self):
        if self.selected_objects:
            self.apply_filter('gaussian_blur', 0.3)
            self.info_label.config(text="✅ Пресет: Film Grain")
    
    def save_custom_preset(self):
        name = self.custom_preset_entry.get()
        if not name:
            messagebox.showinfo("Информация", "Введите название пресета")
            return
        
        state = self.get_current_state()
        self.custom_presets[name] = state
        self.update_custom_preset_list()
        self.custom_preset_entry.delete(0, tk.END)
        self.info_label.config(text=f"✅ Пресет сохранён: {name}")
    
    def apply_custom_preset(self):
        selected = self.custom_preset_list.curselection()
        if selected:
            name = self.custom_preset_list.get(selected[0])
            if name in self.custom_presets:
                self.restore_state(self.custom_presets[name])
                self.update_preview()
                self.info_label.config(text=f"✅ Пресет применён: {name}")
    
    def delete_custom_preset(self):
        selected = self.custom_preset_list.curselection()
        if selected:
            name = self.custom_preset_list.get(selected[0])
            if messagebox.askyesno("Удаление", f"Удалить пресет '{name}'?"):
                del self.custom_presets[name]
                self.update_custom_preset_list()
                self.info_label.config(text=f"✅ Пресет удалён: {name}")
    
    # === ОБЪЕКТЫ ===
    
    def select_all(self):
        self.selected_objects = self.objects.copy()
        self.update_preview()
        self.update_properties_panel()
        self.info_label.config(text=f"✅ Выделено: {len(self.selected_objects)}")
    
    def deselect_all(self):
        self.selected_objects = []
        self.update_preview()
        self.info_label.config(text="✅ Выделение снято")
    
    def select_next_object(self):
        if not self.objects:
            return
        if self.selected_objects:
            idx = self.objects.index(self.selected_objects[-1])
            idx = (idx + 1) % len(self.objects)
        else:
            idx = 0
        self.selected_objects = [self.objects[idx]]
        self.update_preview()
        self.update_properties_panel()
    
    def select_prev_object(self):
        if not self.objects:
            return
        if self.selected_objects:
            idx = self.objects.index(self.selected_objects[0])
            idx = (idx - 1) % len(self.objects)
        else:
            idx = len(self.objects) - 1
        self.selected_objects = [self.objects[idx]]
        self.update_preview()
        self.update_properties_panel()
    
    def duplicate_objects(self):
        if not self.selected_objects:
            return
        new_objects = []
        for obj in self.selected_objects:
            new_obj = copy.deepcopy(obj)
            new_obj['x'] += 30
            new_obj['y'] += 30
            self.objects.append(new_obj)
            layer_idx = obj.get('layer', 0)
            if layer_idx < len(self.layers):
                self.layers[layer_idx]['objects'].append(new_obj)
            new_objects.append(new_obj)
        self.selected_objects = new_objects
        self.update_preview()
        self.add_to_history("Дублирование объектов")
        self.update_layer_list()
        self.info_label.config(text=f"✅ Дублировано: {len(new_objects)}")
    
    def delete_objects(self):
        if not self.selected_objects:
            return
        if messagebox.askyesno("Удаление", f"Удалить {len(self.selected_objects)} объектов?"):
            for obj in self.selected_objects:
                if obj in self.objects:
                    self.objects.remove(obj)
                    layer_idx = obj.get('layer', 0)
                    if layer_idx < len(self.layers) and obj in self.layers[layer_idx]['objects']:
                        self.layers[layer_idx]['objects'].remove(obj)
            self.selected_objects = []
            self.update_preview()
            self.add_to_history("Удаление объектов")
            self.update_layer_list()
            self.info_label.config(text="✅ Объекты удалены")
    
    def align_objects(self):
        if len(self.selected_objects) < 2:
            messagebox.showinfo("Информация", "Выберите минимум 2 объекта")
            return
        
        avg_x = sum(obj['x'] for obj in self.selected_objects) / len(self.selected_objects)
        avg_y = sum(obj['y'] for obj in self.selected_objects) / len(self.selected_objects)
        
        for obj in self.selected_objects:
            obj['x'] = avg_x
            obj['y'] = avg_y
        
        self.update_preview()
        self.add_to_history("Выравнивание")
        self.info_label.config(text="✅ Объекты выровнены")
    
    def resize_dialog(self):
        if not self.selected_objects:
            messagebox.showinfo("Информация", "Выберите объекты")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Изменение размера")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Ширина:").pack(pady=5)
        w_entry = ttk.Entry(dialog)
        w_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Высота:").pack(pady=5)
        h_entry = ttk.Entry(dialog)
        h_entry.pack(pady=5)
        
        keep = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Сохранить пропорции", variable=keep).pack(pady=5)
        
        def apply():
            try:
                w = int(w_entry.get())
                h = int(h_entry.get())
                for obj in self.selected_objects:
                    obj['width'] = w
                    obj['height'] = h
                    obj['image'] = obj['image'].resize((w, h), Image.Resampling.LANCZOS)
                self.update_preview()
                self.add_to_history("Изменение размера")
                self.info_label.config(text=f"✅ Размер: {w}x{h}")
                dialog.destroy()
            except:
                messagebox.showerror("Ошибка", "Введите корректные размеры")
        
        ttk.Button(dialog, text="Применить", command=apply).pack(pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)
    
    def cut_objects(self):
        self.copy_objects()
        self.delete_objects()
        self.info_label.config(text="✂️ Объекты вырезаны")
    
    def copy_objects(self):
        if not self.selected_objects:
            return
        self.clipboard_objects = copy.deepcopy(self.selected_objects)
        self.info_label.config(text=f"📋 Скопировано: {len(self.clipboard_objects)}")
    
    def paste_objects(self):
        if not self.clipboard_objects:
            return
        new_objects = []
        for obj in self.clipboard_objects:
            new_obj = copy.deepcopy(obj)
            new_obj['x'] += 20
            new_obj['y'] += 20
            self.objects.append(new_obj)
            layer_idx = obj.get('layer', 0)
            if layer_idx < len(self.layers):
                self.layers[layer_idx]['objects'].append(new_obj)
            new_objects.append(new_obj)
        self.selected_objects = new_objects
        self.update_preview()
        self.add_to_history("Вставка объектов")
        self.update_layer_list()
        self.info_label.config(text=f"📋 Вставлено: {len(new_objects)}")
    
    # === ПРИМЕНЕНИЕ СВОЙСТВ ===
    
    def apply_position(self):
        if self.selected_objects:
            try:
                x = float(self.x_entry.get())
                y = float(self.y_entry.get())
                for obj in self.selected_objects:
                    obj['x'] = x
                    obj['y'] = y
                self.update_preview()
                self.add_to_history("Изменение позиции")
            except:
                pass
    
    def apply_size(self):
        if self.selected_objects:
            try:
                w = int(self.width_entry.get())
                h = int(self.height_entry.get())
                for obj in self.selected_objects:
                    obj['width'] = w
                    obj['height'] = h
                    obj['image'] = obj['image'].resize((w, h), Image.Resampling.LANCZOS)
                self.update_preview()
                self.add_to_history("Изменение размера")
            except:
                pass
    
    def lock_aspect(self):
        if self.selected_objects:
            obj = self.selected_objects[0]
            aspect = obj['width'] / obj['height']
            try:
                w = int(self.width_entry.get())
                h = int(w / aspect)
                self.height_entry.delete(0, tk.END)
                self.height_entry.insert(0, str(h))
                self.apply_size()
            except:
                pass
    
    def set_angle(self, angle):
        self.angle_scale.set(angle)
        self.apply_angle(angle)
    
    def apply_angle(self, value):
        if self.selected_objects:
            angle = float(value)
            self.angle_label.config(text=f"{int(angle)}°")
            for obj in self.selected_objects:
                obj['angle'] = angle
            self.update_preview()
            self.add_to_history("Изменение угла")
    
    def apply_opacity(self, value):
        if self.selected_objects:
            opacity = float(value)
            self.opacity_label.config(text=f"{int(opacity)}%")
            for obj in self.selected_objects:
                obj['opacity'] = opacity
            self.update_preview()
            self.add_to_history("Изменение прозрачности")
    
    def apply_mirror(self, axis):
        if self.selected_objects:
            for obj in self.selected_objects:
                if axis == 'x' or axis == 'both':
                    obj['mirror_x'] = not obj.get('mirror_x', False)
                if axis == 'y' or axis == 'both':
                    obj['mirror_y'] = not obj.get('mirror_y', False)
            self.update_preview()
            self.add_to_history("Отражение")
            self.info_label.config(text="✅ Отражение применено")
    
    # === ИСТОРИЯ ===
    
    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_state(self.history[self.history_index]['state'])
            self.update_history_list()
            self.info_label.config(text=f"↩ Отмена: {self.history[self.history_index]['name']}")
    
    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_state(self.history[self.history_index]['state'])
            self.update_history_list()
            self.info_label.config(text=f"↪ Повтор: {self.history[self.history_index]['name']}")
    
    def clear_history(self):
        if messagebox.askyesno("Очистка", "Удалить всю историю?"):
            self.history = []
            self.history_index = -1
            self.update_history_list()
            self.history_count_label.config(text="0")
            self.info_label.config(text="✅ История очищена")
    
    def take_snapshot(self):
        self.add_to_history(f"📸 Снимок {len(self.history) + 1}")
        self.info_label.config(text="✅ Снимок создан")
    
    def on_history_select(self, event):
        selected = self.history_listbox.curselection()
        if selected:
            index = selected[0]
            if index != self.history_index and index < len(self.history):
                self.history_index = index
                self.restore_state(self.history[index]['state'])
                self.update_history_list()
    
    # === ПАКЕТНАЯ ОБРАБОТКА ===
    
    def save_template(self):
        if not self.batch_operations:
            messagebox.showinfo("Информация", "Нет операций")
            return
        name = simpledialog.askstring("Название", "Введите название шаблона:")
        if name:
            self.batch_templates[name] = copy.deepcopy(self.batch_operations)
            self.update_template_list()
            self.info_label.config(text=f"✅ Шаблон сохранён: {name}")
    
    def load_template(self):
        if not self.batch_templates:
            messagebox.showinfo("Информация", "Нет шаблонов")
            return
        selected = self.template_listbox.curselection()
        if selected:
            name = list(self.batch_templates.keys())[selected[0]]
            self.batch_operations = copy.deepcopy(self.batch_templates[name])
            self.update_batch_ops_list()
            self.info_label.config(text=f"✅ Шаблон загружен: {name}")
    
    def delete_template(self):
        selected = self.template_listbox.curselection()
        if selected:
            name = list(self.batch_templates.keys())[selected[0]]
            if messagebox.askyesno("Удаление", f"Удалить шаблон '{name}'?"):
                del self.batch_templates[name]
                self.update_template_list()
                self.info_label.config(text=f"✅ Шаблон удалён: {name}")
    
    def on_template_select(self, event):
        pass
    
    def update_template_list(self):
        self.template_listbox.delete(0, tk.END)
        for name in self.batch_templates.keys():
            self.template_listbox.insert(tk.END, name)
    
    def update_batch_ops_list(self):
        self.batch_ops_listbox.delete(0, tk.END)
        for i, op in enumerate(self.batch_operations):
            text = f"{i+1}. {op.get('name', op.get('type', ''))}"
            if op.get('value'):
                text += f" ({op['value']})"
            self.batch_ops_listbox.insert(tk.END, text)
    
    def add_batch_op(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить операцию")
        dialog.geometry("300x250")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Тип операции:").pack(pady=5)
        op_types = [
            'gaussian_blur', 'sharpen', 'grayscale', 'sepia', 
            'brightness', 'contrast', 'resize', 'rotate', 'invert'
        ]
        op_var = tk.StringVar()
        op_combo = ttk.Combobox(dialog, textvariable=op_var, 
                               values=op_types, state='readonly')
        op_combo.pack(pady=5)
        
        ttk.Label(dialog, text="Значение (опционально):").pack(pady=5)
        value_entry = ttk.Entry(dialog)
        value_entry.pack(pady=5)
        
        def add():
            if op_var.get():
                op = {'type': op_var.get(), 'name': op_var.get(), 'value': value_entry.get()}
                self.batch_operations.append(op)
                self.update_batch_ops_list()
                dialog.destroy()
                self.info_label.config(text=f"✅ Операция добавлена")
        
        ttk.Button(dialog, text="Добавить", command=add).pack(pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)
    
    def remove_batch_op(self):
        selected = self.batch_ops_listbox.curselection()
        if selected:
            del self.batch_operations[selected[0]]
            self.update_batch_ops_list()
    
    def batch_up(self):
        selected = self.batch_ops_listbox.curselection()
        if selected and selected[0] > 0:
            idx = selected[0]
            self.batch_operations[idx], self.batch_operations[idx-1] = \
                self.batch_operations[idx-1], self.batch_operations[idx]
            self.update_batch_ops_list()
            self.batch_ops_listbox.selection_set(idx - 1)
    
    def batch_down(self):
        selected = self.batch_ops_listbox.curselection()
        if selected and selected[0] < len(self.batch_operations) - 1:
            idx = selected[0]
            self.batch_operations[idx], self.batch_operations[idx+1] = \
                self.batch_operations[idx+1], self.batch_operations[idx]
            self.update_batch_ops_list()
            self.batch_ops_listbox.selection_set(idx + 1)
    
    def execute_batch(self):
        if not self.batch_operations:
            messagebox.showinfo("Информация", "Добавьте операции")
            return
        
        target = self.batch_target_var.get()
        target_objects = []
        
        if target == 'all':
            target_objects = self.objects.copy()
        elif target == 'selected':
            target_objects = self.selected_objects.copy()
        elif target == 'layer':
            if self.current_layer_index < len(self.layers):
                target_objects = self.layers[self.current_layer_index]['objects'].copy()
        
        if not target_objects:
            messagebox.showinfo("Информация", "Нет объектов")
            return
        
        total = len(target_objects) * len(self.batch_operations)
        current = 0
        self.batch_progress['maximum'] = total
        self.batch_status.config(text="⏳ Выполняется...")
        
        for obj in target_objects:
            for op in self.batch_operations:
                img = obj['image'].copy()
                
                if op['type'] == 'gaussian_blur':
                    radius = float(op['value']) if op['value'] else 2.0
                    img = img.filter(ImageFilter.GaussianBlur(radius=radius))
                elif op['type'] == 'sharpen':
                    img = img.filter(ImageFilter.SHARPEN)
                elif op['type'] == 'grayscale':
                    img = ImageOps.grayscale(img)
                    img = img.convert('RGBA')
                elif op['type'] == 'sepia':
                    img = self.apply_sepia(img)
                elif op['type'] == 'brightness':
                    value = float(op['value']) if op['value'] else 1.0
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(value)
                elif op['type'] == 'contrast':
                    value = float(op['value']) if op['value'] else 1.0
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(value)
                elif op['type'] == 'resize':
                    value = float(op['value']) if op['value'] else 0.5
                    new_size = (int(img.width * value), int(img.height * value))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                elif op['type'] == 'rotate':
                    angle = float(op['value']) if op['value'] else 45
                    img = img.rotate(angle, expand=True)
                elif op['type'] == 'invert':
                    img = ImageOps.invert(img.convert('RGB'))
                    img = img.convert('RGBA')
                
                obj['image'] = img
                obj['width'], obj['height'] = img.size
                current += 1
                self.batch_progress['value'] = current
                self.root.update_idletasks()
        
        self.update_preview()
        self.add_to_history("Пакетная обработка")
        self.batch_progress['value'] = 0
        self.batch_status.config(text="✅ Готово!")
        self.info_label.config(text=f"✅ Пакетная обработка завершена")
    
    # === АНАЛИЗ ===
    
    def analyze_histogram(self):
        if not self.current_background:
            return
        
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, "📊 ГИСТОГРАММА\n")
        self.analysis_text.insert(tk.END, "=" * 30 + "\n\n")
        
        try:
            if HAS_CV2:
                import cv2
                import numpy as np
                
                img = self.current_background.convert('RGB')
                arr = np.array(img)
                
                for i, color in enumerate(['B', 'G', 'R']):
                    hist = cv2.calcHist([arr], [i], None, [256], [0, 256])
                    mean = np.mean(hist)
                    std = np.std(hist)
                    self.analysis_text.insert(tk.END, f"Канал {color}:\n")
                    self.analysis_text.insert(tk.END, f"  Среднее: {mean:.2f}\n")
                    self.analysis_text.insert(tk.END, f"  Отклонение: {std:.2f}\n\n")
            else:
                self.analysis_text.insert(tk.END, "⚠️ Установите opencv-python")
        except Exception as e:
            self.analysis_text.insert(tk.END, f"❌ Ошибка: {str(e)}")
    
    def analyze_colors(self):
        if not self.current_background:
            return
        
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, "🎨 ЦВЕТОВАЯ ПАЛИТРА\n")
        self.analysis_text.insert(tk.END, "=" * 30 + "\n\n")
        
        try:
            if HAS_SKLEARN:
                import numpy as np
                
                img = self.current_background.resize((100, 100))
                pixels = np.array(img).reshape(-1, 3)
                
                kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
                kmeans.fit(pixels)
                colors = kmeans.cluster_centers_.astype(int)
                
                self.analysis_text.insert(tk.END, "Основные цвета:\n")
                for i, color in enumerate(colors):
                    hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
                    self.analysis_text.insert(tk.END, f"  {i+1}. RGB{tuple(color)} {hex_color}\n")
            else:
                self.analysis_text.insert(tk.END, "⚠️ Установите scikit-learn")
        except Exception as e:
            self.analysis_text.insert(tk.END, f"❌ Ошибка: {str(e)}")
    
    def analyze_edges(self):
        if not self.current_background:
            return
        
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, "🔍 ДЕТЕКЦИЯ КРАЁВ\n")
        self.analysis_text.insert(tk.END, "=" * 30 + "\n\n")
        
        try:
            if HAS_CV2:
                import cv2
                import numpy as np
                
                arr = np.array(self.current_background.convert('RGB'))
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                edge_count = np.sum(edges > 0)
                total = edges.size
                
                self.analysis_text.insert(tk.END, f"Краевых пикселей: {edge_count:,}\n")
                self.analysis_text.insert(tk.END, f"Процент: {(edge_count/total)*100:.2f}%\n")
                self.analysis_text.insert(tk.END, f"Резкость: {np.std(edges):.2f}\n")
            else:
                self.analysis_text.insert(tk.END, "⚠️ Установите opencv-python")
        except Exception as e:
            self.analysis_text.insert(tk.END, f"❌ Ошибка: {str(e)}")
    
    def analyze_quality(self):
        if not self.current_background:
            return
        
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, "📐 КАЧЕСТВО\n")
        self.analysis_text.insert(tk.END, "=" * 30 + "\n\n")
        
        width, height = self.current_background.size
        self.analysis_text.insert(tk.END, f"Разрешение: {width} x {height}\n")
        self.analysis_text.insert(tk.END, f"Пикселей: {width*height:,}\n\n")
        
        if width < 800 or height < 600:
            self.analysis_text.insert(tk.END, "⚠️ Низкое разрешение\n")
        elif width < 1920 or height < 1080:
            self.analysis_text.insert(tk.END, "✅ Среднее разрешение\n")
        else:
            self.analysis_text.insert(tk.END, "✅ Высокое разрешение\n")
    
    def compare_images(self):
        if not self.current_background:
            return
        
        file_path = filedialog.askopenfilename(
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if file_path:
            try:
                img2 = Image.open(file_path)
                self.analysis_text.delete(1.0, tk.END)
                self.analysis_text.insert(tk.END, "🧬 СРАВНЕНИЕ\n")
                self.analysis_text.insert(tk.END, "=" * 30 + "\n\n")
                
                img1 = self.current_background
                self.analysis_text.insert(tk.END, f"Изображение 1: {img1.width}x{img1.height}\n")
                self.analysis_text.insert(tk.END, f"Изображение 2: {img2.width}x{img2.height}\n\n")
                
                if HAS_SKIMAGE:
                    from skimage.metrics import structural_similarity as ssim
                    import numpy as np
                    
                    i1 = np.array(img1.resize((256, 256)).convert('L'))
                    i2 = np.array(img2.resize((256, 256)).convert('L'))
                    similarity = ssim(i1, i2)
                    
                    self.analysis_text.insert(tk.END, f"Сходство (SSIM): {similarity:.4f}\n")
                    if similarity > 0.9:
                        self.analysis_text.insert(tk.END, "✅ Изображения очень похожи\n")
                    elif similarity > 0.7:
                        self.analysis_text.insert(tk.END, "⚠️ Умеренное сходство\n")
                    else:
                        self.analysis_text.insert(tk.END, "❌ Сильно отличаются\n")
                else:
                    self.analysis_text.insert(tk.END, "⚠️ Установите scikit-image")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
    
    # === ЭКСПОРТ ===
    
    def export_dialog(self):
        if not self.current_background:
            messagebox.showinfo("Информация", "Нет изображения")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("📤 Экспорт")
        dialog.geometry("350x280")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Формат:").pack(pady=5)
        format_var = tk.StringVar(value="PNG")
        format_combo = ttk.Combobox(dialog, textvariable=format_var,
                                   values=self.export_formats, state='readonly')
        format_combo.pack(pady=5)
        
        ttk.Label(dialog, text="Качество:").pack(pady=5)
        quality_scale = ttk.Scale(dialog, from_=1, to=100, orient=tk.HORIZONTAL, length=250)
        quality_scale.set(self.export_quality)
        quality_scale.pack(pady=5)
        quality_label = ttk.Label(dialog, text=f"{self.export_quality}%")
        quality_label.pack(pady=2)
        
        def update_quality(val):
            quality_label.config(text=f"{int(float(val))}%")
        quality_scale.configure(command=update_quality)
        
        def do_export():
            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{format_var.get().lower()}",
                filetypes=[(format_var.get(), f"*.{format_var.get().lower()}")]
            )
            if file_path:
                self.export_image(file_path, format_var.get(), int(quality_scale.get()))
                dialog.destroy()
        
        ttk.Button(dialog, text="📤 Экспортировать", command=do_export).pack(pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)
    
    def export_image(self, file_path, format_type='PNG', quality=90):
        try:
            img = self.render_final_image()
            
            if format_type == 'PNG':
                img.save(file_path, 'PNG')
            elif format_type == 'JPG':
                img.convert('RGB').save(file_path, 'JPEG', quality=quality)
            elif format_type == 'BMP':
                img.save(file_path, 'BMP')
            elif format_type == 'WEBP':
                img.save(file_path, 'WEBP', quality=quality)
            elif format_type == 'PDF':
                img.save(file_path, 'PDF')
            elif format_type == 'PSD':
                self.export_psd(file_path)
            elif format_type == 'SVG' and HAS_SVG:
                self.export_svg(file_path)
            
            self.info_label.config(text=f"✅ Экспортировано: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def render_final_image(self):
        if not self.current_background:
            return None
        
        img = self.current_background.copy()
        
        for layer in self.layers:
            if not layer['visible']:
                continue
            layer_img = self.render_layer(layer)
            if layer_img:
                img = Image.alpha_composite(img.convert('RGBA'), layer_img)
        
        return img
    
    def export_psd(self, file_path):
        try:
            from psd_tools import PSDImage
            psd = PSDImage.new(mode='RGB', size=self.current_background.size)
            
            bg_layer = psd.create_layer(name='Фон')
            bg_layer.paste(self.current_background)
            psd.append(bg_layer)
            
            for layer in self.layers:
                layer_img = self.render_layer(layer)
                if layer_img:
                    psd_layer = psd.create_layer(name=layer['name'])
                    psd_layer.paste(layer_img)
                    psd_layer.opacity = int(layer['opacity'] * 2.55)
                    psd.append(psd_layer)
            
            psd.save(file_path)
        except ImportError:
            self.export_image(file_path, 'PNG')
    
    def export_svg(self, file_path):
        if HAS_SVG:
            temp_png = file_path + ".temp.png"
            self.export_image(temp_png, 'PNG')
            cairosvg.png2svg(url=temp_png, write_to=file_path)
            os.remove(temp_png)
    
    # === ПРОЕКТ ===
    
    def new_project(self):
        if messagebox.askyesno("Новый проект", "Создать новый проект?"):
            self.backgrounds = []
            self.objects = []
            self.selected_objects = []
            self.layers = []
            self.current_background = None
            self.history = []
            self.history_index = -1
            self.project_path = None
            self.batch_templates = {}
            self.batch_operations = []
            self.add_layer()
            self.update_layer_list()
            self.update_template_list()
            self.update_batch_ops_list()
            self.update_preview()
            self.info_label.config(text="✅ Новый проект создан")
    
    def save_project(self):
        if not self.backgrounds and not self.objects:
            messagebox.showinfo("Информация", "Нет данных")
            return
        
        if not self.project_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".bep",
                filetypes=[("Background Editor Project", "*.bep")]
            )
            if not file_path:
                return
            self.project_path = file_path
            self.project_folder = os.path.dirname(file_path)
        
        self.save_project_to_path(self.project_path)
        self.info_label.config(text="✅ Проект сохранён")
    
    def save_project_as(self):
        self.project_path = None
        self.save_project()
    
    def save_project_to_path(self, path):
        try:
            folder = os.path.dirname(path)
            name = os.path.splitext(os.path.basename(path))[0]
            data_folder = os.path.join(folder, name)
            
            if not os.path.exists(data_folder):
                os.makedirs(data_folder)
            
            # Сохраняем фоны
            bg_paths = []
            for i, bg in enumerate(self.backgrounds):
                bg_path = os.path.join(data_folder, f"bg_{i}.png")
                bg.save(bg_path)
                bg_paths.append(os.path.join(name, f"bg_{i}.png"))
            
            # Сохраняем объекты
            obj_data = []
            for i, obj in enumerate(self.objects):
                obj_path = os.path.join(data_folder, f"obj_{i}.png")
                obj['image'].save(obj_path)
                obj_data.append({
                    'path': os.path.join(name, f"obj_{i}.png"),
                    'x': obj['x'], 'y': obj['y'],
                    'width': obj['width'], 'height': obj['height'],
                    'angle': obj['angle'], 'opacity': obj['opacity'],
                    'mirror_x': obj.get('mirror_x', False),
                    'mirror_y': obj.get('mirror_y', False),
                    'layer': obj.get('layer', 0)
                })
            
            # Сохраняем слои
            layers_data = []
            for layer in self.layers:
                layers_data.append({
                    'name': layer['name'],
                    'visible': layer['visible'],
                    'opacity': layer['opacity'],
                    'blend_mode': layer.get('blend_mode', 'normal'),
                    'object_indices': [self.objects.index(obj) for obj in layer['objects'] if obj in self.objects]
                })
            
            project_data = {
                'version': self.version,
                'created': datetime.now().isoformat(),
                'backgrounds': bg_paths,
                'current_bg_index': self.current_bg_index,
                'objects': obj_data,
                'layers': layers_data,
                'templates': self.batch_templates,
                'settings': self.config
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return False
    
    def open_project(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Background Editor Project", "*.bep")]
        )
        if file_path:
            self.open_project_path(file_path)
    
    def open_project_path(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            folder = os.path.dirname(path)
            
            # Загружаем фоны
            self.backgrounds = []
            for bg_path in data['backgrounds']:
                abs_path = os.path.join(folder, bg_path)
                if os.path.exists(abs_path):
                    self.backgrounds.append(Image.open(abs_path))
            
            self.current_bg_index = data.get('current_bg_index', 0)
            if self.backgrounds:
                self.current_background = self.backgrounds[self.current_bg_index].copy()
            
            # Загружаем объекты
            self.objects = []
            for obj_data in data['objects']:
                abs_path = os.path.join(folder, obj_data['path'])
                if os.path.exists(abs_path):
                    img = Image.open(abs_path)
                    obj = {
                        'image': img,
                        'x': obj_data['x'], 'y': obj_data['y'],
                        'width': obj_data['width'], 'height': obj_data['height'],
                        'angle': obj_data['angle'], 'opacity': obj_data['opacity'],
                        'mirror_x': obj_data.get('mirror_x', False),
                        'mirror_y': obj_data.get('mirror_y', False),
                        'path': abs_path
                    }
                    self.objects.append(obj)
            
            # Загружаем слои
            self.layers = []
            for layer_data in data.get('layers', []):
                layer = {
                    'name': layer_data['name'],
                    'visible': layer_data['visible'],
                    'opacity': layer_data['opacity'],
                    'blend_mode': layer_data.get('blend_mode', 'normal'),
                    'objects': []
                }
                for idx in layer_data.get('object_indices', []):
                    if idx < len(self.objects):
                        layer['objects'].append(self.objects[idx])
                        self.objects[idx]['layer'] = len(self.layers)
                self.layers.append(layer)
            
            if not self.layers:
                self.add_layer()
            
            self.batch_templates = data.get('templates', {})
            self.update_template_list()
            
            self.project_path = path
            self.project_folder = folder
            
            self.update_layer_list()
            self.update_preview()
            self.info_label.config(text=f"✅ Проект загружен: {os.path.basename(path)}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def import_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )
        if file_path:
            self.add_object_from_path(file_path)
    
    def reset(self):
        if messagebox.askyesno("Сброс", "Сбросить все изменения?"):
            self.objects = []
            self.selected_objects = []
            self.layers = []
            self.add_layer()
            self.history = []
            self.history_index = -1
            if self.backgrounds:
                self.current_background = self.backgrounds[0].copy()
            self.update_layer_list()
            self.update_history_list()
            self.update_preview()
            self.info_label.config(text="✅ Сброс выполнен")
    
    # === АВТОСОХРАНЕНИЕ ===
    
    def start_auto_save(self):
        def auto_save_loop():
            while True:
                time.sleep(self.auto_save_interval)
                if self.auto_save_enabled and self.project_path:
                    self.root.after(0, self.auto_save)
        
        if self.auto_save_enabled:
            threading.Thread(target=auto_save_loop, daemon=True).start()
    
    def auto_save(self):
        if self.project_path and (self.backgrounds or self.objects):
            temp_path = self.project_path + ".autosave"
            self.save_project_to_path(temp_path)
            self.info_label.config(text="💾 Автосохранение")
    
    # === ПОСЛЕДНИЕ ПРОЕКТЫ ===
    
    def load_recent_projects(self):
        try:
            config_path = os.path.join(os.path.expanduser("~"), ".bg_editor_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.recent_projects = config.get('recent', [])
                    self.config.update(config.get('settings', {}))
        except:
            pass
    
    # === О ПРОГРАММЕ ===
    
    def show_about(self):
        about = f"""🎨 Редактор Фона Ultimate v{self.version}

✨ Возможности:
• 📚 Слои и объекты
• 🎨 Фильтры и эффекты  
• 📦 Пакетная обработка
• 🤖 ИИ удаление фона
• 📤 Экспорт в 7 форматов
• ⏳ История действий
• 💾 Автосохранение
• 🔄 Автообновление

📦 Библиотеки:
• Pillow - работа с изображениями
• OpenCV - обработка изображений
• Rembg - ИИ удаление фона
• scikit-learn - анализ цветов

📅 Версия: {self.version}
📆 Создано: 2026

© Все права защищены"""
        messagebox.showinfo("О программе", about)
    
    def show_help(self):
        help_text = """📖 ПОМОЩЬ

🚀 БЫСТРЫЙ СТАРТ:
1. Добавьте фон (📁 Добавить фон)
2. Добавьте объекты (➕ Добавить объект)  
3. Работайте со слоями (📚 Слои)
4. Применяйте фильтры (🎨 Фильтры)
5. Сохраните результат (📤 Экспорт)

⌨️ ГОРЯЧИЕ КЛАВИШИ:
Ctrl+N - Новый проект
Ctrl+O - Открыть проект
Ctrl+S - Сохранить
Ctrl+E - Экспорт
Ctrl+Z - Отмена
Ctrl+Y - Повтор
Ctrl+A - Выделить всё
Delete - Удалить
Esc - Снять выделение
Ctrl+ + - Увеличить
Ctrl+ - - Уменьшить

💡 СОВЕТЫ:
• Используйте слои для неразрушающего редактирования
• Применяйте ИИ для быстрого удаления фона
• Сохраняйте пресеты для частых эффектов
• Включайте автосохранение в настройках"""
        messagebox.showinfo("Справка", help_text)
    
    def show_hotkeys(self):
        hotkeys = """⌨️ ГОРЯЧИЕ КЛАВИШИ

📁 Файл:
Ctrl+N - Новый проект
Ctrl+O - Открыть
Ctrl+S - Сохранить
Ctrl+Shift+S - Сохранить как
Ctrl+E - Экспорт
Ctrl+Q - Выход

✏️ Правка:
Ctrl+Z - Отмена
Ctrl+Y - Повтор
Ctrl+X - Вырезать
Ctrl+C - Копировать
Ctrl+V - Вставить
Ctrl+A - Выделить всё
Esc - Снять выделение
Delete - Удалить

👁 Вид:
Ctrl++ - Увеличить
Ctrl+- - Уменьшить
Tab - Следующий объект
Shift+Tab - Предыдущий объект

📚 Слои:
F2 - Переименовать слой"""
        messagebox.showinfo("Горячие клавиши", hotkeys)


# === ЗАПУСК ===
if __name__ == "__main__":
    root = tk.Tk()
    app = BackgroundEditorUltimate(root)
    root.mainloop()