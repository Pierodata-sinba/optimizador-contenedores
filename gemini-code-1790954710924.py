import numpy as np
import pandas as pd
import streamlit as st

# Configuración de la página con identidad de Sinba
st.set_page_config(
    page_title="Sinba | Optimizador de Flota y Contenedores",
    page_icon="♻️",
    layout="wide"
)

# Estilos CSS personalizados basados en el Brandbook de Sinba
# Paleta de colores principal:
# Morado (#5A1A9B), Lila (#EBE9FC), Verde (#419847), Rojo (#E05841), Naranja (#F2AC2C), Amarillo (#F5DB22)
st.markdown("""

""", unsafe_allow_html=True)

# Encabezado principal de la Marca
st.title("sinba® | Sistema de Análisis de Contenedores")
st.markdown("### *Por un mundo sin basura* ♻️")
st.markdown("Carga tu archivo de recojos para actualizar dinámicamente el análisis de migración a **120L** y la **subutilización de flota**.")

uploaded_file = st.sidebar.file_uploader(
    "Subir dataset (CSV o Excel)", type=["csv", "xlsx"]
)

# Función para interpretación robusta de fechas en español
def convertir_fechas_espanol(series):
    s = series.astype(str).str.lower().str.strip()
    reemplazos = {
        'enero': 'Jan', 'ene': 'Jan',
        'febrero': 'Feb', 'feb': 'Feb',
        'marzo': 'Mar', 'mar': 'Mar',
        'abril': 'Apr', 'abr': 'Apr',
        'mayo': 'May', 'may': 'May',
        'junio': 'Jun', 'jun': 'Jun',
        'julio': 'Jul', 'jul': 'Jul',
        'agosto': 'Aug', 'ago': 'Aug',
        'septiembre': 'Sep', 'setiembre': 'Sep', 'sep': 'Sep', 'set': 'Sep',
        'octubre': 'Oct', 'oct': 'Oct',
        'noviembre': 'Nov', 'nov': 'Nov',
        'diciembre': 'Dec', 'dic': 'Dec'
    }
    for es, en in reemplazos.items():
        s = s.str.replace(es, en, regex=False)
    return pd.to_datetime(s, errors='coerce', dayfirst=True)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()

    # Normalización de la columna fecha
    df["fecha"] = convertir_fechas_espanol(df["fecha"])
    df = df.dropna(subset=["fecha"])

    if df.empty:
        st.warning("El archivo cargado no contiene registros con fechas válidas.")
        st.stop()

    min_date_data = df["fecha"].min().date()
    max_date_data = df["fecha"].max().date()

    st.sidebar.header("🗓️ Filtro de Periodo")
    opcion_periodo = st.sidebar.selectbox(
        "Seleccionar tipo de filtro:",
        ["Rango Personalizado", "Semana", "Mes", "Trimestre", "Semestre", "Anual"],
    )

    df["Anio"] = df["fecha"].dt.year
    df["Mes_Nombre"] = df["fecha"].dt.strftime("%Y-%m (%B)")
    df["Semana"] = df["fecha"].dt.to_period("W").astype(str)
    df["Trimestre"] = df["fecha"].dt.to_period("Q").astype(str)
    df["Semestre"] = df["fecha"].apply(
        lambda x: f"{x.year}-H1" if x.month <= 6 else f"{x.year}-H2"
    )

    if opcion_periodo == "Rango Personalizado":
        rango_fechas = st.sidebar.date_input(
            "Seleccionar Rango (Inicio - Fin):",
            value=[min_date_data, max_date_data],
        )

        if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
            start_date, end_date = rango_fechas
            df_filtered = df[
                (df["fecha"].dt.date >= start_date)
                & (df["fecha"].dt.date <= end_date)
            ]
        elif isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 1:
            st.sidebar.info("👉 Haz clic en la fecha final para completar el rango.")
            df_filtered = df[df["fecha"].dt.date >= rango_fechas[0]]
        else:
            df_filtered = df.copy()

    elif opcion_periodo == "Semana":
        semana_sel = st.sidebar.selectbox(
            "Seleccionar Semana:", sorted(df["Semana"].unique(), reverse=True)
        )
        df_filtered = df[df["Semana"] == semana_sel]

    elif opcion_periodo == "Mes":
        mes_sel = st.sidebar.selectbox(
            "Seleccionar Mes:", sorted(df["Mes_Nombre"].unique(), reverse=True)
        )
        df_filtered = df[df["Mes_Nombre"] == mes_sel]

    elif opcion_periodo == "Trimestre":
        tri_sel = st.sidebar.selectbox(
            "Seleccionar Trimestre:", sorted(df["Trimestre"].unique(), reverse=True)
        )
        df_filtered = df[df["Trimestre"] == tri_sel]

    elif opcion_periodo == "Semestre":
        sem_sel = st.sidebar.selectbox(
            "Seleccionar Semestre:", sorted(df["Semestre"].unique(), reverse=True)
        )
        df_filtered = df[df["Semestre"] == sem_sel]

    elif opcion_periodo == "Anual":
        anio_sel = st.sidebar.selectbox(
            "Seleccionar Año:", sorted(df["Anio"].unique(), reverse=True)
        )
        df_filtered = df[df["Anio"] == anio_sel]

    if df_filtered.empty:
        st.warning("No se encontraron registros de recojo para el periodo seleccionado.")
        st.stop()

    st.info(
        f"📅 **Periodo evaluado:** Mostrando {len(df_filtered)} registros de recojo desde "
        f"**{df_filtered['fecha'].min().strftime('%d/%m/%Y')}** hasta **{df_filtered['fecha'].max().strftime('%d/%m/%Y')}**."
    )

    tab1, tab2 = st.tabs(
        ["📉 Análisis Migración 120L", "⚠️ Análisis Déficit / Subutilización"]
    )

    # TAB 1: MIGRACIÓN 120L
    with tab1:
        st.subheader("Evaluación de Factibilidad para Cambio de 180L a 120L")

        resumen_120L = (
            df_filtered.groupby(["Cliente", "sede"])
            .agg(
                total_dias=("fecha", "count"),
                peso_p90=("peso_neto", lambda x: np.percentile(x, 90)),
                peso_max=("peso_neto", "max"),
                volumen_total=("peso_neto", "sum"),
                contenedores_est=("contenedores_establecidos", "first"),
            )
            .reset_index()
        )

        resumen_120L["capacidad_120L"] = resumen_120L["contenedores_est"] * 80
        resumen_120L["cumple_p90"] = (
            resumen_120L["peso_p90"] <= resumen_120L["capacidad_120L"]
        )
        resumen_120L["cumple_max"] = (
            resumen_120L["peso_max"] <= resumen_120L["capacidad_120L"]
        )

        def dictamen_120l(row):
            if row["cumple_p90"] and row["cumple_max"]:
                return "100% FACTIBLE"
            elif row["cumple_p90"]:
                return "POTENCIAL A REVISAR"
            else:
                return "NO FACTIBLE"

        resumen_120L["Dictamen Final"] = resumen_120L.apply(dictamen_120l, axis=1)

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Sedes 100% Factibles",
            (resumen_120L["Dictamen Final"] == "100% FACTIBLE").sum(),
        )
        c2.metric(
            "Sedes Potenciales",
            (resumen_120L["Dictamen Final"] == "POTENCIAL A REVISAR").sum(),
        )
        c3.metric(
            "Sedes No Factibles",
            (resumen_120L["Dictamen Final"] == "NO FACTIBLE").sum(),
        )

        # Paleta de colores oficial Sinba
        def color_dictamen_sinba(val):
            if val == "100% FACTIBLE":
                return "background-color: #419847; color: #FFFFFF; font-weight: bold;"  # Verde Sinba
            elif val == "NO FACTIBLE":
                return "background-color: #E05841; color: #FFFFFF; font-weight: bold;"  # Rojo Sinba
            else:
                return "background-color: #F2AC2C; color: #FFFFFF; font-weight: bold;"  # Naranja Sinba

        st_df = resumen_120L[[
            "Cliente",
            "sede",
            "total_dias",
            "contenedores_est",
            "capacidad_120L",
            "peso_p90",
            "peso_max",
            "volumen_total",
            "Dictamen Final",
        ]].style

        if hasattr(st_df, "map"):
            st_df = st_df.map(color_dictamen_sinba, subset=["Dictamen Final"])
        else:
            st_df = st_df.applymap(color_dictamen_sinba, subset=["Dictamen Final"])

        st.dataframe(st_df, use_container_width=True)

        factibles_df = resumen_120L[
            resumen_120L["Dictamen Final"] == "100% FACTIBLE"
        ].sort_values(by="volumen_total", ascending=False)

        if not factibles_df.empty:
            st.subheader("Concentración de Volumen en Sedes Factibles (kg)")
            st.bar_chart(
                data=factibles_df,
                x="sede",
                y="volumen_total",
                color="#5A1A9B",  # Morado Sinba
                use_container_width=True,
            )

    # TAB 2: DÉFICIT Y SUBUTILIZACIÓN
    with tab2:
        st.subheader("Detección de Clientes con Subutilización de Contenedores")
        df_filtered["es_deficit"] = (
            df_filtered["contenedores_recogidos"]
            < df_filtered["contenedores_establecidos"]
        )

        resumen_deficit = (
            df_filtered.groupby(["Cliente", "sede"])
            .agg(
                total_recojos=("fecha", "count"),
                dias_con_deficit=("es_deficit", "sum"),
                contenedores_est=("contenedores_establecidos", "first"),
                promedio_recogidos=("contenedores_recogidos", "mean"),
            )
            .reset_index()
        )

        resumen_deficit["% Días Déficit"] = (
            resumen_deficit["dias_con_deficit"] / resumen_deficit["total_recojos"]
        ) * 100

        def clasificar_riesgo(pct):
            if pct >= 75:
                return "Crítico (≥75% déficit)"
            elif pct >= 40:
                return "Alto (40%-74% déficit)"
            elif pct >= 15:
                return "Medio (15%-39% déficit)"
            else:
                return "Bajo / Nulo (<15% déficit)"

        resumen_deficit["Clasificación Riesgo"] = resumen_deficit[
            "% Días Déficit"
        ].apply(clasificar_riesgo)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric(
            "Riesgo Crítico",
            (resumen_deficit["Clasificación Riesgo"] == "Crítico (≥75% déficit)").sum(),
        )
        k2.metric(
            "Riesgo Alto",
            (resumen_deficit["Clasificación Riesgo"] == "Alto (40%-74% déficit)").sum(),
        )
        k3.metric(
            "Riesgo Medio",
            (resumen_deficit["Clasificación Riesgo"] == "Medio (15%-39% déficit)").sum(),
        )
        k4.metric(
            "Riesgo Bajo / Nulo",
            (resumen_deficit["Clasificación Riesgo"] == "Bajo / Nulo (<15% déficit)").sum(),
        )

        st.dataframe(
            resumen_deficit.sort_values(
                by="% Días Déficit", ascending=False
            ).style.format(
                {"% Días Déficit": "{:.1f}%", "promedio_recogidos": "{:.2f}"}
            ),
            use_container_width=True,
        )

else:
    st.info("👋 Por favor, sube un archivo CSV o Excel con los datos para comenzar el análisis.")
