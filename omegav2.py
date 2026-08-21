#!/usr/bin/env python3

import os
import sys
import ssl
import time
import socket
import random
import ipaddress
import concurrent.futures
from itertools import groupby

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("Falta el modulo 'requests'. Instalalo con: pip install -r requirements.txt")
    sys.exit(1)

if os.name == "nt":
    os.system("")


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[97m"
    GREY = "\033[90m"


FONT_BITMAP = {
    "Ω": [
        "0111110",
        "0100010",
        "0100010",
        "0100010",
        "0100010",
        "0100010",
        "1100011",
    ],
    "M": [
        "10001",
        "11011",
        "10101",
        "10101",
        "10001",
        "10001",
        "10001",
    ],
    "E": [
        "11111",
        "10000",
        "11110",
        "10000",
        "10000",
        "10000",
        "11111",
    ],
    "G": [
        "01111",
        "10000",
        "10000",
        "10111",
        "10001",
        "10001",
        "01110",
    ],
    "A": [
        "01110",
        "10001",
        "10001",
        "11111",
        "10001",
        "10001",
        "10001",
    ],
}

FILLED, EMPTY = "██", "  "


def render_glyph(bitmap):
    return ["".join(FILLED if bit == "1" else EMPTY for bit in row) for row in bitmap]


GLYPHS = {letter: render_glyph(bitmap) for letter, bitmap in FONT_BITMAP.items()}

WORD = ["Ω", "M", "E", "G", "A"]
GLYPH_HEIGHT = 7


def build_banner_rows():
    rows = ["" for _ in range(GLYPH_HEIGHT)]
    for letter in WORD:
        glyph = GLYPHS[letter]
        width = max(len(line) for line in glyph)
        for i in range(GLYPH_HEIGHT):
            rows[i] += glyph[i].ljust(width) + "  "
    return rows


def clear_screen():
    print("\033[H\033[J", end="")


def glitch_intro():
    rows = build_banner_rows()
    scramble_chars = "!<>-_\\/[]{}=+*^?#01"
    total_frames = 15

    for frame_i in range(total_frames):
        progress = frame_i / (total_frames - 1)
        corruption = 0.9 * (1 - progress) ** 1.6

        frame = []
        for row in rows:
            scrambled = "".join(
                ch if ch == " " or random.random() > corruption else random.choice(scramble_chars)
                for ch in row
            )
            frame.append(scrambled)

        clear_screen()
        print(C.CYAN + "\n".join(frame) + C.RESET)
        time.sleep(0.03 + progress * 0.035)

    clear_screen()
    print_static_banner(rows)


def _add_drop_shadow(rows):
    height = len(rows)
    width = max(len(r) for r in rows)
    rows = [r.ljust(width) for r in rows]

    new_h, new_w = height + 1, width + 1
    comp = [[" " for _ in range(new_w)] for _ in range(new_h)]

    for r in range(height):
        for c in range(width):
            if rows[r][c] == "█":
                comp[r + 1][c + 1] = "S"

    for r in range(height):
        for c in range(width):
            if rows[r][c] == "█":
                comp[r][c] = "F"

    return comp


def _render_composite(comp):
    lines = []
    for row in comp:
        segments = []
        for style, group in groupby(row):
            n = len(list(group))
            if style == "F":
                segments.append(f"{C.BOLD}{C.WHITE}{'█' * n}{C.RESET}")
            elif style == "S":
                segments.append(f"{C.DIM}{C.CYAN}{'▓' * n}{C.RESET}")
            else:
                segments.append(" " * n)
        lines.append("".join(segments))
    return lines


def print_static_banner(rows=None):
    if rows is None:
        rows = build_banner_rows()
    comp = _add_drop_shadow(rows)
    for line in _render_composite(comp):
        print(line)
    print(f"{C.DIM}{C.CYAN}        Omega Tracker v2{C.RESET}\n")


def show_banner():
    if not sys.stdout.isatty():
        print_static_banner()
        return
    try:
        glitch_intro()
    except Exception:
        print_static_banner()


def valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def print_section(title):
    bar = "─" * max(4, 50 - len(title))
    print(f"\n{C.BOLD}{C.CYAN}── {title} {bar}{C.RESET}")


def print_kv(key, value, color=C.WHITE):
    if value in (None, "", [], {}):
        shown = f"{C.GREY}no disponible{C.RESET}"
    else:
        shown = f"{color}{value}{C.RESET}"
    print(f"  {C.DIM}{key:<22}{C.RESET} {shown}")


def get_geo_info(ip):
    fields = (
        "status,message,continent,country,countryCode,region,regionName,"
        "city,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,"
        "proxy,hosting,query"
    )
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields={fields}", timeout=6)
        data = r.json()
        if data.get("status") != "success":
            return None
        return data
    except requests.RequestException:
        return None


def reverse_dns(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror):
        return None


def get_whois_info(ip):
    try:
        from ipwhois import IPWhois
    except ImportError:
        return "MODULE_MISSING"
    try:
        obj = IPWhois(ip)
        return obj.lookup_rdap(depth=1)
    except Exception:
        return None


COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 6379: "Redis",
    8080: "HTTP-alt", 8443: "HTTPS-alt", 27017: "MongoDB",
}

