import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Calculadora de Cargas Condominio - CNFL", layout="wide")

# --- TEXTOS Y NORMATIVAS (CONTEXTO COSTA RICA) ---
CNFL_INFO = """
### 🇨🇷 Normativa y Referencias CNFL / CSCR 2014
Para Costa Rica, el diseño debe regirse por el **Código Eléctrico de Costa Rica (CSCR 2014)**, el cual adopta gran parte del NEC (National Electrical Code) de EE.UU.

**Puntos Clave para el Diseño del Panel de Medidores:**
1.  **Acometida:** La CNFL exige que para más de 3 medidores, se utilice un ducto de barras o una caja concentradora de medidores modular certificada.
2.  **Protección Principal:** Debe haber un interruptor principal (Main) que desconecte todo el sistema si la carga total excede cierto amperaje (usualmente si es > 100A o 200A, depende del estudio de ingeniería).
3.  **Factor de Demanda:** No todos los apartamentos usan toda la electricidad al mismo tiempo. El código permite aplicar factores de reducción (ej. primeros 3000VA al 100%, resto al 35% para iluminación).
4.  **Bombas y Elevadores:** Los motores deben calcularse al 125% de su carga nominal para el breaker.
"""

# --- FUNCIONES DE CÁLCULO ---

def calcular_apartamento_estandar(voltaje, outlets_qty, watts_cocina, watts_lavado, watts_refri, watts_calentador):
    # Carga instalada bruta (sin factores de demanda para seguridad del breaker individual)
    # Asumimos 180VA por salida general (outlet) según código estándar
    carga_ilum_tomas = outlets_qty * 180 
    carga_total_watts = carga_ilum_tomas + watts_cocina + watts_lavado + watts_refri + watts_calentador
    amperaje = carga_total_watts / voltaje # Estimado monofásico/bifásico
    return carga_total_watts, amperaje

def calcular_areas_comunes(datos_comunes):
    total_watts = 0
    detalles = []
    
    # Pasillos
    total_watts += datos_comunes['tomas_pasillo'] * 180
    detalles.append(f"Tomas Pasillo: {datos_comunes['tomas_pasillo'] * 180} W")
    
    # Ascensor (Motor) - Asumimos un factor de seguridad
    total_watts += datos_comunes['ascensor_watts']
    detalles.append(f"Ascensor: {datos_comunes['ascensor_watts']} W")
    
    # Bombas (Se debe tomar la mayor al 125% si operan simultáneas, aquí sumamos lineal para carga conectada)
    total_watts += datos_comunes['bombas_watts']
    detalles.append(f"Bombas de Agua: {datos_comunes['bombas_watts']} W")
    
    # Luces Parqueo
    total_watts += datos_comunes['luces_parqueo'] * datos_comunes['watts_por_luz']
    detalles.append(f"Iluminación Parqueo: {datos_comunes['luces_parqueo'] * datos_comunes['watts_por_luz']} W")
    
    # Portones y Seguridad
    total_watts += (datos_comunes['portones'] * 300) + 150 # 300W estimado por motor, 150W malla
    detalles.append(f"Portones y Malla: {(datos_comunes['portones'] * 300) + 150} W")
    
    return total_watts, detalles

# --- INTERFAZ DE USUARIO ---

st.title("⚡ Calculadora de Cargas Eléctricas - Condominio")
st.markdown("Herramienta preliminar para dimensionamiento de acometida y balanceo de cargas.")

with st.expander("Ver Normativa CNFL / CSCR"):
    st.markdown(CNFL_INFO)

# --- SIDEBAR: CONFIGURACIÓN DE UNIDADES ---
st.sidebar.header("1. Configuración de Apartamentos")

# Voltaje del sistema
voltage_sys = st.sidebar.selectbox("Voltaje del Sistema", [240, 208], index=0, help="En CR residencial bifásico suele ser 120/240V")

st.sidebar.subheader("Apartamento Estándar (x12)")
watts_cocina = st.sidebar.number_input("Potencia Cocina (Watts)", value=8000, step=500, help="220V")
watts_lavado = st.sidebar.number_input("Centro Lavado (Watts)", value=4500, step=500, help="220V")
watts_refri = st.sidebar.number_input("Refrigeradora (Watts)", value=600, step=100, help="115V")
watts_calentador = st.sidebar.number_input("Calentador Agua (Watts)", value=4500, step=500, help="Termoducha o Tanque pequeño")
qty_outlets = st.sidebar.number_input("Cantidad Tomas (115V)", value=15)

st.sidebar.subheader("Penthouse (Apt 9)")
factor_ph = st.sidebar.slider("Factor de tamaño Penthouse", 1.5, 3.0, 2.0, help="Multiplicador de carga general respecto al estándar")
watts_jacuzzi = st.sidebar.number_input("Jacuzzi Azotea (Watts)", value=3000, step=500)

# --- SIDEBAR: ÁREAS COMUNES ---
st.sidebar.header("2. Áreas Comunes")
n_pasillos = 4 # Asumido por 13 aptos
tomas_pasillo = st.sidebar.number_input("Tomas totales pasillos", value=n_pasillos*2)
watts_ascensor = st.sidebar.number_input("Potencia Ascensor (Watts)", value=7500)
n_bombas = st.sidebar.number_input("Cantidad Bombas Agua", value=2)
hp_bomba = st.sidebar.number_input("HP por Bomba", value=1.5)
watts_bombas = n_bombas * hp_bomba * 746 # 746 W por HP
n_portones = st.sidebar.number_input("Portones Eléctricos", value=5)

