# mailer.py
import json, smtplib, ssl, mimetypes, socket
from email.message import EmailMessage


# ----------------- Carga de configuración -----------------
def load_mail_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "smtp" not in cfg:
        raise ValueError("config.json no tiene sección 'smtp'")
    s = cfg["smtp"]
    # sanea strings por si hay espacios
    s["host"] = str(s.get("host", "smtp.gmail.com")).strip()
    s["user"] = str(s.get("user", "")).strip()
    return cfg


# ----------------- Contexto SSL -----------------
def _build_ssl_context(verify_ssl: bool):
    """Crea un contexto SSL; si verify_ssl=False, no valida certificados (solo para demo)."""
    if verify_ssl:
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return ssl.create_default_context()
    # ⚠️ Inseguro: solo para redes que interceptan TLS durante desarrollo
    return ssl._create_unverified_context()


# ----------------- Envío -----------------
def send_mail(
    to_email: str,
    subject: str,
    body: str,
    attach_path: str,
    config: dict,
    use_starttls: bool | None = True,   # Gmail recomendado: STARTTLS (587)
    timeout: int = 25,
):
    smtp = config["smtp"]
    host = smtp.get("host", "smtp.gmail.com").strip()
    port = int(smtp.get("port", 587))               # 587 = STARTTLS, 465 = SSL
    user = smtp.get("user", "").strip()
    pwd  = smtp.get("password", "")
    verify_ssl = bool(smtp.get("verify_ssl", True)) # permite desactivar verificación en redes con inspección SSL

    if not user or not pwd:
        raise RuntimeError("Faltan credenciales SMTP (user/password) en config.json.")

    # Mensaje con adjunto
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to_email.strip()
    msg["Subject"] = subject
    msg.set_content(body)

    ctype, _ = mimetypes.guess_type(attach_path)
    maintype, subtype = (ctype or "application/pdf").split("/")
    with open(attach_path, "rb") as f:
        msg.add_attachment(
            f.read(), maintype=maintype, subtype=subtype,
            filename=attach_path.split("/")[-1]
        )

    ctx = _build_ssl_context(verify_ssl)

    def _send_ssl():
        with smtplib.SMTP_SSL(host, 465, context=ctx, timeout=timeout) as s:
            s.login(user, pwd)
            s.send_message(msg)

    def _send_starttls():
        with smtplib.SMTP(host, 587, timeout=timeout) as s:
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.send_message(msg)

    # Estrategia de transporte
    try:
        if use_starttls is True or port == 587:
            _send_starttls()
        elif use_starttls is False or port == 465:
            _send_ssl()
        else:
            # auto: intenta SSL y si falla por SSL, cae a STARTTLS
            try:
                _send_ssl()
            except ssl.SSLError:
                _send_starttls()

    except socket.gaierror as e:
        raise RuntimeError(
            f"No se pudo resolver el host SMTP '{host}'. Revisa DNS/VPN/Proxy."
        ) from e
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError(
            "Autenticación SMTP fallida. En Gmail debes usar un **App Password** (16 caracteres), "
            "no tu contraseña normal."
        )
    except ssl.SSLError as e:
        extra = " (verify_ssl=false en config.json)" if verify_ssl else ""
        raise RuntimeError(
            f"Error SSL/TLS con el servidor SMTP: {e}\n"
            f"Sugerencias: prueba otra red (hotspot), desactiva la inspección HTTPS del antivirus/proxy, "
            f"o desactiva temporalmente la verificación de certificados{extra}."
        ) from e
    except Exception as e:
        raise RuntimeError(f"No se pudo enviar el correo: {type(e).__name__}: {e}") from e
