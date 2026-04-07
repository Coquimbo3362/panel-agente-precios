import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Panel de Control - Agente de Precios", layout="wide")

# ==========================================
# 2. CONEXIÓN A BASE DE DATOS
# ==========================================
load_dotenv(override=True)
opciones = ClientOptions(schema="agente_precios")

# Soporta tanto ejecución local (.env) como en la nube de Streamlit (Secrets)
supabase_url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY")

supabase = create_client(supabase_url, supabase_key, options=opciones)

st.title("⚙️ Backoffice - Agente de Precios")
st.write("Administración de datos maestros para el Bot de Scraping.")

# 3. PESTAÑAS (Tabs)
tab_cat, tab_marcas, tab_ret, tab_urls = st.tabs(["📁 Categorías", "🏷️ Marcas", "🏢 Retailers", "🔗 URLs de Navegación"])

# ==========================================
# PESTAÑA 1: CATEGORÍAS
# ==========================================
with tab_cat:
    st.subheader("Gestión de Categorías")
    categorias = supabase.table("categorias").select("*").order("id").execute().data
    st.dataframe(categorias, use_container_width=True)
    
    col_alta, col_baja = st.columns(2)
    with col_alta:
        with st.form("form_cat", clear_on_submit=True):
            st.write("➕ **Agregar Nueva Categoría**")
            nueva_cat = st.text_input("Nombre de la categoría (ej: Lavarropas)")
            if st.form_submit_button("Guardar Categoría"):
                if nueva_cat:
                    supabase.table("categorias").insert({"nombre": nueva_cat}).execute()
                    st.success("¡Categoría guardada!")
                    st.rerun()
                    
    with col_baja:
        st.write("🗑️ **Eliminar Categoría**")
        if categorias:
            dicc_cat_borrar = {f"ID: {c['id']} - {c['nombre']}": c['id'] for c in categorias}
            cat_a_borrar = st.selectbox("Seleccione la categoría a eliminar:", options=list(dicc_cat_borrar.keys()))
            if st.button("🚨 Borrar Categoría Seleccionada", type="primary"):
                supabase.table("categorias").delete().eq("id", dicc_cat_borrar[cat_a_borrar]).execute()
                st.success("¡Categoría eliminada!")
                st.rerun()

# ==========================================
# PESTAÑA 2: MARCAS
# ==========================================
with tab_marcas:
    st.subheader("Gestión de Marcas")
    marcas = supabase.table("marcas").select("*").order("id").execute().data
    st.dataframe(marcas, use_container_width=True)
    
    col_alta, col_baja = st.columns(2)
    with col_alta:
        with st.form("form_marca", clear_on_submit=True):
            st.write("➕ **Agregar Nueva Marca**")
            nueva_marca = st.text_input("Nombre de la marca (ej: Drean)")
            if st.form_submit_button("Guardar Marca"):
                if nueva_marca:
                    supabase.table("marcas").insert({"nombre": nueva_marca}).execute()
                    st.success("¡Marca guardada!")
                    st.rerun()

    with col_baja:
        st.write("🗑️ **Eliminar Marca**")
        if marcas:
            dicc_marcas_borrar = {f"ID: {m['id']} - {m['nombre']}": m['id'] for m in marcas}
            marca_a_borrar = st.selectbox("Seleccione la marca a eliminar:", options=list(dicc_marcas_borrar.keys()))
            if st.button("🚨 Borrar Marca Seleccionada", type="primary", key="btn_borrar_marca"):
                supabase.table("marcas").delete().eq("id", dicc_marcas_borrar[marca_a_borrar]).execute()
                st.success("¡Marca eliminada correctamente!")
                st.rerun()

# ==========================================
# PESTAÑA 3: RETAILERS
# ==========================================
with tab_ret:
    st.subheader("Configuración de Retailers (Tiendas)")
    retailers = supabase.table("retailers").select("*").order("id").execute().data
    st.dataframe(retailers, use_container_width=True)
    
    col_alta, col_baja = st.columns(2)
    with col_alta:
        with st.form("form_retailer", clear_on_submit=True):
            st.write("➕ **Agregar Nuevo Retailer**")
            nombre_ret = st.text_input("Nombre (ej: Fravega)")
            tipo_pag = st.selectbox("Tipo Paginación",["PARAMETRO_URL", "CLICK_AJAX", "SCROLL_INFINITO", "ENLACE_SIGUIENTE"])
            sel_caja = st.text_input("Selector Caja Producto (ej: .product-item)")
            sel_sig = st.text_input("Selector Botón Siguiente (ej: a.next)")
            
            if st.form_submit_button("Guardar Retailer"):
                if nombre_ret and sel_caja:
                    supabase.table("retailers").insert({
                        "nombre": nombre_ret,
                        "selector_caja": sel_caja,
                        "selector_siguiente": sel_sig,
                        "tipo_paginacion": tipo_pag
                    }).execute()
                    st.success("¡Retailer guardado!")
                    st.rerun()
                    
    with col_baja:
        st.write("🗑️ **Eliminar Retailer**")
        if retailers:
            dicc_ret_borrar = {f"ID: {r['id']} - {r['nombre']}": r['id'] for r in retailers}
            ret_a_borrar = st.selectbox("Seleccione el retailer a eliminar:", options=list(dicc_ret_borrar.keys()))
            if st.button("🚨 Borrar Retailer Seleccionado", type="primary", key="btn_borrar_ret"):
                supabase.table("retailers").delete().eq("id", dicc_ret_borrar[ret_a_borrar]).execute()
                st.success("¡Retailer eliminado!")
                st.rerun()

