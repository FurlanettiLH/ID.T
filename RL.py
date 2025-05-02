import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy import stats
from datetime import datetime, timedelta
import pandas as pd
import re
from babel.dates import format_date

# Configuração da página
st.set_page_config(
    page_title="Regressão Linear",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Datas para o título
hoje = datetime.now().date()
inicio = hoje - timedelta(days=hoje.weekday())  # Segunda-feira
fim = inicio + timedelta(days=4)  # Sexta-feira

# Título da página com Babel para data
mes_formatado = format_date(hoje, format='MMMM', locale='pt_BR')
st.title(f"Física Experimental III - Semana: {inicio.day} a {fim.day} de {mes_formatado}")

# Função para calcular a regressão linear
def regressao_linear(x, y):
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return slope, intercept, r_value, p_value, std_err

# Função para extrair valor e erro de uma célula no formato "5,0 ± 0,2"
def extrair_valor_erro(celula):
    if isinstance(celula, str):
        match = re.match(r'([\d.,]+)\s*[±\+\-]\s*([\d.,]+)', celula)
        if match:
            valor = float(match.group(1).replace(',', '.'))
            erro = float(match.group(2).replace(',', '.'))
            return valor, erro
    try:
        return float(str(celula).replace(',', '.')), None
    except:
        return None, None

st.title(f'Experimento:  ')
st.sidebar.subheader('Insira os dados ou envie um arquivo')

uploaded_file = st.sidebar.file_uploader("Faça upload do arquivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        dados_excel = pd.read_excel(uploaded_file)
        st.sidebar.success("Arquivo carregado com sucesso!")

        st.write("Prévia dos dados carregados:")
        st.dataframe(dados_excel.head())

        colunas_disponiveis = list(dados_excel.columns)
        coluna_x = st.sidebar.selectbox("Coluna com valores de X (ou X ± erro)", colunas_disponiveis)
        coluna_y = st.sidebar.selectbox("Coluna com valores de Y (ou Y ± erro)", colunas_disponiveis)

        inverter_y = st.sidebar.checkbox("Usar 1/Y ao invés de Y?")

        valores_x = []
        erros_x = []
        valores_y = []
        erros_y = []

        for x_raw, y_raw in zip(dados_excel[coluna_x], dados_excel[coluna_y]):
            x_val, x_err = extrair_valor_erro(x_raw)
            y_val, y_err = extrair_valor_erro(y_raw)
            valores_x.append(x_val)
            erros_x.append(x_err)
            valores_y.append(y_val)
            erros_y.append(y_err)

        x_values = np.array(valores_x, dtype=float)
        y_values = np.array(valores_y, dtype=float)
        erro_x = np.array(erros_x, dtype=float) if any(erros_x) else None
        erro_y = np.array(erros_y, dtype=float) if any(erros_y) else None

        if inverter_y:
            y_values = 1 / y_values

        if st.sidebar.button('Plotar gráfico e calcular regressão'):
            slope, intercept, r_value, p_value, std_err = regressao_linear(x_values, y_values)

            st.subheader(f'Regressão Linear: Y = {slope:.2f} * X + {intercept:.2f}')
            st.write(f'Coeficiente angular (A): {slope:.2f}')
            st.write(f'Coeficiente linear (B): {intercept:.2f}')
            st.write(f'R²: {r_value**2:.2f}')
            st.write(f'Erro padrão da regressão: {std_err:.2f}')
            st.write(f'Valor p da regressão: {p_value:.3f}')

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_values, y=y_values, mode='markers',
                                     error_x=dict(type='data', array=erro_x, visible=True) if erro_x is not None else None,
                                     error_y=dict(type='data', array=erro_y, visible=True) if erro_y is not None else None,
                                     marker=dict(color='#FF5733', size=10), name='Pontos Experimentais'))

            x_fit = np.linspace(min(x_values), max(x_values), 100)
            y_fit = slope * x_fit + intercept
            fig.add_trace(go.Scatter(x=x_fit, y=y_fit, mode='lines',
                                     line=dict(color='#1E90FF', width=2),
                                     name=f'Reta de Ajuste'))

            fig.update_layout(
                title="Regressão Linear - Dados do Excel",
                xaxis_title=coluna_x,
                yaxis_title="1/" + coluna_y if inverter_y else coluna_y,
                plot_bgcolor='#121212',
                paper_bgcolor='#121212',
                font=dict(color="white"),
                legend=dict(title='Legenda', font=dict(color='white')),
                margin=dict(l=40, r=40, b=40, t=40),
                xaxis=dict(showgrid=True, gridcolor='gray', zeroline=True, showline=True),
                yaxis=dict(showgrid=True, gridcolor='gray', zeroline=True, showline=True)
            )

            st.plotly_chart(fig)

    except Exception as e:
        st.sidebar.error(f"Erro ao processar o arquivo: {e}")