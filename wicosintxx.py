import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import json
import os
import requests
import subprocess
import webbrowser
from urllib.parse import quote_plus
import threading
import time

# --- Configuración y Utilidades ---
CONFIG_FILE = "apis.json"

def cargar_apis():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_apis(apis):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(apis, f, indent=4)

# --- Clase Principal de la Aplicación ---
class WicOsintXApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WicOsintX")
        self.root.geometry("800x600")
        self.apis = cargar_apis()
        self.link_map = {} 
        self._crear_interfaz()

    def _crear_interfaz(self):
        self.frame_menu = tk.Frame(self.root, width=200, bg="lightgray")
        self.frame_menu.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        opciones = [
            ("👤 Persona (Nombre/DNI)", self._mostrar_menu_persona),
            ("🔍 IP (Opciones)", self._mostrar_menu_ip),
            ("🌐 Dominio (WHOIS)", lambda: self._crear_ventana_input("Análisis de Dominio (WHOIS)", self._ejecutar_analisis_dominio)),
            ("📧 Email (Opciones)", self._mostrar_menu_email),
            ("👤 Usuario (Redes)", self._mostrar_menu_usuario),
            ("🖼 Imagen (Opciones)", self._mostrar_menu_imagen),
            ("📱 Teléfono (Opciones)", self._mostrar_menu_telefono),
            ("---", None),
            ("⚙️ Claves API", self._configurar_apis),
            ("🧹 Limpiar Resultados", self._limpiar_resultado)
        ]

        for texto, comando in opciones:
            if comando:
                tk.Button(self.frame_menu, text=texto, command=comando, width=25).pack(pady=4)
            else:
                tk.Label(self.frame_menu, text=texto, bg="lightgray", fg="gray").pack(pady=2)

        self.text_resultado = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, bg="#2b2b2b", fg="white", insertbackground="white")
        self.text_resultado.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configuración para que los enlaces sean clickables
        self.text_resultado.tag_config("link", foreground="cyan", underline=1)
        self.text_resultado.tag_bind("link", "<Button-1>", self._abrir_link)
        self.text_resultado.tag_bind("link", "<Enter>", lambda e: self.text_resultado.config(cursor="hand2"))
        self.text_resultado.tag_bind("link", "<Leave>", lambda e: self.text_resultado.config(cursor=""))

        # Tags para estados de búsqueda
        self.text_resultado.tag_config("success", foreground="lightgreen")
        self.text_resultado.tag_config("not_found", foreground="red")
        self.text_resultado.tag_config("info", foreground="yellow")
        self.text_resultado.tag_config("error", foreground="orange")
        self.text_resultado.tag_config("pending", foreground="gray")


    def _abrir_link(self, event):
        """Abre la URL asociada a una etiqueta 'link' cuando se hace clic."""
        index = self.text_resultado.index(f"@{event.x},{event.y}")
        tags = self.text_resultado.tag_names(index)
        for tag in tags:
            if tag.startswith("link-"):
                url = self.link_map.get(tag)
                if url:
                    webbrowser.open(url)
                return

    def _ejecutar_en_hilo(self, funcion, *args):
        hilo = threading.Thread(target=funcion, args=args, daemon=True)
        hilo.start()

    def _mostrar_resultado(self, texto, tags=None):
        """Inserta texto en el área de resultados y hace scroll al final, aceptando tags."""
        # Usamos .after para asegurar que la actualización de la UI se hace en el hilo principal
        self.root.after(0, lambda: self._insertar_en_ui(texto, tags))

    def _insertar_en_ui(self, texto, tags):
        """Función auxiliar para insertar texto en el scrolledtext desde el hilo principal."""
        self.text_resultado.insert(tk.END, texto)
        if tags:
            # Apply tags from the start of the inserted text to the end
            start_index = f"{self.text_resultado.index(tk.END)} - {len(texto)}c"
            end_index = self.text_resultado.index(tk.END)
            # Check if tags is a single string or a tuple/list of strings
            if isinstance(tags, str):
                self.text_resultado.tag_add(tags, start_index, end_index)
            else: # Assume it's an iterable of tags
                for tag in tags:
                    self.text_resultado.tag_add(tag, start_index, end_index)
        self.text_resultado.see(tk.END)


    def _limpiar_resultado(self):
        self.text_resultado.delete(1.0, tk.END)
        self.link_map.clear() # Limpiar el mapa de enlaces también

    def _configurar_apis(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Configurar Claves API")
        ventana.geometry("400x550")
        ventana.transient(self.root)
        ventana.grab_set()
        
        api_entries_vars = {}

        def guardar():
            for k, var in api_entries_vars.items():
                self.apis[k] = var.get()
            guardar_apis(self.apis)
            messagebox.showinfo("Éxito", "Claves API guardadas correctamente", parent=ventana)
            ventana.destroy()

        api_keys_list = [
            "veriphone", "abstractapi", "shodan", "dehashed_user",
            "dehashed_pass", "abstractapi_email", "abstractapi_ip",
            "censys_uid", "censys_secret"
        ]

        for i, clave in enumerate(api_keys_list):
            tk.Label(ventana, text=f"{clave}:").pack(pady=2, anchor=tk.W, padx=10)
            var = tk.StringVar(value=self.apis.get(clave, ""))
            entry = tk.Entry(ventana, textvariable=var, width=50)
            entry.pack(pady=2, padx=10)
            api_entries_vars[clave] = var

            menu = tk.Menu(entry, tearoff=0)
            menu.add_command(label="Copiar", command=lambda e=entry: e.event_generate("<<Copy>>"))
            menu.add_command(label="Pegar", command=lambda e=entry: e.event_generate("<<Paste>>"))
            entry.bind("<Button-3>", lambda event, m=menu: m.tk_popup(event.x_root, event.y_root))

        tk.Button(ventana, text="Guardar Claves", command=guardar, bg="#4CAF50", fg="white").pack(pady=15)
        ventana.protocol("WM_DELETE_WINDOW", lambda: self.root.grab_release() or ventana.destroy())


    def _crear_ventana_input(self, titulo, accion_callback):
        ventana_input = tk.Toplevel(self.root)
        ventana_input.title(titulo)
        ventana_input.geometry("350x150")
        ventana_input.transient(self.root)
        ventana_input.grab_set()

        tk.Label(ventana_input, text="Introduce el dato a analizar:").pack(pady=10)
        entrada_dato = tk.Entry(ventana_input, width=40)
        entrada_dato.pack(pady=5)
        entrada_dato.focus_set()

        def ejecutar_y_cerrar():
            dato = entrada_dato.get().strip()
            if dato:
                self._ejecutar_en_hilo(accion_callback, dato)
                ventana_input.destroy()
            else:
                messagebox.showwarning("Campo Vacío", "Por favor, introduce un dato.", parent=ventana_input)

        tk.Button(ventana_input, text="Ejecutar", command=ejecutar_y_cerrar, bg="#2196F3", fg="white").pack(pady=10)
        ventana_input.protocol("WM_DELETE_WINDOW", ventana_input.destroy)

    def _mostrar_error_api(self, api_name, parent_window=None):
        msg = f"⚠️ No hay clave API de {api_name} configurada. Configúrala en 'Claves API'."
        self._mostrar_resultado(msg + "\n", "error")
        messagebox.showwarning("API no configurada", msg, parent=parent_window if parent_window else self.root)
        return False
        
    # --- MÓDULO BÚSQUEDA DE PERSONAS (MEJORADO) ---
    def _ejecutar_busqueda_persona(self, query):
        """
        MODIFICADO: Realiza búsquedas más específicas y reporta el estado de conexión
        a la página de resultados.
        """
        self._mostrar_resultado(f"\n[Búsqueda Persona] Iniciando búsqueda para: \"{query}\"\n" + "="*50 + "\n", "info")
        query_encoded = quote_plus(f'"{query}"') # Codifica la consulta para URL, con comillas para búsqueda exacta

        # Definimos los "buscadores" con sus dorks o URLs de búsqueda directa
        # Hemos cambiado algunos para usar dorks de Google que son más efectivos para "buscar en 50 páginas"
        # y hemos añadido comentarios sobre la expectativa de "encontrado/no encontrado"
        buscadores_y_dorks = [
            # Buscadores generales (la "presencia" se basa en si el buscador devuelve una página de resultados)
            {"nombre": "Google (General)", "url": f"https://www.google.com/search?q={query_encoded}", "tipo": "general"},
            {"nombre": "Google (PDFs/Docs)", "url": f"https://www.google.com/search?q=filetype:pdf+OR+filetype:doc+OR+filetype:docx+OR+filetype:xls+OR+filetype:xlsx+{query_encoded}", "tipo": "general"},
            {"nombre": "DuckDuckGo", "url": f"https://duckduckgo.com/?q={query_encoded}", "tipo": "general"},
            {"nombre": "Bing", "url": f"https://www.bing.com/search?q={query_encoded}", "tipo": "general"},

            # Redes Sociales (búsqueda directa o dorks específicos)
            {"nombre": "LinkedIn", "url": f"https://www.linkedin.com/search/results/all/?keywords={query_encoded}", "tipo": "social"},
            {"nombre": "Facebook", "url": f"https://www.facebook.com/search/top/?q={query_encoded}", "tipo": "social"},
            {"nombre": "Twitter / X", "url": f"https://twitter.com/search?q={query_encoded}&src=typed_query", "tipo": "social"},
            {"nombre": "Instagram (Google Dork)", "url": f"https://www.google.com/search?q=site:instagram.com+{query_encoded}", "tipo": "social"},
            {"nombre": "Reddit (Google Dork)", "url": f"https://www.google.com/search?q=site:reddit.com+{query_encoded}", "tipo": "social"},
            {"nombre": "TikTok (Google Dork)", "url": f"https://www.google.com/search?q=site:tiktok.com+{query_encoded}", "tipo": "social"},
            {"nombre": "YouTube (Google Dork)", "url": f"https://www.google.com/search?q=site:youtube.com+{query_encoded}", "tipo": "social"},

            # Registros Oficiales / Públicos (España)
            {"nombre": "BOE (Boletín Oficial)", "url": f"https://www.boe.es/buscar/boe.php?campo%5B1%5D=DOC&operador%5B1%5D=and&texto%5B1%5D={query_encoded}", "tipo": "official"},
            {"nombre": "Noticias (Google News)", "url": f"https://news.google.com/search?q={query_encoded}&hl=es&gl=ES&ceid=ES:es", "tipo": "news"},
            
            # Otros recursos útiles (más genéricos o especializados)
            {"nombre": "Pastebin (Google Dork)", "url": f"https://www.google.com/search?q=site:pastebin.com+{query_encoded}", "tipo": "other"},
            {"nombre": "GitHub (Google Dork)", "url": f"https://www.google.com/search?q=site:github.com+{query_encoded}", "tipo": "other"},
            {"nombre": "Stack Overflow (Google Dork)", "url": f"https://www.google.com/search?q=site:stackoverflow.com+{query_encoded}", "tipo": "other"},
            {"nombre": "Foros España (Google Dork)", "url": f"https://www.google.com/search?q=site:.es+foro+{query_encoded}", "tipo": "other"},
            {"nombre": "Blogs Personales (Google Dork)", "url": f"https://www.google.com/search?q=blog+personal+{query_encoded}", "tipo": "other"},
        ]
        
        # Una lista para almacenar hilos
        threads = []
        for i, item in enumerate(buscadores_y_dorks):
            thread = threading.Thread(target=self._realizar_busqueda_web, args=(item['nombre'], item['url'], i))
            threads.append(thread)
            thread.start()
            # Opcional: Introducir un pequeño retraso para no saturar los servidores
            time.sleep(0.1) 
        
        # Opcional: Esperar a que todos los hilos terminen si necesitas un mensaje final consolidado
        # for thread in threads:
        #     thread.join()

        self._mostrar_resultado("\n" + "="*50 + "\n✅ Búsquedas iniciadas. Haz clic en los enlaces para revisar los resultados. El estado indica la conectividad.\n", "info")


    def _realizar_busqueda_web(self, nombre_sitio, url, index):
        """
        Intenta acceder a la URL y reporta el estado. No intenta parsear el contenido
        para determinar si el 'query' está presente, solo si la página de búsqueda
        o el perfil existe/es accesible.
        """
        status_text = f"[{nombre_sitio}] Consultando..."
        # Usamos _insertar_en_ui directamente desde aquí para mostrar el estado inicial
        # Creamos una etiqueta única para cada enlace para poder actualizar el texto
        temp_tag = f"temp-link-{index}"
        self._mostrar_resultado(f"-> {status_text}\n", ("pending", temp_tag))
        
        # Guardamos la URL en el link_map usando la misma etiqueta que será permanente
        final_link_tag = f"link-{index}"
        self.link_map[final_link_tag] = url

        try:
            # Intentamos obtener la página. Un HEAD es más rápido, pero un GET podría ser necesario
            # para algunos sitios que redirigen o solo muestran contenido relevante con GET.
            # Sin embargo, para "buscar si hay algo", GET es más apropiado aunque más lento.
            response = requests.get(url, timeout=10) # Aumentamos el timeout un poco
            
            if 200 <= response.status_code < 300: # Éxito (incluye 200 OK y 2xx success)
                # Para Google y DuckDuckGo, un 200 OK ya significa que la búsqueda se realizó.
                # Para redes sociales, un 200 OK significa que el URL del perfil (o la búsqueda) fue accesible.
                # No podemos saber si "hay" el dato sin parsing avanzado.
                message = f"✅ {nombre_sitio}: Accesible. (Haz clic para ver resultados)"
                tags = ("success", "link", final_link_tag)
            elif 300 <= response.status_code < 400: # Redirección
                message = f"➡️ {nombre_sitio}: Redirección ({response.status_code}). (Haz clic)"
                tags = ("info", "link", final_link_tag)
            elif response.status_code == 404: # No encontrado (podría indicar "usuario no existe" en algunos perfiles directos)
                message = f"❌ {nombre_sitio}: No encontrado (404). Posiblemente sin resultados."
                tags = "not_found"
            elif response.status_code == 403: # Prohibido
                message = f"🚫 {nombre_sitio}: Acceso denegado (403). Podría ser por bot o login requerido."
                tags = "error"
            else: # Otros errores HTTP
                message = f"❗ {nombre_sitio}: Error HTTP {response.status_code}. (Haz clic para depurar)"
                tags = "error"
                
        except requests.exceptions.Timeout:
            message = f"⏱️ {nombre_sitio}: Tiempo de espera agotado. (URL: {url})"
            tags = "error"
        except requests.exceptions.ConnectionError:
            message = f"🔌 {nombre_sitio}: Error de conexión. (URL: {url})"
            tags = "error"
        except Exception as e:
            message = f"🚨 {nombre_sitio}: Error inesperado: {e}. (URL: {url})"
            tags = "error"

        # Actualiza el texto en la UI.
        # Primero, busca el texto temporal que insertamos.
        # Esto es un poco más complejo porque ScrolledText no tiene un "update_by_tag_name" directo.
        # La forma más robusta es re-insertar el texto con la nueva etiqueta, o modificarlo si es un solo elemento.
        # Para simplificar y dado que los resultados van en orden, simplemente mostraremos el resultado final.
        # Una alternativa más avanzada sería usar un widget Treeview o Label/Button por cada resultado.
        
        # Para este ejemplo, simplemente re-escribimos la línea que se acaba de imprimir,
        # o agregamos una nueva línea con el resultado final.
        # La forma más limpia en Tkinter con ScrolledText es eliminar y re-insertar o insertar una nueva línea final.
        # Vamos a insertar una nueva línea final con el estado, haciendo que la primera línea "Consultando" quede como una pista.
        self.root.after(0, lambda: self._actualizar_linea_resultado(index, f"-> {message}\n", tags))


    def _actualizar_linea_resultado(self, index, new_text, tags):
        """
        Busca la línea de "Consultando..." para un índice específico y la reemplaza/actualiza.
        Esto es un hack para ScrolledText. Una mejor UX podría ser una tabla o listbox.
        """
        # Encuentra la posición inicial del texto temporal para este índice
        # Esto asume que cada búsqueda tiene un índice único y que no hay muchos cambios en el texto
        # Si el scrolledtext es muy largo o se actualiza mucho, esto puede ser ineficiente.
        # Un enfoque más robusto para una UI interactiva con muchos elementos sería usar un Treeview.

        # Eliminar la línea "Consultando..." y reinsertar la línea final
        # Encuentra el inicio y fin de la línea que contiene el tag temporal
        # Esto es más fácil si cada resultado tiene su propia línea dedicada y sabemos su inicio.
        
        # Una forma más sencilla para ScrolledText es simplemente añadir el resultado final
        # justo después de la línea de "Consultando..." que se insertó inicialmente.
        # La línea "Consultando..." quedará arriba, y debajo su resultado final.
        self._mostrar_resultado(new_text, tags)


    # --- Resto de funciones de Análisis y Menús (sin cambios, solo se pegan para completar el código) ---

    def _ejecutar_analisis_ip_ipinfo(self, ip):
        self._mostrar_resultado(f"\n[ipinfo.io] Buscando información para {ip}...\n")
        try:
            resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=10)
            if resp.status_code != 200:
                self._mostrar_resultado(f"❌ Error HTTP {resp.status_code}: {resp.text}\n", "error")
                return
            data = resp.json()
            resultado = (
                f"IP: {data.get('ip')}\nHostname: {data.get('hostname', 'N/A')}\n"
                f"Ciudad: {data.get('city')}\nRegión: {data.get('region')}\n"
                f"País: {data.get('country')}\nUbicación: {data.get('loc')}\n"
                f"Organización: {data.get('org')}\n"
                f"ASN: {data.get('asn', {}).get('asn', 'N/A') if isinstance(data.get('asn'), dict) else 'N/A'}\n"
            )
            self._mostrar_resultado(resultado, "success")
        except requests.exceptions.RequestException as e:
            self._mostrar_resultado(f"❌ Error de conexión: {e}\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error inesperado: {e}\n", "error")

    def _ejecutar_geolocalizar_ip_abstractapi(self, ip):
        api_key = self.apis.get("abstractapi_ip")
        if not api_key: return self._mostrar_error_api("AbstractAPI (IP)")
        self._mostrar_resultado(f"\n[AbstractAPI] Geolocalizando IP: {ip}...\n")
        try:
            resp = requests.get(f"https://ipgeolocation.abstractapi.com/v1/?api_key={api_key}&ip_address={ip}", timeout=10)
            if resp.status_code != 200:
                self._mostrar_resultado(f"❌ Error HTTP {resp.status_code}: {resp.text}\n", "error")
                return
            data = resp.json()
            resultado = (
                f"IP: {data.get('ip_address')}\nPaís: {data.get('country')} ({data.get('country_code')})\n"
                f"Región: {data.get('region')}, Ciudad: {data.get('city')}\n"
                f"Ubicación: {data.get('latitude')}, {data.get('longitude')}\n"
                f"ISP: {data.get('connection', {}).get('isp_name', 'N/A')}\n"
            )
            self._mostrar_resultado(resultado, "success")
        except requests.exceptions.RequestException as e:
            self._mostrar_resultado(f"❌ Error de conexión: {e}\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error inesperado: {e}\n", "error")

    def _ejecutar_analisis_shodan(self, ip):
        api_key = self.apis.get("shodan")
        if not api_key: return self._mostrar_error_api("Shodan")
        self._mostrar_resultado(f"\n[Shodan] Buscando información para {ip}...\n")
        try:
            resp = requests.get(f"https://api.shodan.io/shodan/host/{ip}?key={api_key}", timeout=15)
            if resp.status_code != 200:
                self._mostrar_resultado(f"❌ Error Shodan HTTP {resp.status_code}: {resp.json().get('error', resp.text)}\n", "error")
                return
            data = resp.json()
            resultado = (
                f"IP: {data.get('ip_str', 'N/A')}\nOrganización: {data.get('org', 'N/A')}\n"
                f"ISP: {data.get('isp', 'N/A')}\nPaís: {data.get('country_name', 'N/A')}\n"
                f"Hostnames: {', '.join(data.get('hostnames', ['N/A']))}\n"
                f"Puertos abiertos: {data.get('ports', ['N/A'])}\n"
            )
            self._mostrar_resultado(resultado, "success")
        except requests.exceptions.RequestException as e:
            self._mostrar_resultado(f"❌ Error de conexión: {e}\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error inesperado: {e}\n", "error")

    def _ejecutar_analisis_dominio(self, dominio):
        self._mostrar_resultado(f"\n[Dominio] Consultando WHOIS para {dominio}...\n")
        try:
            salida = subprocess.getoutput(f"whois {dominio}")
            if salida.strip():
                self._mostrar_resultado(salida + "\n", "success")
            else:
                self._mostrar_resultado("❌ No se encontraron resultados WHOIS.\n", "not_found")
        except FileNotFoundError:
            self._mostrar_resultado("❌ Error: 'whois' no encontrado. Asegúrate de tenerlo instalado.\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error al ejecutar WHOIS: {e}\n", "error")

    def _ejecutar_analisis_email_dehashed(self, email):
        api_user = self.apis.get("dehashed_user")
        api_pass = self.apis.get("dehashed_pass")
        if not api_user or not api_pass: return self._mostrar_error_api("Dehashed (usuario/contraseña)")
        self._mostrar_resultado(f"\n[Dehashed] Buscando filtraciones para {email}...\n")
        try:
            resp = requests.get(f"https://api.dehashed.com/search?query=email:{email}", auth=(api_user, api_pass), timeout=10)
            if resp.status_code != 200:
                self._mostrar_resultado(f"❌ Error HTTP {resp.status_code}: {resp.text}\n", "error")
                return
            data = resp.json()
            if data.get("total", 0) == 0:
                self._mostrar_resultado("✅ No se encontraron filtraciones para este correo.\n", "not_found")
                return
            resultado = f"❗ Se encontraron {data.get('total')} registros en Dehashed:\n"
            for r in data.get("entries", [])[:5]:
                resultado += f"- Usuario: {r.get('username', 'N/A')}, Email: {r.get('email', 'N/A')}, Hash: {r.get('hashed_password', 'N/A')}\n"
            self._mostrar_resultado(resultado, "success")
        except requests.exceptions.RequestException as e:
            self._mostrar_resultado(f"❌ Error de conexión: {e}\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error inesperado: {e}\n", "error")

    def _ejecutar_analisis_email_abstractapi(self, email):
        api_key = self.apis.get("abstractapi_email")
        if not api_key: return self._mostrar_error_api("AbstractAPI (Email)")
        self._mostrar_resultado(f"\n[AbstractAPI] Validando correo: {email}...\n")
        try:
            resp = requests.get(f"https://emailvalidation.abstractapi.com/v1/?api_key={api_key}&email={email}", timeout=10)
            if not resp.ok:
                self._mostrar_resultado(f"❌ Error AbstractAPI (Email) HTTP {resp.status_code}: {resp.json().get('error', {}).get('message', 'Error')}\n", "error")
                return
            data = resp.json()
            resultado = (
                f"✔️ Dirección: {data.get('email', 'N/A')}\nFormato válido: {data.get('is_valid_format', {}).get('value', 'N/A')}\n"
                f"SMTP válido: {data.get('is_smtp_valid', {}).get('value', 'N/A')}\n"
                f"Correo desechable: {data.get('is_disposable_email', {}).get('value', 'N/A')}\n"
            )
            self._mostrar_resultado(resultado, "success")
        except requests.exceptions.RequestException as e:
            self._mostrar_resultado(f"❌ Error de conexión: {e}\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error inesperado: {e}\n", "error")

    def _ejecutar_analisis_telefono_veriphone(self, telefono):
        api_key = self.apis.get("veriphone")
        if not api_key: return self._mostrar_error_api("Veriphone")
        self._mostrar_resultado(f"\n[Veriphone] Validando número: {telefono}...\n")
        try:
            resp = requests.get(f"https://api.veriphone.io/v2/verify?phone={telefono}&key={api_key}", timeout=10)
            data = resp.json()
            if not data.get("phone_valid"):
                self._mostrar_resultado(f"❌ Número inválido. Mensaje: {data.get('error', 'N/A')}\n", "not_found")
                return
            resultado = (
                f"✔️ Número válido: {data.get('international_number', 'N/A')}\nPaís: {data.get('country', 'N/A')}\n"
                f"Operador: {data.get('carrier', 'N/A')}\nTipo de línea: {data.get('phone_type', 'N/A')}\n"
            )
            self._mostrar_resultado(resultado, "success")
        except requests.exceptions.RequestException as e:
            self._mostrar_resultado(f"❌ Error de conexión: {e}\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error inesperado: {e}\n", "error")

    def _ejecutar_analisis_telefono_abstractapi(self, telefono):
        api_key = self.apis.get("abstractapi")
        if not api_key: return self._mostrar_error_api("AbstractAPI (Teléfono)")
        self._mostrar_resultado(f"\n[AbstractAPI] Validando número: {telefono}...\n")
        try:
            resp = requests.get(f"https://phonevalidation.abstractapi.com/v1/?api_key={api_key}&phone={telefono}", timeout=10)
            data = resp.json()
            if not data.get("valid"):
                self._mostrar_resultado(f"❌ Número inválido. Mensaje: {data.get('error', {}).get('message', 'N/A')}\n", "not_found")
                return
            resultado = (
                f"✔️ Número válido: {data.get('international_format', 'N/A')}\n"
                f"País: {data.get('country', {}).get('name', 'N/A')}\n"
                f"Operador: {data.get('carrier', 'N/A')}\n"
            )
            self._mostrar_resultado(resultado, "success")
        except requests.exceptions.RequestException as e:
            self._mostrar_resultado(f"❌ Error de conexión: {e}\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error inesperado: {e}\n", "error")
        
    def _ejecutar_analisis_metadatos(self):
        filepath = filedialog.askopenfilename(title="Selecciona una imagen para EXIF")
        if filepath:
            self._ejecutar_en_hilo(self._extraer_exif_thread, filepath)
        
    def _extraer_exif_thread(self, filepath):
        self._mostrar_resultado(f"\n[EXIF] Analizando archivo: {filepath}\n")
        try:
            salida = subprocess.getoutput(f"exiftool \"{filepath}\"")
            if salida.strip():
                self._mostrar_resultado(salida + "\n", "success")
            else:
                self._mostrar_resultado("❌ No se pudieron extraer metadatos.\n", "not_found")
        except FileNotFoundError:
            self._mostrar_resultado("❌ Error: 'exiftool' no encontrado. Asegúrate de tenerlo instalado.\n", "error")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error al ejecutar EXIFTool: {e}\n", "error")

    def _ejecutar_buscar_imagen_google(self):
        self._mostrar_resultado(f"\n[Google Reverse] Abriendo Google Imágenes para búsqueda inversa...\n")
        try:
            webbrowser.open("https://images.google.com/")
            self._mostrar_resultado("🔍 Se ha abierto Google Imágenes. Arrastra una imagen al buscador.\n", "info")
        except Exception as e:
            self._mostrar_resultado(f"❌ Error al abrir navegador: {e}\n", "error")

    def _ejecutar_analisis_usuario(self, usuario):
        self._mostrar_resultado(f"\n[Usuario] Buscando presencia online para: {usuario}\n")
        sitios = {
            "Twitter (X)": "https://twitter.com/{}", "GitHub": "https://github.com/{}",
            "Reddit": "https://www.reddit.com/user/{}", "Instagram": "https://www.instagram.com/{}",
            "Facebook": "https://www.facebook.com/{}", "TikTok": "https://www.tiktok.com/@{}",
        }
        for nombre, url_template in sitios.items():
            self._ejecutar_en_hilo(self._verificar_sitio_usuario, nombre, url_template.format(usuario))

    def _verificar_sitio_usuario(self, nombre_sitio, url):
        # Para verificar si un perfil de usuario existe, un HEAD es a menudo suficiente
        # ya que un 404 (Not Found) es un buen indicador de que el perfil no existe.
        # Sin embargo, muchos sitios redirigen o devuelven 200 con contenido "vacío"
        # si el usuario no existe, requiriendo un análisis más profundo del HTML,
        # lo cual se evita aquí por la complejidad.
        
        status_text = f"[{nombre_sitio}] Verificando perfil..."
        # Temporalmente, vamos a imprimir una línea que será sobrescrita o complementada
        temp_tag = f"temp-user-{nombre_sitio}"
        self._mostrar_resultado(f"-> {status_text}\n", ("pending", temp_tag))

        try:
            res = requests.head(url, timeout=7, allow_redirects=True)
            message = ""
            tags = ""
            if res.status_code == 200:
                message = f"✅ {nombre_sitio}: Perfil accesible."
                tags = ("success", "link", url) # Añadir el tag "link" y la URL para que sea clickable
                self.link_map[url] = url # Guardar la URL para el tag
            elif res.status_code == 404:
                message = f"❌ {nombre_sitio}: Perfil no encontrado (404)."
                tags = "not_found"
            else:
                message = f"❗ {nombre_sitio}: Estado {res.status_code}. (Haz clic para revisar)"
                tags = ("info", "link", url)
                self.link_map[url] = url
            
            # Actualizamos el resultado
            self.root.after(0, lambda: self._actualizar_linea_resultado(0, f"-> {message}\n", tags))

        except requests.exceptions.RequestException as e:
            message = f"🔌 {nombre_sitio}: Error de conexión o timeout: {e}"
            tags = "error"
            self.root.after(0, lambda: self._actualizar_linea_resultado(0, f"-> {message}\n", tags))

    def _mostrar_menu_persona(self):
        self._crear_ventana_input("Buscar Persona por Nombre, DNI, etc.", self._ejecutar_busqueda_persona)

    def _mostrar_menu_ip(self):
        ventana_menu = tk.Toplevel(self.root)
        ventana_menu.title("Opciones de Análisis IP")
        ventana_menu.geometry("300x180")
        ventana_menu.transient(self.root); ventana_menu.grab_set()
        tk.Label(ventana_menu, text="Elige una opción de análisis de IP:").pack(pady=10)
        tk.Button(ventana_menu, text="📂 IP con ipinfo.io", command=lambda: [self._crear_ventana_input("Análisis IP (ipinfo.io)", self._ejecutar_analisis_ip_ipinfo), ventana_menu.destroy()]).pack(pady=3)
        tk.Button(ventana_menu, text="📍 IP con AbstractAPI", command=lambda: [self._crear_ventana_input("Geolocalizar IP (AbstractAPI)", self._ejecutar_geolocalizar_ip_abstractapi), ventana_menu.destroy()]).pack(pady=3)
        tk.Button(ventana_menu, text="🛰️ IP con Shodan", command=lambda: [self._crear_ventana_input("Consulta Shodan por IP", self._ejecutar_analisis_shodan), ventana_menu.destroy()]).pack(pady=3)
        ventana_menu.protocol("WM_DELETE_WINDOW", ventana_menu.destroy)

    def _mostrar_menu_email(self):
        ventana_menu = tk.Toplevel(self.root)
        ventana_menu.title("Opciones de Análisis de Email")
        ventana_menu.geometry("300x150")
        ventana_menu.transient(self.root); ventana_menu.grab_set()
        tk.Label(ventana_menu, text="Elige una opción de análisis de Email:").pack(pady=10)
        tk.Button(ventana_menu, text="📧 Email con Dehashed", command=lambda: [self._crear_ventana_input("Filtraciones de Email (Dehashed)", self._ejecutar_analisis_email_dehashed), ventana_menu.destroy()]).pack(pady=3)
        tk.Button(ventana_menu, text="📧 Email con AbstractAPI", command=lambda: [self._crear_ventana_input("Validar Email (AbstractAPI)", self._ejecutar_analisis_email_abstractapi), ventana_menu.destroy()]).pack(pady=3)
        ventana_menu.protocol("WM_DELETE_WINDOW", ventana_menu.destroy)
        
    def _mostrar_menu_usuario(self):
        self._crear_ventana_input("Buscar Usuario en Redes", self._ejecutar_analisis_usuario)

    def _mostrar_menu_telefono(self):
        ventana_menu = tk.Toplevel(self.root)
        ventana_menu.title("Opciones de Análisis de Teléfono")
        ventana_menu.geometry("300x150")
        ventana_menu.transient(self.root); ventana_menu.grab_set()
        tk.Label(ventana_menu, text="Elige una opción de análisis de Teléfono:").pack(pady=10)
        tk.Button(ventana_menu, text="📱 Teléfono con Veriphone", command=lambda: [self._crear_ventana_input("Teléfono (Veriphone)", self._ejecutar_analisis_telefono_veriphone), ventana_menu.destroy()]).pack(pady=3)
        tk.Button(ventana_menu, text="📱 Teléfono con AbstractAPI", command=lambda: [self._crear_ventana_input("Teléfono (AbstractAPI)", self._ejecutar_analisis_telefono_abstractapi), ventana_menu.destroy()]).pack(pady=3)
        ventana_menu.protocol("WM_DELETE_WINDOW", ventana_menu.destroy)

    def _mostrar_menu_imagen(self):
        ventana_menu = tk.Toplevel(self.root)
        ventana_menu.title("Opciones de Análisis de Imagen")
        ventana_menu.geometry("300x150")
        ventana_menu.transient(self.root); ventana_menu.grab_set()
        tk.Label(ventana_menu, text="Elige una opción de análisis de Imagen:").pack(pady=10)
        tk.Button(ventana_menu, text="🖼️ Metadatos EXIF", command=lambda: [self._ejecutar_analisis_metadatos(), ventana_menu.destroy()]).pack(pady=3)
        tk.Button(ventana_menu, text="🔎 Búsqueda Inversa Google", command=lambda: [self._ejecutar_buscar_imagen_google(), ventana_menu.destroy()]).pack(pady=3)
        ventana_menu.protocol("WM_DELETE_WINDOW", ventana_menu.destroy)

# --- Ejecución de la Aplicación ---
if __name__ == "__main__":
    root = tk.Tk()
    app = WicOsintXApp(root)
    root.mainloop()