# ==========================================
# PESTAÑA 4: URLs DE EXTRACCIÓN
# ==========================================
with tab_urls:
    st.subheader("Mapa de Navegación del Bot")
    
    # 1. MOSTRAR LA TABLA CON EL CAMPO max_paginas
    urls_data = supabase.table("urls_extraccion").select(
        "id, url_base, activo, max_paginas, categorias(nombre), retailers(nombre)"
    ).order("id").execute().data

    if urls_data:
        df_urls = pd.DataFrame(urls_data)
        df_urls['Retailer'] = df_urls['retailers'].apply(lambda x: x['nombre'] if x else '')
        df_urls['Categoría'] = df_urls['categorias'].apply(lambda x: x['nombre'] if x else '')
        df_urls = df_urls[['id', 'Retailer', 'Categoría', 'url_base', 'max_paginas', 'activo']]
        st.dataframe(df_urls, use_container_width=True)
    else:
        st.info("No hay URLs configuradas en el sistema.")

    st.write("---")
    
    categorias_basicas = supabase.table("categorias").select("*").execute().data
    retailers_basicos = supabase.table("retailers").select("*").execute().data
    
    if categorias_basicas and retailers_basicos:
        dicc_cat = {c['nombre']: c['id'] for c in categorias_basicas}
        dicc_ret = {r['nombre']: r['id'] for r in retailers_basicos}
        
        # SUB-PESTAÑAS DE ACCIONES
        sub_nueva, sub_editar, sub_borrar = st.tabs(["➕ Nueva URL", "✏️ Editar URL", "🗑️ Borrar URL"])
        
        # --- A. NUEVA URL ---
        with sub_nueva:
            with st.form("form_urls", clear_on_submit=True):
                cat_sel = st.selectbox("Seleccione la Categoría", options=list(dicc_cat.keys()))
                ret_sel = st.selectbox("Seleccione el Retailer", options=list(dicc_ret.keys()))
                url_ing = st.text_input("Pegue la URL base aquí")
                
                # NUEVO CAMPO DE LÍMITE
                limite_ing = st.number_input("Límite de páginas (Deje en 0 para infinito)", min_value=0, step=1, value=0)
                activo_ing = st.checkbox("Activar URL inmediatamente", value=True)
                
                if st.form_submit_button("Guardar URL"):
                    if url_ing:
                        val_lim = int(limite_ing) if limite_ing > 0 else None
                        supabase.table("urls_extraccion").insert({
                            "categoria_id": dicc_cat[cat_sel],
                            "retailer_id": dicc_ret[ret_sel],
                            "url_base": url_ing,
                            "max_paginas": val_lim,
                            "activo": activo_ing
                        }).execute()
                        st.success("¡Ruta creada con éxito!")
                        st.rerun()

        if urls_data:
            dicc_urls_edit = {f"ID {u['id']} - {u['retailers']['nombre']} ({u['categorias']['nombre']})": u for u in urls_data}
            
            # --- B. EDITAR URL ---
            with sub_editar:
                url_a_editar = st.selectbox("Seleccione la configuración a editar:", options=list(dicc_urls_edit.keys()))
                datos_actuales = dicc_urls_edit[url_a_editar]
                
                with st.form("form_editar_url"):
                    st.write(f"**Modificando registro ID:** {datos_actuales['id']}")
                    
                    limite_actual_val = int(datos_actuales.get('max_paginas') or 0)
                    
                    nueva_url = st.text_input("URL base", value=datos_actuales['url_base'])
                    # EDICIÓN DEL LÍMITE
                    nuevo_limite = st.number_input("Límite de páginas (0 = infinito)", min_value=0, step=1, value=limite_actual_val)
                    nuevo_activo = st.checkbox("Activo", value=datos_actuales['activo'])
                    
                    if st.form_submit_button("Actualizar Cambios"):
                        val_lim_upd = int(nuevo_limite) if nuevo_limite > 0 else None
                        
                        supabase.table("urls_extraccion").update({
                            "url_base": nueva_url,
                            "max_paginas": val_lim_upd,
                            "activo": nuevo_activo
                        }).eq("id", datos_actuales['id']).execute()
                        
                        st.success("¡Registro actualizado correctamente!")
                        st.rerun()

            # --- C. BORRAR URL ---
            with sub_borrar:
                url_a_borrar = st.selectbox("Seleccione la URL a eliminar:", options=list(dicc_urls_edit.keys()), key="del_url")
                id_borrar = dicc_urls_edit[url_a_borrar]['id']
                
                if st.button("🚨 Borrar URL Definitivamente", type="primary"):
                    supabase.table("urls_extraccion").delete().eq("id", id_borrar).execute()
                    st.success("¡Ruta eliminada!")
                    st.rerun()
    else:
        st.warning("⚠️ Primero debes crear al menos una Categoría y un Retailer.")