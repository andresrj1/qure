import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MRO Enterprise Architect v5.1", layout="wide")

st.title("✈️ MRO Enterprise Architect v5.1")
st.markdown("""
**Simulador de Ingeniería & Finanzas.**
Versión corregida: Control total sobre cantidades de Gerentes y Project Managers para ajustar la carga administrativa.
""")

# ==========================================
# 1. BARRA LATERAL: INPUTS DE INGENIERÍA
# ==========================================

with st.sidebar:
    st.header("1. Configuración de Flota (Input Detallado)")
    st.info("Define la mezcla exacta de aeronaves en el hangar este mes.")
    
    # Inputs por modelo específico
    c1, c2 = st.columns(2)
    with c1:
        qty_b757 = st.number_input("Cant. Boeing 757 (Heavy)", 0, 10, 2)
        qty_a320 = st.number_input("Cant. Airbus A320 (Narrow)", 0, 15, 4)
    with c2:
        qty_b737 = st.number_input("Cant. Boeing 737 (Narrow)", 0, 15, 3)
        qty_e190 = st.number_input("Cant. Embraer 190 (Regional)", 0, 10, 2)
        
    st.divider()

    st.header("2. Fuerza Técnica y Aviónica")
    
    # Desglose Aviónica
    st.subheader("Departamento de Aviónica")
    av_tecnicos = st.number_input("Técnicos Aviónica", value=30)
    av_encargados = st.number_input("Encargados Aviónica (No Facturan)", value=5)
    av_jefatura = st.number_input("Jefatura Aviónica (No Factura)", value=1)
    
    # Resto de la Planta
    st.subheader("Resto de la Planta")
    otros_tecnicos = st.number_input("Otros Técnicos (Estructuras/Sist/Int)", value=470)
    
    total_tecnicos = av_tecnicos + otros_tecnicos
    
    st.divider()

    st.header("3. Nómina y Estructura Gerencial")
    
    # Estructura Alta Gerencia
    st.subheader("Alta Gerencia")
    salario_gg = st.number_input("Salario Gerente General ($)", value=12000)
    
    # Estructura Media (Dinámica)
    st.subheader("Gerencias de Área y PMs")
    
    col_ga1, col_ga2 = st.columns(2)
    with col_ga1:
        cant_gtes_area = st.number_input("Cant. Gtes Área", value=3, min_value=0, help="Ej: Gerente Producción, Gte Talleres, Gte Calidad")
    with col_ga2:
        salario_gte_area = st.number_input("Salario Gte Área ($)", value=6000)
        
    col_pm1, col_pm2 = st.columns(2)
    with col_pm1:
        cant_pms = st.number_input("Cant. Project Managers", value=8, min_value=0, help="Un PM por cada línea de avión o proyecto grande")
    with col_pm2:
        salario_pm = st.number_input("Salario Project Mgr ($)", value=4500)

    # Costos Técnicos
    st.subheader("Costos Operativos")
    salario_tecnico_base = st.number_input("Costo Hora Técnico Base ($)", value=14.0)
    
    # Política de Horas Extras
    he_15 = st.slider("Extras 1.5x (Hrs/sem/tec)", 0, 15, 5)
    he_20 = st.slider("Domingos 2.0x (Días/mes/tec)", 0, 4, 1)

    st.divider()
    
    st.header("4. Finanzas Globales")
    tarifa_venta = st.number_input("Tarifa Venta Promedio ($/hr)", value=65.0)
    gastos_fijos = st.number_input("Gastos Fijos Planta ($)", value=250000)

# ==========================================
# 2. MOTOR DE CÁLCULO (BACKEND)
# ==========================================

# --- A. MODELO DE CARGA DE TRABAJO (WORKLOAD) ---
PERFIL_AVION = {
    "B757": {"hrs": 7500, "pct_avionica": 0.18}, 
    "A320": {"hrs": 5500, "pct_avionica": 0.22},
    "B737": {"hrs": 5800, "pct_avionica": 0.20},
    "E190": {"hrs": 3500, "pct_avionica": 0.25}
}

