app_code_with_gemini = '''import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
from google import genai

# Intentar importar reportlab de forma segura
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Configuración de la página
st.set_page_config(page_title="Control de Deudas - Comedor", layout="wide")
st.title("🍴 Control de Cuentas con Asesor Financiero IA (Gemini bajo demanda)")

# Inicializar estados de la sesión
if 'estudiantes' not in st.session_state:
    st.session_state.estudiantes = {}
if 'productos' not in st.session_state:
    st.session_state.productos = {
        "Almuerzo Completo": 2000.00,
        "Desayuno": 1200.00,
        "Bebida": 600.00,
        "Snack": 800.00
    }
if 'transacciones' not in st.session_state:
    st.session_state.transacciones = []
if 'alerta_activa' not in st.session_state:
    st.session_state.alerta_activa = None
if 'estudiantes_bloqueados' not in st.session_state:
    st.session_state.estudiantes_bloqueados = set()

# Función de Reporte PDF
def generar_pdf_deudores(datos_estudiantes):
    if not REPORTLAB_AVAILABLE:
        return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#1e3d59"),
        alignment=1
    )
    story.append(Paragraph("Reporte de Estudiantes Adeudados - Comedor", titulo_style))
    story.append(Spacer(1, 20))
    deudores = [est for est in datos_estudiantes if est["Deuda Pendiente (₡)"] > 0]
    if len(deudores) == 0:
        story.append(Paragraph("No existen deudas pendientes.", styles['Normal']))
    else:
        tabla_datos = [["Estudiante", "Teléfono", "Consumido", "Pagado", "Deuda Pendiente"]]
        for d in deudores:
            tabla_datos.append([
                d["Estudiante"],
                d["Teléfono"],
                f"₡{d['Total Consumido (₡)']:,.2f}",
                f"₡{d['Total Pagado (₡)']:,.2f}",
                f"₡{d['Deuda Pendiente (₡)']:,.2f}"
            ])
        t = Table(tabla_datos, colWidths=[150, 100, 100, 100, 100])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e3d59")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("GRID", (0,0), (-1,-1), 1, colors.HexColor("#dddddd")),
        ]))
        story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

# Definir el Diálogo Emergente Obligatorio de Alerta del Asesor IA
@st.dialog("🚨 Alerta de Riesgo - Asesor Financiero IA")
def mostrar_alerta_dialog(mensaje_alerta, estudiante_implicado):
    st.warning("🛑 Alerta sobre cuenta bajo análisis solicitado.")
    st.markdown(mensaje_alerta)
    st.markdown("---")
    st.subheader("¿Qué acción desea tomar el administrador?")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        if st.button("👍 Acatar y Bloquear Crédito"):
            st.session_state.estudiantes_bloqueados.add(estudiante_implicado)
            st.session_state.alerta_activa = None
            st.success(f"Se ha suspendido temporalmente el crédito para {estudiante_implicado}.")
            st.rerun()
    with col_opt2:
        if st.button("⚠️ Ignorar Recomendación (Cerrar)"):
            st.session_state.alerta_activa = None
            st.rerun()

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    gemini_api_key = st.text_input("Google Gemini API Key", type="password", help="Consigue una llave gratuita en Google AI Studio. Se usará solo bajo demanda.")

    st.markdown("---")
    st.subheader("👥 Registrar Estudiante")
    nuevo_estudiante = st.text_input("Nombre del Estudiante").strip()
    telefono_estudiante = st.text_input("Número de Teléfono").strip()
    deuda_inicial = st.number_input("Deuda Inicial (₡)", min_value=0.0, value=0.0, step=500.0)
    if st.button("Registrar Estudiante"):
        if nuevo_estudiante and telefono_estudiante:
            if nuevo_estudiante not in st.session_state.estudiantes:
                st.session_state.estudiantes[nuevo_estudiante] = {
                    "telefono": telefono_estudiante,
                    "consumido": deuda_inicial,
                    "pagado": 0.0
                }
                st.success(f"{nuevo_estudiante} registrado con éxito.")
                st.rerun()

    st.markdown("---")
    st.subheader("🍔 Agregar/Actualizar Producto")
    nuevo_producto = st.text_input("Nombre del Producto/Servicio").strip()
    precio_producto = st.number_input("Precio (₡)", min_value=1.0, value=1000.0, step=100.0)
    if st.button("Guardar Producto"):
        if nuevo_producto:
            st.session_state.productos[nuevo_producto] = precio_producto
            st.success(f"Producto {nuevo_producto} guardado a ₡{precio_producto:,.2f}")
            st.rerun()

# Consulta manual solicitada explícitamente por el usuario a Google Gemini
def consultar_asesor_ia_manual(estudiante, nueva_deuda):
    if not gemini_api_key:
        st.warning("⚠️ Por favor, ingresa tu Google Gemini API Key en la barra lateral para usar el asesor.")
        return
    try:
        # Correcto uso del SDK google-genai
        client = genai.Client(api_key=gemini_api_key)
        
        # Obtener el historial de compras del estudiante para darle contexto a la IA
        historial_estudiante = [t for t in st.session_state.transacciones if t["Estudiante"] == estudiante]
        historial_texto = str(historial_estudiante[-8:])

        system_prompt = "Eres un Asesor de Riesgo de Crédito y Cobranza para un Comedor Universitario. Tu única función es analizar la cuenta de un estudiante bajo demanda del administrador, y justificar si se le debe suspender el crédito basándose en su saldo acumulado e historial (ejemplo de riesgo mayor a ₡10,000). Escribe de manera profesional, asertiva y concisa en colones costarricenses (₡)."
        query_user = f"El estudiante {estudiante} tiene una deuda acumulada de ₡{nueva_deuda:,.2f}. Su historial de consumo y abonos es: {historial_texto}. Analiza si amerita congelarle el crédito temporalmente y da tu recomendación directa."

        # Combinación de textos evitando escapes complejos de saltos de línea
        prompt_completo = system_prompt + "\\n\\n" + query_user

        # Usando 'gemini-1.5-flash' para compatibilidad máxima de la API sin problemas de migración
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt_completo,
        )
        resultado = response.text

        st.session_state.alerta_activa = {
            "mensaje": resultado,
            "estudiante": estudiante
        }
        st.rerun()
    except Exception as e:
        st.error(f"Error al conectar con Gemini: {e}")

# Evaluar si hay una alerta de IA pendiente para forzar el diálogo
if st.session_state.alerta_activa:
    mostrar_alerta_dialog(st.session_state.alerta_activa["mensaje"], st.session_state.alerta_activa["estudiante"])

# Layout Principal
col1, col2 = st.columns([1, 1])

with col1:
    st.header("💸 Registrar Consumo (Anotar a Cuenta)")
    if st.session_state.estudiantes:
        with st.form("form_consumo"):
            estudiante_sel = st.selectbox("Selecciona Estudiante", list(st.session_state.estudiantes.keys()))
            producto_sel = st.selectbox("Selecciona Producto", list(st.session_state.productos.keys()))
            cantidad = st.number_input("Cantidad", min_value=1, value=1)
            submit_cobro = st.form_submit_button("Confirmar Consumo")

            if submit_cobro:
                if estudiante_sel in st.session_state.estudiantes_bloqueados:
                    st.error(f"❌ ERROR: El crédito para {estudiante_sel} está SUSPENDIDO por recomendación del Asesor IA.")
                else:
                    total_cobrar = st.session_state.productos[producto_sel] * cantidad
                    st.session_state.estudiantes[estudiante_sel]["consumido"] += total_cobrar

                    st.session_state.transacciones.append({
                        "Fecha": date.today().strftime("%Y-%m-%d"),
                        "Estudiante": estudiante_sel,
                        "Detalle": f"{producto_sel} (x{cantidad})",
                        "Monto (₡)": total_cobrar,
                        "Tipo": "Consumo"
                    })
                    st.success("Consumo registrado con éxito.")
                    st.rerun()

    st.header("💵 Registrar Pago (Abono)")
    if st.session_state.estudiantes:
        with st.form("form_pago"):
            estudiante_pago = st.selectbox("Estudiante que Paga", list(st.session_state.estudiantes.keys()))
            monto_pago = st.number_input("Monto (₡)", min_value=1.0, value=1000.0)
            submit_pago = st.form_submit_button("Registrar Pago")

            if submit_pago:
                st.session_state.estudiantes[estudiante_pago]["pagado"] += monto_pago
                st.session_state.transacciones.append({
                    "Fecha": date.today().strftime("%Y-%m-%d"),
                    "Estudiante": estudiante_pago,
                    "Detalle": "Abono a Cuenta",
                    "Monto (₡)": monto_pago,
                    "Tipo": "Pago"
                })

                deuda_restante = st.session_state.estudiantes[estudiante_pago]["consumido"] - st.session_state.estudiantes[estudiante_pago]["pagado"]
                if deuda_restante < 5000.0 and estudiante_pago in st.session_state.estudiantes_bloqueados:
                    st.session_state.estudiantes_bloqueados.remove(estudiante_pago)
                    st.info(f"🎉 El crédito de {estudiante_pago} ha sido reactivado automáticamente al reducir su deuda.")

                st.success("Abono registrado.")
                st.rerun()

with col2:
    st.header("📋 Estado de Cuentas")
    datos_estudiantes = []
    if st.session_state.estudiantes:
        for nombre, valores in st.session_state.estudiantes.items():
            deuda_total = valores["consumido"] - valores["pagado"]
            estado = "❌ SUSPENDIDO" if nombre in st.session_state.estudiantes_bloqueados else "✅ Activo"
            datos_estudiantes.append({
                "Estudiante": nombre,
                "Teléfono": valores.get("telefono", "No registrado"),
                "Deuda Pendiente (₡)": deuda_total,
                "Total Consumido (₡)": valores["consumido"],
                "Total Pagado (₡)": valores["pagado"],
                "Estado de Crédito": estado
            })
        df_estudiantes = pd.DataFrame(datos_estudiantes)
        st.dataframe(df_estudiantes.style.format({
            "Total Consumido (₡)": "₡{:,.2f}",
            "Total Pagado (₡)": "₡{:,.2f}",
            "Deuda Pendiente (₡)": "₡{:,.2f}"
        }), use_container_width=True)

        # Botón para forzar análisis manual con Gemini únicamente bajo demanda
        st.subheader("🔍 Consulta Proactiva al Asesor IA")
        estudiante_analizar = st.selectbox("Selecciona el estudiante que deseas analizar:", list(st.session_state.estudiantes.keys()))
        if st.button("🤖 Consultar Asesor Financiero IA"):
            valores_e = st.session_state.estudiantes[estudiante_analizar]
            deuda_e = valores_e["consumido"] - valores_e["pagado"]
            consultar_asesor_ia_manual(estudiante_analizar, deuda_e)
    else:
        st.write("No hay estudiantes registrados.")

# Historial de Transacciones
st.header("📝 Historial de Transacciones")
if st.session_state.transacciones:
    df_trans = pd.DataFrame(st.session_state.transacciones)
    st.dataframe(df_trans.iloc[::-1], use_container_width=True)
'''

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code_with_gemini)
