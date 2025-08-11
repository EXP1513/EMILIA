import streamlit as st
import pandas as pd
import os
from io import BytesIO

# Configuração básica
st.set_page_config(page_title="Valida Matrícula", layout="wide")
st.title("📊 Valida Matrícula")

def normalize_col_names(df):
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df

# Função robusta de importação
def carregar_arquivo(file):
    if file is None:
        return None
    ext = os.path.splitext(file.name)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(file, encoding="utf-8", sep=";", header=1)
            return normalize_col_names(df)

        for engine in ["openpyxl", "pyxlsb", "odf", "xlrd"]:
            try:
                df = pd.read_excel(file, header=1, engine=engine)
                return normalize_col_names(df)
            except:
                pass

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

# Session states
for base in ["educapi_base", "comercial_base", "painel_base", "verificar"]:
    if base not in st.session_state:
        st.session_state[base] = None

# Uploads
st.subheader("📂 Envie suas bases:")

educapi_file = st.file_uploader("Base Educapi", type=None)
if educapi_file:
    st.session_state.educapi_base = carregar_arquivo(educapi_file)
    if st.session_state.educapi_base is not None:
        st.success("Base Educapi carregada.")

comercial_file = st.file_uploader("Base Comercial", type=None)
if comercial_file:
    st.session_state.comercial_base = carregar_arquivo(comercial_file)
    if st.session_state.comercial_base is not None:
        st.success("Base Comercial carregada.")

painel_file = st.file_uploader("Base Painel", type=None)
if painel_file:
    st.session_state.painel_base = carregar_arquivo(painel_file)
    if st.session_state.painel_base is not None:
        st.success("Base Painel carregada.")

# Função de verificação
def gerar_verificacao():
    educapi = st.session_state.educapi_base
    comercial = st.session_state.comercial_base
    painel = st.session_state.painel_base

    # Identificar colunas importantes
    col_cpf_painel = next((c for c in painel.columns if "cpf" in c), None)
    col_estado_painel = next((c for c in painel.columns if "estado" in c and "cobran" in c), None)
    col_status_painel = next((c for c in painel.columns if "status" in c), None)
    col_nome_cobranca = next((c for c in painel.columns if "nome completo" in c and "cobran" in c), None)

    col_cpf_educapi = next((c for c in educapi.columns if "cpf" in c), None)
    col_nome_educapi = next((c for c in educapi.columns if "nome" in c), None)

    col_cpf_comercial = next((c for c in comercial.columns if "cpf" in c), None)
    col_nome_comercial = next((c for c in comercial.columns if "nome" in c), None)

    if not all([col_cpf_painel, col_estado_painel, col_status_painel, col_nome_cobranca,
                col_cpf_educapi, col_nome_educapi,
                col_cpf_comercial, col_nome_comercial]):
        st.error("❌ Faltam colunas obrigatórias.")
        return None

    inconsistencias_dict = {}

    for _, row in painel.iterrows():
        cpf = str(row[col_cpf_painel] or "").strip()
        estado = str(row[col_estado_painel] or "").strip()
        status_pedido = str(row[col_status_painel] or "").strip()
        nome_cobranca = str(row[col_nome_cobranca] or "").strip()

        educapi_aluno = educapi[educapi[col_cpf_educapi].astype(str).str.strip() == cpf]
        comercial_aluno = comercial[comercial[col_cpf_comercial].astype(str).str.strip() == cpf]

        status_list = []

        # 1. Plataforma incorreta SP na Educapi
        if estado.lower() == "são paulo" and not educapi_aluno.empty:
            status_list.append("Cadastro feito na plataforma incorreta")

        # 2. Plataforma incorreta fora SP na Comercial
        if estado.lower() != "são paulo" and not comercial_aluno.empty:
            status_list.append("Cadastro feito na plataforma incorreta")

        # 3. Status incorreto Comercial
        if not comercial_aluno.empty and status_pedido != "Matricula Liberada SP":
            status_list.append("Status incorreto (Comercial)")

        # 4. Status incorreto Educapi
        if not educapi_aluno.empty and status_pedido != "Matricula Liberada EDUCAPI":
            status_list.append("Status incorreto (Educapi)")

        # 5. Nome divergente (Educapi)
        if not educapi_aluno.empty:
            nome_educapi = str(educapi_aluno.iloc[0][col_nome_educapi] or "").strip()
            if nome_cobranca.lower() != nome_educapi.lower():
                status_list.append("Nome divergente")

        # 5b. Nome divergente (Comercial)
        if not comercial_aluno.empty:
            nome_comercial = str(comercial_aluno.iloc[0][col_nome_comercial] or "").strip()
            if nome_cobranca.lower() != nome_comercial.lower():
                status_list.append("Nome divergente")

        if status_list:
            inconsistencias_dict[cpf] = {**row.to_dict(), "Status": " / ".join(sorted(set(status_list)))}

    return pd.DataFrame(list(inconsistencias_dict.values()))

# Gera automaticamente
if all([
    st.session_state.educapi_base is not None,
    st.session_state.comercial_base is not None,
    st.session_state.painel_base is not None
]):
    st.session_state.verificar = gerar_verificacao()

# Exibe e permite exportar
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



