# mailer.py
import json, smtplib, ssl, mimetypes
from email.message import EmailMessage

def load_mail_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "smtp" not in cfg:
        raise ValueError("config.json no tiene sección 'smtp'")
    return cfg

def send_mail(to_email, subject, body, attach_path, config):
    smtp_cfg = config["smtp"]
    user = smtp_cfg["user"]
    pwd  = smtp_cfg["password"]
    host = smtp_cfg.get("host","smtp.gmail.com")
    port = int(smtp_cfg.get("port",465))

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    ctype, _ = mimetypes.guess_type(attach_path)
    maintype, subtype = (ctype or "application/pdf").split("/")
    with open(attach_path, "rb") as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=attach_path.split("/")[-1])

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(user, pwd)
        server.send_message(msg)
