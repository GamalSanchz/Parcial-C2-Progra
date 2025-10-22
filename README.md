# Parcial-C2-Progra
Parcial del Cómputo 2 de programación computacional 3

Integrantes:
Diego Maximiliano Aviles Gómez.
Codigo: SMTR042724.
Francisco Javier Hernández Aguirre.
Codigo: SMSS068924.
Brandom Gamaliel Sánchez Guevara.
Codigo:SMSS.

Descripción del repositorio:
programa en Python para hacer tickets o facturas en PDF usando FPDF que fue la que elegimos como base principal. La idea era generar tickets o facturas en PDF con formato tipo térmico, como los que salen en impresoras de 80 mm. Todo lo demás (interfaz, envío por correo, etc.) se agregó como complemento para que fuera más útil y presentable

Tiene una interfaz con PySimpleGUI para meter los datos del cliente y los productos, calcula subtotal, IVA y total, y genera el PDF con diseño personalizado. También se puede enviar por correo si se configura el SMTP en el config.json.

No usa base de datos. Los productos se guardan en memoria mientras se usa la app. El diseño del PDF se puede modificar desde el archivo pdf_gen.py, que tiene todo lo relacionado con márgenes, fuentes, columnas, etc.
