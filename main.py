# main.py
# pip install fpdf2 PySimpleGUI
import json, os, sys, datetime, subprocess
import PySimpleGUI as sg
from pdf_gen import create_ticket_pdf

# correo opcional
MAIL_AVAILABLE = True
try:
    from mailer import send_mail, load_mail_config
except Exception:
    MAIL_AVAILABLE = False

# -------- utilidades --------
def load_store_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    store = data.get("store", {})
    if not store:
        raise ValueError("Falta sección 'store' en config.json")
    return store, data

def open_file(path):
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        pass

def to_float(s, default=0.0):
    try:
        return float(str(s).replace(",", "."))
    except:
        return default

def calc_totals(items, iva_rate=0.13, prices_include_iva=False):
    gross = sum(it["qty"] * it["price"] for it in items)
    if prices_include_iva:
        base = gross / (1 + iva_rate)
        iva  = gross - base
        subtotal, total = base, gross
    else:
        subtotal = gross
        iva = subtotal * iva_rate
        total = subtotal + iva
    return round(subtotal,2), round(iva,2), round(total,2)

def now_date_time():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

# --------- cargar config empresa ---------
try:
    STORE, RAW_CFG = load_store_config("config.json")
    IVA_RATE = float(STORE.get("iva_rate", 0.13))
    PRICES_INCLUDE_IVA = bool(STORE.get("prices_include_iva", False))
except Exception as e:
    sg.popup_error(f"Error en config.json: {e}")
    sys.exit(1)

sg.theme("SystemDefault")

# ========= Estado de productos en memoria (sin BD) =========
items = []  # cada item: {"name": str, "qty": float, "price": float}

def refresh_items_table():
    table_vals = [[i+1, it["name"], f"{it['qty']:.2f}", f"{it['price']:.2f}", f"{it['qty']*it['price']:.2f}"] for i,it in enumerate(items)]
    win["-TABLE-"].update(values=table_vals)

def refresh_totals():
    subtotal, iva, total = calc_totals(items, IVA_RATE, PRICES_INCLUDE_IVA)
    win["-SUB-"].update(f"Subtotal: ${subtotal:.2f}")
    win["-IVA-"].update(f"IVA (13%): ${iva:.2f}")
    win["-TOT-"].update(f"Total: ${total:.2f}")
    return subtotal, iva, total

# ========= Layout =========
header_frame = sg.Frame(
    "Empresa (preconfigurada)",
    [[sg.Text(f"{STORE['name']} — NIT: {STORE['nit']}")],
     [sg.Text(STORE["address"])]],
)

left = [
    [sg.Text("Cliente"),   sg.Input("", key="-CLIENTE-", size=(35,1))],
    [sg.Text("Documento"), sg.Input("", key="-DOC-", size=(20,1))],
    [sg.Text("Método de pago"), sg.Combo(["Efectivo","Tarjeta","Transferencia"],
        default_value="Tarjeta", key="-PAY-", readonly=True, size=(15,1), enable_events=True)],
    [sg.Text("Efectivo recibido"), sg.Input("0", key="-CASH-", size=(10,1), disabled=True)],
    [sg.Checkbox("Enviar por correo", key="-SENDMAIL-", enable_events=True),
     sg.Input("", key="-EMAIL-", size=(28,1), disabled=True, tooltip="correo@cliente.com")],
]

right_items = [
    [sg.Text("Agregar producto")],
    [sg.Text("Nombre", size=(8,1)), sg.Input("", key="-P_NAME-", size=(28,1))],
    [sg.Text("Cantidad", size=(8,1)), sg.Input("1", key="-P_QTY-", size=(10,1)),
     sg.Text("Precio", size=(7,1)), sg.Input("0.00", key="-P_PRICE-", size=(12,1))],
    [sg.Button("Agregar", key="-ADD-"), sg.Button("Editar seleccionado", key="-EDIT-"), sg.Button("Eliminar seleccionado", key="-DEL-")],
    [sg.Text("Listado")],
    [sg.Table(
        values=[], headings=["#","Producto","Cant","Precio","Importe"],
        key="-TABLE-", auto_size_columns=False, justification="right",
        col_widths=[4,28,8,10,10], num_rows=8, enable_events=True,
        expand_x=True, expand_y=False, alternating_row_color="#f5f5f5")],
    [sg.Text("Subtotal: $0.00", key="-SUB-"),
     sg.Text("   IVA (13%): $0.00", key="-IVA-"),
     sg.Text("   Total: $0.00", key="-TOT-")],
]

layout = [
    [header_frame],
    [sg.Column(left, vertical_alignment="top"), sg.VSeparator(), sg.Column(right_items, vertical_alignment="top")],
    [sg.Push(), sg.Button("Generar PDF", bind_return_key=True), sg.Button("Salir")]
]

win = sg.Window("Ticket/Factura → PDF (sin BD)", layout, finalize=True)

# ========= helpers de UI =========
def toggle_email_field(checked):
    win["-EMAIL-"].update(disabled=not checked)

def toggle_cash_field(pay_method):
    win["-CASH-"].update(disabled=(pay_method != "Efectivo"))

# ========= init =========
toggle_email_field(False)
toggle_cash_field(win["-PAY-"].get())
refresh_items_table()
refresh_totals()

