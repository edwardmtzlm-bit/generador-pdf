import streamlit as st
import io, os, copy, tempfile, re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader  # reservado para futuro (logos)
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, ArrayObject

# =========================
#    AJUSTES DE LA APP
# =========================
st.set_page_config(page_title="Generador de PDF", page_icon="📝")
st.title("🧾 Generador de PDF con Plantilla")
st.caption(f"Streamlit {st.__version__}")

DEFAULT_TEMPLATE_NAME = "Membrete textos editable.pdf"  # si está en la carpeta, la usa por defecto

# ============
#  UTILIDADES
# ============
def sanitize_filename(name: str) -> str:
    name = name.lower().replace(" ", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    return name[:50]

def _wrap_por_ancho(c, texto: str, ancho_max: float) -> list[str]:
    """Rompe texto por ancho real (no por número fijo de caracteres)."""
    lineas = []
    for parrafo in texto.splitlines():
        if not parrafo.strip():
            lineas.append("")
            continue
        actual = ""
        for palabra in parrafo.split():
            candidato = (actual + " " + palabra).strip()
            if c.stringWidth(candidato) <= ancho_max:
                actual = candidato
            else:
                if actual:
                    lineas.append(actual)
                actual = palabra
        if actual:
            lineas.append(actual)
    return lineas

def _nombre_campo(annot_obj) -> str:
    """Normaliza el nombre del campo (/T) a texto plano sin paréntesis."""
    val = annot_obj.get("/T")
    if val is None:
        return ""
    return str(val).strip("()").strip()

# ============================================
#  GENERACIÓN DEL CONTENIDO (SIN PLANTILLA)
# ============================================
def crear_pdf_contenido(titulo: str, cuerpo: str, solo_primera_con_titulo: bool) -> PdfReader:
    """
    Devuelve un PdfReader en memoria con:
      - Título solo en la 1a página (si solo_primera_con_titulo=True).
      - Paginado automático por ancho real.
      - Numeración "Página X de Y" solo si hay >1 página.
    """
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    width, height = letter

    # Márgenes y tipografías
    MARGEN_IZQ = 0.75 * inch
    MARGEN_SUP = 1.0 * inch
    ESPACIADO = 15  # puntos
    FUENTE_TIT = ("Helvetica-Bold", 16)
    FUENTE_TXT = ("Helvetica", 11)
    FUENTE_PAG = ("Helvetica", 9)

    ancho_texto = width - 2 * MARGEN_IZQ
    c.setFont(*FUENTE_TXT)
    lineas = _wrap_por_ancho(c, cuerpo, ancho_texto)

    # Líneas por página (estimado por altura disponible / espaciado)
    lineas_por_pagina = int((height - MARGEN_SUP - 1.5 * inch) / ESPACIADO)

    # Partir en páginas
    paginas, pagina = [], []
    for ln in lineas:
        pagina.append(ln)
        if len(pagina) >= lineas_por_pagina:
            paginas.append(pagina)
            pagina = []
    if pagina:
        paginas.append(pagina)

    total = len(paginas)

    for i, bloque in enumerate(paginas):
        y = height - MARGEN_SUP

        # Título en 1ª página, o en todas si se desactiva la opción
        if (i == 0 and solo_primera_con_titulo) or (not solo_primera_con_titulo):
            c.setFont(*FUENTE_TIT)
            c.drawString(MARGEN_IZQ, y, titulo)
            y -= 30

        c.setFont(*FUENTE_TXT)
        for ln in bloque:
            c.drawString(MARGEN_IZQ, y, ln)
            y -= ESPACIADO

        # Numeración si hay más de 1 página
        if total > 1:
            c.setFont(*FUENTE_PAG)
            c.drawRightString(width - MARGEN_IZQ, 0.75 * inch, f"Página {i+1} de {total}")

        c.showPage()

    c.save()
    packet.seek(0)
    return PdfReader(packet)

# ===============================================
#  FUSIÓN CON PLANTILLA Y LIMPIEZA DE CAMPOS
# ===============================================
def mezclar_con_plantilla_y_limpiar(contenido_reader: PdfReader, plantilla_reader: PdfReader) -> PdfWriter:
    """
    Superpone cada página de `contenido_reader` sobre la plantilla.
    Limpia:
      - 'Text Body' en TODAS las páginas.
      - 'Text Title' a partir de la segunda página.
    Devuelve un PdfWriter listo para escribir.
    """
    writer = PdfWriter()
    n_tpl = len(plantilla_reader.pages)
    last_idx = max(0, n_tpl - 1)

    for i in range(len(contenido_reader.pages)):
        idx = i if i < n_tpl else last_idx
        base = copy.deepcopy(plantilla_reader.pages[idx])  # clonar

        if "/Annots" in base:
            nuevos = ArrayObject()
            for annot_ref in base["/Annots"]:
                annot_obj = annot_ref.get_object()
                nombre = _nombre_campo(annot_obj)
                if nombre == "Text Body":
                    continue
                if i > 0 and nombre == "Text Title":
                    continue
                nuevos.append(annot_ref)
            base[NameObject("/Annots")] = nuevos

        base.merge_page(contenido_reader.pages[i])
        writer.add_page(base)

    return writer

# =========================
#       INTERFAZ UI
# =========================
st.subheader("1) Selecciona la plantilla (opcional)")
plantilla_file = st.file_uploader("Sube tu plantilla PDF (opcional)", type=["pdf"], key="tpl")

st.subheader("2) Escribe tu contenido")
titulo = st.text_input("Título (solo en la primera hoja por defecto)", "Reporte de Ventas", key="title")
cuerpo = st.text_area("Cuerpo del artículo (se paginará automáticamente)", height=240, key="body")

st.subheader("3) Ajustes")
solo_primera_con_titulo = st.checkbox("Mostrar título solo en la primera hoja", value=True, key="only_first_title")

if st.button("Generar PDF", key="go"):
    if not cuerpo.strip():
        st.warning("Escribe algún contenido en el cuerpo del artículo.")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 1) Construye el contenido
                contenido_reader = crear_pdf_contenido(titulo, cuerpo, solo_primera_con_titulo)

                # 2) Plantilla: subida por el usuario o archivo local por defecto (si existe)
                plantilla_reader = None
                if plantilla_file is not None:
                    plantilla_reader = PdfReader(plantilla_file)
                else:
                    if os.path.exists(DEFAULT_TEMPLATE_NAME):
                        plantilla_reader = PdfReader(DEFAULT_TEMPLATE_NAME)

                # 3) Fusiona (si hay plantilla) o exporta directo
                out_path = os.path.join(tmpdir, sanitize_filename(titulo or "documento") + ".pdf")

                if plantilla_reader:
                    writer = mezclar_con_plantilla_y_limpiar(contenido_reader, plantilla_reader)
                    with open(out_path, "wb") as fh:
                        writer.write(fh)
                else:
                    # >>> CORRECCIÓN AQUI: NO usar append_pages_from_reader (no existe en PyPDF2 3.x)
                    writer = PdfWriter()
                    for p in contenido_reader.pages:
                        writer.add_page(p)
                    with open(out_path, "wb") as fh:
                        writer.write(fh)

                # 4) Botón de descarga
                with open(out_path, "rb") as f:
                    st.download_button("⬇️ Descargar PDF", f, file_name=os.path.basename(out_path), mime="application/pdf")

        except Exception as e:
            # Muestra el error concreto para poder depurar si algo más aparece
            st.error(f"Ocurrió un error: {type(e).__name__}: {e}")