def scan_port_socket(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.2)
            if s.connect_ex((ip, port)) == 0:
                return port
    except socket.error:
        pass
    return None


def scan_ports_socket(ip):
    open_ports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(scan_port_socket, ip, p) for p in COMMON_PORTS]
        for future in concurrent.futures.as_completed(futures):
            port = future.result()
            if port:
                open_ports.append(port)
    return sorted((p, COMMON_PORTS.get(p, "desconocido")) for p in open_ports)


def grab_http_headers(ip, use_https=False):
    scheme = "https" if use_https else "http"
    try:
        r = requests.get(f"{scheme}://{ip}", timeout=4, verify=False)
        return dict(r.headers)
    except requests.RequestException:
        return None


def get_tls_cert(ip, port=443):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((ip, port), timeout=4) as sock:
            with ctx.wrap_socket(sock, server_hostname=ip) as ssock:
                der = ssock.getpeercert(binary_form=True)
        if not der:
            return None
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            cert = x509.load_der_x509_certificate(der, default_backend())
            try:
                not_after = cert.not_valid_after_utc.strftime("%Y-%m-%d")
            except AttributeError:
                not_after = cert.not_valid_after.strftime("%Y-%m-%d")
            return {
                "issuer": cert.issuer.rfc4514_string(),
                "subject": cert.subject.rfc4514_string(),
                "not_after": not_after,
            }
        except ImportError:
            return "MODULE_MISSING"
    except Exception:
        return None


def clear_and_banner():
    if sys.stdout.isatty():
        clear_screen()
    print_static_banner()


def print_menu():
    print(f"{C.BOLD}{C.WHITE}  [1]{C.RESET}  Ingresar IP a trackear")
    print(f"{C.BOLD}{C.WHITE}  [2]{C.RESET}  Ayuda e informacion")
    print(f"{C.BOLD}{C.WHITE}  [3]{C.RESET}  Creditos")
    print(f"{C.BOLD}{C.WHITE}  [0]{C.RESET}  Salir\n")


def print_help():
    print_section("Ayuda e informacion")
    print(f"  {C.WHITE}Omega Tracker v2{C.RESET} es una herramienta OSINT para direcciones IP.")
    print("  Usa unicamente APIs publicas y tecnicas no intrusivas.\n")
    print(f"  {C.BOLD}Que informacion recolecta:{C.RESET}")
    print("    - Geolocalizacion, ISP, ASN y datos de red")
    print("    - DNS inverso")
    print("    - WHOIS / RDAP y contactos de abuso")
    print("    - Escaneo de puertos comunes")
    print("    - Certificado TLS (si el puerto 443 esta abierto)")
    print("    - Cabeceras HTTP (si el puerto 80/443 esta abierto)\n")
    input(f"{C.DIM}Presiona Enter para volver al menu...{C.RESET}")


def print_credits():
    print_section("Creditos")
    print(f"  {C.WHITE}Creador:{C.RESET}      Spyk3r")
    print(f"  {C.WHITE}GitHub:{C.RESET}       https://github.com/Spyk3r")
    print(f"  {C.WHITE}Discord:{C.RESET}      spyk3r\n")
    input(f"{C.DIM}Presiona Enter para volver al menu...{C.RESET}")


