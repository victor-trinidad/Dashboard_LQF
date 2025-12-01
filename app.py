import streamlit as st
import pandas as pd
import numpy as np

# --- 1. PARÁMETROS DE AUDITORÍA (REGLAS DE NEGOCIO LQF) ---

# 🔴 LISTA DE CÓDIGOS CONTROLADOS (MÁXIMO 5% DE DESCUENTO)
codigos_controlados = [
    '3000113', '3000114', '3000080', '3000082', '3000083', '3000084', '3000085',
    '3000098', '3001265', '3001266', '3001267', '3001894', '3001896', '3002906',
    '3003648', '3004041', '3003870', '3004072', '5000002', '3004071', '3003953',
    '3003955', '3003952', '3004074', '3004073', '3003773', '3003775', '3004756'
]

# Topes de Descuento
DESC_MAX_CONTROLADOS = 5.0
DESC_MAX_EMPLEADOS = 0.0
DESC_MAX_NUTRICIA_BEBELAC = 6.0
DESC_MAX_GENERAL = 7.0

# Reglas de Intercompany (CONFIRMADAS)
DESC_INTERCOMPANY_200046 = 11.0 
DESC_INTERCOMPANY_200173 = 10.0
CLIENTE_200046 = '200046'
CLIENTE_200173 = '200173'
ALMACEN_EMPLEADOS_PERMITIDO = 1041
marcas_6_porciento = ['NUTRICIA', 'BEBELAC']


# --- 2. FUNCIÓN PRINCIPAL DE AUDITORÍA (CON LIMPIEZA DE COLUMNAS) ---
@st.cache_data
def ejecutar_auditoria(df):
    
    # 1. LIMPIEZA AUTOMÁTICA DE ENCABEZADOS (Solución a espacios y formato)
    df.columns = df.columns.str.strip()
    column_mapping = {
        'Fecha factura': 'Fecha factura', 'Almacen': 'Almacen', 'Tipo Venta': 'Tipo Venta',
        'Zona de Venta': 'Zona de Venta', 'Solicitante': 'Solicitante', 'Nombre 1': 'Nombre 1',
        'Codigo': 'Codigo', 'Material': 'Material', 'Jerarquia': 'Jerarquia',
        '% Desc': '% Desc', 'Valor neto': 'Valor neto',
        'Descuento %': '% Desc', 'codigo': 'Codigo', 'jerarquia': 'Jerarquia', 
        'Valor Neto': 'Valor neto', 'VALOR NETO': 'Valor neto'
    }
    df = df.rename(columns=column_mapping)
    
    # 2. Limpieza y Normalización de Datos
    df['% Desc'] = pd.to_numeric(df['% Desc'], errors='coerce')
    df['Almacen'] = pd.to_numeric(df['Almacen'], errors='coerce', downcast='integer')
    df['Solicitante'] = df['Solicitante'].astype(str)
    
    # 3. Lógica de Prioridad de Descuentos (np.select)
    condiciones = [
        ((df['Zona de Venta'] == 'EMPLEADOS LQF') & (df['Almacen'] != ALMACEN_EMPLEADOS_PERMITIDO) & (df['% Desc'] > DESC_MAX_EMPLEADOS)) | \
        ((df['Zona de Venta'] == 'MEDICOS PARTICULARES') & (df['% Desc'] > DESC_MAX_EMPLEADOS)),
        (df['Codigo'].isin(codigos_controlados)) & (df['% Desc'] > DESC_MAX_CONTROLADOS),
        (df['Solicitante'] == CLIENTE_200046) & (df['% Desc'] > DESC_INTERCOMPANY_200046),
        (df['Solicitante'] == CLIENTE_200173) & (df['% Desc'] > DESC_INTERCOMPANY_200173),
        (df['Jerarquia'].isin(marcas_6_porciento)) & (df['% Desc'] > DESC_MAX_NUTRICIA_BEBELAC),
        (df['% Desc'] > DESC_MAX_GENERAL)
    ]
    etiquetas_alerta = [
        '❌ Ilegal (Empleado/Médico)', '⚠️ Controlado (>5%) Excedido',
        '⚠️ Intercompany 200046 (>11%) Excedido', '⚠️ Intercompany 200173 (>10%) Excedido',
        '⚠️ Marca Nutricion (>6%) Excedido', '⚠️ General (>7%) Excedido'
    ]

    df['Alerta_Descuento'] = np.select(condiciones, etiquetas_alerta, default='OK')
    desvios_encontrados = df[df['Alerta_Descuento'] != 'OK']
    
    return desvios_encontrados, df


# --- INTERFAZ STREAMLIT (EL DASHBOARD) ---

st.set_page_config(page_title="Auditoría Continua de Precios LQF", layout="wide")
st.title("🛡️ Dashboard de Auditoría de Desviaciones de Precios - LQF")
uploaded_file = st.file_uploader("Subir Reporte de Ventas (CSV/XLSX)", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # CORRECCIÓN DE ENCABEZADO: Usamos header=1 para saltar la primera fila
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='latin1', header=1) 
        else:
            df = pd.read_excel(uploaded_file, header=1)
            
        desvios, df_completo = ejecutar_auditoria(df)
        
        # CÁLCULO DE KPIs (Métricas)
        total_transacciones = len(df_completo)
        transacciones_desviadas = len(desvios)
        porcentaje_cumplimiento = (1 - (transacciones_desviadas / total_transacciones)) * 100 if total_transacciones > 0
