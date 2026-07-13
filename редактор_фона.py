# редактор_фона.py - Редактор фона 1.0
"""
Редактор фона 1.0 - Универсальный редактор изображений
Разработан: DeepSeek
Версия: 1.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, scrolledtext, simpledialog
from PIL import Image, ImageTk, ImageFilter, ImageEnhance, ImageOps, ImageDraw
import os
import json
import copy
import threading
import time
import sys
import subprocess
import tempfile
import shutil
import zipfile
from datetime import datetime
import random
import webbrowser

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
    from skimage import exposure
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

# === ВЕРСИЯ ПРОГРАММЫ ===
VERSION = "1.0"
PROGRAM_NAME = "Редактор фона"
PROGRAM_NAME_EN = "Background Editor"

# === КЛАСС АВТООБНОВЛЕНИЯ ===
class Updater:
    def __init__(self, current_version=VERSION):
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
        except:
            return False, None, None
        return False, None, None
    
    def download_update(self, url=None):
        if not HAS_REQUESTS:
            return None, "Установите requests"
        
        try:
            download_url = url or self.download_url
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


# === КЛАСС ПРОГРАММЫ ===
class BackgroundEditor:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{PROGRAM_NAME} v{VERSION}")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 700)
        
        # === ПЕРЕМЕННЫЕ ===
        self.version = VERSION
        self.program_name = PROGRAM_NAME
        self.current_language = 'ru'
        self.updater = Updater(self.version)
        
        # Пути
        self.project_path = None
        self.project_folder = None
        
        # Масштаб
        self.zoom_level = 1.0
        
        # Данные проекта
        self.backgrounds = []
        self.current_background = None
        self.current_bg_index = 0
        self.objects = []
        self.selected_objects = []
        self.layers = []
        self.current_layer_index = 0
        self.recent_projects = []
        self.max_recent = 10
        self.clipboard_objects = []
        
        # История
        self.history = []
        self.history_index = -1
        self.max_history = 100
        
        # Пакетная обработка
        self.batch_templates = {}
        self.batch_operations = []
        self.batch_target_var = tk.StringVar(value="all")
        
        # Настройки
        self.config = {
            'auto_save': True,
            'confirm_delete': True,
            'theme': 'dark',
            'language': 'ru',
            'check_updates': True,
            'windows_style': 'Windows 10',
            'interface_style': 'Классический',
            'quality': 90
        }
        
        # Переменные интерфейса
        self.grid_visible = False
        self.rules_visible = False
        self.auto_save_enabled = True
        self.auto_save_interval = 300
        self.resize_handles_var = tk.BooleanVar(value=True)
        
        # Экспорт
        self.export_formats = ['PNG', 'JPG', 'BMP', 'WEBP', 'PDF', 'PSD']
        if HAS_SVG:
            self.export_formats.append('SVG')
        self.export_quality = 90
        self.export_as_zip = False
        
        # Пресеты
        self.custom_presets = {}
        self.interface_presets = {}
        self.interface_custom_settings = {}
        
        # Кэш
        self.preview_cache = None
        self.preview_cache_time = 0
        
        # Статус библиотек
        self.has_cv2 = HAS_CV2
        self.has_skimage = HAS_SKIMAGE
        self.has_rembg = HAS_REMBG
        self.has_sklearn = HAS_SKLEARN
        self.has_ai = HAS_AI
        self.has_requests = HAS_REQUESTS
        self.has_svg = HAS_SVG
        
        # === СОЗДАНИЕ ИНТЕРФЕЙСА ===
        self.setup_languages()
        self.setup_interface_presets()
        self.setup_ui()
        self.setup_menu()
        self.setup_hotkeys()
        self.setup_context_menu()
        self.apply_theme()
        self.apply_windows_style()
        self.apply_interface_style()
        self.load_recent_projects()
        self.start_auto_save()
        self.setup_drag_drop()
        
        # === ПРОВЕРКА ОБНОВЛЕНИЙ ===
        if self.config.get('check_updates', True):
            self.root.after(3000, self.check_updates_auto)
        
        # === СТАТУС ===
        self.update_status()
    
    def setup_languages(self):
        """Настройка языков"""
        self.languages = {
            'ru': {
                'program_name': 'Редактор фона',
                'file': 'Файл',
                'edit': 'Правка',
                'view': 'Вид',
                'settings': 'Настройки',
                'help': 'Помощь',
                'new': 'Новый проект',
                'open': 'Открыть проект',
                'save': 'Сохранить проект',
                'save_as': 'Сохранить как',
                'export': 'Экспорт',
                'import': 'Импорт',
                'exit': 'Выход',
                'undo': 'Отмена',
                'redo': 'Повтор',
                'cut': 'Вырезать',
                'copy': 'Копировать',
                'paste': 'Вставить',
                'select_all': 'Выделить всё',
                'deselect': 'Снять выделение',
                'zoom_in': 'Увеличить',
                'zoom_out': 'Уменьшить',
                'reset_view': 'Сбросить вид',
                'grid': 'Сетка',
                'rules': 'Правило третей',
                'resize_handles': 'Маркеры ресайза',
                'check_updates': 'Проверить обновления',
                'about': 'О программе',
                'help_text': 'Справка',
                'hotkeys': 'Горячие клавиши',
                'add_background': 'Добавить фон',
                'add_objects': 'Добавить объекты',
                'background': 'Фон',
                'objects': 'Объекты',
                'layers': 'Слои',
                'filters': 'Фильтры',
                'presets': 'Пресеты',
                'batch': 'Пакетная обработка',
                'analysis': 'Анализ',
                'history': 'История',
                'settings_tab': 'Настройки',
                'tools': 'Инструменты',
                'properties': 'Свойства',
                'position': 'Позиция',
                'size': 'Размер',
                'rotation': 'Поворот',
                'opacity': 'Прозрачность',
                'mirror': 'Отражение',
                'remove_background': 'Удаление фона',
                'ai_remove': 'ИИ удаление фона',
                'color_remove': 'По цвету',
                'edges_remove': 'Обрезка краёв',
                'duplicate': 'Дублировать',
                'delete': 'Удалить',
                'align': 'Выровнять',
                'resize': 'Изменить размер',
                'reset': 'Сброс',
                'save_as_zip': 'Сохранить как ZIP-файл',
                'windows_style': 'Стиль Windows',
                'interface_style': 'Стиль интерфейса',
                'language': 'Язык',
                'theme': 'Тема',
                'dark': 'Тёмная',
                'light': 'Светлая',
                'auto_save': 'Автосохранение',
                'confirm_delete': 'Подтверждение удаления',
                'classic': 'Классический',
                'modern': 'Современный',
                'minimal': 'Минималистичный',
                'dark_theme': 'Тёмная тема',
                'light_theme': 'Светлая тема',
                'blue': 'Синий',
                'green': 'Зелёный',
                'purple': 'Фиолетовый',
                'orange': 'Оранжевый',
                'red': 'Красный',
                'custom': 'Пользовательский'
            },
            'en': {
                'program_name': 'Background Editor',
                'file': 'File',
                'edit': 'Edit',
                'view': 'View',
                'settings': 'Settings',
                'help': 'Help',
                'new': 'New Project',
                'open': 'Open Project',
                'save': 'Save Project',
                'save_as': 'Save As',
                'export': 'Export',
                'import': 'Import',
                'exit': 'Exit',
                'undo': 'Undo',
                'redo': 'Redo',
                'cut': 'Cut',
                'copy': 'Copy',
                'paste': 'Paste',
                'select_all': 'Select All',
                'deselect': 'Deselect',
                'zoom_in': 'Zoom In',
                'zoom_out': 'Zoom Out',
                'reset_view': 'Reset View',
                'grid': 'Grid',
                'rules': 'Rule of Thirds',
                'resize_handles': 'Resize Handles',
                'check_updates': 'Check for Updates',
                'about': 'About',
                'help_text': 'Help',
                'hotkeys': 'Hotkeys',
                'add_background': 'Add Background',
                'add_objects': 'Add Objects',
                'background': 'Background',
                'objects': 'Objects',
                'layers': 'Layers',
                'filters': 'Filters',
                'presets': 'Presets',
                'batch': 'Batch Processing',
                'analysis': 'Analysis',
                'history': 'History',
                'settings_tab': 'Settings',
                'tools': 'Tools',
                'properties': 'Properties',
                'position': 'Position',
                'size': 'Size',
                'rotation': 'Rotation',
                'opacity': 'Opacity',
                'mirror': 'Mirror',
                'remove_background': 'Remove Background',
                'ai_remove': 'AI Remove',
                'color_remove': 'By Color',
                'edges_remove': 'Crop Edges',
                'duplicate': 'Duplicate',
                'delete': 'Delete',
                'align': 'Align',
                'resize': 'Resize',
                'reset': 'Reset',
                'save_as_zip': 'Save as ZIP',
                'windows_style': 'Windows Style',
                'interface_style': 'Interface Style',
                'language': 'Language',
                'theme': 'Theme',
                'dark': 'Dark',
                'light': 'Light',
                'auto_save': 'Auto Save',
                'confirm_delete': 'Confirm Delete',
                'classic': 'Classic',
                'modern': 'Modern',
                'minimal': 'Minimal',
                'dark_theme': 'Dark Theme',
                'light_theme': 'Light Theme',
                'blue': 'Blue',
                'green': 'Green',
                'purple': 'Purple',
                'orange': 'Orange',
                'red': 'Red',
                'custom': 'Custom'
            }
        }
    
    def setup_interface_presets(self):
        """Настройка предустановленных стилей интерфейса"""
        self.interface_presets = {
            'Классический': {
                'bg_color': '#2b2b2b',
                'fg_color': '#ffffff',
                'button_color': '#3b3b3b',
                'font_family': 'Segoe UI',
                'font_size': 9,
                'padding': 5,
                'border_radius': 0
            },
            'Современный': {
                'bg_color': '#1a1a2e',
                'fg_color': '#e0e0e0',
                'button_color': '#16213e',
                'font_family': 'Segoe UI',
                'font_size': 10,
                'padding': 8,
                'border_radius': 8
            },
            'Минималистичный': {
                'bg_color': '#f5f5f5',
                'fg_color': '#333333',
                'button_color': '#e8e8e8',
                'font_family': 'Arial',
                'font_size': 9,
                'padding': 4,
                'border_radius': 0
            },
            'Тёмная тема': {
                'bg_color': '#0d0d0d',
                'fg_color': '#f0f0f0',
                'button_color': '#1a1a1a',
                'font_family': 'Segoe UI',
                'font_size': 10,
                'padding': 6,
                'border_radius': 4
            },
            'Светлая тема': {
                'bg_color': '#f0f0f0',
                'fg_color': '#222222',
                'button_color': '#e0e0e0',
                'font_family': 'Arial',
                'font_size': 9,
                'padding': 5,
                'border_radius': 0
            },
            'Синяя тема': {
                'bg_color': '#0a1628',
                'fg_color': '#b8d4ff',
                'button_color': '#1a2d4a',
                'font_family': 'Segoe UI',
                'font_size': 10,
                'padding': 6,
                'border_radius': 4
            },
            'Зелёная тема': {
                'bg_color': '#0a1a0a',
                'fg_color': '#b8ffb8',
                'button_color': '#1a2a1a',
                'font_family': 'Segoe UI',
                'font_size': 10,
                'padding': 6,
                'border_radius': 4
            },
            'Фиолетовая тема': {
                'bg_color': '#1a0a2a',
                'fg_color': '#d4b8ff',
                'button_color': '#2a1a3a',
                'font_family': 'Segoe UI',
                'font_size': 10,
                'padding': 6,
                'border_radius': 4
            },
            'Оранжевая тема': {
                'bg_color': '#2a1a0a',
                'fg_color': '#ffd4b8',
                'button_color': '#3a2a1a',
                'font_family': 'Segoe UI',
                'font_size': 10,
                'padding': 6,
                'border_radius': 4
            },
            'Красная тема': {
                'bg_color': '#2a0a0a',
                'fg_color': '#ffb8b8',
                'button_color': '#3a1a1a',
                'font_family': 'Segoe UI',
                'font_size': 10,
                'padding': 6,
                'border_radius': 4
            }
        }
        
        # Пользовательские настройки
        self.interface_custom_settings = {
            'bg_color': '#2b2b2b',
            'fg_color': '#ffffff',
            'button_color': '#3b3b3b',
            'font_family': 'Segoe UI',
            'font_size': 9,
            'padding': 5,
            'border_radius': 0
        }
    
    def get_text(self, key):
        """Получение текста на текущем языке"""
        lang = self.current_language
        if lang in self.languages and key in self.languages[lang]:
            return self.languages[lang][key]
        return key
    
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
        notebook.add(tab, text="🔧 " + self.get_text('tools'))
        
        # === ФОН ===
        bg_frame = ttk.LabelFrame(tab, text=self.get_text('background'))
        bg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(bg_frame, text="📂 " + self.get_text('add_background'), 
                  command=self.add_background).pack(fill=tk.X, pady=2)
        ttk.Button(bg_frame, text="📦 " + self.get_text('add_objects') + " (пакетно)", 
                  command=self.add_objects_batch).pack(fill=tk.X, pady=2)
        
        btn_frame = ttk.Frame(bg_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="◄", command=self.prev_background, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="►", command=self.next_background, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🎲", command=self.random_background, width=5).pack(side=tk.LEFT, padx=2)
        
        # === УДАЛЕНИЕ ФОНА ===
        remove_frame = ttk.LabelFrame(tab, text=self.get_text('remove_background'))
        remove_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(remove_frame, text="🎯 " + self.get_text('color_remove'), 
                  command=self.remove_by_color).pack(fill=tk.X, pady=2)
        ttk.Button(remove_frame, text="🤖 " + self.get_text('ai_remove'), 
                  command=self.remove_ai).pack(fill=tk.X, pady=2)
        ttk.Button(remove_frame, text="✂️ " + self.get_text('edges_remove'), 
                  command=self.remove_edges).pack(fill=tk.X, pady=2)
        
        # === ОБЪЕКТЫ ===
        obj_frame = ttk.LabelFrame(tab, text=self.get_text('objects'))
        obj_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(obj_frame, text="➕ " + self.get_text('add_objects'), 
                  command=self.add_object).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="📦 " + self.get_text('add_objects') + " (пакетно)", 
                  command=self.add_objects_batch).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="📋 " + self.get_text('duplicate'), 
                  command=self.duplicate_objects).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="🗑 " + self.get_text('delete'), 
                  command=self.delete_objects).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="🔀 " + self.get_text('align'), 
                  command=self.align_objects).pack(fill=tk.X, pady=2)
        ttk.Button(obj_frame, text="📐 " + self.get_text('resize'), 
                  command=self.resize_dialog).pack(fill=tk.X, pady=2)
        
        # === ДЕЙСТВИЯ ===
        action_frame = ttk.LabelFrame(tab, text="⚡ " + self.get_text('edit'))
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        action_btns = ttk.Frame(action_frame)
        action_btns.pack(fill=tk.X, pady=2)
        ttk.Button(action_btns, text="↩ " + self.get_text('undo'), 
                  command=self.undo, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_btns, text="↪ " + self.get_text('redo'), 
                  command=self.redo, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_btns, text="⟳ " + self.get_text('reset'), 
                  command=self.reset, width=10).pack(side=tk.LEFT, padx=2)
        
        # === МАРКЕРЫ ===
        resize_frame = ttk.LabelFrame(tab, text="📐 " + self.get_text('resize_handles'))
        resize_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Checkbutton(resize_frame, text=self.get_text('resize_handles'), 
                       variable=self.resize_handles_var,
                       command=self.update_preview).pack(fill=tk.X, pady=2)
    
    def setup_layers_tab(self, notebook):
        """Вкладка Слои"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📚 " + self.get_text('layers'))
        
        self.layer_listbox = tk.Listbox(tab, height=14, selectmode=tk.SINGLE)
        self.layer_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.layer_listbox.bind('<<ListboxSelect>>', self.on_layer_select)
        
        layer_btns = ttk.Frame(tab)
        layer_btns.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(layer_btns, text="➕ Новый", command=self.add_layer).pack(side=tk.LEFT, padx=2)
        ttk.Button(layer_btns, text="🗑 Удалить", command=self.delete_layer).pack(side=tk.LEFT, padx=2)
        ttk.Button(layer_btns, text="⬆", command=self.layer_up, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(layer_btns, text="⬇", command=self.layer_down, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(layer_btns, text="🔗", command=self.merge_layers, width=3).pack(side=tk.LEFT, padx=2)
        
        settings_frame = ttk.LabelFrame(tab, text="⚙️ " + self.get_text('settings'))
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.layer_name_entry = ttk.Entry(settings_frame)
        self.layer_name_entry.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(settings_frame, text="Переименовать", command=self.rename_layer).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(settings_frame, text=self.get_text('opacity') + ":").pack(anchor=tk.W, padx=5)
        self.layer_opacity_scale = ttk.Scale(settings_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                            command=self.change_layer_opacity)
        self.layer_opacity_scale.pack(fill=tk.X, padx=5, pady=2)
        self.layer_opacity_label = ttk.Label(settings_frame, text="100%")
        self.layer_opacity_label.pack(pady=2)
        
        self.layer_visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="👁 Видимый", 
                       variable=self.layer_visible_var,
                       command=self.toggle_layer_visibility).pack(anchor=tk.W, padx=5, pady=2)
    
    def setup_filters_tab(self, notebook):
        """Вкладка Фильтры"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🎨 " + self.get_text('filters'))
        
        filter_notebook = ttk.Notebook(tab)
        filter_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Размытие
        blur_tab = ttk.Frame(filter_notebook)
        filter_notebook.add(blur_tab, text="Размытие")
        
        ttk.Label(blur_tab, text="Размытие по Гауссу").pack(pady=5)
        self.blur_scale = ttk.Scale(blur_tab, from_=0, to=10, orient=tk.HORIZONTAL, length=250)
        self.blur_scale.set(2)
        self.blur_scale.pack(pady=5)
        ttk.Button(blur_tab, text="Применить", 
                  command=lambda: self.apply_filter('gaussian_blur', self.blur_scale.get())).pack(pady=5)
        
        for text, cmd in [("Сглаживание", 'smooth'), ("Резкость", 'sharpen'), ("Тиснение", 'emboss')]:
            ttk.Button(blur_tab, text=text, command=lambda c=cmd: self.apply_filter(c)).pack(fill=tk.X, pady=2)
        
        # Коррекция
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
        
        # Эффекты
        eff_tab = ttk.Frame(filter_notebook)
        filter_notebook.add(eff_tab, text="Эффекты")
        
        for text, cmd in [("Ч/б", 'grayscale'), ("Сепия", 'sepia'), ("Инверсия", 'invert'),
                         ("Постеризация", 'posterize'), ("Соляризация", 'solarize'),
                         ("Виньетка", 'vignette'), ("Пикселизация", 'pixelate')]:
            ttk.Button(eff_tab, text=text, command=lambda c=cmd: self.apply_effect(c)).pack(fill=tk.X, pady=2)
    
    def setup_presets_tab(self, notebook):
        """Вкладка Пресеты"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⚡ " + self.get_text('presets'))
        
        ttk.Label(tab, text="🚀 Быстрые пресеты", font=("Arial", 10, "bold")).pack(pady=10)
        
        presets = [
            ("🎨 Vintage", self.preset_vintage),
            ("🎬 Cinematic", self.preset_cinematic),
            ("⚫ B&W", self.preset_bw),
            ("🔥 Warm", self.preset_warm),
            ("❄️ Cool", self.preset_cool),
            ("🌈 HDR", self.preset_hdr),
            ("🎭 Dramatic", self.preset_dramatic),
            ("✨ Soft Glow", self.preset_soft_glow)
        ]
        
        presets_frame = ttk.Frame(tab)
        presets_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for i, (name, cmd) in enumerate(presets):
            row = i // 3
            col = i % 3
            btn = ttk.Button(presets_frame, text=name, command=cmd, width=14)
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        for col in range(3):
            presets_frame.columnconfigure(col, weight=1)
        
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
        notebook.add(tab, text="📦 " + self.get_text('batch'))
        
        template_frame = ttk.LabelFrame(tab, text="📋 Шаблоны")
        template_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.template_listbox = tk.Listbox(template_frame, height=4)
        self.template_listbox.pack(fill=tk.X, padx=5, pady=5)
        
        template_btns = ttk.Frame(template_frame)
        template_btns.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(template_btns, text="💾 Сохранить", command=self.save_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_btns, text="📂 Загрузить", command=self.load_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_btns, text="🗑 Удалить", command=self.delete_template).pack(side=tk.LEFT, padx=2)
        
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
        
        exec_frame = ttk.Frame(tab)
        exec_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(exec_frame, text="Применить к:").pack(side=tk.LEFT)
        for text, value in [("Всем", "all"), ("Выбранным", "selected"), ("Слою", "layer")]:
            ttk.Radiobutton(exec_frame, text=text, variable=self.batch_target_var, 
                           value=value).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(tab, text="▶ ВЫПОЛНИТЬ", command=self.execute_batch).pack(fill=tk.X, padx=5, pady=5)
        
        self.batch_progress = ttk.Progressbar(tab, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.batch_progress.pack(fill=tk.X, padx=5, pady=5)
        self.batch_status = ttk.Label(tab, text="✅ Готов к работе")
        self.batch_status.pack(pady=2)
    
    def setup_analysis_tab(self, notebook):
        """Вкладка Анализ"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📊 " + self.get_text('analysis'))
        
        analysis_frame = ttk.Frame(tab)
        analysis_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(analysis_frame, text="📊 Гистограмма", command=self.analyze_histogram).pack(fill=tk.X, pady=2)
        ttk.Button(analysis_frame, text="🎨 Цветовая палитра", command=self.analyze_colors).pack(fill=tk.X, pady=2)
        ttk.Button(analysis_frame, text="🔍 Детекция краёв", command=self.analyze_edges).pack(fill=tk.X, pady=2)
        ttk.Button(analysis_frame, text="📐 Качество", command=self.analyze_quality).pack(fill=tk.X, pady=2)
        
        results_frame = ttk.LabelFrame(tab, text="📋 Результаты")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.analysis_text = scrolledtext.ScrolledText(results_frame, height=12, width=30)
        self.analysis_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def setup_history_tab(self, notebook):
        """Вкладка История"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⏳ " + self.get_text('history'))
        
        self.history_listbox = tk.Listbox(tab, height=14)
        self.history_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.history_listbox.bind('<<ListboxSelect>>', self.on_history_select)
        
        hist_btns = ttk.Frame(tab)
        hist_btns.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(hist_btns, text="↩ " + self.get_text('undo'), command=self.undo).pack(side=tk.LEFT, padx=2)
        ttk.Button(hist_btns, text="↪ " + self.get_text('redo'), command=self.redo).pack(side=tk.LEFT, padx=2)
        ttk.Button(hist_btns, text="🧹 Очистить", command=self.clear_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(hist_btns, text="📸 Снимок", command=self.take_snapshot).pack(side=tk.LEFT, padx=2)
        
        self.history_count_label = ttk.Label(tab, text="0")
        self.history_count_label.pack(pady=2)
    
    def setup_settings_tab(self, notebook):
        """Вкладка Настройки"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⚙️ " + self.get_text('settings_tab'))
        
        # === ОБЩИЕ ===
        general_frame = ttk.LabelFrame(tab, text=self.get_text('settings'))
        general_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Язык
        ttk.Label(general_frame, text=self.get_text('language') + ":").pack(anchor=tk.W, padx=5, pady=2)
        lang_frame = ttk.Frame(general_frame)
        lang_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(lang_frame, text="🇷🇺 Русский", command=lambda: self.set_language('ru')).pack(side=tk.LEFT, padx=2)
        ttk.Button(lang_frame, text="🇬🇧 English", command=lambda: self.set_language('en')).pack(side=tk.LEFT, padx=2)
        
        # Тема
        ttk.Label(general_frame, text=self.get_text('theme') + ":").pack(anchor=tk.W, padx=5, pady=2)
        theme_frame = ttk.Frame(general_frame)
        theme_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(theme_frame, text="🌙 " + self.get_text('dark'), 
                  command=lambda: self.set_theme('dark')).pack(side=tk.LEFT, padx=2)
        ttk.Button(theme_frame, text="☀️ " + self.get_text('light'), 
                  command=lambda: self.set_theme('light')).pack(side=tk.LEFT, padx=2)
        
        # === СТИЛЬ WINDOWS ===
        style_frame = ttk.LabelFrame(tab, text=self.get_text('windows_style'))
        style_frame.pack(fill=tk.X, padx=5, pady=5)
        
        windows_styles = ['Windows XP', 'Windows Vista', 'Windows 7', 'Windows 8', 'Windows 10', 'Windows 11']
        self.windows_style_var = tk.StringVar(value=self.config.get('windows_style', 'Windows 10'))
        
        for style in windows_styles:
            ttk.Radiobutton(style_frame, text=style, 
                          variable=self.windows_style_var, value=style,
                          command=self.apply_windows_style).pack(anchor=tk.W, padx=10, pady=2)
        
        # === СТИЛЬ ИНТЕРФЕЙСА ===
        interface_frame = ttk.LabelFrame(tab, text=self.get_text('interface_style'))
        interface_frame.pack(fill=tk.X, padx=5, pady=5)
        
        interface_presets = list(self.interface_presets.keys())
        self.interface_style_var = tk.StringVar(value=self.config.get('interface_style', 'Классический'))
        
        # Создаём прокручиваемый список
        interface_listbox = tk.Listbox(interface_frame, height=6, selectmode=tk.SINGLE)
        interface_listbox.pack(fill=tk.X, padx=5, pady=5)
        
        for preset in interface_presets:
            interface_listbox.insert(tk.END, preset)
        
        # Выбираем текущий
        current = self.config.get('interface_style', 'Классический')
        if current in interface_presets:
            interface_listbox.selection_set(interface_presets.index(current))
        
        def apply_interface_selection(event=None):
            selected = interface_listbox.curselection()
            if selected:
                style_name = interface_listbox.get(selected[0])
                self.config['interface_style'] = style_name
                self.apply_interface_style()
                self.update_status()
        
        interface_listbox.bind('<<ListboxSelect>>', apply_interface_selection)
        
        # === НАСТРОЙКИ ИНТЕРФЕЙСА ===
        custom_interface_frame = ttk.LabelFrame(tab, text="🎨 Настройка интерфейса")
        custom_interface_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Цвет фона
        ttk.Label(custom_interface_frame, text="Цвет фона:").pack(anchor=tk.W, padx=5, pady=2)
        bg_color_frame = ttk.Frame(custom_interface_frame)
        bg_color_frame.pack(fill=tk.X, padx=5, pady=2)
        self.bg_color_entry = ttk.Entry(bg_color_frame, width=15)
        self.bg_color_entry.pack(side=tk.LEFT, padx=2)
        self.bg_color_entry.insert(0, self.interface_custom_settings.get('bg_color', '#2b2b2b'))
        ttk.Button(bg_color_frame, text="🎨", width=3,
                  command=lambda: self.choose_interface_color('bg_color')).pack(side=tk.LEFT, padx=2)
        
        # Цвет текста
        ttk.Label(custom_interface_frame, text="Цвет текста:").pack(anchor=tk.W, padx=5, pady=2)
        fg_color_frame = ttk.Frame(custom_interface_frame)
        fg_color_frame.pack(fill=tk.X, padx=5, pady=2)
        self.fg_color_entry = ttk.Entry(fg_color_frame, width=15)
        self.fg_color_entry.pack(side=tk.LEFT, padx=2)
        self.fg_color_entry.insert(0, self.interface_custom_settings.get('fg_color', '#ffffff'))
        ttk.Button(fg_color_frame, text="🎨", width=3,
                  command=lambda: self.choose_interface_color('fg_color')).pack(side=tk.LEFT, padx=2)
        
        # Шрифт
        ttk.Label(custom_interface_frame, text="Шрифт:").pack(anchor=tk.W, padx=5, pady=2)
        self.font_entry = ttk.Entry(custom_interface_frame)
        self.font_entry.pack(fill=tk.X, padx=5, pady=2)
        self.font_entry.insert(0, self.interface_custom_settings.get('font_family', 'Segoe UI'))
        
        # Размер шрифта
        ttk.Label(custom_interface_frame, text="Размер шрифта:").pack(anchor=tk.W, padx=5, pady=2)
        self.font_size_scale = ttk.Scale(custom_interface_frame, from_=8, to=16, orient=tk.HORIZONTAL)
        self.font_size_scale.set(self.interface_custom_settings.get('font_size', 9))
        self.font_size_scale.pack(fill=tk.X, padx=5, pady=2)
        
        def apply_custom_interface():
            self.interface_custom_settings['bg_color'] = self.bg_color_entry.get()
            self.interface_custom_settings['fg_color'] = self.fg_color_entry.get()
            self.interface_custom_settings['font_family'] = self.font_entry.get()
            self.interface_custom_settings['font_size'] = int(self.font_size_scale.get())
            self.apply_interface_style()
            self.info_label.config(text="✅ Интерфейс обновлён")
        
        ttk.Button(custom_interface_frame, text="Применить настройки интерфейса",
                  command=apply_custom_interface).pack(fill=tk.X, padx=5, pady=5)
        
        # === СОХРАНЕНИЕ ===
        save_frame = ttk.LabelFrame(tab, text="💾 Сохранение")
        save_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.auto_save_var = tk.BooleanVar(value=self.auto_save_enabled)
        ttk.Checkbutton(save_frame, text=self.get_text('auto_save'), 
                       variable=self.auto_save_var,
                       command=self.toggle_auto_save).pack(anchor=tk.W, padx=5, pady=2)
        
        self.confirm_delete_var = tk.BooleanVar(value=self.config.get('confirm_delete', True))
        ttk.Checkbutton(save_frame, text=self.get_text('confirm_delete'),
                       variable=self.confirm_delete_var,
                       command=lambda: self.config.update({'confirm_delete': self.confirm_delete_var.get()})).pack(anchor=tk.W, padx=5, pady=2)
        
        # === ОБНОВЛЕНИЯ ===
        update_frame = ttk.LabelFrame(tab, text="🔄 Обновления")
        update_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.check_updates_var = tk.BooleanVar(value=self.config.get('check_updates', True))
        ttk.Checkbutton(update_frame, text="Проверять обновления при запуске", 
                       variable=self.check_updates_var,
                       command=self.toggle_update_check).pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(update_frame, text=f"Версия: {self.version}").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Button(update_frame, text="🔄 " + self.get_text('check_updates'), 
                  command=self.check_updates_manual).pack(fill=tk.X, padx=5, pady=2)
        
        # === О ПРОГРАММЕ ===
        info_frame = ttk.LabelFrame(tab, text="ℹ️ " + self.get_text('about'))
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(info_frame, text=f"{self.program_name} v{self.version}").pack(pady=5)
        ttk.Button(info_frame, text="📖 " + self.get_text('help_text'), command=self.show_help).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(info_frame, text="⌨️ " + self.get_text('hotkeys'), command=self.show_hotkeys).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(info_frame, text="ℹ️ " + self.get_text('about'), command=self.show_about).pack(fill=tk.X, padx=5, pady=2)
    
    def setup_preview(self, container):
        """Область предпросмотра"""
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
        
        canvas_frame = ttk.Frame(container)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#2b2b2b', highlightthickness=1,
                               highlightbackground='#555', cursor='cross')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        info_frame = ttk.Frame(container)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.info_label = ttk.Label(info_frame, text="✅ Готов к работе")
        self.info_label.pack(side=tk.LEFT)
        
        self.coord_label = ttk.Label(info_frame, text="X: 0 Y: 0")
        self.coord_label.pack(side=tk.RIGHT)
        
        self.size_label = ttk.Label(info_frame, text="")
        self.size_label.pack(side=tk.RIGHT, padx=10)
        
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
    
    def setup_properties_panel(self, container):
        """Панель свойств"""
        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        props_tab = ttk.Frame(notebook)
        notebook.add(props_tab, text="📐 " + self.get_text('properties'))
        
        # Позиция
        pos_frame = ttk.LabelFrame(props_tab, text="📍 " + self.get_text('position'))
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
        size_frame = ttk.LabelFrame(props_tab, text="📏 " + self.get_text('size'))
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
        
        ttk.Button(size_frame, text="🔒 Сохранить пропорции", command=self.lock_aspect).pack(fill=tk.X, pady=2)
        
        # Популярные форматы
        format_frame = ttk.LabelFrame(props_tab, text="📐 Популярные форматы")
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        formats = [
            ("4:3", 4/3), ("3:4", 3/4),
            ("16:9", 16/9), ("9:16", 9/16),
            ("1:1", 1), ("2:3", 2/3),
            ("3:2", 3/2), ("5:4", 5/4)
        ]
        
        format_btns = ttk.Frame(format_frame)
        format_btns.pack(fill=tk.X, pady=2)
        
        for i, (name, ratio) in enumerate(formats):
            row = i // 4
            col = i % 4
            btn = ttk.Button(format_btns, text=name, width=8,
                           command=lambda r=ratio: self.apply_format(r))
            btn.grid(row=row, column=col, padx=2, pady=2)
        
        # Поворот
        rot_frame = ttk.LabelFrame(props_tab, text="🔄 " + self.get_text('rotation'))
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
        opacity_frame = ttk.LabelFrame(props_tab, text="👁 " + self.get_text('opacity'))
        opacity_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.opacity_scale = ttk.Scale(opacity_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                       command=self.apply_opacity)
        self.opacity_scale.pack(fill=tk.X, padx=5, pady=2)
        self.opacity_label = ttk.Label(opacity_frame, text="100%")
        self.opacity_label.pack(pady=2)
        
        # Отражение
        mirror_frame = ttk.LabelFrame(props_tab, text="🔄 " + self.get_text('mirror'))
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
        menubar.add_cascade(label="📁 " + self.get_text('file'), menu=file_menu)
        file_menu.add_command(label="📄 " + self.get_text('new'), command=self.new_project, accelerator="Ctrl+N")
        file_menu.add_command(label="📂 " + self.get_text('open'), command=self.open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="💾 " + self.get_text('save'), command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="💾 " + self.get_text('save_as'), command=self.save_project_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="📤 " + self.get_text('export'), command=self.export_dialog, accelerator="Ctrl+E")
        file_menu.add_command(label="📥 " + self.get_text('import'), command=self.import_file, accelerator="Ctrl+I")
        file_menu.add_separator()
        file_menu.add_command(label="🚪 " + self.get_text('exit'), command=self.root.quit, accelerator="Ctrl+Q")
        
        # Правка
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="✏️ " + self.get_text('edit'), menu=edit_menu)
        edit_menu.add_command(label="↩ " + self.get_text('undo'), command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="↪ " + self.get_text('redo'), command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="✂️ " + self.get_text('cut'), command=self.cut_objects, accelerator="Ctrl+X")
        edit_menu.add_command(label="📋 " + self.get_text('copy'), command=self.copy_objects, accelerator="Ctrl+C")
        edit_menu.add_command(label="📋 " + self.get_text('paste'), command=self.paste_objects, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="🎯 " + self.get_text('select_all'), command=self.select_all, accelerator="Ctrl+A")
        edit_menu.add_command(label="❌ " + self.get_text('deselect'), command=self.deselect_all, accelerator="Esc")
        
        # Вид
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁 " + self.get_text('view'), menu=view_menu)
        view_menu.add_command(label="🔍 " + self.get_text('zoom_in'), command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="🔍 " + self.get_text('zoom_out'), command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="⟳ " + self.get_text('reset_view'), command=self.reset_view)
        view_menu.add_separator()
        view_menu.add_command(label="⬡ " + self.get_text('grid'), command=self.toggle_grid)
        view_menu.add_command(label="📐 " + self.get_text('rules'), command=self.toggle_rules)
        view_menu.add_command(label="📐 " + self.get_text('resize_handles'), command=self.toggle_resize_handles)
        
        # Обновление
        update_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🔄 " + self.get_text('check_updates'), menu=update_menu)
        update_menu.add_command(label="🔄 " + self.get_text('check_updates'), command=self.check_updates_manual)
        
        # Помощь
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ " + self.get_text('help'), menu=help_menu)
        help_menu.add_command(label="📖 " + self.get_text('help_text'), command=self.show_help)
        help_menu.add_command(label="⌨️ " + self.get_text('hotkeys'), command=self.show_hotkeys)
        help_menu.add_command(label="ℹ️ " + self.get_text('about'), command=self.show_about)
    
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
    
    def setup_context_menu(self):
        """Контекстное меню (ПКМ)"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="ℹ️ Информация", command=self.show_context_info)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✂️ Вырезать", command=self.cut_objects)
        self.context_menu.add_command(label="📋 Копировать", command=self.copy_objects)
        self.context_menu.add_command(label="📋 Вставить", command=self.paste_objects)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑 Удалить", command=self.delete_objects)
        
        # Привязываем ПКМ ко всем виджетам
        self.root.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """Показать контекстное меню"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def show_context_info(self):
        """Показать информацию по ПКМ"""
        info_text = """📖 Информация о программе