# Calcular demanda
demanda_total_horas = (
    (qty_b757 * PERFIL_AVION["B757"]["hrs"]) +
    (qty_a320 * PERFIL_AVION["A320"]["hrs"]) +
    (qty_b737 * PERFIL_AVION["B737"]["hrs"]) +
    (qty_e190 * PERFIL_AVION["E190"]["hrs"])
)

demanda_avionica_horas = (
    (qty_b757 * PERFIL_AVION["B757"]["hrs"] * PERFIL_AVION["B757"]["pct_avionica"]) +
    (qty_a320 * PERFIL_AVION["A320"]["hrs"] * PERFIL_AVION["A320"]["pct_avionica"]) +
    (qty_b737 * PERFIL_AVION["B737"]["hrs"] * PERFIL_AVION["B737"]["pct_avionica"]) +
    (qty_e190 * PERFIL_AVION["E190"]["hrs"] * PERFIL_AVION["E190"]["pct_avionica"])
)

# --- B. CÁLCULO DE CAPACIDAD Y NÓMINA ---

def calcular_nomina_compleja(n_tecnicos, rate_base, h_extra, d_domingo):
    cap_ord = n_tecnicos * 192
    costo_ord = cap_ord * rate_base
    cap_15 = n_tecnicos * (h_extra * 4)
    costo_15 = cap_15 * (rate_base * 1.5)
    cap_20 = n_tecnicos * (d_domingo * 8)
    costo_20 = cap_20 * (rate_base * 2.0)
    return cap_ord + cap_15 + cap_20, costo_ord + costo_15 + costo_20

capacidad_total, costo_nomina_total = calcular_nomina_compleja(total_tecnicos, salario_tecnico_base, he_15, he_20)
capacidad_avionica, costo_nomina_avionica_directa = calcular_nomina_compleja(av_tecnicos, salario_tecnico_base, he_15, he_20)

# --- C. COSTOS GERENCIALES Y ADMINISTRATIVOS (DINÁMICO) ---
# Aquí aplicamos las variables que pediste modificar
costo_gtes_area_total = cant_gtes_area * salario_gte_area
costo_pms_total = cant_pms * salario_pm
costo_admin_mensual = salario_gg + costo_gtes_area_total + costo_pms_total

costo_indirecto_avionica = (av_encargados * 2500) + (av_jefatura * 3500) 

# --- D. PRODUCCIÓN REAL ---
horas_vendidas_total = min(demanda_total_horas, capacidad_total)
horas_vendidas_avionica = min(demanda_avionica_horas, capacidad_avionica)

ingreso_total = horas_vendidas_total * tarifa_venta
ingreso_avionica = horas_vendidas_avionica * tarifa_venta 

gasto_total_operativo = costo_nomina_total + costo_admin_mensual + gastos_fijos
utilidad_neta = ingreso_total - gasto_total_operativo

# --- E. PREDICCIÓN DE MERCADO ---
def motor_prediccion_mercado():
    meses_futuros = ["Mes +1", "Mes +2", "Mes +3", "Mes +4", "Mes +5", "Mes +6"]
    tendencias = {"Escasez de Piezas": 0.90, "Flota Envejecida": 1.15, "Modernización Cabinas": 1.05}
    data_pred = []
    base_demanda = demanda_total_horas
    
    for i, m in enumerate(meses_futuros):
        if i in [2, 3]: factor_est = 1.10 
        elif i in [5]: factor_est = 0.85 
        else: factor_est = 1.0
        
        factor_mercado = tendencias["Flota Envejecida"] * tendencias["Escasez de Piezas"]
        demanda_proyectada = base_demanda * factor_est * factor_mercado
        estado = "Saturado" if demanda_proyectada > capacidad_total else "Con Capacidad"
        
        data_pred.append({
            "Mes Futuro": m,
            "Demanda Proyectada": demanda_proyectada,
            "Capacidad Actual": capacidad_total,
            "Estado": estado,
            "Tendencia": "Alta Demanda" if factor_mercado > 1 else "Baja"
        })
    return pd.DataFrame(data_pred)

