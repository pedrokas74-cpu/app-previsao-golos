import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E CACHE
# ==========================================
st.set_page_config(page_title="Previsão de Golos", page_icon="⚽", layout="wide")
st.title("⚽ Dashboard Inteligente de Golos (Monte Carlo)")

# Dicionário para traduzir as Ligas
DICIONARIO_LIGAS = {
    'E0': 'Inglaterra - Premier League', 'E1': 'Inglaterra - Championship', 'E2': 'Inglaterra - League 1', 'E3': 'Inglaterra - League 2',
    'P1': 'Portugal - Primeira Liga',
    'SP1': 'Espanha - La Liga', 'SP2': 'Espanha - Segunda Divisão',
    'I1': 'Itália - Serie A', 'I2': 'Itália - Serie B',
    'D1': 'Alemanha - Bundesliga', 'D2': 'Alemanha - 2. Bundesliga',
    'F1': 'França - Ligue 1', 'F2': 'França - Ligue 2',
    'N1': 'Holanda - Eredivisie',
    'B1': 'Bélgica - Pro League',
    'T1': 'Turquia - Super Lig',
    'G1': 'Grécia - Super League',
    'SC0': 'Escócia - Premiership',
    'ARG': 'Argentina - Primera División',
    'BRA': 'Brasil - Série A',
    'JPN': 'Japão - J1 League',
    'USA': 'EUA - MLS',
    'MEX': 'México - Liga MX'
}

@st.cache_data(show_spinner=False)
def carregar_dados(ficheiro_dados, is_historico):
    ficheiro_real = None
    if os.path.exists(ficheiro_dados):
        ficheiro_real = ficheiro_dados
    elif is_historico and os.path.exists('BD_A.csv'):
        ficheiro_real = 'BD_A.csv'
        
    if ficheiro_real:
        try:
            if ficheiro_real.endswith('.zip') or ficheiro_real.endswith('.csv'):
                df = pd.read_csv(ficheiro_real, low_memory=False)
            else:
                df = pd.read_excel(ficheiro_real)
            
            df = df.rename(columns={
                'Div': 'Liga_Codigo',
                'HomeTeam': 'Equipa_Casa',
                'AwayTeam': 'Equipa_Fora',
                'HTHG': 'Golos_HT_Casa',
                'HTAG': 'Golos_HT_Fora',
                'FTHG': 'Golos_FT_Casa',
                'FTAG': 'Golos_FT_Fora'
            })
            
            if 'Liga_Codigo' not in df.columns:
                df['Liga_Codigo'] = 'Competição Geral'
            
            # Aplica a tradução dos nomes
            df['Liga'] = df['Liga_Codigo'].map(DICIONARIO_LIGAS).fillna(df['Liga_Codigo'])
                
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

# ==========================================
# BARRA LATERAL - FONTES E FILTROS AUTOMÁTICOS
# ==========================================
st.sidebar.header("1. Fonte de Dados")
opcao_bd = st.sidebar.radio("Seleciona a Base de Dados:", ["BD_A (Histórico Completo)", "BD_B (Recente)"])

is_historico = opcao_bd == "BD_A (Histórico Completo)"
ficheiro_dados = 'BD_A.zip' if is_historico else 'BD_B.xlsx'

df_dados = carregar_dados(ficheiro_dados, is_historico)

st.sidebar.header("2. Configuração do Jogo")
if not df_dados.empty:
    lista_ligas = sorted(df_dados['Liga'].dropna().unique().astype(str))
    liga_selecionada = st.sidebar.selectbox("Campeonato (Liga):", lista_ligas)
    df_liga = df_dados[df_dados['Liga'] == liga_selecionada]
    
    lista_equipas = sorted(df_liga['Equipa_Casa'].dropna().unique().astype(str))
    jogo_hoje_casa = st.sidebar.selectbox("Equipa da Casa:", lista_equipas)
    
    lista_visitantes = [e for e in lista_equipas if e != jogo_hoje_casa]
    if not lista_visitantes: 
        lista_visitantes = lista_equipas
    jogo_hoje_fora = st.sidebar.selectbox("Equipa Visitante:", lista_visitantes)
