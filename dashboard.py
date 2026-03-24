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

supabase_url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY")

supabase = create_client(supabase_url, supabase_key, options=opciones)

# ==========================================
# 3. OBTENER DATOS (Con extracción por bloques para saltar el límite de 1000)
# ==========================================
@st.cache_data(ttl=600)
def cargar_datos():
    todos_los_datos =[]
    inicio = 0
    tamano_bloque = 1000
    
    # Bucle para descargar la base de datos completa en pedacitos
    while True:
        respuesta = supabase.table("historico_precios").select(
            "id, precio_lista, fecha_extraccion, marca_detectada, nombre_modelo_completo, retailers(nombre), categorias(nombre)"
        ).range(inicio, inicio + tamano_bloque - 1).execute()
        
        datos = respuesta.data
        if not datos:
            break # Si ya no hay datos, rompemos el bucle
            
        todos_los_datos.extend(datos) # Sumamos este bloque a la lista total
        
        # Si nos devolvió menos de 1000, significa que llegamos al final de la tabla
        if len(datos) < tamano_bloque:
            break
            
        inicio += tamano_bloque # Preparamos el inicio para los siguientes 1000
        
    if not todos_los_datos:
        return pd.DataFrame()
        
    df = pd.DataFrame(todos_los_datos)
    
    # Limpieza
    df['Retailer'] = df['retailers'].apply(lambda x: x['nombre'] if x else 'Desconocido')
    df['Categoría'] = df['categorias'].apply(lambda x: x['nombre'] if x else 'Desconocido')
    df['fecha_extraccion'] = pd.to_datetime(df['fecha_extraccion']).dt.date
    
    df = df.rename(columns={
        'precio_lista': 'Precio',
        'marca_detectada': 'Marca',
        'nombre_modelo_completo': 'Modelo',
        'fecha_extraccion': 'Fecha'
    })
    
    return df[['Fecha', 'Categoría', 'Retailer', 'Marca', 'Modelo', 'Precio']]

df_precios = cargar_datos()

# ==========================================
# 4. INTERFAZ: BARRA LATERAL (FILTROS)
# ==========================================
st.sidebar.header("🔍 Filtros de Búsqueda")

if not df_precios.empty:
    # A. FILTRO DE FECHAS
    hoy = datetime.date.today()
    hace_un_mes = hoy - datetime.timedelta(days=30)
    
    rango_fechas = st.sidebar.date_input(
        "📅 Rango de Fechas",
        value=(hace_un_mes, hoy),
        max_value=hoy
    )
    
    # B. FILTRO DE CATEGORÍA (Heladeras por default)
    categorias_unicas = sorted(df_precios['Categoría'].unique().tolist())
    
    # Lógica para que Heladeras sea el valor por defecto si existe en la base
    cat_default = ["Heladeras"] if "Heladeras" in categorias_unicas else categorias_unicas
    
    filtro_categoria = st.sidebar.multiselect("📁 Categoría", categorias_unicas, default=cat_default)
    
    # Filtramos temporalmente para los menús en cascada
    df_temp_cat = df_precios[df_precios['Categoría'].isin(filtro_categoria)] if filtro_categoria else df_precios
    
    # C. FILTRO DE RETAILER
    retailers_unicos = sorted(df_temp_cat['Retailer'].unique().tolist())
    filtro_retailer = st.sidebar.multiselect("🏪 Retailer", retailers_unicos, default=retailers_unicos)
    
    # D. FILTRO DE MARCA
    df_temp_ret = df_temp_cat[df_temp_cat['Retailer'].isin(filtro_retailer)] if filtro_retailer else df_temp_cat
    marcas_unicas = sorted(df_temp_ret['Marca'].unique().tolist())
    filtro_marca = st.sidebar.multiselect("🏷️ Marca", marcas_unicas, default=marcas_unicas)

    # ==========================================
    # 5. APLICAR FILTROS AL DATAFRAME FINAL
    # ==========================================
    if len(rango_fechas) == 2:
        fecha_inicio, fecha_fin = rango_fechas
        
        df_filtrado = df_precios[
            (df_precios['Fecha'] >= fecha_inicio) & 
            (df_precios['Fecha'] <= fecha_fin) &
            (df_precios['Categoría'].isin(filtro_categoria)) &
            (df_precios['Retailer'].isin(filtro_retailer)) &
            (df_precios['Marca'].isin(filtro_marca))
        ]
    else:
        df_filtrado = df_precios

    st.sidebar.markdown("---")
    st.sidebar.write(f"**Registros listados: {len(df_filtrado)}**")

    # ==========================================
    # 6. PANTALLA PRINCIPAL (DASHBOARD)
    # ==========================================
    st.title("📊 Tablero de Control de Precios")
    
    if len(df_filtrado) > 0:
        # Tarjetas de Resumen
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Productos", len(df_filtrado))
        col2.metric("Precio Promedio", f"${int(df_filtrado['Precio'].mean()):,}")
        col3.metric("Marcas Encontradas", df_filtrado['Marca'].nunique())
        
        st.write("---")
        
        # OPCIÓN DE GRÁFICO (Solo si hay más de 1 marca en los filtros aplicados)
        if df_filtrado['Marca'].nunique() > 1:
            mostrar_grafico = st.checkbox("📈 Mostrar gráfico comparativo de precio promedio", value=False)
            
            if mostrar_grafico:
                st.subheader("Precio Promedio por Marca")
                promedio_marcas = df_filtrado.groupby('Marca')['Precio'].mean().sort_values(ascending=False)
                st.bar_chart(promedio_marcas)
                st.write("---")
                
        # TABLA DE DATOS
        st.subheader("Base de Datos Detallada")
        st.dataframe(
            df_filtrado.style.format({'Precio': '${:,.0f}'}), 
            use_container_width=True,
            height=600
        )
    else:
        st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")

else:
    st.title("📊 Tablero de Control de Precios")
    st.info("Aún no hay datos en la base de datos. ¡Pon a correr el bot!")