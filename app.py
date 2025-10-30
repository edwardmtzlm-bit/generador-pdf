import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import tempfile
import os
from PyPDF2 import PdfReader, PdfWriter

# --- Configuración ---
st.set_page_config(page_title="Generador de PDF", page_icon="📝")

st.title("🧾 Generador de PDF con Plantilla")
st.caption(f"Versión de Streamlit: {st.__version__}")

# 1) Plantilla (opcional)
plantilla = st.file_uploader(
    "Sube tu plantilla PDF (opcional)", type=["pdf"], key="tpl"
)

# 2) Contenido
titulo = st.text_input(
    "Título (solo se imprimirá en la primera hoja)", "Reporte de Ventas", key="title"
)
contenido = st.text_area(
    "Cuerpo del artículo (se paginará automáticamente)", height=250, key="body"
)

# 3) Paginado
st.subheader("Ajustes de paginado")
chars_por_linea = st.slider("Caracteres por línea", 50, 120, 95, key="cpl")
lineas_por_pagina = st.slider("Líneas por página", 20, 60, 35, key="lpp")
solo_primera_con_titulo = st.checkbox(
    "Solo primera hoja con título", value=True, key="title_first_only"
)

# 4) Imagen (opcional)
st.subheader("Imagen (opcional)")
imagen = st.file_uploader(
    "Sube imagen (jpg, jpeg, png)", type=["jpg", "jpeg", "png"], key="img"
)
pos_x = st.number_input("Posición X (0-612)", 0, 612, 400, key="x")
pos_y = st.number_input("Posición Y (0-792)", 0, 792, 700, key="y")
ancho = st.number_input("Ancho (px)", 50, 600, 150, key="w")
alto = st.number_input("Alto (px)", 50, 600, 80, key="h")
aplicar_a_todas = st.checkbox(
    "Aplicar imagen a todas las páginas", value=False, key="img_all"
)
pagina_destino = st.number_input("Página de destino de la imagen", 1, 20, 1, key="img_page")

# 5) Generar
if st.button("Generar PDF", key="generate"):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "output.pdf")
            c = canvas.Canvas(pdf_path, pagesize=letter)

            # Partición de texto en páginas
            lineas = contenido.splitlines()
            paginas, pagina_actual = [], []

            for linea in lineas:
                # Rompe líneas largas según ancho configurado
                while len(linea) > chars_por_linea:
                    pagina_actual.append(linea[:chars_por_linea])
                    linea = linea[chars_por_linea:]
                pagina_actual.append(linea)

                if len(pagina_actual) >= lineas_por_pagina:
                    paginas.append(pagina_actual)
                    pagina_actual = []

            if pagina_actual:
                paginas.append(pagina_actual)

            # Render de páginas
            for i, pagina in enumerate(paginas):
                # Título en primera hoja (o en todas si desmarcas)
                if i == 0 or not solo_primera_con_titulo:
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(72, 750, titulo)

                y = 720
                c.setFont("Helvetica", 11)
                for linea in pagina:
                    c.drawString(72, y, linea)
                    y -= 18

                # Imagen opcional
                if imagen and (aplicar_a_todas or (i + 1) == pagina_destino):
                    img = ImageReader(imagen)
                    c.drawImage(img, pos_x, pos_y, ancho, alto, mask="auto")

                c.showPage()

            c.save()

            # Mezcla con plantilla si se subió
            if plantilla:
                reader_plantilla = PdfReader(plantilla)
                reader_contenido = PdfReader(pdf_path)
                writer = PdfWriter()

                for i in range(len(reader_contenido.pages)):
                    if i < len(reader_plantilla.pages):
                        base = reader_plantilla.pages[i]
                        contenido_pagina = reader_contenido.pages[i]
                        base.merge_page(contenido_pagina)
                        writer.add_page(base)
                    else:
                        writer.add_page(reader_contenido.pages[i])

                final_path = os.path.join(tmpdir, "final.pdf")
                with open(final_path, "wb") as f:
                    writer.write(f)
            else:
                final_path = pdf_path

            with open(final_path, "rb") as f:
                st.download_button(
                    "⬇️ Descargar PDF", f, file_name="resultado.pdf", mime="application/pdf"
                )

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
