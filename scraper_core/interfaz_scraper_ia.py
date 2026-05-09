import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import sys
import os
import subprocess
import platform
from datetime import datetime
import queue
import time
from PIL import Image, ImageTk  # Asegúrate de tener Pillow instalado
from expediente_vencimientos_analyzer import analizar_vencimientos_expedientes

# Importar los códigos del scraper
# Asegúrate de que 'codigo_con_deox_ia.py' esté en el mismo directorio
from codigo_con_deox_ia import filtrar_por_fecha, analizar_expedientes_individuales

class TerminalRedirector:
    """Redirige la salida de print() hacia la terminal de la interfaz"""
    def __init__(self, text_widget, queue_obj):
        self.text_widget = text_widget
        self.queue = queue_obj

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass

class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔍 Scraper de Expedientes con Análisis IA - Portal PJN")
        self.root.geometry("1000x800")
        self.root.configure(bg='#f0f0f0')
        
        # Variables de configuración
        self.fecha_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.paginas_var = tk.StringVar(value="6")
        self.usuario_var = tk.StringVar(value="20286335528")
        self.password_var = tk.StringVar(value="")
        self.filas_deox_var = tk.StringVar(value="10")
        self.headless_var = tk.BooleanVar(value=True)
        
        # Nuevas variables para APIs
        self.gemini_api_var = tk.StringVar(value="")
        self.captcha_api_var = tk.StringVar(value="")
        
        # Variables de control
        self.ejecutando_extraccion = False
        self.ejecutando_analisis = False
        self.ejecutando_vencimientos = False
        
        # Queue para la comunicación entre threads
        self.output_queue = queue.Queue()
        
        # Configurar la interfaz
        self.setup_ui()
        
        # Iniciar el procesamiento de la cola de salida
        self.process_queue()

    def setup_ui(self):
        """Configura toda la interfaz de usuario"""
        
        # Título principal
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill='x', padx=10, pady=(10, 0))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="🔍 SCRAPER DE EXPEDIENTES CON ANÁLISIS IA - PORTAL PJN",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(expand=True)
        
        # Frame principal con dos columnas
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Columna izquierda - Configuración con Scroll
        config_canvas = tk.Canvas(main_frame, bg='#f0f0f0', highlightthickness=0)
        config_canvas.pack(side='left', fill='y', padx=(0, 5))

        config_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=config_canvas.yview)
        config_scrollbar.pack(side="left", fill="y")

        config_canvas.configure(yscrollcommand=config_scrollbar.set)
        config_canvas.bind('<Configure>', lambda e: config_canvas.configure(scrollregion = config_canvas.bbox("all")))
        
        # Frame interno para los widgets de configuración
        self.config_frame_inner = tk.Frame(config_canvas, bg='#f0f0f0')
        config_canvas.create_window((0, 0), window=self.config_frame_inner, anchor="nw")
        
        self.setup_config_section(self.config_frame_inner)
        
        # Columna derecha - Terminal y controles
        right_frame = tk.Frame(main_frame, bg='#f0f0f0')
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        self.setup_terminal_section(right_frame)
        self.setup_control_buttons(right_frame)

        # Bind mouse wheel for scrolling
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel) # Linux
        self.root.bind_all("<Button-5>", self._on_mousewheel) # Linux

    def _on_mousewheel(self, event):
        """Handles mouse wheel scrolling for the canvas."""
        if self.config_frame_inner.winfo_exists():
            canvas = self.config_frame_inner.master
            if canvas.winfo_exists():
                if event.num == 5 or event.delta == -120: # Scroll down
                    canvas.yview_scroll(1, "unit")
                elif event.num == 4 or event.delta == 120: # Scroll up
                    canvas.yview_scroll(-1, "unit")

    def setup_config_section(self, parent):
        """Configura la sección de configuración"""
        
        # Sección de Extracción de Expedientes
        extraccion_frame = tk.LabelFrame(parent, text="📋 Extracción de Expedientes", font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        extraccion_frame.pack(fill='x', pady=(10, 15), padx=5)
        
        # Fecha
        tk.Label(extraccion_frame, text="📅 Fecha a buscar:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', pady=(10, 5), padx=5)
        fecha_frame = tk.Frame(extraccion_frame, bg='#f0f0f0')
        fecha_frame.pack(fill='x', pady=(0, 10), padx=5)
        
        self.fecha_entry = tk.Entry(fecha_frame, textvariable=self.fecha_var, font=('Arial', 10), width=15)
        self.fecha_entry.pack(side='left')
        
        tk.Label(fecha_frame, text="(DD/MM/YYYY)", font=('Arial', 8), fg='gray', bg='#f0f0f0').pack(side='left', padx=(5, 0))
        
        # Páginas
        tk.Label(extraccion_frame, text="📄 Páginas a procesar:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', pady=(10, 5), padx=5)
        paginas_frame = tk.Frame(extraccion_frame, bg='#f0f0f0')
        paginas_frame.pack(fill='x', pady=(0, 10), padx=5)
        
        self.paginas_entry = tk.Entry(paginas_frame, textvariable=self.paginas_var, font=('Arial', 10), width=10)
        self.paginas_entry.pack(side='left')
        
        tk.Label(paginas_frame, text="(Consultas)", font=('Arial', 8), fg='gray', bg='#f0f0f0').pack(side='left', padx=(5, 0))
        
        # Filas DEOX
        tk.Label(extraccion_frame, text="📋 Filas DEOX a procesar:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', pady=(10, 5), padx=5)
        deox_frame = tk.Frame(extraccion_frame, bg='#f0f0f0')
        deox_frame.pack(fill='x', pady=(0, 10), padx=5)
        
        self.filas_deox_entry = tk.Entry(deox_frame, textvariable=self.filas_deox_var, font=('Arial', 10), width=10)
        self.filas_deox_entry.pack(side='left')
        
        tk.Label(deox_frame, text="(Máximo)", font=('Arial', 8), fg='gray', bg='#f0f0f0').pack(side='left', padx=(5, 0))
        
        # Separador
        separator1 = ttk.Separator(parent, orient='horizontal')
        separator1.pack(fill='x', pady=15, padx=5)
        
        # Sección de APIs
        api_frame = tk.LabelFrame(parent, text="🔑 Configuración de APIs", font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        api_frame.pack(fill='x', pady=(0, 15), padx=5)
        
        # API Gemini
        tk.Label(api_frame, text="🤖 API Key Gemini:", font=('Arial', 9), bg='#f0f0f0').pack(anchor='w', pady=(10, 2), padx=5)
        self.gemini_entry = tk.Entry(api_frame, textvariable=self.gemini_api_var, font=('Arial', 9), width=30, show='*')
        self.gemini_entry.pack(fill='x', pady=(0, 10), padx=5)
        
        # API 2Captcha
        tk.Label(api_frame, text="🔓 API Key 2Captcha:", font=('Arial', 9), bg='#f0f0f0').pack(anchor='w', pady=(5, 2), padx=5)
        self.captcha_entry = tk.Entry(api_frame, textvariable=self.captcha_api_var, font=('Arial', 9), width=30, show='*')
        self.captcha_entry.pack(fill='x', pady=(0, 10), padx=5)
        
        # Checkbox para mostrar APIs
        self.show_apis_var = tk.BooleanVar()
        show_apis_cb = tk.Checkbutton(
            api_frame,
            text="Mostrar API Keys",
            variable=self.show_apis_var,
            command=self.toggle_apis_visibility,
            font=('Arial', 8),
            bg='#f0f0f0'
        )
        show_apis_cb.pack(anchor='w', pady=(0, 10), padx=5)
        
        # Separador
        separator2 = ttk.Separator(parent, orient='horizontal')
        separator2.pack(fill='x', pady=15, padx=5)
        
        # Modo de ejecución
        tk.Label(parent, text="🖥️ Modo de ejecución:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', pady=(0, 5), padx=5)
        
        # Checkbox para modo headless
        headless_frame = tk.Frame(parent, bg='#f0f0f0')
        headless_frame.pack(fill='x', pady=(0, 10), padx=5)
        
        self.headless_checkbox = tk.Checkbutton(
            headless_frame,
            text="🔇 Modo Headless (sin ventana del navegador)",
            variable=self.headless_var,
            font=('Arial', 9),
            bg='#f0f0f0',
            command=self.on_headless_change
        )
        self.headless_checkbox.pack(anchor='w')
        
        # Etiqueta informativa sobre el modo
        self.modo_info_label = tk.Label(
            headless_frame,
            text="✅ Recomendado: Más rápido y consume menos recursos",
            font=('Arial', 8),
            fg='#27ae60',
            bg='#f0f0f0'
        )
        self.modo_info_label.pack(anchor='w', padx=(20, 0))
        
        # Separador
        separator3 = ttk.Separator(parent, orient='horizontal')
        separator3.pack(fill='x', pady=15, padx=5)
        
        # Credenciales
        tk.Label(parent, text="👤 Credenciales de acceso:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', pady=(0, 10), padx=5)
        
        # Usuario
        tk.Label(parent, text="Usuario:", font=('Arial', 9), bg='#f0f0f0').pack(anchor='w', pady=(5, 2), padx=5)
        self.usuario_entry = tk.Entry(parent, textvariable=self.usuario_var, font=('Arial', 10), width=20)
        self.usuario_entry.pack(fill='x', pady=(0, 10), padx=5)
        
        # Contraseña
        tk.Label(parent, text="Contraseña:", font=('Arial', 9), bg='#f0f0f0').pack(anchor='w', pady=(5, 2), padx=5)
        self.password_entry = tk.Entry(parent, textvariable=self.password_var, font=('Arial', 10), width=20, show='*')
        self.password_entry.pack(fill='x', pady=(0, 10), padx=5)
        
        # Checkbox para mostrar contraseña
        self.show_password_var = tk.BooleanVar()
        show_password_cb = tk.Checkbutton(
            parent,
            text="Mostrar contraseña",
            variable=self.show_password_var,
            command=self.toggle_password_visibility,
            font=('Arial', 8),
            bg='#f0f0f0'
        )
        show_password_cb.pack(anchor='w', pady=(0, 15), padx=5)
        
        # Separador
        separator4 = ttk.Separator(parent, orient='horizontal')
        separator4.pack(fill='x', pady=15, padx=5)
        
        # Información
        info_frame = tk.Frame(parent, bg='#e8f4fd', relief='ridge', bd=1)
        info_frame.pack(fill='x', pady=(0, 10), padx=5)
        
        info_text = """ℹ️ INFORMACIÓN:
• PROCESO 1 - Extracción:
  - Consultas (con paginación)
  - Notificaciones (automático)
  - DEOX (con límite configurable)
  - Resultado: expedientes.xlsx

• PROCESO 2 - Análisis IA:
  - Análisis individual con Gemini
  - Extracción de texto de PDFs
  - OCR con Tesseract
  - Resultado: expedientes_analizados.xlsx

• PROCESO 3 - Análisis de Vencimientos:
  - Busca vencimientos en cada expediente
  - Resultado: expedientes_vencimientos.xlsx

• Control de duplicados automático
• Modo Headless recomendado"""
        
        tk.Label(
            info_frame,
            text=info_text,
            font=('Arial', 8),
            bg='#e8f4fd',
            fg='#2c3e50',
            justify='left'
        ).pack(padx=10, pady=10)

    def on_headless_change(self):
        """Se ejecuta cuando cambia el estado del checkbox headless"""
        if self.headless_var.get():
            self.modo_info_label.config(
                text="✅ Recomendado: Más rápido y consume menos recursos",
                fg='#27ae60'
            )
        else:
            self.modo_info_label.config(
                text="⚠️ Modo visual: Más lento, pero puedes ver el navegador",
                fg='#f39c12'
            )

    def toggle_password_visibility(self):
        """Alterna la visibilidad de la contraseña"""
        if self.show_password_var.get():
            self.password_entry.config(show='')
        else:
            self.password_entry.config(show='*')

    def toggle_apis_visibility(self):
        """Alterna la visibilidad de las API Keys"""
        if self.show_apis_var.get():
            self.gemini_entry.config(show='')
            self.captcha_entry.config(show='')
        else:
            self.gemini_entry.config(show='*')
            self.captcha_entry.config(show='*')

    def setup_terminal_section(self, parent):
        """Configura la sección de terminal"""
        
        terminal_frame = tk.LabelFrame(
            parent,
            text="🖥️ Terminal de progreso",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        terminal_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Frame para la terminal con scrollbar
        text_frame = tk.Frame(terminal_frame)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Terminal de texto
        self.terminal_text = tk.Text(
            text_frame,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#00ff00',
            insertbackground='#00ff00',
            wrap='word',
            state='disabled'
        )
        
        # Scrollbar para la terminal
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.terminal_text.yview)
        self.terminal_text.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar terminal y scrollbar
        self.terminal_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mensaje inicial
        self.write_to_terminal("🚀 Scraper de Expedientes con Análisis IA iniciado\n")
        self.write_to_terminal("📋 Configure los parámetros y APIs\n")
        self.write_to_terminal("🔇 Modo Headless activado por defecto (recomendado)\n")
        self.write_to_terminal("=" * 60 + "\n\n")

    def setup_control_buttons(self, parent):
        """Configura los botones de control"""
        
        buttons_frame = tk.Frame(parent, bg='#f0f0f0')
        buttons_frame.pack(fill='x', pady=(0, 10))
        
        # Frame para botones principales
        main_buttons_frame = tk.Frame(buttons_frame, bg='#f0f0f0')
        main_buttons_frame.pack(fill='x', pady=(0, 10))
        
        # Botón Extraer Expedientes
        self.extract_button = tk.Button(
            main_buttons_frame,
            text="📋 EXTRAER\nEXPEDIENTES",
            font=('Arial', 10, 'bold'),
            bg='#27ae60',
            fg='white',
            relief='raised',
            bd=3,
            command=self.iniciar_extraccion,
            height=2
        )
        self.extract_button.pack(side='left', fill='x', expand=True, padx=(0, 3))
        
        # Botón Analizar con IA
        self.analyze_button = tk.Button(
            main_buttons_frame,
            text="🤖 ANALIZAR\nCON IA",
            font=('Arial', 10, 'bold'),
            bg='#3498db',
            fg='white',
            relief='raised',
            bd=3,
            command=self.iniciar_analisis,
            height=2
        )
        self.analyze_button.pack(side='left', fill='x', expand=True, padx=3)
        
        # Botón Analizar Vencimientos
        self.vencimientos_button = tk.Button(
            main_buttons_frame,
            text="⏰ ANALIZAR\nVENCIMIENTOS",
            font=('Arial', 10, 'bold'),
            bg='#e67e22',
            fg='white',
            relief='raised',
            bd=3,
            command=self.iniciar_vencimientos,
            height=2
        )
        self.vencimientos_button.pack(side='right', fill='x', expand=True, padx=(3, 0))
        
        # Frame para botones secundarios
        secondary_buttons = tk.Frame(buttons_frame, bg='#f0f0f0')
        secondary_buttons.pack(fill='x', pady=(10, 0))
        
        # Botón abrir Excel expedientes
        self.excel_expedientes_button = tk.Button(
            secondary_buttons,
            text="📊 Expedientes.xlsx",
            font=('Arial', 9),
            bg='#2ecc71',
            fg='white',
            command=lambda: self.abrir_excel("expedientes.xlsx"),
            width=15
        )
        self.excel_expedientes_button.pack(side='left', padx=(0, 5))
        
        # Botón abrir Excel analizados
        self.excel_analizados_button = tk.Button(
            secondary_buttons,
            text="📈 Analizados.xlsx",
            font=('Arial', 9),
            bg='#9b59b6',
            fg='white',
            command=lambda: self.abrir_excel("expedientes_analizados.xlsx"),
            width=15
        )
        self.excel_analizados_button.pack(side='left', padx=5)
        
        # Botón abrir Excel vencimientos
        self.excel_vencimientos_button = tk.Button(
            secondary_buttons,
            text="⏰ Vencimientos.xlsx",
            font=('Arial', 9),
            bg='#e67e22',
            fg='white',
            command=lambda: self.abrir_excel("expedientes_vencimientos.xlsx"),
            width=15
        )
        self.excel_vencimientos_button.pack(side='left', padx=5)
        
        # Botón limpiar terminal
        self.clear_button = tk.Button(
            secondary_buttons,
            text="🧹 Limpiar",
            font=('Arial', 9),
            bg='#95a5a6',
            fg='white',
            command=self.limpiar_terminal,
            width=12
        )
        self.clear_button.pack(side='left', padx=5)
        
        # Botón salir
        self.exit_button = tk.Button(
            secondary_buttons,
            text="❌ Salir",
            font=('Arial', 9),
            bg='#e74c3c',
            fg='white',
            command=self.salir_aplicacion,
            width=12
        )
        self.exit_button.pack(side='right')
        
        # Barra de progreso
        self.progress_frame = tk.Frame(buttons_frame, bg='#f0f0f0')
        self.progress_frame.pack(fill='x', pady=(10, 0))
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            font=('Arial', 9),
            bg='#f0f0f0'
        )
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            length=400
        )
        self.progress_bar.pack(fill='x', pady=(5, 0))

    def write_to_terminal(self, text):
        """Escribe texto en la terminal"""
        self.terminal_text.config(state='normal')
        self.terminal_text.insert('end', text)
        self.terminal_text.see('end')
        self.terminal_text.config(state='disabled')
        self.root.update_idletasks()

    def limpiar_terminal(self):
        """Limpia el contenido de la terminal"""
        self.terminal_text.config(state='normal')
        self.terminal_text.delete(1.0, 'end')
        self.terminal_text.config(state='disabled')
        self.write_to_terminal("🧹 Terminal limpiada\n\n")

    def validar_datos_extraccion(self):
        """Valida los datos para extracción"""
        # Validar fecha
        fecha = self.fecha_var.get().strip()
        if not fecha:
            messagebox.showerror("Error", "Por favor ingrese una fecha")
            return False
        
        try:
            datetime.strptime(fecha, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use DD/MM/YYYY")
            return False
        
        # Validar páginas
        try:
            paginas = int(self.paginas_var.get())
            if paginas < 1 or paginas > 50:
                messagebox.showerror("Error", "El número de páginas debe estar entre 1 y 10")
                return False
        except ValueError:
            messagebox.showerror("Error", "El número de páginas debe ser un número entero")
            return False
        
        # Validar filas DEOX
        try:
            filas_deox = int(self.filas_deox_var.get())
            if filas_deox < 1 or filas_deox > 100:
                messagebox.showerror("Error", "El número de filas DEOX debe estar entre 1 y 100")
                return False
        except ValueError:
            messagebox.showerror("Error", "El número de filas DEOX debe ser un número entero")
            return False
        
        # Validar credenciales
        if not self.usuario_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese el usuario")
            return False
        
        if not self.password_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese la contraseña")
            return False
        
        return True

    def validar_datos_analisis(self):
        """Valida los datos para análisis"""
        # Verificar que existe el archivo de expedientes
        if not os.path.exists("expedientes.xlsx"):
            messagebox.showerror("Error", "No se encontró el archivo 'expedientes.xlsx'.\nPrimero debe extraer expedientes.")
            return False
        
        # Validar API Keys
        if not self.gemini_api_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese la API Key de Gemini")
            return False
        
        if not self.captcha_api_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese la API Key de 2Captcha")
            return False
        
        # Validar credenciales
        if not self.usuario_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese el usuario")
            return False
        
        if not self.password_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese la contraseña")
            return False
        
        return True

    def validar_datos_vencimientos(self):
        """Valida los datos para análisis de vencimientos"""
        # Verificar que existe el archivo de expedientes
        if not os.path.exists("expedientes.xlsx"):
            messagebox.showerror("Error", "No se encontró el archivo 'expedientes.xlsx'.\nPrimero debe extraer expedientes.")
            return False
        
        # Validar API Keys
        if not self.gemini_api_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese la API Key de Gemini")
            return False
        
        if not self.captcha_api_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese la API Key de 2Captcha")
            return False
        
        # Validar credenciales
        if not self.usuario_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese el usuario")
            return False
        
        if not self.password_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese la contraseña")
            return False
        
        return True

    def iniciar_extraccion(self):
        """Inicia el proceso de extracción de expedientes"""
        if self.ejecutando_extraccion or self.ejecutando_analisis or self.ejecutando_vencimientos:
            messagebox.showwarning("Advertencia", "Ya hay un proceso en ejecución")
            return
        
        if not self.validar_datos_extraccion():
            return
        
        self.ejecutando_extraccion = True
        
        # Cambiar interfaz
        self.extract_button.config(
            text="⏹️ DETENER EXTRACCIÓN",
            bg='#e74c3c'
        )
        self.analyze_button.config(state='disabled')
        self.vencimientos_button.config(state='disabled')
        
        # Mostrar progreso
        modo_texto = "🔇 Modo Headless" if self.headless_var.get() else "🖥️ Modo Visual"
        self.progress_label.config(text=f"🔄 Extrayendo expedientes... {modo_texto}")
        self.progress_bar.start(10)
        
        # Deshabilitar campos
        self.deshabilitar_campos()
        
        # Limpiar terminal
        self.limpiar_terminal()
        
        # Redirigir stdout
        self.original_stdout = sys.stdout
        sys.stdout = TerminalRedirector(self.terminal_text, self.output_queue)
        
        # Iniciar thread
        self.extraccion_thread = threading.Thread(target=self.ejecutar_extraccion, daemon=True)
        self.extraccion_thread.start()

    def iniciar_analisis(self):
        """Inicia el proceso de análisis con IA"""
        if self.ejecutando_extraccion or self.ejecutando_analisis or self.ejecutando_vencimientos:
            messagebox.showwarning("Advertencia", "Ya hay un proceso en ejecución")
            return
        
        if not self.validar_datos_analisis():
            return
        
        self.ejecutando_analisis = True
        
        # Cambiar interfaz
        self.analyze_button.config(
            text="⏹️ DETENER ANÁLISIS",
            bg='#e74c3c'
        )
        self.extract_button.config(state='disabled')
        self.vencimientos_button.config(state='disabled')
        
        # Mostrar progreso
        self.progress_label.config(text="🤖 Analizando expedientes con IA...")
        self.progress_bar.start(10)
        
        # Deshabilitar campos
        self.deshabilitar_campos()
        
        # Limpiar terminal
        self.limpiar_terminal()
        
        # Redirigir stdout
        self.original_stdout = sys.stdout
        sys.stdout = TerminalRedirector(self.terminal_text, self.output_queue)
        
        # Iniciar thread
        self.analisis_thread = threading.Thread(target=self.ejecutar_analisis, daemon=True)
        self.analisis_thread.start()

    def iniciar_vencimientos(self):
        """Inicia el proceso de análisis de vencimientos"""
        if self.ejecutando_extraccion or self.ejecutando_analisis or self.ejecutando_vencimientos:
            messagebox.showwarning("Advertencia", "Ya hay un proceso en ejecución")
            return
        
        if not self.validar_datos_vencimientos():
            return
        
        # Confirmar inicio del proceso
        respuesta = messagebox.askyesno(
            "Confirmar Análisis de Vencimientos",
            "Este proceso analizará cada expediente individualmente buscando vencimientos.\n\n"
            "⚠️ ADVERTENCIA: Este proceso puede tomar mucho tiempo dependiendo de la cantidad de expedientes.\n\n"
            "¿Desea continuar?"
        )
        
        if not respuesta:
            return
        
        self.ejecutando_vencimientos = True
        
        # Cambiar interfaz
        self.vencimientos_button.config(
            text="⏹️ DETENER\nVENCIMIENTOS",
            bg='#e74c3c'
        )
        self.extract_button.config(state='disabled')
        self.analyze_button.config(state='disabled')
        
        # Mostrar progreso
        modo_texto = "🔇 Modo Headless" if self.headless_var.get() else "🖥️ Modo Visual"
        self.progress_label.config(text=f"⏰ Analizando vencimientos... {modo_texto}")
        self.progress_bar.start(10)
        
        # Deshabilitar campos
        self.deshabilitar_campos()
        
        # Limpiar terminal
        self.limpiar_terminal()
        
        # Redirigir stdout
        self.original_stdout = sys.stdout
        sys.stdout = TerminalRedirector(self.terminal_text, self.output_queue)
        
        # Iniciar thread
        self.vencimientos_thread = threading.Thread(target=self.ejecutar_vencimientos, daemon=True)
        self.vencimientos_thread.start()

    def ejecutar_extraccion(self):
        """Ejecuta la extracción en un thread separado"""
        try:
            fecha = self.fecha_var.get().strip()
            paginas = int(self.paginas_var.get())
            filas_deox = int(self.filas_deox_var.get())
            usuario = self.usuario_var.get().strip()
            password = self.password_var.get().strip()
            headless = self.headless_var.get()
            
            print(f"🚀 INICIANDO EXTRACCIÓN DE EXPEDIENTES")
            print(f"📅 Fecha objetivo: {fecha}")
            print(f"📄 Páginas a procesar: {paginas}")
            print(f"📋 Filas DEOX máximas: {filas_deox}")
            print(f"👤 Usuario: {usuario}")
            print(f"🖥️ Modo: {'Headless (sin ventana)' if headless else 'Visual (con ventana)'}")
            print("=" * 60)
            
            print("🔧 Configurando navegador...")
            print("🌐 Conectando al Portal PJN...")
            print("🔐 Iniciando sesión...")
            
            # Ejecutar extracción
            filtrar_por_fecha(fecha, paginas, usuario, password, headless, filas_deox)
            
            print("\n" + "=" * 60)
            print("✅ EXTRACCIÓN COMPLETADA EXITOSAMENTE")
            print("📊 Revise el archivo expedientes.xlsx")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ ERROR DURANTE LA EXTRACCIÓN:")
            print(f"   {str(e)}")
            if self.headless_var.get():
                print("💡 Sugerencia: Si hay problemas en modo headless,")
                print("   desactive la opción y pruebe en modo visual")
            print("=" * 60)
        finally:
            # Restaurar stdout
            sys.stdout = self.original_stdout
            
            # Actualizar interfaz en el thread principal
            self.root.after(0, self.extraccion_completada)

    def ejecutar_analisis(self):
        """Ejecuta el análisis en un thread separado"""
        try:
            usuario = self.usuario_var.get().strip()
            password = self.password_var.get().strip()
            headless = self.headless_var.get()
            gemini_api = self.gemini_api_var.get().strip()
            captcha_api = self.captcha_api_var.get().strip()
            
            print(f"🤖 INICIANDO ANÁLISIS CON IA")
            print(f"👤 Usuario: {usuario}")
            print(f"🖥️ Modo: {'Headless (sin ventana)' if headless else 'Visual (con ventana)'}")
            print(f"🔑 API Gemini: {'Configurada ✅' if gemini_api else 'No configurada ❌'}")
            print(f"🔓 API 2Captcha: {'Configurada ✅' if captcha_api else 'No configurada ❌'}")
            print("=" * 60)
            
            print("🧠 Configurando modelo Gemini...")
            print("🔧 Inicializando sistema de análisis IA...")
            print("📄 Cargando archivo expedientes.xlsx...")
            print("🔍 Preparando análisis individual de expedientes...")
            print("⚡ Sistema IA listo para procesar")
            print("-" * 40)
            
            # Ejecutar análisis
            analizar_expedientes_individuales(usuario, password, headless, gemini_api, captcha_api)
            
            print("\n" + "=" * 60)
            print("✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
            print("📊 Revise el archivo expedientes_analizados.xlsx")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ ERROR DURANTE EL ANÁLISIS:")
            print(f"   {str(e)}")
            print("💡 Sugerencias:")
            print("   - Verifique las API Keys")
            print("   - Compruebe la conexión a internet")
            print("   - Revise que expedientes.xlsx existe")
            print("=" * 60)
        finally:
            # Restaurar stdout
            sys.stdout = self.original_stdout
            
            # Actualizar interfaz en el thread principal
            self.root.after(0, self.analisis_completado)

    def ejecutar_vencimientos(self):
        """Ejecuta el análisis de vencimientos en un thread separado"""
        try:
            gemini_api = self.gemini_api_var.get().strip()
            captcha_api = self.captcha_api_var.get().strip()
            headless = self.headless_var.get()
            
            print(f"⏰ INICIANDO ANÁLISIS DE VENCIMIENTOS")
            print(f"🖥️ Modo: {'Headless (sin ventana)' if headless else 'Visual (con ventana)'}")
            print(f"🔑 API Gemini: {'Configurada ✅' if gemini_api else 'No configurada ❌'}")
            print(f"🔓 API 2Captcha: {'Configurada ✅' if captcha_api else 'No configurada ❌'}")
            print("=" * 60)
            
            print("🧠 Configurando modelo Gemini para análisis de vencimientos...")
            print("📊 Cargando expedientes desde Excel...")
            print("🔍 Preparando análisis especializado en fechas de vencimiento...")
            print("⚡ Sistema de análisis de vencimientos listo")
            print("⚠️  Este proceso puede tomar tiempo considerable...")
            print("-" * 40)
            
            analizar_vencimientos_expedientes(gemini_api, captcha_api, headless)
            
            print("\n" + "=" * 60)
            print("✅ ANÁLISIS DE VENCIMIENTOS COMPLETADO")
            print("📊 Revise el archivo expedientes_vencimientos.xlsx")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ ERROR DURANTE EL ANÁLISIS DE VENCIMIENTOS:")
            print(f"   {str(e)}")
            print("💡 Sugerencias:")
            print("   - Verifique las API Keys de Gemini")
            print("   - Compruebe que expedientes.xlsx existe")
            print("   - Revise la conexión a internet")
            print("=" * 60)
        finally:
            # Restaurar stdout
            sys.stdout = self.original_stdout
            
            # Actualizar interfaz en el thread principal
            self.root.after(0, self.vencimientos_completado)

    def extraccion_completada(self):
        """Se ejecuta cuando la extracción termina"""
        self.ejecutando_extraccion = False
        
        # Restaurar interfaz
        self.extract_button.config(
            text="📋 EXTRAER\nEXPEDIENTES",
            bg='#27ae60'
        )
        self.analyze_button.config(state='normal')
        self.vencimientos_button.config(state='normal')
        self.progress_label.config(text="")
        self.progress_bar.stop()
        
        # Habilitar campos
        self.habilitar_campos()
        
        # Mostrar notificación
        messagebox.showinfo("Completado", "La extracción ha terminado. Revise la terminal para más detalles.")

    def analisis_completado(self):
        """Se ejecuta cuando el análisis termina"""
        self.ejecutando_analisis = False
        
        # Restaurar interfaz
        self.analyze_button.config(
            text="🤖 ANALIZAR\nCON IA",
            bg='#3498db'
        )
        self.extract_button.config(state='normal')
        self.vencimientos_button.config(state='normal')
        self.progress_label.config(text="")
        self.progress_bar.stop()
        
        # Habilitar campos
        self.habilitar_campos()
        
        # Mostrar notificación
        messagebox.showinfo("Completado", "El análisis ha terminado. Revise la terminal para más detalles.")

    def vencimientos_completado(self):
        """Se ejecuta cuando el análisis de vencimientos termina"""
        self.ejecutando_vencimientos = False
        
        # Restaurar interfaz
        self.vencimientos_button.config(
            text="⏰ ANALIZAR\nVENCIMIENTOS",
            bg='#e67e22'
        )
        self.extract_button.config(state='normal')
        self.analyze_button.config(state='normal')
        self.progress_label.config(text="")
        self.progress_bar.stop()
        
        # Habilitar campos
        self.habilitar_campos()
        
        # Mostrar notificación
        messagebox.showinfo("Completado", "El análisis de vencimientos ha terminado. Revise la terminal para más detalles.")

    def deshabilitar_campos(self):
        """Deshabilita los campos de entrada"""
        self.fecha_entry.config(state='disabled')
        self.paginas_entry.config(state='disabled')
        self.filas_deox_entry.config(state='disabled')
        self.usuario_entry.config(state='disabled')
        self.password_entry.config(state='disabled')
        self.gemini_entry.config(state='disabled')
        self.captcha_entry.config(state='disabled')
        self.headless_checkbox.config(state='disabled')

    def habilitar_campos(self):
        """Habilita los campos de entrada"""
        self.fecha_entry.config(state='normal')
        self.paginas_entry.config(state='normal')
        self.filas_deox_entry.config(state='normal')
        self.usuario_entry.config(state='normal')
        self.password_entry.config(state='normal')
        self.gemini_entry.config(state='normal')
        self.captcha_entry.config(state='normal')
        self.headless_checkbox.config(state='normal')

    def abrir_excel(self, archivo):
        """Abre el archivo Excel especificado"""
        if os.path.exists(archivo):
            try:
                if platform.system() == "Windows":
                    os.startfile(archivo)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", archivo])
                else:  # Linux
                    subprocess.run(["xdg-open", archivo])
                
                self.write_to_terminal(f"📊 Abriendo {archivo}...\n")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el archivo Excel:\n{str(e)}")
        else:
            messagebox.showwarning("Archivo no encontrado", f"El archivo {archivo} no existe.\nEjecute el proceso correspondiente primero.")

    def salir_aplicacion(self):
        """Cierra la aplicación"""
        if self.ejecutando_extraccion or self.ejecutando_analisis or self.ejecutando_vencimientos:
            respuesta = messagebox.askyesno(
                "Confirmar salida",
                "Hay un proceso en ejecución. ¿Está seguro de que desea salir?"
            )
            if not respuesta:
                return
        
        self.root.quit()
        self.root.destroy()

    def process_queue(self):
        """Procesa la cola de salida para actualizar la terminal"""
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.write_to_terminal(message)
        except queue.Empty:
            pass
        
        # Programar la próxima verificación
        self.root.after(100, self.process_queue)

def main():
    """Función principal"""
    root = tk.Tk()
    # 🧠 Agregar ícono personalizado
    try:
        icon_image = Image.open("icono_pjn.png")  # tu archivo .png
        icon_photo = ImageTk.PhotoImage(icon_image)
        root.iconphoto(False, icon_photo)
    except Exception as e:
        print("No se pudo cargar el ícono:", e)

    app = ScraperGUI(root)
    
    # Configurar el cierre de la ventana
    root.protocol("WM_DELETE_WINDOW", app.salir_aplicacion)
    
    # Centrar la ventana
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Iniciar la aplicación
    root.mainloop()

if __name__ == "__main__":
    main()
