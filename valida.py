import streamlit as st
import pandas as pd

st.set_page_config(page_title="Valida Matrícula", layout="wide")
st.title("📊 Valida Matrícula - Verificação Completa")
st.write("Importe as bases Educapi, Comercial e Painel para validação cruzada.")

def normalize_col_names(df):
    df.columns = [col.strip().lower() for col in df.columns]
    return df

# Upload dos arquivos
arquivos = st.file_uploader(
    "Selecione os arquivos (Educapi, Comercial, Painel) em Excel ou CSV",
    type=["xls", "xlsx", "csv"],
    accept_multiple_files=True
)

if arquivos:
    bases = {}
    for arquivo in arquivos:
        nome = arquivo.name.lower()
        try:
            if nome.endswith(".csv"):
                df = pd.read_csv(arquivo, encoding="utf-8", sep=";", header=1)  # Ignora a primeira linha e usa A2 como cabeçalho
            else:
                df = pd.read_excel(arquivo, header=1)
            bases[nome] = df
            st.success(f"Arquivo '{arquivo.name}' carregado!")
        except Exception as e:
            st.error(f"Erro ao carregar arquivo {arquivo.name}: {e}")

    # Confere se as 3 bases foram enviadas
    required_bases = ["educapi", "comercial", "painel"]
    if all(any(b in k for k in bases.keys()) for b in required_bases):
        
        # Identificar as bases
        educapi_base = normalize_col_names(next(v for k, v in bases.items() if "educapi" in k))
        comercial_base = normalize_col_names(next(v for k, v in bases.items() if "comercial" in k))
        painel_base = normalize_col_names(next(v for k, v in bases.items() if "painel" in k))

        # Identificar colunas importantes
        col_cpf_painel = next((col for col in painel_base.columns if "cpf" in col), None)
        col_nome_painel = next((col for col in painel_base.columns if "nome" in col), None)

        col_cpf_educapi = next((col for col in educapi_base.columns if "cpf" in col), None)
        col_estado_educapi = next((col for col in educapi_base.columns if "estado" in col or "uf" in col), None)
        col_nome_educapi = next((col for col in educapi_base.columns if "nome" in col), None)

        col_cpf_comercial = next((col for col in comercial_base.columns if "cpf" in col), None)
        col_estado_comercial = next((col for col in comercial_base.columns if "estado" in col or "uf" in col), None)
        col_nome_comercial = next((col for col in comercial_base.columns if "nome" in col), None)

        if not all([col_cpf_painel, col_nome_painel,
                    col_cpf_educapi, col_estado_educapi, col_nome_educapi,
                    col_cpf_comercial, col_estado_comercial, col_nome_comercial]):
            st.error("Faltam colunas obrigatórias (CPF, Nome ou Estado/UF) em alguma das bases.")
        else:
            verificar = pd.DataFrame()

            # Loop em cada aluno do Painel
            for _, row in painel_base.iterrows():
                cpf = str(row[col_cpf_painel]).strip()
                nome_painel = str(row[col_nome_painel]).strip()

                educapi_aluno = educapi_base[educapi_base[col_cpf_educapi].astype(str).str.strip() == cpf]
                comercial_aluno = comercial_base[comercial_base[col_cpf_comercial].astype(str).str.strip() == cpf]

                encontrado = False

                # 🔹 Regra: CPF presente em ambas as bases
                if not educapi_aluno.empty and not comercial_aluno.empty:
                    inconsistencia = row.to_dict()
                    inconsistencia["Status"] = "CPF presente em ambas as bases"
                    verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)
                    encontrado = True

                # 🔹 Nome divergente na Educapi
                if not educapi_aluno.empty:
                    encontrado = True
                    nome_educapi = str(educapi_aluno.iloc[0][col_nome_educapi]).strip()
                    if nome_educapi.lower() != nome_painel.lower():
                        inconsistencia = row.to_dict()
                        inconsistencia["Status"] = "Nome cadastrado não bate no Painel"
                        verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

                # 🔹 Nome divergente na Comercial
                if not comercial_aluno.empty:
                    encontrado = True
                    nome_comercial = str(comercial_aluno.iloc[0][col_nome_comercial]).strip()
                    if nome_comercial.lower() != nome_painel.lower():
                        inconsistencia = row.to_dict()
                        inconsistencia["Status"] = "Nome cadastrado não bate no Painel"
                        verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

                # 🔹 Plataforma errada (SP)
                if not educapi_aluno.empty:
                    estado_educapi = str(educapi_aluno.iloc[0][col_estado_educapi]).strip().upper()
                    if "SP" in estado_educapi:
                        inconsistencia = row.to_dict()
                        inconsistencia["Status"] = "Cadastro em plataforma errada"
                        verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

                # 🔹 Plataforma errada (fora de SP)
                if not comercial_aluno.empty:
                    estado_comercial = str(comercial_aluno.iloc[0][col_estado_comercial]).strip().upper()
                    if "SP" not in estado_comercial:
                        inconsistencia = row.to_dict()
                        inconsistencia["Status"] = "Cadastro em plataforma errada"
                        verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

                # 🔹 CPF não encontrado
                if educapi_aluno.empty and comercial_aluno.empty:
                    inconsistencia = row.to_dict()
                    inconsistencia["Status"] = "CPF não encontrado"
                    verificar = pd.concat([verificar, pd.DataFrame([inconsistencia])], ignore_index=True)

            # Exibe e permite baixar
            if not verificar.empty:
                st.subheader("📋 Base de Inconsistências - VERIFICAR")
                st.dataframe(verificar, use_container_width=True)
                csv = verificar.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Base VERIFICAR (CSV)", data=csv, file_name="verificar.csv", mime="text/csv")
            else:
                st.success("Nenhuma inconsistência encontrada.")

    else:
        st.warning("Você precisa enviar as 3 bases: Educapi, Comercial e Painel.")