Редактор фона 1.0

Это программа для редактирования изображений,
позволяющая менять фон, добавлять объекты,
применять фильтры и эффекты, а также
работать со слоями.

Основные возможности:
• Добавление и удаление фона
• Работа с объектами и слоями
• Фильтры и эффекты
• Пакетная обработка
• Экспорт в различные форматы

Версия: 1.0
Разработчик: DeepSeek"""
        
        messagebox.showinfo("ℹ️ Информация", info_text)
    
    def setup_drag_drop(self):
        """Drag & Drop"""
        try:
            self.root.tk.call('package', 'require', 'tkdnd')
            self.root.drop_target_register('DND_Files')
            self.root.dnd_bind('<<Drop>>', self.on_drop)
        except:
            pass
    
    # === ФУНКЦИИ ИНТЕРФЕЙСА ===
    
    def apply_windows_style(self):
        """Применить стиль Windows"""
        style_name = self.windows_style_var.get()
        self.config['windows_style'] = style_name
        
        style = ttk.Style()
        
        if style_name == 'Windows XP':
            style.theme_use('classic')
            self.root.configure(bg='#3a6ea5')
        elif style_name == 'Windows Vista':
            try:
                style.theme_use('vista')
            except:
                style.theme_use('default')
            self.root.configure(bg='#d4d0c8')
        elif style_name == 'Windows 7':
            try:
                style.theme_use('vista')
            except:
                style.theme_use('default')
            self.root.configure(bg='#d4d0c8')
        elif style_name == 'Windows 8':
            try:
                style.theme_use('vista')
            except:
                style.theme_use('default')
            self.root.configure(bg='#00a2ed')
        elif style_name == 'Windows 10':
            try:
                style.theme_use('vista')
            except:
                style.theme_use('default')
            self.root.configure(bg='#0078d7')
        elif style_name == 'Windows 11':
            try:
                style.theme_use('vista')
            except:
                style.theme_use('default')
            self.root.configure(bg='#005fb8')
        
        self.update_status()
    
    def apply_interface_style(self):
        """Применить стиль интерфейса"""
        style_name = self.config.get('interface_style', 'Классический')
        
        # Получаем настройки из пресета или пользовательские
        if style_name in self.interface_presets:
            settings = self.interface_presets[style_name]
        else:
            settings = self.interface_custom_settings
        
        # Применяем настройки к корневому окну
        self.root.configure(bg=settings.get('bg_color', '#2b2b2b'))
        self.canvas.configure(bg=settings.get('bg_color', '#2b2b2b'))
        
        # Обновляем стиль
        style = ttk.Style()
        style.configure('TFrame', background=settings.get('bg_color', '#2b2b2b'))
        style.configure('TLabel', background=settings.get('bg_color', '#2b2b2b'),
                       foreground=settings.get('fg_color', '#ffffff'),
                       font=(settings.get('font_family', 'Segoe UI'), settings.get('font_size', 9)))
        style.configure('TButton', background=settings.get('button_color', '#3b3b3b'),
                       foreground=settings.get('fg_color', '#ffffff'),
                       font=(settings.get('font_family', 'Segoe UI'), settings.get('font_size', 9)))
        style.configure('TNotebook.Tab', padding=settings.get('padding', 5))
        
        self.update_status()
    
    def choose_interface_color(self, color_type):
        """Выбор цвета интерфейса"""
        color = colorchooser.askcolor()[1]
        if color:
            if color_type == 'bg_color':
                self.bg_color_entry.delete(0, tk.END)
                self.bg_color_entry.insert(0, color)
            elif color_type == 'fg_color':
                self.fg_color_entry.delete(0, tk.END)
                self.fg_color_entry.insert(0, color)
    
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
        self.update_status()
    
    def set_language(self, lang):
        """Установить язык"""
        self.current_language = lang
        self.config['language'] = lang
        
        # Обновляем заголовок окна
        program_name = self.get_text('program_name')
        self.root.title(f"{program_name} v{self.version}")
        
        self.update_status()
        self.info_label.config(text=f"✅ Язык: {'Русский' if lang == 'ru' else 'English'}")
        
        # TODO: Полное обновление интерфейса (для упрощения просто перезапускаем)
        messagebox.showinfo("Язык", "Для полного применения языка перезапустите программу")
    
    def toggle_auto_save(self):
        self.auto_save_enabled = self.auto_save_var.get()
    
    def toggle_update_check(self):
        self.config['check_updates'] = self.check_updates_var.get()
    
    def toggle_resize_handles(self):
        self.update_preview()
    
    def update_status(self):
        """Обновить статус"""
        status = "✅ Готов к работе"
        if self.has_ai:
            status += " | 🤖 ИИ доступен"
        if self.has_svg:
            status += " | 📤 SVG доступен"
        status += f" | {self.get_text('language')}: {'Русский' if self.current_language == 'ru' else 'English'}"
        status += f" | Стиль: {self.config.get('windows_style', 'Windows 10')}"
        self.info_label.config(text=status)
    
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
    
    def add_objects_batch(self):
        """Пакетное добавление объектов"""
        files = filedialog.askopenfilenames(
            title="Выберите несколько изображений",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )
        
        if files:
            count = 0
            for file_path in files:
                try:
                    img = Image.open(file_path)
                    obj = {
                        'image': img,
                        'x': 100 + count * 20,
                        'y': 100 + count * 20,
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
                    count += 1
                except Exception as e:
                    print(f"Ошибка загрузки {file_path}: {e}")
            
            self.selected_objects = self.objects[-count:] if count > 0 else []
            self.update_preview()
            self.add_to_history(f"Добавлено объектов: {count}")
            self.info_label.config(text=f"✅ Добавлено объектов: {count}")
    
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
            if self.config.get('confirm_delete', True):
                if not messagebox.askyesno("Удаление", f"Удалить слой '{self.layers[index]['name']}'?"):
                    return
            
            for obj in self.layers[index]['objects']:
                if obj in self.objects:
                    self.objects.remove(obj)
            del self.layers[index]
            if self.current_layer_index >= len(self.layers):
                self.current_layer_index = len(self.layers) - 1
            self.update_layer_list()
            self.update_preview()
            self.add_to_history("Удалён слой")
    
    def update_layer_list(self):
        """Обновить список слоёв"""
        self.layer_listbox.delete(0, tk.END)
        for i, layer in enumerate(reversed(self.layers)):
            visible = "👁" if layer['visible'] else "👁‍🗨"
            name = layer['name']
            count = len(layer['objects'])
            self.layer_listbox.insert(tk.END, f"{visible} {name} ({count})")
            if i == len(self.layers) - 1 - self.current_layer_index:
                self.layer_listbox.selection_set(i)
    
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
            
            for layer in self.layers:
                if not layer['visible']:
                    continue
                layer_img = self.render_layer(layer)
                if layer_img:
                    img = Image.alpha_composite(img.convert('RGBA'), layer_img)
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width < 10 or canvas_height < 10:
                canvas_width = 800
                canvas_height = 600
            
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
            
            img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img_resized)
            
            x_offset = (canvas_width - display_width) // 2
            y_offset = (canvas_height - display_height) // 2
            
            self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.photo)
            
            for obj in self.selected_objects:
                self.draw_selection(obj, x_offset, y_offset, display_width, display_height, img.width, img.height)
            
            if self.grid_visible:
                self.draw_grid(canvas_width, canvas_height)
            
            if self.rules_visible:
                self.draw_rules(canvas_width, canvas_height)
            
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
        """Рисование выделения"""
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
            handles = [(x1, y1), (x2, y1), (x1, y2), (x2, y2),
                      ((x1+x2)/2, y1), ((x1+x2)/2, y2), (x1, (y1+y2)/2), (x2, (y1+y2)/2)]
            for hx, hy in handles:
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
        self.grid_visible = not self.grid_visible
        self.update_preview()
    
    def toggle_rules(self):
        self.rules_visible = not self.rules_visible
        self.update_preview()
    
    def fit_to_window(self):
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
                if event.state & 0x0001:
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
        if event.state & 0x0004:
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
        self.deselect_all()
        self.info_label.config(text="✅ Выделение снято")
    
    def on_drop(self, event):
        """Drop файлов"""
        files = self.root.tk.splitlist(event.data)
        count = 0
        for file_path in files:
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                try:
                    img = Image.open(file_path)
                    
                    # Определяем, добавлять как фон или объект
                    if not self.backgrounds and count == 0:
                        # Если нет фона - добавляем как фон
                        self.backgrounds.append(img)
                        self.current_bg_index = len(self.backgrounds) - 1
                        self.current_background = img.copy()
                    else:
                        # Добавляем как объект
                        obj = {
                            'image': img,
                            'x': 100 + count * 20,
                            'y': 100 + count * 20,
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
                    count += 1
                except:
                    pass
        
        self.update_preview()
        self.add_to_history(f"Добавлено файлов: {count}")
        self.info_label.config(text=f"✅ Загружено: {count} файлов")
    
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
    
    # === УДАЛЕНИЕ ФОНА ===
    
    def remove_by_color(self):
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
    
    # === РАЗМЕР И ФОРМАТЫ ===
    
    def apply_format(self, ratio):
        """Применить формат (4:3, 16:9 и т.д.)"""
        if not self.selected_objects:
            messagebox.showinfo("Информация", "Выберите объекты")
            return
        
        for obj in self.selected_objects:
            current_ratio = obj['width'] / obj['height']
            
            if current_ratio > ratio:
                new_width = int(obj['height'] * ratio)
                new_height = obj['height']
            else:
                new_width = obj['width']
                new_height = int(obj['width'] / ratio)
            
            obj['width'] = new_width
            obj['height'] = new_height
            obj['image'] = obj['image'].resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        self.update_preview()
        self.add_to_history(f"Применён формат: {ratio:.2f}")
        self.info_label.config(text=f"✅ Формат применён")
    
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
    
    def update_custom_preset_list(self):
        self.custom_preset_list.delete(0, tk.END)
        for name in self.custom_presets.keys():
            self.custom_preset_list.insert(tk.END, name)
    
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
        if self.config.get('confirm_delete', True):
            if not messagebox.askyesno("Удаление", f"Удалить {len(self.selected_objects)} объектов?"):
                return
        
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
    
    def add_to_history(self, action_name):
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
        return {
            'objects': copy.deepcopy(self.objects),
            'layers': copy.deepcopy(self.layers),
            'background': self.current_background.copy() if self.current_background else None,
            'selected': [self.objects.index(obj) for obj in self.selected_objects if obj in self.objects]
        }
    
    def restore_state(self, state):
        self.objects = copy.deepcopy(state['objects'])
        self.layers = copy.deepcopy(state['layers'])
        if state['background']:
            self.current_background = state['background'].copy()
        self.selected_objects = [self.objects[i] for i in state['selected'] if i < len(self.objects)]
        
        self.update_layer_list()
        self.update_preview()
        self.update_properties_panel()
    
    def update_history_list(self):
        self.history_listbox.delete(0, tk.END)
        for i, item in enumerate(self.history):
            prefix = "▶ " if i == self.history_index else "  "
            self.history_listbox.insert(tk.END, f"{prefix}{item['name']}")
            if i == self.history_index:
                self.history_listbox.selection_set(i)
    
    def on_history_select(self, event):
        selected = self.history_listbox.curselection()
        if selected:
            index = selected[0]
            if index != self.history_index and index < len(self.history):
                self.history_index = index
                self.restore_state(self.history[index]['state'])
                self.update_history_list()
    
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
        op_types = ['gaussian_blur', 'sharpen', 'grayscale', 'sepia', 
                   'brightness', 'contrast', 'resize', 'rotate', 'invert']
        op_var = tk.StringVar()
        op_combo = ttk.Combobox(dialog, textvariable=op_var, 
                               values=op_types, state='readonly')
        op_combo.pack(pady=5)
        
        ttk.Label(dialog, text="Значение:").pack(pady=5)
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
    
    # === ЭКСПОРТ ===
    
    def export_dialog(self):
        if not self.current_background:
            messagebox.showinfo("Информация", "Нет изображения")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("📤 Экспорт")
        dialog.geometry("350x320")
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
        
        # ZIP опция
        zip_var = tk.BooleanVar(value=self.export_as_zip)
        ttk.Checkbutton(dialog, text=self.get_text('save_as_zip'), 
                       variable=zip_var,
                       command=lambda: setattr(self, 'export_as_zip', zip_var.get())).pack(anchor=tk.W, padx=10, pady=5)
        
        def do_export():
            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{format_var.get().lower()}",
                filetypes=[(format_var.get(), f"*.{format_var.get().lower()}")]
            )
            if file_path:
                self.export_image(file_path, format_var.get(), int(quality_scale.get()), zip_var.get())
                dialog.destroy()
        
        ttk.Button(dialog, text="📤 Экспортировать", command=do_export).pack(pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)
    
    def export_image(self, file_path, format_type='PNG', quality=90, as_zip=False):
        try:
            # Рендерим финальное изображение
            img = self.render_final_image()
            
            if as_zip:
                # Сохраняем как ZIP
                zip_path = file_path + '.zip'
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    temp_path = file_path + '.temp.' + format_type.lower()
                    self.save_image(img, temp_path, format_type, quality)
                    zipf.write(temp_path, os.path.basename(file_path))
                    os.remove(temp_path)
                self.info_label.config(text=f"✅ Экспортировано в ZIP: {os.path.basename(zip_path)}")
            else:
                # Сохраняем как обычный файл
                self.save_image(img, file_path, format_type, quality)
                self.info_label.config(text=f"✅ Экспортировано: {os.path.basename(file_path)}")
                
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def save_image(self, img, file_path, format_type, quality):
        """Сохранение изображения в указанном формате"""
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
    
    def render_final_image(self):
        """Рендеринг финального изображения (фон + все объекты)"""
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
            self.save_image(self.render_final_image(), file_path, 'PNG', 90)
    
    def export_svg(self, file_path):
        if HAS_SVG:
            temp_png = file_path + ".temp.png"
            self.save_image(self.render_final_image(), temp_png, 'PNG', 90)
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
            
            bg_paths = []
            for i, bg in enumerate(self.backgrounds):
                bg_path = os.path.join(data_folder, f"bg_{i}.png")
                bg.save(bg_path)
                bg_paths.append(os.path.join(name, f"bg_{i}.png"))
            
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
            
            layers_data = []
            for layer in self.layers:
                layers_data.append({
                    'name': layer['name'],
                    'visible': layer['visible'],
                    'opacity': layer['opacity'],
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
            
            self.backgrounds = []
            for bg_path in data['backgrounds']:
                abs_path = os.path.join(folder, bg_path)
                if os.path.exists(abs_path):
                    self.backgrounds.append(Image.open(abs_path))
            
            self.current_bg_index = data.get('current_bg_index', 0)
            if self.backgrounds:
                self.current_background = self.backgrounds[self.current_bg_index].copy()
            
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
            
            self.layers = []
            for layer_data in data.get('layers', []):
                layer = {
                    'name': layer_data['name'],
                    'visible': layer_data['visible'],
                    'opacity': layer_data['opacity'],
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
    
    def add_object_from_path(self, file_path):
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
    
    def update_properties_panel(self):
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
    
    # === ОБНОВЛЕНИЯ ===
    
    def check_updates_auto(self):
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
        success, msg = self.updater.apply_update(new_exe)
        if success:
            messagebox.showinfo("✅ Обновление", "Программа перезапустится")
            self.root.quit()
        else:
            messagebox.showerror("Ошибка", msg)
    
    # === ЗАГРУЗКА ПОСЛЕДНИХ ПРОЕКТОВ ===
    
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
        about = f"""🎨 {self.program_name} v{self.version}

