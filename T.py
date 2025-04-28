# Função de fazer gestão de tempo e procedimentos de forma genérica
# Autor: Luiz Furlanetti 
# Versão: 1.0.6

import sqlite3
import pandas as pd
import streamlit as st
import os
import altair as alt
from datetime import datetime, timedelta
from babel.dates import format_date

# Configuração da página
st.set_page_config(
    page_title="Base",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Datas da semana atual
hoje = datetime.now().date()
inicio = hoje - timedelta(days=hoje.weekday())
fim = inicio + timedelta(days=4)

# Formata datas completas em português
inicio_formatado = format_date(inicio, format='full', locale='pt_BR')
fim_formatado = format_date(fim, format='full', locale='pt_BR')

st.sidebar.title(f"Semana: {inicio_formatado} até {fim_formatado}")

# Caminho do banco
db_path = os.path.join(os.getcwd(), 'memoria.db')
print("Banco em uso:", db_path)

# ----------------------
# Função para inicializar o banco (cria as tabelas se não existirem)
# ----------------------
def get_connection():
    return sqlite3.connect(db_path, check_same_thread=False)

def inicializar_banco():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS disciplinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                disciplina TEXT
            );
            CREATE TABLE IF NOT EXISTS disponibilidade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                dia TEXT NOT NULL,
                hora TEXT NOT NULL,
                atividade TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS missoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                missao TEXT NOT NULL,
                concluida BOOLEAN NOT NULL
            );
        """)
        conn.commit()

inicializar_banco()

# ----------------------
# Funções de acesso ao banco
# ----------------------
def carregar_disciplinas():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM disciplinas")
        return [row[0] for row in cur.fetchall()]

def salvar_disciplina(nome):
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO disciplinas (nome) VALUES (?)", (nome,))
        conn.commit()

def adicionar_funcionario(nome, disciplina):
    with get_connection() as conn:
        conn.execute("INSERT INTO funcionarios (nome, disciplina) VALUES (?, ?)", (nome, disciplina))
        tempos = conn.execute("SELECT hora FROM disponibilidade WHERE nome = ? LIMIT 15", ("Geral",)).fetchall()
        tempos = [t[0] for t in tempos] if tempos else [f"{h:02d}:00 as {h+1:02d}:00" for h in range(8, 23)]
        for dia in ['segunda', 'terca', 'quarta', 'quinta', 'sexta']:
            for hora in tempos:
                conn.execute("INSERT INTO disponibilidade (nome, dia, hora, atividade) VALUES (?, ?, ?, 'Livre')",
                             (nome, dia, hora))
        conn.execute("INSERT INTO missoes (nome, missao, concluida) VALUES (?, '', 0)", (nome,))
        conn.commit()

def carregar_disponibilidade(nome):
    with get_connection() as conn:
        df = pd.read_sql_query("""
            SELECT dia, hora, atividade FROM disponibilidade
            WHERE nome = ?
        """, conn, params=(nome,))
        return df

def salvar_disponibilidade(nome, df):
    with get_connection() as conn:
        for _, row in df.iterrows():
            for dia in ['segunda', 'terca', 'quarta', 'quinta', 'sexta']:
                conn.execute("""
                    UPDATE disponibilidade
                    SET atividade = ?
                    WHERE nome = ? AND dia = ? AND hora = ?
                """, (row[dia], nome, dia, row['Tempo']))
        conn.commit()

def carregar_missoes(nome):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, missao FROM missoes WHERE nome = ? AND concluida = 0 AND missao != ''", (nome,))
        return cur.fetchall()

def carregar_missoes_concluidas(nome):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, missao FROM missoes WHERE nome = ? AND concluida = 1", (nome,))
        return cur.fetchall()

def adicionar_missao(nome, missao):
    with get_connection() as conn:
        conn.execute("INSERT INTO missoes (nome, missao, concluida) VALUES (?, ?, 0)", (nome, missao))
        conn.commit()

def concluir_missao(missao_id):
    with get_connection() as conn:
        conn.execute("UPDATE missoes SET concluida = 1 WHERE id = ?", (missao_id,))
        conn.commit()

def apagar_missao(missao_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM missoes WHERE id = ?", (missao_id,))
        conn.commit()

def listar_funcionarios_por_disciplina(disc):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM funcionarios WHERE disciplina = ?", (disc,))
        return [row[0] for row in cur.fetchall()]

# ----------------------
# Interface Streamlit
# ----------------------
st.sidebar.header("📋 Cadastros")

with st.sidebar.expander("➕ Cadastrar Disciplina"):
    nova_disc = st.text_input("Nova Disciplina", key="nova_disc")
    if st.button("Adicionar Disciplina", key="btn_add_disc"):
        if nova_disc:
            salvar_disciplina(nova_disc)
            st.success(f"Disciplina '{nova_disc}' adicionada!")

with st.sidebar.expander("➕ Cadastrar Funcionário"):
    disciplinas = carregar_disciplinas()
    novo_nome = st.text_input("Nome do Funcionário", key="novo_func")
    disc_sel = st.selectbox("Disciplina", disciplinas, key="disc_func")
    if st.button("Adicionar Funcionário", key="btn_add_func"):
        if novo_nome:
            adicionar_funcionario(novo_nome, disc_sel)
            st.success(f"Funcionário '{novo_nome}' cadastrado em {disc_sel}!")

disciplinas = carregar_disciplinas()
disc_sel = st.sidebar.selectbox("Disciplina", disciplinas, key="disc_sel")
funcionarios = listar_funcionarios_por_disciplina(disc_sel)
func_sel = st.sidebar.radio("Funcionário", funcionarios, key="func_sel")

df_disp = carregar_disponibilidade(func_sel)
df_pivot = df_disp.pivot_table(index="hora", columns="dia", values="atividade", aggfunc="first").reset_index()
df_pivot.rename(columns={"hora": "Tempo"}, inplace=True)
dias_ordem = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']

tab1, tab2, tab3 = st.tabs(["Missões", "Disponibilidade", "Concluído"])

with tab1:
    col1, col2 = st.columns([2, 2])
    with col1:
        st.subheader(f"Disponibilidade de {func_sel}")
        df_melt = df_pivot.melt(id_vars=["Tempo"], value_vars=dias_ordem, var_name="Dia", value_name="Atividade")
        chart = (
            alt.Chart(df_melt)
            .mark_rect()
            .encode(
                x=alt.X("Dia:N", sort=dias_ordem),
                y=alt.Y("Tempo:N"),
                color=alt.Color("Atividade:N"),
                tooltip=["Dia", "Tempo", "Atividade"]
            ).properties(width=700, height=500)
        )
        st.altair_chart(chart, use_container_width=True)
    with col2:
        st.markdown("### Nova Missão")
        prompt = st.chat_input("Digite uma nova missão...")
        if prompt:
            adicionar_missao(func_sel, prompt)
        missoes = carregar_missoes(func_sel)
        if missoes:
            st.markdown("### Missões Pendentes")
            for mid, m in missoes:
                if st.toggle(m, key=f"missao_{mid}"):
                    concluir_missao(mid)

with tab2:
    st.subheader("Editar Disponibilidade Semanal")
    edited_df = st.data_editor(
        df_pivot,
        use_container_width=True,
        num_rows="fixed",
        row_height=35,
        column_config={"Tempo": st.column_config.Column(label="Tempo", disabled=True)}
    )
    if st.button("Salvar"):
        salvar_disponibilidade(func_sel, edited_df)
        st.success("Dados salvos com sucesso!")

with tab3:
    st.subheader('Concluído')
    missoes_concluidas = carregar_missoes_concluidas(func_sel)
    if missoes_concluidas:
        for mid, m in missoes_concluidas:
            if st.toggle(m, key=f"deletar_{mid}"):
                apagar_missao(mid)
                st.success("Missão removida.")

# Corrigir caminho para a imagem
st.sidebar.image('32443B9A-0511-49A5-BBA6-4B5C0A836BA8.PNG')
