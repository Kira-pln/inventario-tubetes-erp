import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# ===============================
# CONFIGURAÇÃO GERAL
# ===============================
st.set_page_config(
    page_title="Inventário de Tubetes",
    layout="wide"
)

# ===============================
# ESTILO ERP
# ===============================
st.markdown("""
<style>
.stApp { background-color: #f4f6f8; }
h1, h2, h3 { color: #1f2937; }
[data-testid=stSidebar] { background-color: #111827; }
[data-testid=stSidebar] * { color: #e5e7eb; }

.card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# ===============================
# ARQUIVOS
# ===============================
ARQ_INV = "inventario.csv"
ARQ_TIPOS = "tipos_tubetes.csv"

# ===============================
# FUNÇÕES
# ===============================
def carregar_csv(path, colunas):
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=True)
    return pd.DataFrame(columns=colunas)

def salvar_csv(df, path):
    df.to_csv(path, index=False)

# ===============================
# DADOS
# ===============================
tipos_df = carregar_csv(ARQ_TIPOS, ["Tipo", "Descricao", "Tempo Estufa (h)"])
inv_df = carregar_csv(ARQ_INV, [
    "Tipo","Descricao","Quantidade",
    "Entrada","Retirada Prevista",
    "Saida","Quantidade Saida","Umidade Saida"
])

st.session_state.setdefault("tipos", tipos_df)
st.session_state.setdefault("inventario", inv_df)

# ===============================
# MENU
# ===============================
menu = st.sidebar.radio(
    "Menu",
    ["Dashboard", "Cadastro", "Entrada", "Saída", "Relatórios"]
)

# ===============================
# DASHBOARD
# ===============================
if menu == "Dashboard":
    st.title("Dashboard Geral")

    col1, col2, col3 = st.columns(3)

    col1.metric("Tipos Cadastrados", len(st.session_state.tipos))
    col2.metric("Lotes em Estoque", st.session_state.inventario["Saida"].isna().sum())
    col3.metric("Quantidade Total", st.session_state.inventario["Quantidade"].sum())

# ===============================
# CADASTRO
# ===============================
elif menu == "Cadastro":
    st.title("Cadastro de Tipos")

    with st.form("cad_tipo"):
        tipo = st.text_input("Tipo")
        desc = st.text_area("Descrição")
        tempo = st.number_input("Tempo Máx. Estufa (h)", min_value=1)
        salvar = st.form_submit_button("Salvar")

    if salvar:
        novo = pd.DataFrame([{
            "Tipo": tipo,
            "Descricao": desc,
            "Tempo Estufa (h)": tempo
        }])
        st.session_state.tipos = pd.concat([st.session_state.tipos, novo], ignore_index=True)
        salvar_csv(st.session_state.tipos, ARQ_TIPOS)
        st.success("Tipo cadastrado.")

    st.dataframe(st.session_state.tipos, use_container_width=True)

# ===============================
# ENTRADA
# ===============================
elif menu == "Entrada":
    st.title("Entrada em Estufa")

    if st.session_state.tipos.empty:
        st.warning("Cadastre um tipo primeiro.")
    else:
        tipo = st.selectbox("Tipo", st.session_state.tipos["Tipo"])
        info = st.session_state.tipos.query("Tipo == @tipo").iloc[0]

        qtd = st.number_input("Quantidade", min_value=1)
        data = st.datetime_input("Entrada", datetime.now())

        if st.button("Registrar"):
            novo = pd.DataFrame([{
                "Tipo": tipo,
                "Descricao": info["Descricao"],
                "Quantidade": qtd,
                "Entrada": data,
                "Retirada Prevista": data + timedelta(hours=int(info["Tempo Estufa (h)"])),
                "Saida": None,
                "Quantidade Saida": None,
                "Umidade Saida": None
            }])
            st.session_state.inventario = pd.concat(
                [st.session_state.inventario, novo],
                ignore_index=True
            )
            salvar_csv(st.session_state.inventario, ARQ_INV)
            st.success("Entrada registrada.")

# ===============================
# SAÍDA
# ===============================
elif menu == "Saída":
    st.title("Saída")

    estoque = st.session_state.inventario.query("Saida.isna()", engine="python")

    if estoque.empty:
        st.warning("Sem estoque.")
    else:
        idx = st.selectbox("Lote", estoque.index)
        qtd = st.number_input(
            "Quantidade",
            min_value=1,
            max_value=int(estoque.loc[idx,"Quantidade"])
        )
        umidade = st.number_input("Umidade (%)", min_value=0, max_value=100)

        if datetime.now() < estoque.loc[idx,"Retirada Prevista"]:
            st.error("Ainda não liberado.")
        elif st.button("Confirmar Saída"):
            st.session_state.inventario.at[idx,"Quantidade"] -= qtd
            st.session_state.inventario.at[idx,"Saida"] = datetime.now()
            st.session_state.inventario.at[idx,"Quantidade Saida"] = qtd
            st.session_state.inventario.at[idx,"Umidade Saida"] = umidade
            salvar_csv(st.session_state.inventario, ARQ_INV)
            st.success("Saída registrada.")

# ===============================
# RELATÓRIOS
# ===============================
else:
    st.title("Relatórios")

    st.dataframe(st.session_state.inventario, use_container_width=True)

    st.download_button(
        "Exportar Excel",
        st.session_state.inventario.to_excel(index=False),
        "inventario.xlsx"
    )