else:
    st.sidebar.warning("Base de dados não encontrada para ler as equipas.")
    jogo_hoje_casa, jogo_hoje_fora, liga_selecionada = "Equipa A", "Equipa B", "Desconhecida"

st.sidebar.markdown("---")
botao_analisar = st.sidebar.button("Analisar Jogo e Odds", type="primary", use_container_width=True)
n_simulacoes = st.sidebar.slider("Número de Simulações:", 1000, 50000, 10000)

st.sidebar.markdown("---")
st.sidebar.header("3. Comparador de Odds (Encontrar Valor)")
mercados_opcoes = [
    "1X2: Vitória Casa (1)", "1X2: Empate (X)", "1X2: Vitória Fora (2)", 
    "Over 0.5 HT", "Over 1.5 HT",
    "Over 1.5 FT", "Over 2.5 FT", "Over 3.5 FT", 
    "Under 2.5 FT", "Under 3.5 FT",
    "+ Golos na 1ª Parte", "Igualdade (HT = 2HT)", "+ Golos na 2ª Parte"
]
mercado_alvo = st.sidebar.selectbox("Mercado que queres testar:", mercados_opcoes)
odd_casa_apostas = st.sidebar.number_input("Odd da Casa de Apostas (ex: 1.90):", min_value=1.01, max_value=20.0, value=1.90, step=0.01)