def analyze_ip(ip):
    print(f"\n{C.YELLOW}[*] Analizando {ip}...{C.RESET}")

    geo = get_geo_info(ip)
    rdns = reverse_dns(ip)

    print_section("Informacion general")
    if geo:
        print_kv("IP", geo.get("query"))
        print_kv("Pais", f"{geo.get('country')} ({geo.get('countryCode')})")
        print_kv("Region", geo.get("regionName"))
        print_kv("Ciudad", geo.get("city"))
        print_kv("Codigo postal", geo.get("zip"))
        print_kv("Latitud / Longitud", f"{geo.get('lat')}, {geo.get('lon')}")
        print_kv("Zona horaria", geo.get("timezone"))
    else:
        print(f"  {C.RED}No se pudo obtener geolocalizacion.{C.RESET}")

    print_section("Red / ISP")
    if geo:
        print_kv("ISP", geo.get("isp"))
        print_kv("Organizacion", geo.get("org"))
        print_kv("ASN", geo.get("as"))
        print_kv("Nombre ASN", geo.get("asname"))
        print_kv("Hosting / Datacenter", geo.get("hosting"))
        print_kv("Proxy / VPN detectado", geo.get("proxy"))
        print_kv("Conexion movil", geo.get("mobile"))
    print_kv("DNS inverso", rdns)

    print_section("WHOIS / RDAP")
    whois_data = get_whois_info(ip)
    if whois_data == "MODULE_MISSING":
        print(f"  {C.GREY}Instala 'ipwhois' para esta seccion: pip install ipwhois{C.RESET}")
    elif whois_data:
        network = whois_data.get("network", {}) or {}
        print_kv("Rango CIDR", network.get("cidr"))
        print_kv("Nombre de red", network.get("name"))
        print_kv("Pais (RDAP)", network.get("country"))
        print_kv("Descripcion ASN", whois_data.get("asn_description"))
        emails = set()
        for entity in (whois_data.get("objects") or {}).values():
            contact = entity.get("contact") or {}
            for e in (contact.get("email") or []):
                if isinstance(e, dict) and e.get("value"):
                    emails.add(e["value"])
        print_kv("Contactos de abuso", ", ".join(sorted(emails)) if emails else None)
    else:
        print(f"  {C.GREY}Sin datos RDAP disponibles para esta IP.{C.RESET}")

    print_section("Escaneo de puertos")
    print(f"  {C.DIM}Escaneando {len(COMMON_PORTS)} puertos comunes...{C.RESET}")
    open_ports = scan_ports_socket(ip)

    if open_ports:
        for port, service in open_ports:
            print(f"  {C.GREEN}[abierto]{C.RESET} {port:<6} {C.DIM}{service}{C.RESET}")
    else:
        print(f"  {C.GREY}No se detectaron puertos abiertos entre los analizados.{C.RESET}")

    open_port_numbers = [p for p, _ in open_ports]

    if 443 in open_port_numbers:
        print_section("Certificado TLS (puerto 443)")
        cert_info = get_tls_cert(ip)
        if cert_info == "MODULE_MISSING":
            print(f"  {C.GREY}Instala 'cryptography' para esta seccion: pip install cryptography{C.RESET}")
        elif cert_info:
            print_kv("Emisor", cert_info.get("issuer"))
            print_kv("Sujeto", cert_info.get("subject"))
            print_kv("Valido hasta", cert_info.get("not_after"))
        else:
            print(f"  {C.GREY}No se pudo leer el certificado.{C.RESET}")

    if 80 in open_port_numbers or 443 in open_port_numbers:
        print_section("Cabeceras HTTP")
        headers = grab_http_headers(ip, use_https=443 in open_port_numbers)
        if headers:
            for k in ("Server", "X-Powered-By", "Via", "Content-Type"):
                if k in headers:
                    print_kv(k, headers[k])
        else:
            print(f"  {C.GREY}El host no respondio a la peticion HTTP.{C.RESET}")

    print(f"\n{C.CYAN}[✓] Analisis completado.{C.RESET}\n")


def run_lookup():
    while True:
        try:
            ip = input(f"{C.BOLD}{C.GREEN}➤ Ingresa la IP objetivo: {C.RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not valid_ip(ip):
            print(f"{C.RED}IP invalida.{C.RESET}")
            input(f"{C.DIM}Presiona Enter para continuar...{C.RESET}")
            return

        analyze_ip(ip)

        try:
            again = input(
                f"{C.BOLD}➤ Analizar otra IP (Enter) o volver al menu (m): {C.RESET}"
            ).strip().lower()
        except (KeyboardInterrupt, EOFError):
            return

        if again == "m":
            return
        print()





def main():
    show_banner()

    while True:
        print_menu()
        try:
            choice = input(f"{C.BOLD}{C.GREEN}➤ Selecciona una opcion: {C.RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C.YELLOW}Cancelado.{C.RESET}")
            sys.exit(0)

        if choice in ("1", "01"):
            print()
            run_lookup()
            clear_and_banner()
        elif choice in ("2", "02"):
            print()
            print_help()
            clear_and_banner()
        elif choice in ("3", "03"):
            print()
            print_credits()
            clear_and_banner()
        elif choice in ("0", "00"):
            print(f"\n{C.CYAN}Hasta pronto.{C.RESET}\n")
            sys.exit(0)
        else:
            print(f"{C.RED}Opcion invalida.{C.RESET}\n")


if __name__ == "__main__":
    main()
