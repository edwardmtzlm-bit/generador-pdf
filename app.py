import io
import re
import textwrap
from copy import deepcopy

import streamlit as st
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfObject
from pdfrw.objects.pdfstring import PdfString

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader as PyPdfReader, PdfWriter as PyPdfWriter


# ===================== Configuración básica =====================
st.set_page_config(page_title="Generador de PDF", page_icon="🧾", layout="centered")
st.title("🧾 Generador de PDF con plantilla")
st.caption("Rellena tu membrete, pagina el texto automáticamente y (opcional) coloca una imagen.")


# Nombres de campos del formulario PDF (deben existir en la plantilla)
TITLE_FIELD_NAME = "Text Title"
BODY_FIELD_NAME = "Text Body"

DEFAULT_TEMPLATE_PATH = "Membrete textos editable.pdf"


# ===================== Utilidades =====================
def sanitize_filename(name: str) -> str:
    name = name.lower().replace(" ", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    return name[:50] or "documento"

def safe_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except Exception:
        return default

def _field_name(annot) -> str:
    """Obtiene el nombre del campo (/T) de forma segura, sin llamadas a métodos."""
    t = annot.get("/T")
    if t is None:
        return ""
    return str(t).strip("()").strip()

def find_annotation_in_pdf(pdf_template, field_name):
    """Busca una anotación por nombre en TODO el documento."""
    for page in pdf_template.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        for annot in annots:
            if str(annot.get("/Subtype")) == "/Widget" and _field_name(annot) == field_name:
                return annot
    return None

def find_annotation_in_page(page, field_name):
    """Busca una anotación por nombre en UNA página."""
    annots = page.get("/Annots")
    if not annots:
        return None
    for annot in annots:
        if str(annot.get("/Subtype")) == "/Widget" and _field_name(annot) == field_name:
            return annot
    return None


# ===================== Núcleo =====================
def fill_pdf(template_reader, titulo, cuerpo, chars_por_linea=95, lineas_por_pagina=35, titulo_solo_primera=True):
    """Duplica páginas según sea necesario y rellena el texto paginado."""
    # Forzar NeedAppearances
    acroform = getattr(template_reader.Root, "AcroForm", None)
    if acroform is None:
        template_reader.Root.AcroForm = PdfDict()
        acroform = template_reader.Root.AcroForm
    acroform.update(PdfDict(NeedAppearances=PdfObject("true")))

    # Dividir el texto en líneas
    lineas = []
    for bloque in cuerpo.splitlines():
        if not bloque.strip():
            lineas.append("")
        else:
            lineas.extend(textwrap.wrap(bloque, width=chars_por_linea, break_long_words=False))

    if not lineas:
        lineas = [""]

    trozos = []
    for i in range(0, len(lineas), lineas_por_pagina):
        trozos.append("\n".join(lineas[i:i + lineas_por_pagina]))

    # Primera página: poner título
    first_title = find_annotation_in_pdf(template_reader, TITLE_FIELD_NAME)
    if first_title:
        first_title.update(PdfDict(V=PdfString.encode(titulo), DV=PdfString.encode(titulo)))

    base_page = template_reader.pages[0]

    # Crear nuevas páginas según sea necesario
    for idx, texto_parcial in enumerate(trozos, start=1):
        if idx == 1:
            page = template_reader.pages[0]
        else:
            page = deepcopy(base_page)
            template_reader.pages.append(page)

        if idx > 1 and titulo_solo_primera:
            annots = page.get("/Annots") or []
            to_remove = []
            for annot in annots:
                if _field_name(annot) == TITLE_FIELD_NAME:
                    to_remove.append(annot)
            for a in to_remove:
                annots.remove(a)

        # Rellenar cuerpo
        body_annot = find_annotation_in_page(page, BODY_FIELD_NAME)
        if body_annot:
            nuevo_nombre = f"{BODY_FIELD_NAME}_{idx}"
            body_annot.update(PdfDict(T=PdfString.encode(nuevo_nombre)))
            body_annot.update(PdfDict(V=PdfString.encode(texto_parcial), DV=PdfString.encode(texto_parcial)))
            current_flags = safe_int(body_annot.get("/Ff"), 0)
            multiline_flag = 1 << 12
            if (current_flags & multiline_flag) == 0:
                body_annot.update(PdfDict(Ff=PdfObject(str(current_flags | multiline_flag))))

    # Guardar en memoria
    out_buf = io.BytesIO()
    PdfWriter().write(out_buf, template_reader)
    return out_buf.getvalue()


def overlay_image_on_pdf(pdf_bytes, img_bytes, x=400, y=700, w=150, h=80, pagina=1, aplicar_a_todas=False):
    """Superpone imagen JPG/PNG en coordenadas indicadas."""
    src = PyPdfReader(io.BytesIO(pdf_bytes))
    dst = PyPdfWriter()

    for i in range(len(src.pages)):
        page = src.pages[i]
        if (i == (pagina - 1)) or aplicar_a_todas:
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=letter)
            c.drawImage(io.BytesIO(img_bytes), x, y, width=w, height=h, preserveAspectRatio=True, mask="auto")
            c.save()
            buf.seek(0)
            overlay_reader = PyPdfReader(buf)
            overlay_page = overlay_reader.pages[0]
            page.merge_page(overlay_page)
        dst.add_page(page)

    out = io.BytesIO()
    dst.write(out)
    return out.getvalue()


