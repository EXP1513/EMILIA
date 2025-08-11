import streamlit as st
import pandas as pd
import os
from io import BytesIO

st.set_page_config(page_title="Valida Matrícula", layout="wide")
st.title("📊 Valida Matrícula")

def normalize_col_names(df):
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df

def carregar_arquivo(file):
    if file is None:
        return None

    ext = os.path.splitext(file.name)[1].lower()
    try:
        # 1. Tenta CSV
        if ext == ".csv":
            df = pd.read_csv(file, encoding="utf-8", sep=";", header=1)
            return normalize_col_names(df)

        # 2. Tenta Excel múltiplos engines
        for engine in ["openpyxl", "xlrd", "odf", "pyxlsb"]:
            try:
                df = pd.read_excel(file, header=1, engine=engine)
                return normalize_col_names(df)
            except:
                pass

        # 3. Tenta HTML (exportação em .xls que é HTML)
        file.seek(0)
        try:
            tables = pd.read_html(file)
            if tables:
                df = tables[0]
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)
                return normalize_col_names(df)
        except:
            pass

        st.error(f"⚠️ Não foi possível ler o arquivo {file.name}. Formato não suportado ou corrompido.")
        return None

    except Exception as e:
        st.error(f"Erro ao processar {file.name}: {e}")
        return None

for base in ["educapi_base", "comercial_base", "painel_base", "verificar"]:
    if base not in st.session_state:
        st.session_state[base] = None

st.subheader("📂 Envie suas bases:")

educapi_file = st.file_uploader("Base Educapi", type=None, key="educapi")
if educapi_file:
    st.session_state.educapi_base = carregar_arquivo(educapi_file)
    if st.session_state.educapi_base is not None:
        st.success("Base Educapi carregada.")

comercial_file = st.file_uploader("Base Comercial", type=None, key="comercial")
if comercial_file:
    st.session_state.comercial_base = carregar_arquivo(comercial_file)
    if st.session_state.comercial_base is not None:
        st.success("Base Comercial carregada.")

painel_file = st.file_uploader("Base Painel", type=None, key="painel")
if painel_file:
    st.session_state.painel_base = carregar_arquivo(painel_file)
    if st.session_state.painel_base is not None:
        st.success("Base Painel carregada.")

def gerar_verificacao():
    educapi = st.session_state.educapi_base
    comercial = st.session_state.comercial_base
    painel = st.session_state.painel_base

    col_cpf_painel = next((c for c in painel.columns if "cpf" in c), None)
    col_nome_painel = next((c for c in painel.columns if "nome" in c), None)
    col_cpf_educapi = next((c for c in educapi.columns if "cpf" in c), None)
    col_estado_educapi = next((c for c in educapi.columns if "estado" in c or "uf" in c), None)
    col_nome_educapi = next((c for c in educapi.columns if "nome" in c), None)
    col_cpf_comercial = next((c for c in comercial.columns if "cpf" in c), None)
    col_estado_comercial = next((c for c in comercial.columns if "estado" in c or "uf" in c), None)
    col_nome_comercial = next((c for c in comercial.columns if "nome" in c), None)

    if not all([col_cpf_painel, col_nome_painel,
                col_cpf_educapi, col_estado_educapi, col_nome_educapi,
                col_cpf_comercial, col_estado_comercial, col_nome_comercial]):
        st.error("❌ Faltam colunas obrigatórias (CPF, Nome ou Estado/UF).")
        return None

    inconsistencias_dict = {}

    for _, row in painel.iterrows():
        cpf = str(row[col_cpf_painel] or "").strip()
        nome_painel = str(row[col_nome_painel] or "").strip()
        educapi_aluno = educapi[educapi[col_cpf_educapi].astype(str).str.strip() == cpf]
        comercial_aluno = comercial[comercial[col_cpf_comercial].astype(str).str.strip() == cpf]

        status_list = []

        if not educapi_aluno.empty and not comercial_aluno.empty:
            status_list.append("CPF presente em ambas as bases")
        if not educapi_aluno.empty:
            nome_educapi = str(educapi_aluno.iloc[0][col_nome_educapi] or "").strip()
            if nome_educapi.lower() != nome_painel.lower():
                status_list.append("Nome cadastrado não bate no Painel")
        if not comercial_aluno.empty:
            nome_comercial = str(comercial_aluno.iloc[0][col_nome_comercial] or "").strip()
            if nome_comercial.lower() != nome_painel.lower():
                status_list.append("Nome cadastrado não bate no Painel")
        if not educapi_aluno.empty:
            estado_educapi = str(educapi_aluno.iloc[0][col_estado_educapi] or "").strip().upper()
            if "SP" in estado_educapi:
                status_list.append("Cadastro em plataforma errada")
        if not comercial_aluno.empty:
            estado_comercial = str(comercial_aluno.iloc[0][col_estado_comercial] or "").strip().upper()
            if "SP" not in estado_comercial:
                status_list.append("Cadastro em plataforma errada")
        if educapi_aluno.empty and comercial_aluno.empty:
            status_list.append("CPF não encontrado")

        if status_list:
            inconsistencias_dict[cpf] = {**row.to_dict(), "Status": ", ".join(sorted(set(status_list)))}

    return pd.DataFrame(list(inconsistencias_dict.values()))

if all([st.session_state.educapi_base is not None,
        st.session_state.comercial_base is not None,
        st.session_state.painel_base is not None]):
    st.session_state.verificar = gerar_verificacao()

if st.session_state.verificar is not None and not st.session_state.verificar.empty:
    st.subheader("📋 Base de Inconsistências")
    st.dataframe(st.session_state.verificar, use_container_width=True)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        st.session_state.verificar.to_excel(writer, index=False, sheet_name="Verificar")
    st.download_button(
        label="📥 Baixar Excel",
        data=output.getvalue(),
        file_name="verificar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
