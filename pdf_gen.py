# pdf_gen.py
from fpdf import FPDF

# Ticket térmico 80 mm
PAGE_WIDTH_MM = 80
MARGIN_L, MARGIN_R = 5, 5        # márgenes laterales generosos

class TicketPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format=(PAGE_WIDTH_MM, 200))
        self.set_auto_page_break(auto=True, margin=8)

    def header(self):
        self.set_font("Helvetica", "B", 12)
        # Nunca usar cell(0,...). Usamos EPW explícito en create_ticket_pdf.
        self.ln(1)

    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 4, "Documento interno. No sustituye DTE.", 0, 1, "C")

def _line(pdf: FPDF, epw: float):
    pdf.set_draw_color(180, 180, 180)
    pdf.set_x(pdf.l_margin)
    pdf.cell(epw, 0, "", 0, 1)  # mueve el cursor a la derecha
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(1)

def _force_wrap_no_spaces(text: str, every: int = 18) -> str:
    s = (text or "").strip()
    if " " in s or "-" in s:
        return s
    return "\n".join(s[i:i+every] for i in range(0, len(s), every))

def create_ticket_pdf(store, datos, items, totales, out_path):
    """
    store:  {name, address, nit}
    datos:  {fecha, hora, metodo_pago, mostrar_recibido_y_cambio, recibido, cambio,
             cliente_nombre?, cliente_doc?}
    items:  [{name, qty, price}]
    totales:{subtotal, iva, total}
    """
    pdf = TicketPDF()
    pdf.set_margins(MARGIN_L, 6, MARGIN_R)
    pdf.add_page()

    # Ancho útil EXPLÍCITO para todas las celdas
    EPW = pdf.w - pdf.l_margin - pdf.r_margin   # e.g., 80 - 5 - 5 = 70 mm
    EPS = 0.8                                    # holgura para la última celda

    # ---- Encabezado tienda (usar EPW, no 0) ----
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(EPW, 5, store["name"], 0, "C")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(EPW, 4, store["address"], 0, "C")
    pdf.set_x(pdf.l_margin)
    pdf.cell(EPW, 4, f"NIT: {store['nit']}", 0, 1, "C")
    _line(pdf, EPW)

    # ---- Fecha / hora ----
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(EPW, 5, f"Fecha: {datos['fecha']}   Hora: {datos['hora']}", 0, 1, "C")

    # ---- Cliente ----
    if datos.get("cliente_nombre"):
        _line(pdf, EPW)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(EPW, 5, "Cliente", 0, 1)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(EPW, 5, f"{datos['cliente_nombre']}")
        doc = (datos.get("cliente_doc") or "").strip()
        if doc:
            pdf.set_x(pdf.l_margin)
            pdf.cell(EPW, 5, f"Documento: {doc}", 0, 1)

    _line(pdf, EPW)

    # ---- Tabla productos (anchos fijos + última columna dinámica) ----
    W_DESC  = 40.0
    W_QTY   = 8.0
    W_PRICE = 10.0
    W_AMT   = max(6.0, EPW - (W_DESC + W_QTY + W_PRICE) - EPS)  # “lo que queda” con holgura

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(W_DESC, 6, "Producto", 0)
    pdf.cell(W_QTY,  6, "Cant",     0, 0, "R")
    pdf.cell(W_PRICE,6, "Precio",   0, 0, "R")
    pdf.cell(W_AMT,  6, "Importe",  0, 1, "R")

    pdf.set_font("Helvetica", "", 8)  # 8pt más seguro en térmico
    for it in items:
        importe = it["qty"] * it["price"]
        name = _force_wrap_no_spaces(str(it["name"]))

        # Descripción multilínea dentro de su ancho
        y0 = pdf.get_y()
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(W_DESC, 4.6, name, 0)
        y1 = pdf.get_y()
        h = max(4.6, y1 - y0)

        # Celdas numéricas
        pdf.set_xy(pdf.l_margin + W_DESC, y0)
        pdf.cell(W_QTY,   h, f"{it['qty']:.2f}",   0, 0, "R")
        pdf.cell(W_PRICE, h, f"{it['price']:.2f}", 0, 0, "R")
        # Calcular SIEMPRE la última con el resto disponible en la fila actual
        rest = (pdf.w - pdf.r_margin) - (pdf.get_x())
        w_amt_row = max(6.0, rest - EPS)
        pdf.cell(w_amt_row, h, f"{importe:.2f}", 0, 1, "R")

    _line(pdf, EPW)

    # ---- Totales (dos columnas que suman < EPW) ----
    VALUE_W = 12.0
    LABEL_W = EPW - VALUE_W - EPS

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(LABEL_W, 6, "Subtotal:", 0, 0, "R"); pdf.cell(VALUE_W, 6, f"{totales['subtotal']:.2f}", 0, 1, "R")
    pdf.set_x(pdf.l_margin)
    pdf.cell(LABEL_W, 6, "IVA (13%):", 0, 0, "R"); pdf.cell(VALUE_W, 6, f"{totales['iva']:.2f}",      0, 1, "R")

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(LABEL_W, 7, "TOTAL:", 0, 0, "R"); pdf.cell(VALUE_W, 7, f"{totales['total']:.2f}", 0, 1, "R")
    _line(pdf, EPW)

    # ---- Pago ----
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(EPW, 5, f"Método de pago: {datos['metodo_pago']}", 0, 1)
    if datos.get("mostrar_recibido_y_cambio"):
        pdf.set_x(pdf.l_margin)
        pdf.cell(LABEL_W, 5, "Recibido:", 0, 0, "R"); pdf.cell(VALUE_W, 5, f"{datos['recibido']:.2f}", 0, 1, "R")
        pdf.set_x(pdf.l_margin)
        pdf.cell(LABEL_W, 5, "Cambio:",   0, 0, "R"); pdf.cell(VALUE_W, 5, f"{datos['cambio']:.2f}",   0, 1, "R")

    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(EPW, 4, "Gracias por su compra.")

    pdf.output(out_path)
