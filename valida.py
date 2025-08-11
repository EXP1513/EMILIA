import streamlit as st
import pandas as pd
import os
from io import BytesIO

st.set_page_config(page_title="Valida Matrícula - Verificação Completa", layout="wide")
st.title("📊 Valida Matrícula - Verificação Completa (Status Unificados)")
st.write("Carregue as três bases separadamente. Ao enviar a última (Painel), gera a base de verificação com status unificados.")

def normalize_col_names(df):
    df.columns = [col.strip().lower() for col in df.columns]
    return df

def carregar_arquivo(file):
    if file is None:
        return None
    ext = os.path.splitext(file.name)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(file, encoding="utf-8", sep=";", header=1)
        elif ext == ".xlsx":
            df = pd.read_excel(file, engine="openpyxl", header=1)
        elif ext == ".xls":
            df = pd.read_excel(file, engine="xlrd", header=1)
        else:
            st.error(f"⚠️ Formato não suportado: {ext}")
            return None
        return normalize_col_names(df)
    except Exception as e:
        st.error(f"Erro ao ler {file.name}: {e}")
        return None

for base in ["educapi_base", "comercial_base", "painel_base", "verificar"]:
    if base not in st.session_state:
        st.session_state[base] = None

st.subheader("📂 Upload das Bases")
educapi_file = st.file_uploader("Carregar Base Educapi", type=["xls", "xlsx", "csv"], key="educapi")
if educapi_file:
    st.session_state.educapi_base = carregar_arquivo(educapi_file)
    if st.session_state.educapi_base is not None:
        st.success("✅ Base Educapi carregada!")

comercial_file = st.file_uploader("Carregar Base Comercial", type=["xls", "xlsx", "csv"], key="comercial")
if comercial_file:
    st.session_state.comercial_base = carregar_arquivo(comercial_file)
    if st.session_state.comercial_base is not None:
        st.success("✅ Base Comercial carregada!")

painel_file = st.file_uploader("Carregar Base Painel", type=["xls", "xlsx", "csv"], key="painel")
if painel_file:
    st.session_state.painel_base = carregar_arquivo(painel_file)
    if st.session_state.painel_base is not None:
        st.success("✅ Base Painel carregada!")

def gerar_verificacao_unificada():
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
        st.error("❌ Faltam colunas obrigatórias (CPF, Nome ou Estado/UF) em alguma das bases.")
        return None

    # Usar um dicionário para acumular status por CPF
    inconsistencias_dict = {}

    for _, row in painel.iterrows():
        cpf = str(row[col_cpf_painel]).strip()
        nome_painel = str(row[col_nome_painel]).strip()

        educapi_aluno = educapi[educapi[col_cpf_educapi].astype(str).str.strip() == cpf]
        comercial_aluno = comercial[comercial[col_cpf_comercial].astype(str).str.strip() == cpf]

        status_list = []

        # Regra 1: CPF presente em ambas as bases
        if not educapi_aluno.empty and not comercial_aluno.empty:
            status_list.append("CPF presente em ambas as bases")

        # Regra 2: Nome divergente Educapi
        if not educapi_aluno.empty:
            nome_educapi = str(educapi_aluno.iloc[0][col_nome_educapi]).strip()
            if nome_educapi.lower() != nome_painel.lower():
                status_list.append("Nome cadastrado não bate no Painel")

        # Regra 2: Nome divergente Comercial
        if not comercial_aluno.empty:
            nome_comercial = str(comercial_aluno.iloc[0][col_nome_comercial]).strip()
            if nome_comercial.lower() != nome_painel.lower():
                status_list.append("Nome cadastrado não bate no Painel")

        # Regra 3: Plataforma errada Educapi (SP)
        if not educapi_aluno.empty:
            estado_educapi = str(educapi_aluno.iloc[0][col_estado_educapi]).strip().upper()
            if "SP" in estado_educapi:
                status_list.append("Cadastro em plataforma errada")

        # Regra 3: Plataforma errada Comercial (fora SP)
        if not comercial_aluno.empty:
            estado_comercial = str(comercial_aluno.iloc[0][col_estado_comercial]).strip().upper()
            if "SP" not in estado_comercial:
                status_list.append("Cadastro em plataforma errada")

        # Regra 4: CPF não encontrado
        if educapi_aluno.empty and comercial_aluno.empty:
            status_list.append("CPF não encontrado")

        if status_list:
            # Unificar status em string separada por vírgulas, removendo duplicados
            status_unificado = ", ".join(sorted(set(status_list)))

            # Incluir a linha original com a coluna Status atualizada
            inconsistencias_dict[cpf] = {**row.to_dict(), "Status": status_unificado}

    # Converter o dicionário de inconsistências para DataFrame
    verificar_df = pd.DataFrame(list(inconsistencias_dict.values()))

    return verificar_df

if all([st.session_state.educapi_base, st.session_state.comercial_base, st.session_state.painel_base]):
    st.session_state.verificar = gerar_verificacao_unificada()

if st.session_state.verificar is not None and not st.session_state.verificar.empty:
    st.subheader("📋 Base de Inconsistências - VERIFICAR")
    st.dataframe(st.session_state.verificar, use_container_width=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        st.session_state.verificar.to_excel(writer, index=False, sheet_name="Verificar")
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Baixar Base VERIFICAR (Excel)",
        data=excel_data,
        file_name="verificar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

