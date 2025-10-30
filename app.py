import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import tempfile
import os
from PyPDF2 import PdfReader, PdfWriter

# --- Configuración de la aplicación ---
st.set_page_config(page_title="Generador de PDF", page_icon="📝")

# --- Limpieza de caché (ayuda a evitar errores visuales tras deploy/restart) ---
try:
    st.cache_data.clear()
    st.cache_resource.clear()
except Exception:
    pass

# --- Título e introducción ---
st.title("🧾 Generador de PDF con Plantilla")
st.write("Sube tu plantilla PDF, escribe el contenido y genera tu documento final automáticamente paginado.")

# --- Subida de plantilla base ---
plantilla = st.file_uploader("Sube tu plantilla PDF (opcional)", type=["pdf"])

# --- Contenido del usuario ---
titulo = st.text_input("Título (solo se imprimirá en la primera hoja)", "Reporte de Ventas")
contenido = st.text_area("Cuerpo del artículo (se paginará automáticamente)", height=250)

# --- Ajustes de paginado ---
st.subheader("Ajustes de paginado")
chars_por_linea = st.slider("Caracteres por línea", 50, 120, 95)
lineas_por_pagina = st.slider("Líneas por página", 20, 60, 35)
solo_primera_con_titulo = st.checkbox("Solo primera hoja con título", value=True)

# --- Imagen opcional ---
st.subheader("Imagen (opcional)")
imagen = st.file_uploader("Sube imagen (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])
pos_x = st.number_input("Posición X (0-612)", 0, 612, 400)
pos_y = st.number_input("Posición Y (0-792)", 0, 792, 700)
ancho = st.number_input("Ancho (px)", 50, 600, 150)
alto = st.number_input("Alto (px)", 50, 600, 80)
aplicar_a_todas = st.checkbox("Aplicar imagen a todas las páginas", value=False)
pagina_destino = st.number_input("Página de destino de la imagen", 1, 20, 1)

# --- Generar PDF ---
if st.button("Generar PDF"):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "output.pdf")
            c = canvas.Canvas(pdf_path, pagesize=letter)

            # Dividir el texto en páginas (paginado simple por caracteres/líneas)
            lineas = contenido.splitlines()
            paginas = []
            pagina_actual = []

            for linea in lineas:
                # Si una línea supera el límite, partir en trozos
                while len(linea) > chars_por_linea:
                    pagina_actual.append(linea[:chars_por_linea])
                    linea = linea[chars_por_linea:]
                pagina_actual.append(linea)

                # Si se llenó la página, apilar y continuar
                if len(pagina_actual) >= lineas_por_pagina:
                    paginas.append(pagina_actual)
                    pagina_actual = []

            # Agregar última página si hay remanente
            if pagina_actual:
                paginas.append(pagina_actual)

            # Escribir páginas
            for i, pagina in enumerate(paginas):
                # Título solo en primera hoja (si se marcó la opción)
                if i == 0 or not solo_primera_con_titulo:
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(72, 750, titulo)

                # Cuerpo
                y = 720
                c.setFont("Helvetica", 11)
                for linea in pagina:
                    c.drawString(72, y, linea)
                    y -= 18  # espaciado entre líneas

                # Imagen opcional
                if imagen and (aplicar_a_todas or (i + 1) == pagina_destino):
                    img = ImageReader(imagen)
                    c.drawImage(img, pos_x, pos_y, ancho, alto, mask='auto')

                c.showPage()

            c.save()

            # Fusionar con plantilla (si se subió)
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

            # Descargar el PDF final
            with open(final_path, "rb") as f:
                st.download_button("⬇️ Descargar PDF", f, file_name="resultado.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
