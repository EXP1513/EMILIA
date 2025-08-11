import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Valida Matrícula - Verificação Completa", layout="wide")
st.title("📊 Valida Matrícula - Verificação Completa")
st.write("Carregue as três bases separadamente. Ao enviar a última (Painel), o sistema fará a verificação automática.")

# Função para normalizar colunas
def normalize_col_names(df):
    df.columns = [col.strip().lower() for col in df.columns]
    return df

# Variáveis para armazenar as bases
if "educapi_base" not in st.session_state:
    st.session_state.educapi_base = None
if "comercial_base" not in st.session_state:
    st.session_state.comercial_base = None
if "painel_base" not in st.session_state:
    st.session_state.painel_base = None
if "verificar" not in st.session_state:
    st.session_state.verificar = None

# Uploads separados
st.subheader("📂 Upload das Bases")
educapi_file = st.file_uploader("Carregar Base Educapi", type=["xls", "xlsx", "csv"], key="educapi")
if educapi_file is not None:
    if educapi_file.name.endswith(".csv"):
        df = pd.read_csv(educapi_file, encoding="utf-8", sep=";", header=1)
    else:
        df = pd.read_excel(educapi_file, header=1)
    st.session_state.educapi_base = normalize_col_names(df)
    st.success("Base Educapi carregada!")

comercial_file = st.file_uploader("Carregar Base Comercial", type=["xls", "xlsx", "csv"], key="comercial")
if comercial_file is not None:
    if comercial_file.name.endswith(".csv"):
        df = pd.read_csv(comercial_file, encoding="utf-8", sep=";", header=1)
    else:
        df = pd.read_excel(comercial_file, header=1)
    st.session_state.comercial_base = normalize_col_names(df)
    st.success("Base Comercial carregada!")

painel_file = st.file_uploader("Carregar Base Painel", type=["xls", "xlsx", "csv"], key="painel")
if painel_file is not None:
    if painel_file.name.endswith(".csv"):
        df = pd.read_csv(painel_file, encoding="utf-8", sep=";", header=1)
    else:
        df = pd.read_excel(painel_file, header=1)
    st.session_state.painel_base = normalize_col_names(df)
    st.success("Base Painel carregada!")

# Função para gerar a base de inconsistências
def gerar_verificacao():
    educapi = st.session_state.educapi_base
    comercial = st.session_state.comercial_base
    painel = st.session_state.painel_base

    verificar = pd.DataFrame()

    # Identificar colunas
    col_cpf_painel = next((col for col in painel.columns if "cpf" in col), None)
    col_nome_painel = next((col for col in painel.columns if "nome" in col), None)

    col_cpf_educapi = next((col for col in educapi.columns if "cpf" in col), None)
    col_estado_educapi = next((col for col in educapi.columns if "estado" in col or "uf" in col), None)
    col_nome_educapi = next((col for col in educapi.columns if "nome" in col), None)

    col_cpf_comercial = next((col for col in comercial.columns if "cpf" in col), None)
    col_estado_comercial = next((col for col in comercial.columns if "estado" in col or "uf" in col), None)
    col_nome_comercial = next((col for col in comercial.columns if "nome" in col), None)

    if not all([col_cpf_painel, col_nome_painel,
                col_cpf_educapi, col_estado_educapi, col_nome_educapi,
                col_cpf_comercial, col_estado_comercial, col_nome_comercial]):
        st.error("Faltam colunas obrigatórias (CPF, Nome ou Estado/UF) em alguma das bases.")
        return None

    for _, row in painel.iterrows():
        cpf = str(row[col_cpf_painel]).strip()
        nome_painel = str(row[col_nome_painel]).strip()

        educapi_aluno = educapi[educapi[col_cpf_educapi].astype(str).str.strip() == cpf]
        comercial_aluno = comercial[comercial[col_cpf_comercial].astype(str).str.strip() == cpf]

        encontrado = False

        # Regra 1: CPF presente em ambas as bases
        if not educapi_aluno.empty and not comercial_aluno.empty:
            inconsistencia = row.to_dict()
            inconsistencia["Status"] = "CPF presente em ambas as bases"
            verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)
            encontrado = True

        # Regra 2: Nome divergente
        if not educapi_aluno.empty:
            encontrado = True
            nome_educapi = str(educapi_aluno.iloc[0][col_nome_educapi]).strip()
            if nome_educapi.lower() != nome_painel.lower():
                inconsistencia = row.to_dict()
                inconsistencia["Status"] = "Nome cadastrado não bate no Painel"
                verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

        if not comercial_aluno.empty:
            encontrado = True
            nome_comercial = str(comercial_aluno.iloc[0][col_nome_comercial]).strip()
            if nome_comercial.lower() != nome_painel.lower():
                inconsistencia = row.to_dict()
                inconsistencia["Status"] = "Nome cadastrado não bate no Painel"
                verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

        # Regra 3: Plataforma errada
        if not educapi_aluno.empty:
            estado_educapi = str(educapi_aluno.iloc[0][col_estado_educapi]).strip().upper()
            if "SP" in estado_educapi:
                inconsistencia = row.to_dict()
                inconsistencia["Status"] = "Cadastro em plataforma errada"
                verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

        if not comercial_aluno.empty:
            estado_comercial = str(comercial_aluno.iloc[0][col_estado_comercial]).strip().upper()
            if "SP" not in estado_comercial:
                inconsistencia = row.to_dict()
                inconsistencia["Status"] = "Cadastro em plataforma errada"
                verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

        # Regra 4: CPF não encontrado
        if educapi_aluno.empty and comercial_aluno.empty:
            inconsistencia = row.to_dict()
            inconsistencia["Status"] = "CPF não encontrado"
            verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

    return verificar

# Se todas as bases já foram carregadas, gerar resultado
if st.session_state.educapi_base is not None and st.session_state.comercial_base is not None and st.session_state.painel_base is not None:
    st.session_state.verificar = gerar_verificacao()

# Mostrar resultado se existir
if st.session_state.verificar is not None and not st.session_state.verificar.empty:
    st.subheader("📋 Base de Inconsistências - VERIFICAR")
    st.dataframe(st.session_state.verificar, use_container_width=True)

    # Exportar para Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.verificar.to_excel(writer, index=False, sheet_name="Verificar")
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Baixar Base VERIFICAR (Excel)",
        data=excel_data,
        file_name="verificar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
