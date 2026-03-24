import streamlit as st
import pandas as pd
import datetime
import os
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard - Agente de Precios", layout="wide")

# ==========================================
# 2. CONEXIÓN A LA BASE DE DATOS
# ==========================================
load_dotenv(override=True)
opciones = ClientOptions(schema="agente_precios")

# Usamos st.secrets si está en la nube, o os.environ si está en local
supabase_url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY")

supabase = create_client(supabase_url, supabase_key, options=opciones)

# ==========================================
# 3. OBTENER DATOS (Función con caché para que sea rápido)
# ==========================================
@st.cache_data(ttl=600) # Guarda los datos en memoria por 10 min para no saturar la base
def cargar_datos():
    # Traemos los precios y cruzamos con el nombre del retailer y la categoría
    respuesta = supabase.table("historico_precios").select(
        "id, precio_lista, fecha_extraccion, marca_detectada, nombre_modelo_completo, retailers(nombre), categorias(nombre)"
    ).execute()
    
    datos = respuesta.data
    if not datos:
        return pd.DataFrame() # Devuelve tabla vacía si no hay nada
        
    df = pd.DataFrame(datos)
    
    # Limpiamos y ordenamos las columnas
    df['Retailer'] = df['retailers'].apply(lambda x: x['nombre'] if x else 'Desconocido')
    df['Categoría'] = df['categorias'].apply(lambda x: x['nombre'] if x else 'Desconocido')
    
    # Convertimos la fecha al formato correcto (quitamos la hora para el filtro)
    df['fecha_extraccion'] = pd.to_datetime(df['fecha_extraccion']).dt.date
    
    # Renombramos para que se vea más bonito
    df = df.rename(columns={
        'precio_lista': 'Precio',
        'marca_detectada': 'Marca',
        'nombre_modelo_completo': 'Modelo',
        'fecha_extraccion': 'Fecha'
    })
    
    return df[['Fecha', 'Retailer', 'Categoría', 'Marca', 'Modelo', 'Precio']]

# Cargamos el DataFrame
df_precios = cargar_datos()

# ==========================================
# 4. INTERFAZ: BARRA LATERAL (FILTROS)
# ==========================================
st.sidebar.header("🔍 Filtros de Búsqueda")

if not df_precios.empty:
    # A. FILTRO DE FECHAS (¡Corregido!)
    hoy = datetime.date.today()
    hace_un_mes = hoy - datetime.timedelta(days=30)
    
    rango_fechas = st.sidebar.date_input(
        "📅 Rango de Fechas",
        value=(hace_un_mes, hoy),  # Rango por defecto (últimos 30 días)
        max_value=hoy              # No permite elegir fechas del futuro
    )
    
    # B. FILTROS DESPLEGABLES (Retailer, Categoría, Marca)
    retailers_unicos = df_precios['Retailer'].unique().tolist()
    filtro_retailer = st.sidebar.multiselect("🏪 Retailer", retailers_unicos, default=retailers_unicos)
    
    categorias_unicas = df_precios['Categoría'].unique().tolist()
    filtro_categoria = st.sidebar.multiselect("📁 Categoría", categorias_unicas, default=categorias_unicas)
    
    marcas_unicas = df_precios['Marca'].unique().tolist()
    filtro_marca = st.sidebar.multiselect("🏷️ Marca", marcas_unicas, default=marcas_unicas)

    # ==========================================
    # 5. APLICAR FILTROS AL DATAFRAME
    # ==========================================
    if len(rango_fechas) == 2:
        fecha_inicio, fecha_fin = rango_fechas
        
        # Filtramos la tabla según lo que eligió el usuario
        df_filtrado = df_precios[
            (df_precios['Fecha'] >= fecha_inicio) & 
            (df_precios['Fecha'] <= fecha_fin) &
            (df_precios['Retailer'].isin(filtro_retailer)) &
            (df_precios['Categoría'].isin(filtro_categoria)) &
            (df_precios['Marca'].isin(filtro_marca))
        ]
    else:
        df_filtrado = df_precios # Por si el usuario no seleccionó un rango válido aún

    # Mostramos cuántos encontró en la barra lateral
    st.sidebar.markdown("---")
    st.sidebar.write(f"**Registros encontrados: {len(df_filtrado)}**")

    # ==========================================
    # 6. PANTALLA PRINCIPAL (DASHBOARD)
    # ==========================================
    st.title("📊 Tablero de Control de Precios")
    
    if len(df_filtrado) > 0:
        # Tarjetas de Resumen (KPIs)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Productos", len(df_filtrado))
        col2.metric("Precio Promedio", f"${int(df_filtrado['Precio'].mean()):,}")
        col3.metric("Marcas Encontradas", df_filtrado['Marca'].nunique())
        
        st.write("---")
        
        # Gráficos y Tablas
        col_grafico, col_tabla = st.columns([1, 1])
        
        with col_grafico:
            st.subheader("Precio Promedio por Marca")
            # Agrupamos los precios por marca para hacer un gráfico de barras
            promedio_marcas = df_filtrado.groupby('Marca')['Precio'].mean().sort_values(ascending=False)
            st.bar_chart(promedio_marcas)
            
        with col_tabla:
            st.subheader("Base de Datos Detallada")
            # Mostramos la tabla con los precios formateados
            st.dataframe(
                df_filtrado.style.format({'Precio': '${:,.0f}'}), 
                use_container_width=True,
                height=400
            )
    else:
        st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")

else:
    st.title("📊 Tablero de Control de Precios")
    st.info("Aún no hay datos en la base de datos. ¡Pon a correr el bot!")