✨ Возможности:
• 📚 Слои и объекты
• 🎨 Фильтры и эффекты  
• 📦 Пакетная обработка
• 🤖 ИИ удаление фона
• 📤 Экспорт в 7 форматов
• ⏳ История действий
• 💾 Автосохранение
• 🔄 Автообновление
• 🎨 Стили Windows (XP/Vista/7/8/10/11)
• 📐 Популярные форматы (4:3, 16:9, 1:1 и др.)
• 📦 Пакетное добавление объектов
• 💾 Экспорт в ZIP

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
2. Добавьте объекты (➕ Добавить объекты или пакетно)
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
• Используйте пакетное добавление для нескольких файлов
• При экспорте можно сохранить в ZIP

🎨 СТИЛИ WINDOWS:
• Windows XP - классический стиль
• Windows Vista - прозрачный стиль
• Windows 7 - аэро-стиль
• Windows 8 - плоский стиль
• Windows 10 - современный стиль
• Windows 11 - округлый стиль"""
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

📚 Слои:
F2 - Переименовать слой

📦 Пакетная:
Выделите несколько объектов и примените действие"""
        messagebox.showinfo("Горячие клавиши", hotkeys)


# === ЗАПУСК ===
if __name__ == "__main__":
    root = tk.Tk()
    app = BackgroundEditor(root)
    root.mainloop()