import streamlit as st
import pandas as pd
import math

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Ingeniería Eléctrica Condominio - Master V3", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS CSS PARA INGENIERÍA ---
st.markdown("""
<style>
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b;}
    .success-card {background-color: #d4edda; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745;}
    .warning-card {background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107;}
    h1, h2, h3 {color: #0e1117;}
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE CÁLCULO NORMATIVO (NEC/CSCR) ---

def seleccionar_breaker_comercial(amperios_requeridos, tipo="main"):
    """
    Selecciona el breaker comercial inmediatamente superior.
    Para cargas continuas, se asume que el input ya viene mayorado al 125% o se aplica aquí.
    """
    # Lista estándar de breakers comerciales (Amps)
    comerciales = [15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 125, 150, 175, 200, 225, 250, 300, 400]
    
    # Regla de seguridad: El breaker no debe operar a más del 80% de su capacidad en carga continua
    # O bien, la capacidad debe ser 125% de la carga continua.
    capacidad_target = amperios_requeridos * 1.25 
    
    for b in comerciales:
        if b >= capacidad_target:
            return b
    return ">400A (Req. Estudio Especial)"

def calc_demanda_iluminacion(watts_totales):
    """
    NEC 220.42: Primeros 3000VA al 100%, resto al 35% (para vivienda).
    """
    if watts_totales <= 3000:
        return watts_totales
    else:
        return 3000 + ((watts_totales - 3000) * 0.35)

def calc_motor_bomba(hp, voltaje, es_motor_mayor=False):
    """
    Estima watts y aplica factor NEC 430.24 (125% al motor mayor).
    1 HP approx 746W (mecánico) -> ~1000W-1200W eléctrico (eficiencia/fp).
    Usamos tablas NEC 430.248 aprox para monofásico 230V: 1.5HP = 10A.
    """
    # Estimación conservadora basada en amperaje de tabla NEC
    if voltaje == 208:
        amps_tabla = {1: 8.8, 1.5: 11.0, 2: 13.2, 3: 18.7}
    else: # 230V/240V
        amps_tabla = {1: 8.0, 1.5: 10.0, 2: 12.0, 3: 17.0}
    
    amps = amps_tabla.get(hp, hp * 7) # fallback
    watts_reales = amps * voltaje
    
    factor = 1.25 if es_motor_mayor else 1.0
    return watts_reales, watts_reales * factor

# --- INTERFAZ DE USUARIO ---

st.title("⚡ Diseño Maestro de Cargas: Condominio Nunciatura")
st.markdown("**Normativa Aplicable:** CSCR 2014 / NEC 2014 (NFPA 70) | **Validación Hardware:** Schneider Electric EZM")

# ---------------- SIDEBAR: DATOS DE ENTRADA ----------------
with st.sidebar:
    st.header("1. Parámetros Generales")
    voltaje = st.selectbox("Voltaje de Servicio", [240, 208], index=0, help="240V es estándar residencial CR (L-L). 208V es común si hay transformadores trifásicos cerca.")
    
    st.divider()
    
    st.header("2. Apartamentos Tipo (1-8, 10-13)")
    cant_apt_std = st.number_input("Cantidad Apts. Estándar", value=12, help="Legalmente 11, Físicamente 13 (menos el PH)")
    
    with st.expander("Detalle Cargas Apto Estándar"):
        st.caption("Ajusta los valores según placa de equipos")
        std_outlets = st.number_input("Tomas Generales (Cant)", 15, key="std_out")
        std_cocina = st.number_input("Cocina (Watts)", 8000, step=500, key="std_coc")
        std_lavado = st.number_input("Centro Lavado (Watts)", 4500, step=500, key="std_lav")
        std_refri = st.number_input("Refrigeradora (Watts)", 600, step=100, key="std_ref")
        std_heater = st.number_input("Calentador Agua (Watts)", 4500, step=500, key="std_heat")
        std_micro = st.number_input("Microondas/Otros (Watts)", 1200, step=100, key="std_mic")

    st.header("3. Penthouse (Apto 9)")
    with st.expander("Detalle Cargas Penthouse"):
        ph_factor = st.slider("Factor Multiplicador Espacio", 1.5, 3.0, 2.0)
        ph_jacuzzi = st.number_input("Jacuzzi/Tina (Watts)", 3500, step=500)
        ph_ac = st.number_input("Aire Acondicionado Total (Watts)", 3000, step=500)
    
    st.divider()
    
    st.header("4. Áreas Comunes (Panel Independiente)")
    st.info("Estas cargas irán en un medidor separado.")
    with st.expander("Configurar Motores y Luces"):
        ac_luces_pasillo = st.number_input("Tomas/Luces Pasillos (Total W)", 2000)
        ac_luces_parqueo = st.number_input("Luces Parqueo (Total W)", 1000)
        ac_portones = st.number_input("Cantidad Portones Eléctricos", 5)
        ac_bombas_qty = st.number_input("Cantidad Bombas Agua", 2)
        ac_bombas_hp = st.number_input("HP por Bomba", 1.5)
        ac_ascensor = st.number_input("Ascensor (Watts)", 7500, help="Verificar si es trifásico. Aquí asumimos monofásico para carga.")
        ac_malla = st.number_input("Malla Eléctrica (Watts)", 100, help="Consumo bajo, requiere circuito dedicado")

    st.header("5. Hardware Comprado (Cotización)")
    hw_slots = st.number_input("Espacios Medidor (EZM)", value=12)
    hw_breaker_amp = st.selectbox("Amperaje Breakers Comprados", [70, 100, 125], index=1)

# ---------------- LÓGICA DE CÁLCULO ----------------

# A. CÁLCULO APARTAMENTO ESTÁNDAR
# Carga Instalada
w_std_ilum = std_outlets * 180 # 180VA por salida según NEC
w_std_total_instalada = w_std_ilum + std_cocina + std_lavado + std_refri + std_heater + std_micro

# Carga Demandada (Simplificada Método Estándar)
# 1. Iluminación
dem_std_ilum = calc_demanda_iluminacion(w_std_ilum)
# 2. Cocina (NEC permite factores, usaremos 80% conservador para 1 unidad unitaria o 100% seguridad)
dem_std_cocina = std_cocina * 0.8 
# 3. Resto al 100% para cálculo de acometida individual
dem_std_total = dem_std_ilum + dem_std_cocina + std_lavado + std_refri + std_heater + std_micro
amp_std_demanda = dem_std_total / voltaje
breaker_std_recomendado = seleccionar_breaker_comercial(amp_std_demanda)

# B. CÁLCULO PENTHOUSE
w_ph_ilum = (std_outlets * ph_factor) * 180
w_ph_total_instalada = w_ph_ilum + std_cocina + std_lavado + std_refri + std_heater + ph_jacuzzi + ph_ac
# Demanda
dem_ph_ilum = calc_demanda_iluminacion(w_ph_ilum)
dem_ph_total = dem_ph_ilum + (std_cocina * 0.8) + std_lavado + std_refri + std_heater + ph_jacuzzi + ph_ac
amp_ph_demanda = dem_ph_total / voltaje
breaker_ph_recomendado = seleccionar_breaker_comercial(amp_ph_demanda)

# C. CÁLCULO ÁREAS COMUNES (PANEL SEPARADO)
# Motores
w_bomba_real, w_bomba_demanda = calc_motor_bomba(ac_bombas_hp, voltaje, es_motor_mayor=True)
# Si hay 2 bombas, se asume alternancia o simultaneidad. Diseñamos para simultaneidad (peor caso)
# Bomba 1 (125%) + Bomba 2 (100%)
demanda_bombas = w_bomba_demanda + (w_bomba_real * (ac_bombas_qty - 1))

# Portones (Motores pequeños, ~300W c/u)
demanda_portones = ac_portones * 300 

# Total Común
demanda_comun_total = demanda_bombas + demanda_portones + ac_luces_pasillo + ac_luces_parqueo + ac_ascensor + ac_malla
amp_comun_demanda = demanda_comun_total / voltaje
breaker_comun_recomendado = seleccionar_breaker_comercial(amp_comun_demanda)


# ---------------- VISUALIZACIÓN DE RESULTADOS ----------------

# TABS PARA ORGANIZAR LA INFORMACIÓN
tab1, tab2, tab3 = st.tabs(["📊 Análisis Panel Principal", "🏗️ Áreas Comunes (Detalle)", "📜 Normativa & Hardware"])

with tab1:
    st.subheader("Balance de Cargas y Breakers (Apartamentos)")
    
    col1, col2, col3 = st.columns(3)
    
    # DATOS APARTAMENTO ESTÁNDAR
    with col1:
        st.markdown("### Apto. Estándar")
        st.metric("Carga Instalada", f"{w_std_total_instalada/1000:.1f} kVA")
        st.metric("Demanda Estimada", f"{amp_std_demanda:.1f} A")
        
        if breaker_std_recomendado > hw_breaker_amp:
            st.error(f"Breaker Req: {breaker_std_recomendado}A")
            st.caption(f"⚠️ El breaker comprado de {hw_breaker_amp}A es insuficiente.")
        else:
            st.success(f"Breaker Req: {breaker_std_recomendado}A")
            st.caption(f"✅ El de {hw_breaker_amp}A funciona.")

    # DATOS PENTHOUSE
    with col2:
        st.markdown("### Penthouse (Apt 9)")
        st.metric("Carga Instalada", f"{w_ph_total_instalada/1000:.1f} kVA")
        st.metric("Demanda Estimada", f"{amp_ph_demanda:.1f} A")
        
        if breaker_ph_recomendado > hw_breaker_amp:
            st.warning(f"Breaker Req: {breaker_ph_recomendado}A")
            st.write(f"⚠️ **ATENCIÓN:** El PH necesita un breaker de **{breaker_ph_recomendado}A**. El de {hw_breaker_amp}A de la cotización se disparará si usan Jacuzzi + Cocina + AC.")
        else:
            st.success(f"Breaker Req: {breaker_ph_recomendado}A")

    # RESUMEN TOTAL
    with col3:
        total_medidores_reales = cant_apt_std + 1 + 1 # Std + PH + Comunes
        deficit = total_medidores_reales - hw_slots
        
        st.markdown("### Estado del Proyecto")
        st.metric("Total Apartamentos Reales", cant_apt_std + 1)
        st.metric("Medidor Áreas Comunes", 1)
        
        if deficit > 0:
            st.markdown(f"""
            <div class="metric-card">
            <h4 style="margin:0">⚠️ DÉFICIT DE ESPACIOS</h4>
            <p>Necesitas: <b>{total_medidores_reales}</b> espacios</p>
            <p>Tienes: <b>{hw_slots}</b> espacios (Cotización)</p>
            <p><b>Faltan: {deficit} medidores</b></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success("Hardware suficiente en espacios.")

with tab2:
    st.subheader("Diseño del Panel de Áreas Comunes (Independiente)")
    st.markdown("Este panel debe ir conectado a un medidor independiente, fuera del banco principal si no hay espacio.")
    
    c_comun1, c_comun2 = st.columns([1, 2])
    
    with c_comun1:
        st.info(f"**Carga Total Demandada:** {demanda_comun_total/1000:.2f} kVA")
        st.error(f"**Breaker Principal Requerido:** {breaker_comun_recomendado} A ({voltaje}V)")
        st.caption("Este breaker protege la acometida del medidor de áreas comunes.")

    with c_comun2:
        st.markdown("#### 🛠️ Distribución de Circuitos Recomendada (Sub-panel)")
        st.markdown("Se recomienda instalar un **Centro de Carga de 8 a 12 espacios** para áreas comunes con los siguientes breakers:")
        
        data_circuitos = {
            "Circuito": ["Ascensor", "Bombas de Agua (Dúplex)", "Portones Eléctricos", "Luces Pasillos/Parqueo", "Malla Seguridad", "Tomacorrientes Servicio"],
            "Carga (Watts)": [ac_ascensor, w_bomba_real*ac_bombas_qty, demanda_portones, ac_luces_pasillo+ac_luces_parqueo, ac_malla, 1500],
            "Polos": [2, 2, 1, 1, 1, 1],
            "Breaker Sugerido": [
                f"{seleccionar_breaker_comercial(ac_ascensor/voltaje)}A (Verificar motor)", 
                f"{seleccionar_breaker_comercial((w_bomba_real*ac_bombas_qty)/voltaje)}A", 
                "20A", 
                "20A", 
                "15A", 
                "20A"
            ]
        }
        st.dataframe(pd.DataFrame(data_circuitos), hide_index=True)
        st.warning("**Nota Ascensor:** Si el ascensor es trifásico, requerirá un banco de medidores trifásico totalmente distinto. Si es monofásico (220V), usar recomendación anterior.")

with tab3:
    st.subheader("Referencias Normativas y Hardware")
    
    st.markdown(f"""
    ### 1. Análisis de Cotización ENERSYS (Oferta 415067)
    * **Equipo:** Schneider EZM (Modular).
    * **Capacidad Main:** 1200A (Suficiente para todo el edificio).
    * **Interruptores Derivados:** QDP 2 polos 100A.
    
    ### 2. Normativa CSCR / NEC
    * **Art 220.84 (Multifamiliares):** Se permite aplicar factores de demanda a la acometida principal por tener más de 3 unidades.
    * **Art 210.11 (Circuitos Ramales):** Se requieren circuitos dedicados de 20A para lavandería y cocina.
    * **Motores:** Los breakers de motores (bombas) deben soportar el arranque. No usar breakers estándar si las bombas son grandes; usar protección térmica adecuada en el panel de control de bombas.
    
    ### 3. Recomendación Final de Ingeniería
    1.  **Instalación Física:** Instalar los 2 módulos EZM (12 medidores) para los Apts 1-12.
    2.  **Apartamento 13:** Instalar una base de medidor individual (Tipo 100A redonda) adyacente al banco principal.
    3.  **Áreas Comunes:** Instalar base de medidor individual (Tipo 100A o 200A según cálculo en Tab 2) adyacente.
    4.  **Penthouse:** Si la carga calculada en la Tab 1 supera los 80A, **sustituir** el breaker QDP de 100A por uno de **125A** (Modelo QDP22125TM) en el módulo EZM.
    """)