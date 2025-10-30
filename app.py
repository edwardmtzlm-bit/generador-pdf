# --- Estilos globales (tema oscuro morado) ---
st.markdown("""
<style>
:root{
  --hm-bg:#12071E;           /* fondo principal */
  --hm-card:#1C0D30;         /* fondo de tarjetas/inputs */
  --hm-primary:#7C4DFF;      /* morado principal */
  --hm-text:#EDE7F6;         /* texto */
  --hm-muted:#A999C3;        /* texto secundario */
}

/* Fondo general con degradado sutil */
html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 10% -10%, #1B0F2F 0%, transparent 60%),
              radial-gradient(800px 400px at 110% 10%, #2A1549 0%, transparent 60%),
              var(--hm-bg) !important;
  color: var(--hm-text);
}

/* Quitar barra superior blanca */
[data-testid="stHeader"]{ background: transparent; }

/* Ancho del contenido y respiro */
.block-container{
  max-width: 980px;
  padding-top: 2rem;
  padding-bottom: 4rem;
}

/* Inputs y textareas estilo tarjeta */
textarea, .stTextInput input, .stNumberInput input{
  background: var(--hm-card) !important;
  color: var(--hm-text) !important;
  border: 1px solid #2C1B4A !important;
  border-radius: 12px !important;
}

/* Sliders */
.css-1kdj8x9, .stSlider [data-baseweb="slider"] div:nth-child(1){
  color: var(--hm-primary) !important;
}

/* Botón principal */
.stButton>button{
  background: var(--hm-primary) !important;
  color: white !important;
  border: 0 !important;
  border-radius: 12px !important;
  padding: .6rem 1.1rem !important;
  box-shadow: 0 6px 18px rgba(124,77,255,.25);
}
.stButton>button:hover{ filter: brightness(1.05); }

/* Botón de descarga */
.stDownloadButton>button{
  background: #5E35B1 !important;
  color: white !important;
  border-radius: 12px !important;
  padding: .6rem 1.1rem !important;
  box-shadow: 0 6px 18px rgba(94,53,177,.25);
}

/* Subtítulos y labels */
h2,h3 { color: var(--hm-text); }
small, .stCaption, label { color: var(--hm-muted) !important; }
</style>
""", unsafe_allow_html=True)