# --- CÁLCULOS ---

# 1. Carga Apartamento Estándar
load_std, amps_std = calcular_apartamento_estandar(voltage_sys, qty_outlets, watts_cocina, watts_lavado, watts_refri, watts_calentador)

# 2. Carga Penthouse
# Asumimos que el PH tiene el doble de tomas y luces, y los mismos electrodomésticos base + Jacuzzi
load_ph = (qty_outlets * 180 * factor_ph) + watts_cocina + watts_lavado + watts_refri + watts_calentador + watts_jacuzzi
amps_ph = load_ph / voltage_sys

# 3. Áreas Comunes
datos_comunes = {
    'tomas_pasillo': tomas_pasillo,
    'ascensor_watts': watts_ascensor,
    'bombas_watts': watts_bombas,
    'luces_parqueo': 13,
    'watts_por_luz': 50, # LED
    'portones': n_portones
}
load_common, detalles_common = calcular_areas_comunes(datos_comunes)

# --- RESULTADOS EN PANTALLA PRINCIPAL ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Desglose de Cargas")
    
    # Crear DataFrame para visualización
    data = {
        "Unidad": ["Apto Estándar (x12)", "Penthouse", "Áreas Comunes"],
        "Carga Individual (Watts)": [load_std, load_ph, load_common],
        "Amperios (aprox p/fase)": [amps_std, amps_ph, load_common/voltage_sys],
        "Cantidad": [12, 1, 1]
    }
    df = pd.DataFrame(data)
    df["Subtotal Watts"] = df["Carga Individual (Watts)"] * df["Cantidad"]
    
    st.dataframe(df.style.format({"Carga Individual (Watts)": "{:.0f}", "Amperios (aprox p/fase)": "{:.1f}", "Subtotal Watts": "{:.0f}"}))
    
    total_instalado = df["Subtotal Watts"].sum()
    st.metric(label="⚡ Carga Total Instalada (Sin factores de demanda)", value=f"{total_instalado/1000:,.2f} kVA")

with col2:
    st.subheader("📉 Carga Estimada con Factores de Demanda")
    st.info("El CSCR permite no sumar el 100% de todo. Aplicando una estimación típica para multifamiliares:")
    
    # Cálculo simplificado de demanda (Simulación)
    # 100% de las cargas mayores (Ascensor, Bombas, Jacuzzi)
    # 35% de la iluminación general y tomas (excedente de 3000VA)
    # Factor de coincidencia para cocinas (aprox 40-50% para 13 unidades)
    
    carga_motores = watts_ascensor + watts_bombas + (n_portones*300)
    carga_cocinas_total = watts_cocina * 13
    demanda_cocinas = carga_cocinas_total * 0.40 # NEC Tabla 220.55 col C aprox
    
    carga_resto = total_instalado - carga_motores - carga_cocinas_total
    demanda_resto = 3000 + (carga_resto - 3000) * 0.35
    
    total_demanda = carga_motores + demanda_cocinas + demanda_resto
    amps_demanda = total_demanda / voltage_sys
    
    st.metric(label="Demanda Real Estimada (kVA)", value=f"{total_demanda/1000:,.2f} kVA")
    st.metric(label="Amperaje Acometida Principal (Estimado)", value=f"{amps_demanda:,.1f} A")
    
    if amps_demanda > 400:
        st.warning("⚠️ La demanda supera los 400A. Probablemente requieras Transformador propio o TC (Transformadores de Corriente) en la medición.")

# --- RECOMENDACIONES ---
st.markdown("---")
st.subheader("🛠️ Recomendaciones de Mejora y Seguridad")

rec_col1, rec_col2 = st.columns(2)

with rec_col1:
    st.markdown("**1. Actualización de Bombas de Agua**")
    if n_bombas < 2:
        st.error("❌ Tienes 1 sola bomba. Riesgo alto.")
    else:
        st.success(f"✅ Tienes {n_bombas} bombas configuradas.")
    st.write("Se recomienda sistema **dúplex alternado**. Si una falla, la otra entra. Deben tener protecciones térmicas independientes.")

    st.markdown("**2. Balanceo de Fases**")
    st.write("Al conectar los 13 medidores en el panel principal, asegúrate de distribuir: Apto 1 (L1-L2), Apto 2 (L2-L1), etc. para que el neutro no se sobrecargue.")

with rec_col2:
    st.markdown("**3. Protecciones Eléctricas**")
    st.write("- **Supresor de Picos (SPD):** Obligatorio instalar uno Clase 1 o 2 en el panel principal de áreas comunes para proteger la electrónica del ascensor y portones.")
    st.write("- **Fallas a Tierra (GFCI):** Verificar que los tomas de cocina y baños de los aptos tengan protección GFCI.")
    
    st.markdown("**4. Acometida del Penthouse**")
    st.write(f"El PH tiene una carga alta ({load_ph/1000:.1f} kVA). Verifica si el medidor estándar de la CNFL (usualmente base 100A o 200A) soporta esto sin sobrecalentarse.")

# --- DISCLAIMER FINAL ---
st.warning("DESCARGO DE RESPONSABILIDAD: Este software proporciona estimaciones básicas. Todos los diseños finales deben ser firmados por un ingeniero eléctrico colegiado en el CIEMI/CFIA para trámites ante la CNFL.")