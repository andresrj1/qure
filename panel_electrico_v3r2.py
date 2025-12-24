import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Cálculo Panel - Estrategia Legal/Técnica", layout="wide")

# --- FUNCIONES DE SEGURIDAD Y CÁLCULO ---
def seleccionar_breaker_seguro(amperios_reales):
    # Factor de seguridad 125% para uso continuo (NEC)
    target = amperios_reales * 1.25
    comerciales = [15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 225]
    for b in comerciales:
        if b >= target:
            return b
    return 250 # Fallback

# --- INTERFAZ ---
st.title("⚡ Diseño Eléctrico: Estrategia de 'Cargas Ocultas'")
st.markdown("""
**Objetivo:** Mantener la apariencia legal de 12 medidores (11 Apts + 1 Área Común) ante la CNFL, 
pero garantizando capacidad técnica para alimentar unidades extra sin "puentear" breakers.
""")

with st.sidebar:
    st.header("1. Configuración Legal (La Fachada)")
    voltaje = st.selectbox("Voltaje", [240, 208], index=0)
    slots_visibles = st.number_input("Espacios de Medidor (CNFL)", value=12, disabled=True, help="Límite estricto por normativa de condominio.")
    
    st.header("2. Cargas 'Fantasma' (Aptos Ilegales)")
    qty_ocultos = st.number_input("Cant. Aptos sin Registro", value=2)
    carga_oculta_watts = st.number_input("Carga Est. por Apto Oculto (W)", value=4500, help="Cocina pq, ducha, luces")
    
    st.header("3. Cargas Legales")
    carga_comun_base = st.number_input("Áreas Comunes Base (Ascensor/Bombas/Luces)", value=12000)
    carga_apt_legal = st.number_input("Apto Legal Promedio (W)", value=14000)

# --- LÓGICA DE ASIGNACIÓN ---
st.subheader("🔌 Estrategia de Conexión")

opcion_conexion = st.radio(
    "¿Dónde se conectarán físicamente los apartamentos ilegales?",
    ["Opción A: Al Medidor de Áreas Comunes (Recomendado)", 
     "Opción B: A un Apartamento 'Padrino' (Ej. Apt 8 alimenta al 13)"]
)

# CÁLCULOS
total_watts_ocultos = qty_ocultos * carga_oculta_watts

if "Opción A" in opcion_conexion:
    # Carga Común + Carga Oculta
    carga_total_medidor_comun = carga_comun_base + total_watts_ocultos
    amps_medidor_comun = carga_total_medidor_comun / voltaje
    breaker_comun = seleccionar_breaker_seguro(amps_medidor_comun)
    
    st.info(f"Los {qty_ocultos} apartamentos ocultos se sumarán a la factura de Áreas Comunes.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🏗️ Diseño del Breaker 'Áreas Comunes'")
        st.metric("Carga Base Común", f"{carga_comun_base} W")
        st.metric("Carga Oculta Adicional", f"+ {total_watts_ocultos} W")
        st.metric("Total en Medidor Común", f"{carga_total_medidor_comun} W")
        
    with col2:
        st.markdown("### 🛠️ Hardware Requerido")
        if breaker_comun > 125:
            st.error(f"⚠️ **ALERTA:** Necesitas un Breaker de **{breaker_comun}A**.")
            st.write("El gabinete EZM estándar usa breakers de hasta 100A o 125A. Esta carga es MUY ALTA para un solo espacio del modular.")
            st.markdown("**Solución:** Instalar una **Base de Medidor 200A (Redonda)** por aparte para Áreas Comunes, fuera del banco EZM.")
        else:
            st.success(f"✅ Breaker Requerido: **{breaker_comun}A**")
            st.write("Cabe en el módulo EZM (usando un breaker QDP de esa capacidad).")

elif "Opción B" in opcion_conexion:
    st.warning("Esta opción depende de que un vecino acepte 'apadrinar' la carga del ilegal.")
    # Cálculo para un apto legal que alimenta a uno ilegal
    carga_apadrinada = carga_apt_legal + carga_oculta_watts
    amps_padrino = carga_apadrinada / voltaje
    breaker_padrino = seleccionar_breaker_seguro(amps_padrino)
    
    st.metric("Nuevo Breaker para Apto Padrino", f"{breaker_padrino}A")
    if breaker_padrino > 100:
        st.error("El breaker necesario excede los 100A típicos. Revisar cableado interno del apto.")

# --- DIAGRAMA DE SOLUCIÓN ---
st.markdown("---")
st.subheader("💡 Solución Técnica: Sub-medición (Private Metering)")

st.graphviz_chart("""
digraph G {
    rankdir=LR;
    CNFL [label="Acometida CNFL", shape=box, style=filled, fillcolor=yellow];
    
    subgraph cluster_legal {
        label = "Panel Principal (12 Espacios - Legal)";
        style=dashed;
        M_Comun [label="Medidor\nÁreas Comunes\n(Oficial)", style=filled, fillcolor=lightblue];
        M_Apts [label="11 Medidores\nAptos Legales", shape=folder];
    }
    
    subgraph cluster_ilegal {
        label = "Zona Gris (Interior)";
        style=dotted;
        Sub_Panel [label="Sub-Panel\nDistribución", shape=rect];
        M_Int1 [label="Medidor Privado\n(Apt 13)", shape=ellipse];
        M_Int2 [label="Medidor Privado\n(Apt 'Fantasma')", shape=ellipse];
        Carga_Real [label="Bombas/Luces\nReales", shape=diamond];
    }
    
    CNFL -> M_Comun;
    CNFL -> M_Apts;
    
    M_Comun -> Sub_Panel [label="Cable Grueso\n(Soporta Todo)", color=red, penwidth=2];
    
    Sub_Panel -> Carga_Real [label="Breaker A"];
    Sub_Panel -> M_Int1 [label="Breaker B"];
    Sub_Panel -> M_Int2 [label="Breaker C"];
    
    M_Int1 -> "Apto 13 (Ilegal)";
    M_Int2 -> "Apto Extra (Ilegal)";
}
""")

st.markdown("""
### Recomendaciones Finales de Seguridad
1.  **Cero Puentes:** No permitas lo que hizo Carlos. Un puente en un baño es un incendio esperando a ocurrir. Todo debe salir de un breaker.
2.  **Cobro Interno:** Al final de mes, tomas la factura de Áreas Comunes (que vendrá alta). Restas la lectura de los **Medidores Privados** (M_Int1, M_Int2).
    * *El condominio paga:* (Factura Total - Lectura Privados).
    * *El inquilino 13 paga:* Su lectura x Tarifa Kwh.
3.  **Capacidad del Medidor Común:** Si eliges la Opción A, asegúrate que la base del medidor de áreas comunes sea **Clase 200 (200 Amperios)** y cableado calibre 2/0 o 4/0, porque va a llevar la carga de todo el edificio más las casas extra.
""")