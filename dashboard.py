import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="Portal de Precios", page_icon="📊", layout="wide")

load_dotenv(override=True)
opciones = ClientOptions(schema="agente_precios")
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"), options=opciones)

# Función para dar formato español a los precios (Ej: 1.500.000)
def formato_precio_es(valor):
    return f"${int(valor):,.0f}".replace(",", ".")

# ==========================================
# 2. FUNCIÓN PARA DESCARGAR DATOS
# ==========================================
@st.cache_data(ttl=300) 
def cargar_datos():
    respuesta = supabase.table("historico_precios").select(
        "fecha_extraccion, precio_lista, marca_detectada, nombre_modelo_completo, retailers(nombre), categorias(nombre)"
    ).order("fecha_extraccion", desc=True).execute()
    
    if not respuesta.data:
        return pd.DataFrame()
        
    datos_limpios =[]
    for fila in respuesta.data:
        datos_limpios.append({
            "Fecha_Real": pd.to_datetime(fila["fecha_extraccion"]).date(), # Fecha real para filtrar bien
            "Categoría": fila["categorias"]["nombre"] if fila.get("categorias") else "N/A",
            "Retailer": fila["retailers"]["nombre"] if fila.get("retailers") else "N/A",
            "Marca": fila["marca_detectada"],
            "Precio_Num": fila["precio_lista"], # Número real para calcular promedios
            "Modelo": fila["nombre_modelo_completo"]
        })
    return pd.DataFrame(datos_limpios)

df = cargar_datos()

if df.empty:
    st.title("📊 Monitor Inteligente de Precios")
    st.info("Aún no hay datos en el historial. Ejecuta el bot para recolectar precios.")
else:
    # ==========================================
    # 3. BARRA LATERAL (FILTROS)
    # ==========================================
    st.sidebar.header("⚙️ Configuración de Consulta")
    
    categorias_disponibles = sorted(df["Categoría"].unique())
    categoria_seleccionada = st.sidebar.selectbox("📁 1. Seleccione la Categoría", options=categorias_disponibles)
    
    df_categoria = df[df["Categoría"] == categoria_seleccionada].copy()

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Búsqueda")

    # Filtro de Fechas (Desde - Hasta)
    fecha_min = df_categoria["Fecha_Real"].min()
    fecha_max = df_categoria["Fecha_Real"].max()

    rango_fechas = st.sidebar.date_input(
        "📅 Rango de Fechas",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )

    filtro_ret = st.sidebar.multiselect("🏢 Retailers", options=df_categoria["Retailer"].unique())
    filtro_marca = st.sidebar.multiselect("🏷️ Marcas", options=df_categoria["Marca"].unique())
    busqueda_modelo = st.sidebar.text_input("🔎 Buscar palabra en modelo (ej: Inverter)")

    # ==========================================
    # 4. APLICAR FILTROS
    # ==========================================
    df_filtrado = df_categoria.copy()
    
    if isinstance(rango_fechas, tuple):
        if len(rango_fechas) == 2:
            df_filtrado = df_filtrado[(df_filtrado["Fecha_Real"] >= rango_fechas[0]) & (df_filtrado["Fecha_Real"] <= rango_fechas[1])]
        elif len(rango_fechas) == 1:
            df_filtrado = df_filtrado[df_filtrado["Fecha_Real"] >= rango_fechas[0]]

    if filtro_ret:
        df_filtrado = df_filtrado[df_filtrado["Retailer"].isin(filtro_ret)]
    if filtro_marca:
        df_filtrado = df_filtrado[df_filtrado["Marca"].isin(filtro_marca)]
    if busqueda_modelo:
        df_filtrado = df_filtrado[df_filtrado["Modelo"].str.contains(busqueda_modelo, case=False, na=False)]

    # ==========================================
    # 5. UI PRINCIPAL Y SELECCIÓN DE MODELOS
    # ==========================================
    st.title(f"📊 Análisis de Mercado: {categoria_seleccionada}")
    
    tab_datos, tab_graficos = st.tabs(["📋 Consulta y Selección", "📈 Análisis Comparativo (Fase 2)"])

    with tab_datos:
        st.sidebar.markdown("---")
        st.sidebar.write(f"**Registros encontrados:** {len(df_filtrado)}")

        if not df_filtrado.empty:
            # Calculamos las métricas con los números reales, pero mostramos con puntos
            col1, col2, col3 = st.columns(3)
            col1.metric("Promedio de Mercado", formato_precio_es(df_filtrado["Precio_Num"].mean()))
            col2.metric("Precio Más Bajo", formato_precio_es(df_filtrado["Precio_Num"].min()))
            col3.metric("Precio Más Alto", formato_precio_es(df_filtrado["Precio_Num"].max()))

            st.write("---")
            st.markdown("### 📋 Detalle de Productos")
            st.markdown("👉 **Haz clic en la casilla izquierda de los modelos que consideres iguales** para agruparlos y compararlos en el futuro.")
            
            # Preparamos el DataFrame final solo para MOSTRAR (con las fechas y precios en formato lindo)
            df_mostrar = df_filtrado[["Fecha_Real", "Retailer", "Marca", "Precio_Num", "Modelo"]].copy()
            df_mostrar["Fecha"] = pd.to_datetime(df_mostrar["Fecha_Real"]).dt.strftime("%d/%m/%Y")
            df_mostrar["Precio ($)"] = df_mostrar["Precio_Num"].apply(formato_precio_es)
            
            # Ordenamos las columnas para que el precio destaque como pediste
            df_mostrar = df_mostrar[["Fecha", "Retailer", "Marca", "Precio ($)", "Modelo"]]

            # TABLA INTERACTIVA (Permite seleccionar filas)
            evento_seleccion = st.dataframe(
                df_mostrar,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",          # Recarga la página si el usuario selecciona algo
                selection_mode="multi-row"  # Permite elegir varias filas a la vez
            )

            # Extraemos lo que el usuario seleccionó
            filas_seleccionadas = evento_seleccion.selection.rows
            if filas_seleccionadas:
                st.success(f"✅ Has seleccionado {len(filas_seleccionadas)} modelos específicos.")
                # Aquí guardamos la selección en la memoria temporal para usarla en los gráficos de la Fase 2
                df_seleccionado = df_filtrado.iloc[filas_seleccionadas]
                st.session_state['modelos_seleccionados'] = df_seleccionado

        else:
            st.warning("No se encontraron productos con los filtros seleccionados.")

    with tab_graficos:
        if 'modelos_seleccionados' in st.session_state and not st.session_state['modelos_seleccionados'].empty:
            st.info("💡 ¡Excelente! Has seleccionado modelos. En esta pestaña armaremos el gráfico de distorsión de precios entre esos retailers.")
            # st.dataframe(st.session_state['modelos_seleccionados'][["Retailer", "Precio_Num", "Modelo"]])
        else:
            st.info("💡 Ve a la pestaña 'Consulta y Selección' y marca al menos un modelo para empezar a compararlo aquí.")

# ==========================================
# 6. BOTÓN DE SALIDA
# ==========================================
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Cerrar Sesión / Salir", type="secondary"):
    st.success("Sesión finalizada. Puedes cerrar esta pestaña del navegador.")
    st.stop()