# ========= Loop =========
while True:
    ev, val = win.read()
    if ev in (sg.WINDOW_CLOSED, "Salir"):
        break

    if ev == "-SENDMAIL-":
        toggle_email_field(val["-SENDMAIL-"])

    if ev == "-PAY-":
        toggle_cash_field(val["-PAY-"])

    if ev == "-ADD-":
        try:
            name = (val["-P_NAME-"] or "").strip()
            if not name:
                sg.popup_error("Ingresa el nombre del producto.")
                continue
            qty = to_float(val["-P_QTY-"], 1.0)
            price = to_float(val["-P_PRICE-"], 0.0)
            if qty <= 0 or price < 0:
                sg.popup_error("Cantidad/Precio inválidos.")
                continue
            items.append({"name": name, "qty": qty, "price": price})
            refresh_items_table()
            refresh_totals()
            # limpiar inputs de producto
            win["-P_NAME-"].update(""); win["-P_QTY-"].update("1"); win["-P_PRICE-"].update("0.00")
        except Exception as e:
            sg.popup_error(f"Error al agregar: {e}")

    if ev == "-EDIT-":
        sel = val["-TABLE-"]
        if not sel:
            sg.popup_error("Selecciona una fila para editar.")
            continue
        idx = sel[0]
        try:
            name = (val["-P_NAME-"] or items[idx]["name"]).strip()
            qty = to_float(val["-P_QTY-"] or items[idx]["qty"])
            price = to_float(val["-P_PRICE-"] or items[idx]["price"])
            if not name or qty <= 0 or price < 0:
                sg.popup_error("Datos inválidos para editar.")
                continue
            items[idx] = {"name": name, "qty": qty, "price": price}
            refresh_items_table()
            refresh_totals()
        except Exception as e:
            sg.popup_error(f"Error al editar: {e}")

    if ev == "-DEL-":
        sel = val["-TABLE-"]
        if not sel:
            sg.popup_error("Selecciona una fila para eliminar.")
            continue
        idx = sel[0]
        try:
            items.pop(idx)
            refresh_items_table()
            refresh_totals()
        except Exception as e:
            sg.popup_error(f"Error al eliminar: {e}")

    if ev == "-TABLE-":
        # al seleccionar, carga los valores al formulario de producto (para editar cómodo)
        sel = val["-TABLE-"]
        if sel:
            it = items[sel[0]]
            win["-P_NAME-"].update(it["name"])
            win["-P_QTY-"].update(f"{it['qty']:.2f}")
            win["-P_PRICE-"].update(f"{it['price']:.2f}")

    if ev == "Generar PDF":
        try:
            if not items:
                sg.popup_error("Agrega al menos un producto.")
                continue

            subtotal, iva, total = refresh_totals()

            # Pago
            metodo = val["-PAY-"]
            recibido = 0.0
            mostrar_cambio = False
            if metodo == "Efectivo":
                recibido = to_float(val["-CASH-"], 0.0)
                if recibido < total:
                    sg.popup_error(f"Efectivo insuficiente. Total ${total:.2f} > Recibido ${recibido:.2f}")
                    continue
                mostrar_cambio = True
                cambio = round(recibido - total, 2)
            else:
                cambio = 0.0

            # Guardar PDF
            default_name = f"TICKET_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            save_path = sg.popup_get_file(
                "Guardar PDF como...",
                save_as=True,
                default_extension=".pdf",
                file_types=(("PDF","*.pdf"),),
                default_path=default_name  # ← corrección: antes decía initial_file
            )

            if not save_path:
                continue

            fecha, hora = now_date_time()
            datos = {
                "fecha": fecha,
                "hora":  hora,
                "metodo_pago": metodo,
                "mostrar_recibido_y_cambio": mostrar_cambio,
                "recibido": recibido,
                "cambio": cambio,
                "cliente_nombre": (val["-CLIENTE-"] or "").strip(),
                "cliente_doc":    (val["-DOC-"] or "").strip()
            }
            totales = {"subtotal": subtotal, "iva": iva, "total": total}

            create_ticket_pdf(
                store={"name": STORE["name"], "address": STORE["address"], "nit": STORE["nit"]},
                datos=datos, items=items, totales=totales, out_path=save_path
            )

            # ¿Enviar por correo?
            if val["-SENDMAIL-"]:
                if not MAIL_AVAILABLE or "smtp" not in RAW_CFG:
                    sg.popup_error("Envío por correo no disponible. Configura SMTP en config.json.")
                else:
                    to = (val["-EMAIL-"] or "").strip()
                    if not to:
                        sg.popup_error("Ingresa el correo destino.")
                    else:
                        cfg = load_mail_config("config.json")
                        subject = f"Comprobante de compra - {STORE['name']}"
                        body = "Adjunto su comprobante de compra. ¡Gracias!"
                        send_mail(to, subject, body, save_path, cfg)
                        sg.popup("Correo enviado.")

            if sg.popup_yes_no(f"PDF generado:\n{save_path}\n\n¿Abrir ahora?",
                               yes_text="Abrir", no_text="Cerrar") == "Yes":
                open_file(save_path)

        except Exception as e:
            sg.popup_error(f"Error: {e}")

win.close()
