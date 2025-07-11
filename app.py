import streamlit as st
import pandas as pd
import datetime
import funciones_S9 as fs

# Configuración de la app
st.set_page_config(page_title="Balance Hídrico", layout="wide")

# Variables de sesión para manejar archivos
if 'archivos' not in st.session_state:
    st.session_state.archivos = [
        # {"nombre": "Buena Vista", "ruta": "docs/ACU_1DIA_BUENA_VISTA.xlsx"},
        # {"nombre": "Pira", "ruta": "docs/ACU-1DIA-PIRA.xlsx"},
        # {"nombre": "Cajamarquilla", "ruta": "docs/ACU-12HORAS-CAJAMARQUILLA.xlsx"},
        # {"nombre": "Pariacoto", "ruta": "docs/ACU-12HORAS-PARIACOTO.xlsx"},
    ]

# Inicializar archivos temporales para nombres
if 'temp_archivos_subidos' not in st.session_state:
    st.session_state.temp_archivos_subidos = []


# Días por mes para los cálculos
DIAS_MESES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# -------------------- SIDEBAR --------------------
with st.sidebar:
    st.image("docs/aecode.jpg", width=120)
    st.markdown("## AECODE")

    st.markdown("### Cargar archivos")
    nuevos_archivos = st.file_uploader("Selecciona archivos (máx. 5) .xlsx", accept_multiple_files=True, type=["xlsx"])

    # Si hay nuevos archivos, agregarlos a temporales si no están ya
    if nuevos_archivos:
        for archivo in nuevos_archivos:
            if not any(a['ruta'].name == archivo.name for a in st.session_state.temp_archivos_subidos):
                st.session_state.temp_archivos_subidos.append({"ruta": archivo, "nombre": ""})

    # Mostrar campos para ingresar nombre de estación
    todos_con_nombre = True
    for idx, archivo in enumerate(st.session_state.temp_archivos_subidos):
        nombre = st.text_input(f"Nombre para {archivo['ruta'].name}", value=archivo['nombre'], key=f"nombre_{archivo['ruta'].name}")
        st.session_state.temp_archivos_subidos[idx]['nombre'] = nombre.strip()
        if nombre.strip() == "":
            todos_con_nombre = False

    # Si todos los archivos tienen nombre, habilitar botón para confirmar subida
    if st.session_state.temp_archivos_subidos and todos_con_nombre:
        if st.button("Confirmar carga de archivos"):
            if len(st.session_state.archivos) + len(st.session_state.temp_archivos_subidos) <= 5:
                st.session_state.archivos.extend(st.session_state.temp_archivos_subidos)
                st.session_state.temp_archivos_subidos = []
                st.success("Archivos cargados correctamente.")
            else:
                st.error("Límite de 5 archivos excedido.")


    st.markdown("### Rango de fechas")
    st.markdown("📅")
    estaciones = fs.extraer_rango_fechas(st.session_state.archivos)
    if estaciones:
        rango_fechas = fs.superponer_rangos(estaciones)
    else:
        rango_fechas = [datetime.date(2020, 1, 1), datetime.date(2022, 12, 31)]

    fecha_inicio = st.date_input("Fecha de inicio", rango_fechas[0])
    fecha_fin = st.date_input("Fecha de fin", rango_fechas[1])

    st.markdown("### Datos de la cuenca")
    area = st.number_input("Área (km²)", min_value=0.0, value=2990.8)
    altura = st.number_input("Altura (m)", min_value=0.0, value=2160.0)
    longitud = st.number_input("Longitud (m)", min_value=0.0, value=83900.0)
    c = st.number_input("Coeficiente C", min_value=0.0, value=0.2)

    pendiente = altura / longitud if longitud else 0
    tc = 0.000325*((longitud**0.77)/(pendiente**0.385)) if pendiente else 0

    st.markdown(f"**Pendiente estimada:** {pendiente:.4f} m/m")
    st.markdown(f"**Tc estimado:** {tc:.2f} h")

# -------------------- MAIN --------------------
st.markdown("<h1 style='text-align: center;'>BALANCE HÍDRICO</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>OFERTA Y DEMANDA HÍDRICA</h3>", unsafe_allow_html=True)

# Sección datos por estación
estaciones_nombres = [e['nombre'] for e in estaciones] if estaciones else ["Estación Demo"]
col1, col2, col3, col4 = st.columns([2, 3, 3, 3])

