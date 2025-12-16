import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import io

# ======================================================
# CONFIGURAÇÃO GERAL
# ======================================================
st.set_page_config(
    page_title="Inventário de Tubetes",
    layout="wide"
)

ARQ_INV = "inventario.csv"
ARQ_TIPOS = "tipos_tubetes.csv"

# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================
def carregar_csv(arquivo, colunas, datas=None):
    if os.path.exists(arquivo):
        return pd.read_csv(arquivo, parse_dates=datas)
    return pd.DataFrame(columns=colunas)

def salvar_csv(df, arquivo):
    df.to_csv(arquivo, index=False)

# ======================================================
# CARGA DE DADOS
# ======================================================
tipos_df = carregar_csv(
    ARQ_TIPOS,
    ["Tipo", "Descricao", "Tempo Estufa (h)"]
)

inv_df = carregar_csv(
    ARQ_INV,
    [
        "Tipo",
        "Descricao",
        "Quantidade",
        "Entrada",
        "Retirada Prevista",
        "Saida",
        "Quantidade Saida",
        "Umidade Saida"
    ],
    datas=["Entrada", "Retirada Prevista", "Saida"]
)

st.session_state.setdefault("tipos", tipos_df)
st.session_state.setdefault("inventario", inv_df)

# ======================================================
# MENU PRINCIPAL (PADRÃO ERP)
# ======================================================
pagina = st.sidebar.radio(
    "Menu Principal",
    [
        "Cadastro de Tubetes",
        "Entrada em Estufa",
        "Saída da Estufa",
        "Relatórios e Exportação"
    ]
)

# ======================================================
# CADASTRO DE TUBETES
# ======================================================
if pagina == "Cadastro de Tubetes":
    st.title("Cadastro de Tipos de Tubetes")

    col1, col2 = st.columns(2)

    with col1:
        tipo = st.text_input("Tipo do Tubete")
        tempo = st.number_input(
            "Tempo máximo na estufa (horas)",
            min_value=1,
            step=1,
            help="Tempo mínimo necessário para liberação"
        )

    with col2:
        descricao = st.text_area("Descrição do Tubete")

    if st.button("Salvar Tipo"):
        novo = pd.DataFrame([{
            "Tipo": tipo,
            "Descricao": descricao,
            "Tempo Estufa (h)": tempo
        }])

        st.session_state.tipos = pd.concat(
            [st.session_state.tipos, novo],
            ignore_index=True
        )
        salvar_csv(st.session_state.tipos, ARQ_TIPOS)
        st.success("Tipo cadastrado com sucesso")

    st.subheader("Tipos Cadastrados")
    st.dataframe(st.session_state.tipos, use_container_width=True)

# ======================================================
# ENTRADA EM ESTUFA
# ======================================================
elif pagina == "Entrada em Estufa":
    st.title("Entrada de Tubetes na Estufa")

    if st.session_state.tipos.empty:
        st.warning("Cadastre um tipo de tubete primeiro.")
    else:
        tipo_sel = st.selectbox(
            "Tipo de Tubete",
            st.session_state.tipos["Tipo"]
        )

        tipo_info = st.session_state.tipos.query(
            "Tipo == @tipo_sel"
        ).iloc[0]

        st.info(
            f"Descrição: {tipo_info['Descricao']} | "
            f"Tempo estufa: {tipo_info['Tempo Estufa (h)']}h"
        )

        col1, col2 = st.columns(2)
        with col1:
            data_entrada = st.datetime_input(
                "Data e hora da entrada",
                datetime.now()
            )
        with col2:
            quantidade = st.number_input(
                "Quantidade",
                min_value=1,
                step=1
            )

        retirada_prev = data_entrada + timedelta(
            hours=int(tipo_info["Tempo Estufa (h)"])
        )

        if st.button("Registrar Entrada"):
            novo = pd.DataFrame([{
                "Tipo": tipo_sel,
                "Descricao": tipo_info["Descricao"],
                "Quantidade": quantidade,
                "Entrada": data_entrada,
                "Retirada Prevista": retirada_prev,
                "Saida": pd.NaT,
                "Quantidade Saida": None,
                "Umidade Saida": None
            }])

            st.session_state.inventario = pd.concat(
                [st.session_state.inventario, novo],
                ignore_index=True
            )
            salvar_csv(st.session_state.inventario, ARQ_INV)
            st.success("Entrada registrada com sucesso")

# ======================================================
# SAÍDA DA ESTUFA
# ======================================================
elif pagina == "Saída da Estufa":
    st.title("Saída de Tubetes da Estufa")

    estoque = st.session_state.inventario[
        st.session_state.inventario["Saida"].isna()
    ]

    if estoque.empty:
        st.warning("Não há tubetes disponíveis.")
    else:
        tipo_sel = st.selectbox(
            "Tipo de Tubete",
            estoque["Tipo"].unique()
        )

        estoque_tipo = estoque.query("Tipo == @tipo_sel")

        idx = st.selectbox(
            "Lote",
            estoque_tipo.index,
            format_func=lambda i: (
                f"Entrada: "
                f"{estoque_tipo.loc[i,'Entrada'].strftime('%d/%m/%Y %H:%M')} | "
                f"Qtd: {estoque_tipo.loc[i,'Quantidade']}"
            )
        )

        liberacao = estoque_tipo.loc[idx, "Retirada Prevista"]

        st.info(
            f"Liberação após: {liberacao.strftime('%d/%m/%Y %H:%M')}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            data_saida = st.datetime_input(
                "Data da retirada",
                datetime.now()
            )
        with col2:
            qtd_saida = st.number_input(
                "Quantidade retirada",
                min_value=1,
                max_value=int(
                    estoque_tipo.loc[idx, "Quantidade"]
                ),
                step=1
            )
        with col3:
            umidade = st.number_input(
                "Umidade (%)",
                min_value=0,
                max_value=100,
                step=1
            )

        if datetime.now() < liberacao:
            st.error("Retirada ainda não liberada")
        else:
            if st.button("Registrar Saída"):
                st.session_state.inventario.at[idx, "Quantidade"] -= qtd_saida
                st.session_state.inventario.at[idx, "Saida"] = data_saida
                st.session_state.inventario.at[idx, "Quantidade Saida"] = qtd_saida
                st.session_state.inventario.at[idx, "Umidade Saida"] = umidade
                salvar_csv(st.session_state.inventario, ARQ_INV)
                st.success("Saída registrada com sucesso")

# ======================================================
# RELATÓRIOS E EXPORTAÇÃO
# ======================================================
else:
    st.title("Relatórios e Exportação")

    df = st.session_state.inventario.copy()

    estoque = df[df["Saida"].isna()]
    estoque["Pode Retirar"] = estoque["Retirada Prevista"].apply(
        lambda x: "Sim" if datetime.now() >= x else "Não"
    )

    st.subheader("Inventário Atual")
    st.dataframe(
        estoque[
            [
                "Tipo",
                "Descricao",
                "Quantidade",
                "Entrada",
                "Retirada Prevista",
                "Pode Retirar"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Histórico de Saídas")
    saidas = df[df["Saida"].notna()]
    st.dataframe(
        saidas[
            [
                "Tipo",
                "Descricao",
                "Entrada",
                "Saida",
                "Quantidade Saida",
                "Umidade Saida"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Exportar para Excel")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventario")

    st.download_button(
        label="Exportar Inventário",
        data=buffer.getvalue(),
        file_name="inventario_tubetes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