df_forecast = motor_prediccion_mercado()

# ==========================================
# 3. DASHBOARD VISUAL
# ==========================================

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ingresos Totales (Mes)", f"${ingreso_total/1000:,.1f}k")
c2.metric("Utilidad Neta", f"${utilidad_neta/1000:,.1f}k", delta_color="normal" if utilidad_neta > 0 else "inverse")
c3.metric("Ocupación Hangar", f"{(horas_vendidas_total/capacidad_total)*100:.1f}%")
c4.metric("Personal Admin/Gcia", f"{1 + cant_gtes_area + cant_pms} px", help="GG + Gtes Área + PMs")

st.markdown("---")

tab_avionica, tab_flota, tab_prediccion = st.tabs(["⚡ Análisis Depto. Aviónica", "✈️ Configuración Flota & Costos", "🔮 Predicción Mercado 6 Meses"])

with tab_avionica:
    st.subheader("Deep Dive: Departamento de Aviónica")
    col_av1, col_av2 = st.columns([1, 2])
    
    with col_av1:
        st.markdown(f"**Fuerza Laboral:** {av_tecnicos} Técnicos | {av_encargados} Encargados + {av_jefatura} Jefe")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = (horas_vendidas_avionica / capacidad_avionica) * 100,
            title = {'text': "Saturación Aviónica"},
            gauge = {'axis': {'range': [0, 120]}, 'bar': {'color': "darkblue"},
                     'steps': [{'range': [0, 80], 'color': "lightgreen"}, {'range': [80, 100], 'color': "yellow"}, {'range': [100, 120], 'color': "red"}]}
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col_av2:
        ingreso_av = horas_vendidas_avionica * tarifa_venta
        gasto_av = costo_nomina_avionica_directa + costo_indirecto_avionica
        margen_av = ingreso_av - gasto_av
        st.markdown("### P&L Aviónica")
        st.dataframe(pd.DataFrame({
            "Concepto": ["Ingresos (Aviónica)", "Costo Nómina Directa", "Costo Mando Indirecto", "Contribución Neta"],
            "Monto USD": [ingreso_av, -costo_nomina_avionica_directa, -costo_indirecto_avionica, margen_av]
        }).style.format({"Monto USD": "${:,.2f}"}))

with tab_flota:
    st.subheader("Estructura de Costos Gerencial vs Operativa")
    
    # Treemap Dinámico actualizado con las variables
    labels = ["Total Empresa", "Gerencia General", "Gerencias Área", "Project Managers", "Producción (Técnicos)", "Gastos Fijos"]
    parents = ["", "Total Empresa", "Total Empresa", "Total Empresa", "Total Empresa", "Total Empresa"]
    values = [0, salario_gg, costo_gtes_area_total, costo_pms_total, costo_nomina_total, gastos_fijos]
    
    fig_tree = go.Figure(go.Treemap(
        labels = labels, parents = parents, values = values, textinfo = "label+value+percent parent"
    ))
    st.plotly_chart(fig_tree, use_container_width=True)
    
    col_det1, col_det2 = st.columns(2)
    with col_det1:
        st.info(f"""
        **Detalle Gerencial:**
        * 1 Gerente General: ${salario_gg:,.0f}
        * {cant_gtes_area} Gerentes de Área: ${costo_gtes_area_total:,.0f}
        * {cant_pms} Project Managers: ${costo_pms_total:,.0f}
        """)
    with col_det2:
        st.warning(f"**Costo Nómina Técnica Total:** ${costo_nomina_total:,.0f}")

with tab_prediccion:
    st.subheader("🔮 Forecast de Mercado")
    fig_line = px.line(df_forecast, x="Mes Futuro", y=["Demanda Proyectada", "Capacidad Actual"], 
                       markers=True, title="Forecast de Demanda a 6 Meses")
    st.plotly_chart(fig_line, use_container_width=True)
    st.dataframe(df_forecast.style.applymap(lambda v: 'color: red;' if v == 'Saturado' else 'color: green;', subset=['Estado']))