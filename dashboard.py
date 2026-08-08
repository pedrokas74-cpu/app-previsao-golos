import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Previsão de Golos", page_icon="⚽", layout="wide")
st.title("⚽ Dashboard Inteligente de Golos (Monte Carlo)")

DICIONARIO_LIGAS = {
    'E0': 'Inglaterra - Premier League', 'E1': 'Inglaterra - Championship', 'E2': 'Inglaterra - League 1', 'E3': 'Inglaterra - League 2',
    'P1': 'Portugal - Primeira Liga',
    'SP1': 'Espanha - La Liga', 'SP2': 'Espanha - Segunda Divisão',
    'I1': 'Itália - Serie A', 'I2': 'Itália - Serie B',
    'D1': 'Alemanha - Bundesliga', 'D2': 'Alemanha - 2. Bundesliga',
    'F1': 'França - Ligue 1', 'F2': 'França - Ligue 2',
    'N1': 'Holanda - Eredivisie', 'B1': 'Bélgica - Pro League',
    'T1': 'Turquia - Super Lig', 'G1': 'Grécia - Super League', 'SC0': 'Escócia - Premiership'
}

@st.cache_data(show_spinner=False)
def carregar_dados(ficheiro_dados):
    # O DETETIVE: Se o ficheiro não existir, mostra o que está na pasta!
    if not os.path.exists(ficheiro_dados):
        lista_ficheiros = os.listdir()
        erro_msg = f"❌ O ficheiro '{ficheiro_dados}' NÃO FOI ENCONTRADO no servidor!\n\nFicheiros que o servidor consegue ver agora mesmo nesta pasta:\n{lista_ficheiros}"
        return pd.DataFrame(), erro_msg
        
    try:
        colunas_usar = ['Div', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HTHG', 'HTAG']
        
        # O Pandas consegue ler ZIPs diretamente de forma simples
        if ficheiro_dados.endswith(('.zip', '.csv')):
            df = pd.read_csv(ficheiro_dados, usecols=colunas_usar, low_memory=True)
        else:
            df = pd.read_excel(ficheiro_dados)
            
        # Otimização de Memória
        for col in ['Div', 'HomeTeam', 'AwayTeam']:
            if col in df.columns:
                df[col] = df[col].astype('category')
        for col in ['FTHG', 'FTAG', 'HTHG', 'HTAG']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], downcast='integer')
        
        df = df.rename(columns={
            'Div': 'Liga_Codigo', 'HomeTeam': 'Equipa_Casa', 'AwayTeam': 'Equipa_Fora',
            'HTHG': 'Golos_HT_Casa', 'HTAG': 'Golos_HT_Fora', 'FTHG': 'Golos_FT_Casa', 'FTAG': 'Golos_FT_Fora'
        })
        
        if 'Golos_HT_Casa' not in df.columns: df['Golos_HT_Casa'] = np.nan
        if 'Golos_HT_Fora' not in df.columns: df['Golos_HT_Fora'] = np.nan
        if 'Liga_Codigo' not in df.columns: df['Liga_Codigo'] = 'Competição Geral'
        
        df['Liga'] = df['Liga_Codigo'].astype(str).map(DICIONARIO_LIGAS).fillna(df['Liga_Codigo'].astype(str))
        df['Liga'] = df['Liga'].astype('category')
        
        return df, ""
    except Exception as e:
        return pd.DataFrame(), f"❌ Erro ao abrir os dados do ficheiro {ficheiro_dados}: {e}"

# ==========================================
# BARRA LATERAL
# ==========================================
st.sidebar.header("1. Fonte de Dados")
opcao_bd = st.sidebar.radio("Seleciona a Base de Dados:", ["BD_A (Histórico Completo)", "BD_B (Recente)"])
is_historico = opcao_bd == "BD_A (Histórico Completo)"
ficheiro_dados = 'BD_A.zip' if is_historico else 'BD_B.xlsx'

df_dados, mensagem_erro = carregar_dados(ficheiro_dados)

st.sidebar.header("2. Configuração do Jogo")

# MOSTRAR ERRO DETETIVE SE EXISTIR
if mensagem_erro:
    st.error(mensagem_erro)

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
    st.sidebar.warning("A ler os dados, por favor aguarda...")
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
if botao_analisar and not df_dados.empty:
    with st.spinner(f'A processar cenários para {jogo_hoje_casa} vs {jogo_hoje_fora}...'):
        
        media_ht_casa, media_ht_fora = 0.8, 0.5 
        media_ft_casa, media_ft_fora = 1.9, 1.2
        usou_exemplo = True
        aviso_sem_ht = False
        
        hist_casa = df_dados[df_dados['Equipa_Casa'] == jogo_hoje_casa]
        hist_fora = df_dados[df_dados['Equipa_Fora'] == jogo_hoje_fora]
        
        if not hist_casa.empty and not hist_fora.empty:
            media_ft_casa = hist_casa['Golos_FT_Casa'].mean()
            media_ft_fora = hist_fora['Golos_FT_Fora'].mean()
            usou_exemplo = False
            
            if hist_casa['Golos_HT_Casa'].isna().all() or hist_fora['Golos_HT_Fora'].isna().all():
                aviso_sem_ht = True
                media_ht_casa = media_ft_casa * 0.45
                media_ht_fora = media_ft_fora * 0.45
            else:
                media_ht_casa = hist_casa['Golos_HT_Casa'].mean()
                media_ht_fora = hist_fora['Golos_HT_Fora'].mean()
        
        media_2ht_casa = max(0, media_ft_casa - media_ht_casa)
        media_2ht_fora = max(0, media_ft_fora - media_ht_fora)

        golos_ht_casa_sim = np.random.poisson(media_ht_casa, n_simulacoes)
        golos_ht_fora_sim = np.random.poisson(media_ht_fora, n_simulacoes)
        golos_2ht_casa_sim = np.random.poisson(media_2ht_casa, n_simulacoes)
        golos_2ht_fora_sim = np.random.poisson(media_2ht_fora, n_simulacoes)
        
        golos_ft_casa_sim = golos_ht_casa_sim + golos_2ht_casa_sim
        golos_ft_fora_sim = golos_ht_fora_sim + golos_2ht_fora_sim
        
        total_ht = golos_ht_casa_sim + golos_ht_fora_sim
        total_2ht = golos_2ht_casa_sim + golos_2ht_fora_sim
        total_ft = golos_ft_casa_sim + golos_ft_fora_sim
        
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
            st.info("ℹ️ **Nota de Análise:** Esta liga não possui registo de golos ao intervalo.")
            
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
        # BOTÃO DE EXPORTAÇÃO
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
            file_name=f"analise_{jogo_hoje_casa}_{jogo_hoje_fora}.csv",
            mime='text/csv'
        )