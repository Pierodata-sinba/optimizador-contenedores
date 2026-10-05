El inconveniente en el selector de rango personalizado ocurre principalmente por tres razones comunes en el comportamiento de st.sidebar.date_input:

Restricción de los límites min_value y max_value: Al fijar min_value y max_value a las fechas encontradas en el archivo actual, Streamlit no permite navegar fuera de ese rango exacto en el calendario.

Selección interactiva incompleta: Cuando un usuario hace clic en el calendario de Streamlit para seleccionar un rango, la variable devuelve temporalmente una lista de 1 solo elemento (solo la fecha de inicio) hasta que se hace clic en la fecha final.

Pérdida de la fecha límite cuando hay registros sin hora: Al comparar fechas sin hora con timestamps, pueden quedar fuera los registros del último día seleccionado.

Código Corregido y Optimizado
Sustituye todo el código en tu repositorio de GitHub por esta versión. Ahora el selector de fecha permite explorar libremente cualquier mes o año y ajusta dinámicamente los periodos filtrados:

Python
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Optimizador de Flota y Contenedores", layout="wide"
)

st.title("📦 Sistema de Análisis de Capacidad y Uso de Contenedores")
st.markdown(
    "Carga tu archivo de recojos para actualizar dinámicamente el análisis de"
    " migración a **120L** y la **subutilización de flota**."
)

uploaded_file = st.sidebar.file_uploader(
    "Subir dataset (CSV o Excel)", type=["csv", "xlsx"]
)

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
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])

    if df.empty:
        st.warning(
            "El archivo cargado no contiene registros con fechas válidas."
        )
        st.stop()

    # Determinar rango real de fechas en el archivo
    min_date_data = df["fecha"].min().date()
    max_date_data = df["fecha"].max().date()

    st.sidebar.header("🗓️ Filtro de Periodo")
    opcion_periodo = st.sidebar.selectbox(
        "Seleccionar tipo de filtro:",
        ["Rango Personalizado", "Semana", "Mes", "Trimestre", "Semestre", "Anual"],
    )

    # Columnas auxiliares para agrupaciones
    df["Anio"] = df["fecha"].dt.year
    df["Mes_Nombre"] = df["fecha"].dt.strftime("%Y-%m (%B)")
    df["Semana"] = df["fecha"].dt.to_period("W").astype(str)
    df["Trimestre"] = df["fecha"].dt.to_period("Q").astype(str)
    df["Semestre"] = df["fecha"].apply(
        lambda x: f"{x.year}-H1" if x.month <= 6 else f"{x.year}-H2"
    )

    # Lógica de filtrado de fechas
    if opcion_periodo == "Rango Personalizado":
        rango_fechas = st.sidebar.date_input(
            "Seleccionar Rango (Inicio - Fin):",
            value=[min_date_data, max_date_data],
            # Eliminamos min_value y max_value estrictos para permitir libre navegación en el calendario
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
        st.warning(
            "No se encontraron registros de recojo para el periodo seleccionado."
        )
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
        
        # Agrupación dinámica en función del periodo filtrado
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

        def color_dictamen(val):
            if val == "100% FACTIBLE":
                return "background-color: #d4edda; color: #155724"
            elif val == "NO FACTIBLE":
                return "background-color: #f8d7da; color: #721c24"
            else:
                return "background-color: #fff3cd; color: #856404"

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
            st_df = st_df.map(color_dictamen, subset=["Dictamen Final"])
        else:
            st_df = st_df.applymap(color_dictamen, subset=["Dictamen Final"])

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