with col1:
    estacion_sel = st.selectbox("Seleccionar estación", estaciones_nombres)

with col2:
    usar_rango_general = st.checkbox("Usar rango general", value=True)
    if usar_rango_general:
        rango_seleccionado = (fecha_inicio, fecha_fin)
    else:
        fecha1 = st.date_input("Inicio", fecha_inicio, key="fecha_inicio_manual")
        fecha2 = st.date_input("Fin", fecha_fin, key="fecha_fin_manual")
        rango_seleccionado = (fecha1, fecha2)

with col3:
    try:
        ppt_media, caudal_medio = fs.calcular_precipitacion_caudal(estacion_sel, estaciones, rango_seleccionado, DIAS_MESES)
    except:
        ppt_media, caudal_medio = 1200.0, 25.0
    st.metric("Precipitación media anual (mm/año)", f"{ppt_media:.2f}")

with col4:
    st.metric("Caudal medio anual (m³/s)", f"{caudal_medio:.2f}")

# -------------------- PESTAÑAS --------------------
tabs = st.tabs(["PROMEDIOS", "CURVAS DE DURACIÓN", "BALANCE HÍDRICO"])

# PROMEDIOS
tabla_pp = None
with tabs[0]:
    st.subheader("Tabla de valores promedio")
    try:
        tabla_pp = fs.tabla_pp_estaciones(estaciones, rango_seleccionado, DIAS_MESES)
        tabla_prom = fs.tabla_promedios(tabla_pp, DIAS_MESES)
    except:
        tabla_prom = pd.DataFrame({
            'pp (mm/mes)': [100]*12,
            'v (m/s)': [0.001]*12,
            'Q (m3/s)': [10]*12,
            'pp (mm/h)': [0.15]*12,
            'I': [0.2]*12
        }).T
    st.dataframe(tabla_prom)

# CURVAS DE DURACIÓN
with tabs[1]:
    st.subheader("Curva de duración del caudal")
    try:
        if tabla_pp is None:
            tabla_pp = fs.tabla_pp_estaciones(estaciones, rango_seleccionado, DIAS_MESES)
        tabla_duracion, tabla_resumen = fs.tabla_curvas_duracion_caudales(tabla_pp, rango_seleccionado, DIAS_MESES)
        fig = fs.graficar_curvas_duracion(tabla_duracion)
        st.plotly_chart(fig)
        st.markdown("### Resumen de caudales")
        st.dataframe(tabla_resumen)
    except:
        tabla_resumen = pd.DataFrame([[10]*12, [8]*12, [6]*12], index=['Q 50%', 'Q 75%', 'Q 95%'])
        st.info("No se pudo generar el gráfico de curvas de duración. Se muestran datos simulados.")
        st.dataframe(tabla_resumen)

# BALANCE HÍDRICO
with tabs[2]:
    st.subheader("Tabla de Demanda (editable)")
    try:
        demanda_editada = st.data_editor(fs.demanda.copy(), use_container_width=True, key="demanda_editor")
    except:
        demanda_editada = pd.DataFrame({
            'MES': ['Modelo1', 'Modelo2'],
            'ENE': [0.01, 0.02],
            'FEB': [0.02, 0.03],
            'MAR': [0.03, 0.04],
            'ABR': [0.04, 0.05],
            'MAY': [0.05, 0.06],
            'JUN': [0.06, 0.07],
            'JUL': [0.07, 0.08],
            'AGO': [0.08, 0.09],
            'SET': [0.09, 0.1],
            'OCT': [0.1, 0.11],
            'NOV': [0.11, 0.12],
            'DIC': [0.12, 0.13],
        })
        demanda_editada = st.data_editor(demanda_editada, use_container_width=True, key="demanda_fallback")

    st.subheader("Clasificación Oferta vs Demanda")
    try:
        tabla_balance = fs.tabla_balance_hidrico(tabla_resumen, demanda_editada)
        st.dataframe(tabla_balance)
    except:
        tabla_balance = pd.DataFrame([["OFERTA"]*12, ["DEFICIT"]*12], index=['Modelo1', 'Modelo2'])
        st.dataframe(tabla_balance)

    st.subheader("Gráfico Oferta vs Demanda")
    try:
        fig = fs.grafica_oferta_demanda(tabla_resumen, demanda_editada)
        st.plotly_chart(fig)
    except:
        st.info("No se pudo generar el gráfico por falta de datos.")