# ==========================================
# MOTOR MATEMÁTICO
# ==========================================
if botao_analisar:
    with st.spinner(f'A processar cenários para {jogo_hoje_casa} vs {jogo_hoje_fora}...'):
        
        # Variáveis base
        media_ht_casa, media_ht_fora = 0.8, 0.5 
        media_ft_casa, media_ft_fora = 1.9, 1.2
        usou_exemplo = True
        aviso_sem_ht = False
        
        if not df_dados.empty:
            hist_casa = df_dados[df_dados['Equipa_Casa'] == jogo_hoje_casa]
            hist_fora = df_dados[df_dados['Equipa_Fora'] == jogo_hoje_fora]
            
            if not hist_casa.empty and not hist_fora.empty:
                media_ft_casa = hist_casa['Golos_FT_Casa'].mean()
                media_ft_fora = hist_fora['Golos_FT_Fora'].mean()
                usou_exemplo = False
                
                # VERIFICAÇÃO SE EXISTEM DADOS HT (Resolve o problema de Brasil/Japão)
                if hist_casa['Golos_HT_Casa'].isna().all() or hist_fora['Golos_HT_Fora'].isna().all():
                    aviso_sem_ht = True
                    # Estimação Estatística Global (45% golos HT / 55% golos 2HT)
                    media_ht_casa = media_ft_casa * 0.45
                    media_ht_fora = media_ft_fora * 0.45
                else:
                    media_ht_casa = hist_casa['Golos_HT_Casa'].mean()
                    media_ht_fora = hist_fora['Golos_HT_Fora'].mean()
        
        # Cálculo da 2ª Parte
        media_2ht_casa = max(0, media_ft_casa - media_ht_casa)
        media_2ht_fora = max(0, media_ft_fora - media_ht_fora)

        # Simulações de Poisson
        golos_ht_casa_sim = np.random.poisson(media_ht_casa, n_simulacoes)
        golos_ht_fora_sim = np.random.poisson(media_ht_fora, n_simulacoes)
        golos_2ht_casa_sim = np.random.poisson(media_2ht_casa, n_simulacoes)
        golos_2ht_fora_sim = np.random.poisson(media_2ht_fora, n_simulacoes)
        
        golos_ft_casa_sim = golos_ht_casa_sim + golos_2ht_casa_sim
        golos_ft_fora_sim = golos_ht_fora_sim + golos_2ht_fora_sim
        
        total_ht = golos_ht_casa_sim + golos_ht_fora_sim
        total_2ht = golos_2ht_casa_sim + golos_2ht_fora_sim
        total_ft = golos_ft_casa_sim + golos_ft_fora_sim
        
        # Dicionário de Probabilidades
        probs = {
            "1X2: Vitória Casa (1)": np.sum(golos_ft_casa_sim > golos_ft_fora_sim) / n_simulacoes * 100,
            "1X2: Empate (X)": np.sum(golos_ft_casa_sim == golos_ft_fora_sim) / n_simulacoes * 100,
            "1X2: Vitória Fora (2)": np.sum(golos_ft_casa_sim < golos_ft_fora_sim) / n_simulacoes * 100,
            "Over 0.5 HT": np.sum(total_ht > 0.5) / n_simulacoes * 100,
            "Over 1.5 HT": np.sum(total_ht > 1.5) / n_simulacoes * 100,
            "Over 1.5 FT": np.sum(total_ft > 1.5) / n_simulacoes * 100,
            "Over 2.5 FT": np.sum(total_ft > 2.5) / n_simulacoes * 100,
            "Over 3.5 FT": np.sum(total_ft > 3.5) / n_simulacoes * 100,
            "Under 2.5 FT": np.sum(total_ft < 2.5) / n_simulacoes * 100,
            "Under 3.5 FT": np.sum(total_ft < 3.5) / n_simulacoes * 100,
            "+ Golos na 1ª Parte": np.sum(total_ht > total_2ht) / n_simulacoes * 100,
            "Igualdade (HT = 2HT)": np.sum(total_ht == total_2ht) / n_simulacoes * 100,
            "+ Golos na 2ª Parte": np.sum(total_2ht > total_ht) / n_simulacoes * 100
        }

        # Cálculo do EV
        probabilidade_alvo = probs[mercado_alvo]
        odd_justa = 100 / probabilidade_alvo if probabilidade_alvo > 0 else 999.99 
        vantagem_percentual = ((odd_casa_apostas / odd_justa) - 1) * 100

        # ==========================================
        # INTERFACE VISUAL
        # ==========================================
        st.markdown("---")
        st.subheader(f"{jogo_hoje_casa} vs {jogo_hoje_fora}")
        
        if usou_exemplo:
            st.warning("⚠️ Histórico não encontrado para estas equipas. A usar médias de exemplo.")
        if aviso_sem_ht:
            st.warning("⚠️ Esta liga não possui dados de Intervalo (HT) no ficheiro original. O modelo estimou a força das equipas ao Intervalo com base numa distribuição estatística de 45% (HT) e 55% (2HT) sobre os golos Finais.")
            
        st.markdown(f"### 📈 Análise de Valor: {mercado_alvo}")
        
        col_odd1, col_odd2, col_odd3 = st.columns(3)
        col_odd1.metric("Odd da Casa de Apostas", f"{odd_casa_apostas:.2f}")
        col_odd2.metric("Odd Justa (Matemática)", f"{odd_justa:.2f}")
        
        if vantagem_percentual > 0:
            col_odd3.metric("Vantagem Encontrada (Valor)", f"+{vantagem_percentual:.1f}%", "Aposta com Valor (EV+)")
        else:
            col_odd3.metric("Vantagem Encontrada (Valor)", f"{vantagem_percentual:.1f}%", "- Sem Valor (EV-)")

        st.markdown("---")
        st.markdown("### ⚖️ Mercado 1X2 (Resultado Final)")
        col_1, col_x, col_2 = st.columns(3)
        col_1.metric(label=f"Vitória {jogo_hoje_casa} (1)", value=f"{probs['1X2: Vitória Casa (1)']:.1f}%")
        col_x.metric(label="Empate (X)", value=f"{probs['1X2: Empate (X)']:.1f}%")
        col_2.metric(label=f"Vitória {jogo_hoje_fora} (2)", value=f"{probs['1X2: Vitória Fora (2)']:.1f}%")

        st.markdown("---")
        st.markdown("### ⏱️ Mercados ao Intervalo (HT)")
        col_ht1, col_ht2 = st.columns(2)
        col_ht1.metric(label="Over 0.5 HT", value=f"{probs['Over 0.5 HT']:.1f}%")
        col_ht2.metric(label="Over 1.5 HT", value=f"{probs['Over 1.5 HT']:.1f}%")

        st.markdown("---")
        st.markdown("### 🏁 Mercados Finais (FT)")
        col4, col5, col6 = st.columns(3)
        col4.metric(label="Over 1.5", value=f"{probs['Over 1.5 FT']:.1f}%")
        col5.metric(label="Over 2.5", value=f"{probs['Over 2.5 FT']:.1f}%")
        col6.metric(label="Under 2.5", value=f"{probs['Under 2.5 FT']:.1f}%")
        
        col7, col8, col9 = st.columns(3)
        col7.metric(label="Over 3.5", value=f"{probs['Over 3.5 FT']:.1f}%")
        col8.metric(label="Under 3.5", value=f"{probs['Under 3.5 FT']:.1f}%")

        st.markdown("---")
        st.markdown("### ⚖️ Parte com Mais Golos (HT vs 2ª Parte)")
        col_mht, col_meq, col_m2ht = st.columns(3)
        col_mht.metric(label="+ Golos na 1ª Parte", value=f"{probs['+ Golos na 1ª Parte']:.1f}%")
        col_meq.metric(label="Igualdade (Mesmo nº)", value=f"{probs['Igualdade (HT = 2HT)']:.1f}%")
        col_m2ht.metric(label="+ Golos na 2ª Parte", value=f"{probs['+ Golos na 2ª Parte']:.1f}%")

        # ==========================================
        # BOTÃO DE EXPORTAÇÃO COMPLETA (REGISTO)
        # ==========================================
        st.markdown("---")
        st.markdown("### 💾 Guardar Análise Completa")
        
        dados_exportar = pd.DataFrame({
            "Data": [datetime.now().strftime("%Y-%m-%d %H:%M")],
            "Liga": [liga_selecionada],
            "Jogo": [f"{jogo_hoje_casa} vs {jogo_hoje_fora}"],
            "Mercado_Analisado": [mercado_alvo],
            "Odd_Casa_Apostas": [odd_casa_apostas],
            "Odd_Justa_Modelo": [round(odd_justa, 2)],
            "EV(%)": [f"{vantagem_percentual:.1f}%"],
            "Veredicto": ["EV+" if vantagem_percentual > 0 else "EV-"],
            "Prob_Casa(1)": [f"{probs['1X2: Vitória Casa (1)']:.1f}%"],
            "Prob_Empate(X)": [f"{probs['1X2: Empate (X)']:.1f}%"],
            "Prob_Fora(2)": [f"{probs['1X2: Vitória Fora (2)']:.1f}%"],
            "Prob_Over_0.5_HT": [f"{probs['Over 0.5 HT']:.1f}%"],
            "Prob_Over_1.5_HT": [f"{probs['Over 1.5 HT']:.1f}%"],
            "Prob_Over_1.5_FT": [f"{probs['Over 1.5 FT']:.1f}%"],
            "Prob_Over_2.5_FT": [f"{probs['Over 2.5 FT']:.1f}%"],
            "Prob_Under_2.5_FT": [f"{probs['Under 2.5 FT']:.1f}%"],
            "Prob_Over_3.5_FT": [f"{probs['Over 3.5 FT']:.1f}%"],
            "Prob_Under_3.5_FT": [f"{probs['Under 3.5 FT']:.1f}%"],
            "Prob_Mais_Golos_1HT": [f"{probs['+ Golos na 1ª Parte']:.1f}%"],
            "Prob_Igualdade_Partes": [f"{probs['Igualdade (HT = 2HT)']:.1f}%"],
            "Prob_Mais_Golos_2HT": [f"{probs['+ Golos na 2ª Parte']:.1f}%"]
        })
        
        csv = dados_exportar.to_csv(index=False, sep=';').encode('utf-8-sig')
        
        st.download_button(
            label="📥 Descarregar Análise Completa (CSV)",
            data=csv,
            file_name=f"analise_completa_{jogo_hoje_casa}_{jogo_hoje_fora}.csv",
            mime='text/csv'
        )