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
  if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
  else:
    df = pd.read_excel(uploaded_file)

  df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
  df = df.dropna(subset=["fecha"])

  st.sidebar.header("🗓️ Filtro de Periodo")
  opcion_periodo = st.sidebar.selectbox(
      "Seleccionar tipo de filtro:",
      ["Semana", "Mes", "Trimestre", "Semestre", "Anual", "Rango de Fechas"],
  )

  min_date = df["fecha"].min().date()
  max_date = df["fecha"].max().date()

  df["Anio"] = df["fecha"].dt.year
  df["Mes_Nombre"] = df["fecha"].dt.strftime("%B %Y")
  df["Semana"] = df["fecha"].dt.to_period("W").astype(str)
  df["Trimestre"] = df["fecha"].dt.to_period("Q").astype(str)
  df["Semestre"] = df["fecha"].apply(
      lambda x: f"{x.year}-H1" if x.month <= 6 else f"{x.year}-H2"
  )

  if opcion_periodo == "Semana":
    semana_sel = st.sidebar.selectbox(
        "Seleccionar Semana:", sorted(df["Semana"].unique())
    )
    df_filtered = df[df["Semana"] == semana_sel]
  elif opcion_periodo == "Mes":
    mes_sel = st.sidebar.selectbox(
        "Seleccionar Mes:", sorted(df["Mes_Nombre"].unique())
    )
    df_filtered = df[df["Mes_Nombre"] == mes_sel]
  elif opcion_periodo == "Trimestre":
    tri_sel = st.sidebar.selectbox(
        "Seleccionar Trimestre:", sorted(df["Trimestre"].unique())
    )
    df_filtered = df[df["Trimestre"] == tri_sel]
  elif opcion_periodo == "Semestre":
    sem_sel = st.sidebar.selectbox(
        "Seleccionar Semestre:", sorted(df["Semestre"].unique())
    )
    df_filtered = df[df["Semestre"] == sem_sel]
  elif opcion_periodo == "Anual":
    anio_sel = st.sidebar.selectbox(
        "Seleccionar Año:", sorted(df["Anio"].unique())
    )
    df_filtered = df[df["Anio"] == anio_sel]
  else:
    rango_fechas = st.sidebar.date_input(
        "Rango personalizado:",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date,
    )
    if len(rango_fechas) == 2:
      start_date, end_date = rango_fechas
      df_filtered = df[
          (df["fecha"].dt.date >= start_date)
          & (df["fecha"].dt.date <= end_date)
      ]
    else:
      df_filtered = df.copy()

  st.info(
      f"📅 **Periodo evaluado:** Mostrando {len(df_filtered)} registros de"
      " recojo."
  )

  tab1, tab2 = st.tabs(
      ["📉 Análisis Migración 120L", "⚠️ Análisis Déficit / Subutilización"]
  )

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

    st.dataframe(
        resumen_120L[[
            "Cliente",
            "sede",
            "total_dias",
            "contenedores_est",
            "capacidad_120L",
            "peso_p90",
            "peso_max",
            "volumen_total",
            "Dictamen Final",
        ]].style.applymap(
            lambda v: (
                "background-color: #d4edda; color: #155724"
                if v == "100% FACTIBLE"
                else (
                    "background-color: #f8d7da; color: #721c24"
                    if v == "NO FACTIBLE"
                    else "background-color: #fff3cd; color: #856404"
                )
            ),
            subset=["Dictamen Final"],
        ),
        use_container_width=True,
    )

    factibles_df = resumen_120L[
        resumen_120L["Dictamen Final"] == "100% FACTIBLE"
    ].sort_values(by="volumen_total", ascending=False)
    if not factibles_df.empty:
      st.subheader("Concentración de Volumen en Sedes Factibles (kg)")
      st.bar_chart(
          data=factibles_df, x="sede", y="volumen_total", use_container_width=True
      )

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
        (
            resumen_deficit["Clasificación Riesgo"] == "Crítico (≥75% déficit)"
        ).sum(),
    )
    k2.metric(
        "Riesgo Alto",
        (
            resumen_deficit["Clasificación Riesgo"] == "Alto (40%-74% déficit)"
        ).sum(),
    )
    k3.metric(
        "Riesgo Medio",
        (
            resumen_deficit["Clasificación Riesgo"] == "Medio (15%-39% déficit)"
        ).sum(),
    )
    k4.metric(
        "Riesgo Bajo / Nulo",
        (
            resumen_deficit["Clasificación Riesgo"]
            == "Bajo / Nulo (<15% déficit)"
        ).sum(),
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
  st.info(
      "👋 Por favor, sube un archivo CSV o Excel con los datos para comenzar el"
      " análisis."
  )
    st.info("👋 Por favor, sube un archivo CSV o Excel con los datos para comenzar el análisis.")
