import re
import io
import streamlit as st
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfObject, PdfName
from pdfrw.objects.pdfstring import PdfString

# ---- Configuración de la página ----
st.set_page_config(page_title="Generador de PDF", page_icon="🧾", layout="centered")
st.title("🧾 Generador de PDF con plantilla")
st.caption("Rellena los campos y descarga tu PDF listo para usar.")

# ---- Constantes / nombres de campos en tu PDF ----
DEFAULT_TEMPLATE_PATH = "Membrete textos editable.pdf"
TITLE_FIELD_NAME = "Text Title"
BODY_FIELD_NAME  = "Text Body"

def sanitize_filename(name: str) -> str:
    name = name.lower().replace(" ", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    return name[:50] or "documento"

def safe_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except Exception:
        return default

def find_annotation_in_pdf(pdf_template, field_name):
    for page in pdf_template.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        for annot in annots:
            if annot.get("/Subtype") != PdfName.Widget:
                continue
            t = annot.get("/T")
            if t is None:
                continue
            try:
                t_name = t.to_unicode()
            except Exception:
                t_name = str(t).strip("()")
            if t_name == field_name:
                return annot
    return None

def fill_pdf(template_reader, titulo, cuerpo):
    # Asegurar NeedAppearances
    acroform = getattr(template_reader.Root, "AcroForm", None)
    if acroform is None:
        template_reader.Root.AcroForm = PdfDict()
        acroform = template_reader.Root.AcroForm
    acroform.update(PdfDict(NeedAppearances=PdfObject("true")))

    # Título
    title_annot = find_annotation_in_pdf(template_reader, TITLE_FIELD_NAME)
    if title_annot:
        title_annot.update(PdfDict(V=PdfString.encode(titulo),
                                   DV=PdfString.encode(titulo)))
    else:
        st.warning(f"No se encontró el campo '{TITLE_FIELD_NAME}' en la plantilla.")

    # Cuerpo
    body_annot = find_annotation_in_pdf(template_reader, BODY_FIELD_NAME)
    if body_annot:
        body_annot.update(PdfDict(V=PdfString.encode(cuerpo),
                                  DV=PdfString.encode(cuerpo)))
        current_flags = safe_int(body_annot.get("/Ff"), 0)
        multiline_flag = 1 << 12  # 4096
        if (current_flags & multiline_flag) == 0:
            body_annot.update(PdfDict(Ff=PdfObject(str(current_flags | multiline_flag))))
    else:
        st.warning(f"No se encontró el campo '{BODY_FIELD_NAME}' en la plantilla.")

    # Escribir a memoria
    out_buf = io.BytesIO()
    PdfWriter().write(out_buf, template_reader)
    return out_buf.getvalue()

# ---- UI: plantilla ----
st.subheader("1) Selecciona la plantilla PDF")
up = st.file_uploader("Sube tu plantilla (opcional). Si no subes, usaré la de la carpeta.",
                      type=["pdf"])

# ---- UI: contenido ----
st.subheader("2) Escribe tu contenido")
titulo = st.text_input("Título del artículo", value="Reporte de Ventas")
cuerpo = st.text_area(
    "Cuerpo del artículo",
    value="Este es el contenido del cuerpo del artículo. Puede ser un párrafo largo con múltiples oraciones.",
    height=180
)

# ---- Generar ----
if st.button("Generar PDF"):
    try:
        if up is not None:
            # Leer desde el archivo subido
            data = up.read()
            template_reader = PdfReader(io.BytesIO(data))
        else:
            # Usar plantilla local por defecto
            template_reader = PdfReader(DEFAULT_TEMPLATE_PATH)

        pdf_bytes = fill_pdf(template_reader, titulo, cuerpo)
        nombre = sanitize_filename(titulo) + ".pdf"
        st.success("¡PDF generado con éxito!")
        st.download_button("⬇️ Descargar PDF", data=pdf_bytes, file_name=nombre, mime="application/pdf")
    except FileNotFoundError:
        st.error(f"No encontré '{DEFAULT_TEMPLATE_PATH}'. Sube una plantilla o coloca ese archivo en la carpeta.")
    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