# ===================== Interfaz =====================
st.subheader("1) Selecciona la plantilla")
up = st.file_uploader("Sube tu plantilla (opcional)", type=["pdf"])

st.subheader("2) Escribe tu contenido")
titulo = st.text_input("Título (solo se imprimirá en la primera hoja)", value="Reporte de Ventas")
cuerpo = st.text_area("Cuerpo del artículo (se paginará automáticamente)",
                      value="Este es el contenido del cuerpo del artículo. Puede ser un párrafo largo con múltiples oraciones. ",
                      height=200)

st.subheader("3) Ajustes de paginado")
chars_por_linea = st.slider("Caracteres por línea", 60, 140, 95, 1)
lineas_por_pagina = st.slider("Líneas por página", 20, 60, 35, 1)
titulo_solo_primera = st.checkbox("Solo primera hoja con título", value=True)

st.subheader("4) Imagen (opcional)")
imagen = st.file_uploader("Subir imagen (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])
x = st.number_input("Posición X", 0, 612, 400)
y = st.number_input("Posición Y", 0, 792, 700)
w = st.number_input("Ancho (px)", 10, 612, 150)
h = st.number_input("Alto (px)", 10, 792, 80)
aplicar_a_todas = st.checkbox("Aplicar imagen a todas las páginas", value=False)
pagina_img = st.number_input("Página destino de la imagen", min_value=1, value=1, step=1)

if st.button("Generar PDF"):
    try:
        if up is not None:
            template_reader = PdfReader(io.BytesIO(up.read()))
        else:
            template_reader = PdfReader(DEFAULT_TEMPLATE_PATH)

        pdf_bytes = fill_pdf(template_reader, titulo, cuerpo,
                             chars_por_linea, lineas_por_pagina, titulo_solo_primera)

        if imagen is not None:
            img_bytes = imagen.read()
            pdf_bytes = overlay_image_on_pdf(pdf_bytes, img_bytes,
                                             x=x, y=y, w=w, h=h,
                                             pagina=int(pagina_img),
                                             aplicar_a_todas=aplicar_a_todas)

        nombre = sanitize_filename(titulo) + ".pdf"
        st.success("¡PDF generado con éxito!")
        st.download_button("⬇️ Descargar PDF", data=pdf_bytes, file_name=nombre, mime="application/pdf")

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
