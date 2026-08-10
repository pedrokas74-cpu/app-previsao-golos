import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import pickle
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="AI Trading Bot", page_icon="🤖", layout="wide")
st.title("🤖 AI Trading: Veredicto do Algoritmo")

DICIONARIO_LIGAS = {
    'E0': 'Inglaterra - Premier League', 'E1': 'Inglaterra - Championship (D2)', 'E2': 'Inglaterra - League 1 (D3)', 'E3': 'Inglaterra - League 2 (D4)',
    'SC0': 'Escócia - Premiership', 'SC1': 'Escócia - Championship (D2)',
    'P1': 'Portugal - Primeira Liga',
    'SP1': 'Espanha - La Liga', 'SP2': 'Espanha - Segunda Divisão',
    'I1': 'Itália - Serie A', 'I2': 'Itália - Serie B',
    'D1': 'Alemanha - Bundesliga', 'D2': 'Alemanha - 2. Bundesliga',
    'F1': 'França - Ligue 1', 'F2': 'França - Ligue 2',
    'N1': 'Holanda - Eredivisie', 'B1': 'Bélgica - Pro League',
    'T1': 'Turquia - Super Lig', 'G1': 'Grécia - Super League'
}

@st.cache_data(show_spinner=False)
def carregar_dados(ficheiro_dados):
    if not os.path.exists(ficheiro_dados):
        return pd.DataFrame(), f"❌ Ficheiro '{ficheiro_dados}' não encontrado!"
    try:
        colunas_usar = ['Div', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HTHG', 'HTAG', 'HC', 'AC', 'HS', 'AS', 'HST', 'AST', 'HF', 'AF']
        if ficheiro_dados.endswith('.zip'):
            with zipfile.ZipFile(ficheiro_dados, 'r') as z:
                ficheiros_csv = [f for f in z.namelist() if f.endswith('.csv') and not f.startswith('__MACOSX')]
                if not ficheiros_csv: return pd.DataFrame(), "Erro: ZIP vazio."
                with z.open(ficheiros_csv[0]) as f:
                    try: df = pd.read_csv(f, usecols=colunas_usar, low_memory=True)
                    except ValueError: f.seek(0); df = pd.read_csv(f, low_memory=True)
        else:
            df = pd.read_excel(ficheiro_dados)
            
        df = df.rename(columns={
            'Div': 'Liga_Codigo', 'HomeTeam': 'Equipa_Casa', 'AwayTeam': 'Equipa_Fora',
            'HC': 'Cantos_Casa', 'AC': 'Cantos_Fora',
            'HS': 'Remates_Casa', 'AS': 'Remates_Fora', 'HST': 'Remates_Baliza_Casa', 'AST': 'Remates_Baliza_Fora',
            'HF': 'Faltas_Casa', 'AF': 'Faltas_Fora'
        })
        
        df = df[df['Liga_Codigo'].isin(DICIONARIO_LIGAS.keys())].copy()
        for col in ['Liga_Codigo', 'Equipa_Casa', 'Equipa_Fora']:
            if col in df.columns: df[col] = df[col].astype('category')
            
        colunas_num = ['Cantos_Casa', 'Cantos_Fora', 'Remates_Casa', 'Remates_Fora', 'Remates_Baliza_Casa', 'Remates_Baliza_Fora', 'Faltas_Casa', 'Faltas_Fora']
        for col in colunas_num:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['Liga'] = df['Liga_Codigo'].astype(str).map(DICIONARIO_LIGAS)
        df['Liga'] = df['Liga'].astype('category')
        return df, ""
    except Exception as e:
        return pd.DataFrame(), f"❌ Erro ao abrir os dados: {e}"

@st.cache_resource(show_spinner=False)
def carregar_cerebro_ia():
    if os.path.exists('cerebro_ia.pkl'):
        with open('cerebro_ia.pkl', 'rb') as f:
            return pickle.load(f)
    return None

# ==========================================
# BARRA LATERAL E CARREGAMENTO
# ==========================================
st.sidebar.header("1. Configuração do Jogo")
df_dados, mensagem_erro = carregar_dados('BD_A.zip')
modelos_ia = carregar_cerebro_ia()

if mensagem_erro: st.sidebar.error(mensagem_erro)
if not modelos_ia: st.sidebar.error("❌ Cérebro IA (cerebro_ia.pkl) não encontrado no servidor!")

if not df_dados.empty:
    lista_ligas = sorted(df_dados['Liga'].dropna().unique().astype(str))
    liga_selecionada = st.sidebar.selectbox("Campeonato:", lista_ligas)
    df_liga = df_dados[df_dados['Liga'] == liga_selecionada]
    
    lista_equipas = sorted(df_liga['Equipa_Casa'].dropna().unique().astype(str))
    jogo_hoje_casa = st.sidebar.selectbox("Equipa da Casa:", lista_equipas)
    
    lista_visitantes = [e for e in lista_equipas if e != jogo_hoje_casa]
    if not lista_visitantes: lista_visitantes = lista_equipas
    jogo_hoje_fora = st.sidebar.selectbox("Equipa Visitante:", lista_visitantes)
else:
    st.sidebar.warning("A ler os dados...")
    jogo_hoje_casa, jogo_hoje_fora, liga_selecionada = "Equipa A", "Equipa B", "Desconhecida"

st.sidebar.markdown("---")
botao_analisar = st.sidebar.button("Extrair Padrões (Gerar Dicas)", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.header("📁 Base de Dados Pessoal")
ficheiro_historico = 'minhas_analises_guardadas.csv'
if os.path.exists(ficheiro_historico):
    with open(ficheiro_historico, 'rb') as f:
        st.sidebar.download_button(label="📥 Descarregar Histórico", data=f.read(), file_name="bd_minhas_analises.csv", mime="text/csv", type="primary")

# ==========================================
# MOTOR IA E PREVISÕES
# ==========================================
if botao_analisar and not df_dados.empty and modelos_ia:
    with st.spinner('A IA está a consultar mais de 46.000 jogos para encontrar os padrões...'):
        
        hist_casa = df_dados[df_dados['Equipa_Casa'] == jogo_hoje_casa]
        hist_fora = df_dados[df_dados['Equipa_Fora'] == jogo_hoje_fora]
        
        # Obter médias estatísticas das equipas para alimentar o Cérebro
        avg_HS = hist_casa['Remates_Casa'].mean() if not hist_casa['Remates_Casa'].isna().all() else 10
        avg_AS = hist_fora['Remates_Fora'].mean() if not hist_fora['Remates_Fora'].isna().all() else 10
        avg_HST = hist_casa['Remates_Baliza_Casa'].mean() if not hist_casa['Remates_Baliza_Casa'].isna().all() else 4
        avg_AST = hist_fora['Remates_Baliza_Fora'].mean() if not hist_fora['Remates_Baliza_Fora'].isna().all() else 4
        avg_HF = hist_casa['Faltas_Casa'].mean() if not hist_casa['Faltas_Casa'].isna().all() else 12
        avg_AF = hist_fora['Faltas_Fora'].mean() if not hist_fora['Faltas_Fora'].isna().all() else 12
        avg_HC = hist_casa['Cantos_Casa'].mean() if not hist_casa['Cantos_Casa'].isna().all() else 5
        avg_AC = hist_fora['Cantos_Fora'].mean() if not hist_fora['Cantos_Fora'].isna().all() else 5
        
        X_novo = pd.DataFrame([[avg_HS, avg_AS, avg_HST, avg_AST, avg_HF, avg_AF, avg_HC, avg_AC]], 
                              columns=['HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HC', 'AC']).fillna(0)

        # A IA FAZ AS SUAS PREVISÕES
        previsoes_finais = {}
        # Mapeamento estético
        nomes_mercados = {
            'Over_15': 'Over 1.5 FT',
            'Over_25': 'Over 2.5 FT',
            'Under_25': 'Under 2.5 FT',
            'Under_35': 'Under 3.5 FT'
        }
        
        for alvo, modelo in modelos_ia.items():
            # Pegamos na probabilidade (índice 1 é a probabilidade do evento acontecer)
            probabilidade = modelo.predict_proba(X_novo)[0][1] * 100
            previsoes_finais[nomes_mercados[alvo]] = probabilidade
            
        sugestoes_ordenadas = sorted(previsoes_finais.items(), key=lambda item: item[1], reverse=True)
        top_2 = sugestoes_ordenadas[:2] 

        # Gravação Automática
        dados_exportar = pd.DataFrame({
            "Data": [datetime.now().strftime("%Y-%m-%d %H:%M")], "Liga": [liga_selecionada], "Jogo": [f"{jogo_hoje_casa} vs {jogo_hoje_fora}"],
            "Dica_1": [top_2[0][0]], "Prob_1(%)": [f"{top_2[0][1]:.1f}%"],
            "Dica_2": [top_2[1][0]], "Prob_2(%)": [f"{top_2[1][1]:.1f}%"]
        })
        if os.path.exists(ficheiro_historico): dados_exportar.to_csv(ficheiro_historico, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')
        else: dados_exportar.to_csv(ficheiro_historico, mode='w', header=True, index=False, sep=';', encoding='utf-8-sig')

        # ==========================================
        # INTERFACE VISUAL - EXTREMAMENTE LIMPA
        # ==========================================
        st.subheader(f"{jogo_hoje_casa} vs {jogo_hoje_fora}")
        
        st.info("A IA analisou as estatísticas intensivas de ataque, defesa e faltas destas equipas comparando-as com milhares de padrões de jogos passados, extraindo as dicas mais seguras.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_sug1, col_sug2 = st.columns(2)
        
        # Design Gigante da Probabilidade
        with col_sug1:
            st.markdown(f"<p style='font-size: 14px; color: #f1c40f;'>⭐ Melhor Aposta (Segurança)</p>", unsafe_allow_html=True)
            st.markdown(f"<h1 style='margin-bottom: 0rem; padding-bottom: 0rem;'>{top_2[0][0]}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 18px; color: #2ecc71; font-weight: bold;'>↑ {top_2[0][1]:.1f}% Probabilidade</p>", unsafe_allow_html=True)
            
        with col_sug2:
            st.markdown(f"<p style='font-size: 14px; color: #f1c40f;'>⭐⭐ Dica Secundária (Valor)</p>", unsafe_allow_html=True)
            st.markdown(f"<h1 style='margin-bottom: 0rem; padding-bottom: 0rem;'>{top_2[1][0]}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 18px; color: #2ecc71; font-weight: bold;'>↑ {top_2[1][1]:.1f}% Probabilidade</p>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 💾 Guardar Análise Singular")
        csv = dados_exportar.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button(
            label="📥 Descarregar Jogo (CSV)",
            data=csv,
            file_name=f"analise_veredicto_{jogo_hoje_casa}_{jogo_hoje_fora}.csv",
            mime='text/csv'
        )