import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Pro xG Dashboard", page_icon="📈", layout="wide")
st.title("📈 Dashboard Profissional: Modelo xG e Simulação Avançada")

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
        colunas_usar = [
            'Div', 'HomeTeam', 'AwayTeam', 
            'FTHG', 'FTAG', 'HTHG', 'HTAG', 'HC', 'AC',
            'HS', 'AS', 'HST', 'AST', 'HF', 'AF'
        ]
        
        if ficheiro_dados.endswith('.zip'):
            with zipfile.ZipFile(ficheiro_dados, 'r') as z:
                ficheiros_csv = [f for f in z.namelist() if f.endswith('.csv') and not f.startswith('__MACOSX')]
                if not ficheiros_csv: return pd.DataFrame(), "Erro: ZIP vazio."
                with z.open(ficheiros_csv[0]) as f:
                    try: df = pd.read_csv(f, usecols=colunas_usar, low_memory=True)
                    except ValueError: f.seek(0); df = pd.read_csv(f, low_memory=True)
                        
        elif ficheiro_dados.endswith('.csv'):
            try: df = pd.read_csv(ficheiro_dados, usecols=colunas_usar, low_memory=True)
            except ValueError: df = pd.read_csv(ficheiro_dados, low_memory=True)
        else:
            df = pd.read_excel(ficheiro_dados)
            
        df = df.rename(columns={
            'Div': 'Liga_Codigo', 'HomeTeam': 'Equipa_Casa', 'AwayTeam': 'Equipa_Fora',
            'HTHG': 'Golos_HT_Casa', 'HTAG': 'Golos_HT_Fora', 'FTHG': 'Golos_FT_Casa', 'FTAG': 'Golos_FT_Fora',
            'HC': 'Cantos_Casa', 'AC': 'Cantos_Fora',
            'HS': 'Remates_Casa', 'AS': 'Remates_Fora', 'HST': 'Remates_Baliza_Casa', 'AST': 'Remates_Baliza_Fora',
            'HF': 'Faltas_Casa', 'AF': 'Faltas_Fora'
        })
        
        df = df[df['Liga_Codigo'].isin(DICIONARIO_LIGAS.keys())].copy()
            
        for col in ['Liga_Codigo', 'Equipa_Casa', 'Equipa_Fora']:
            if col in df.columns: df[col] = df[col].astype('category')
            
        colunas_num = [
            'Golos_FT_Casa', 'Golos_FT_Fora', 'Golos_HT_Casa', 'Golos_HT_Fora', 
            'Cantos_Casa', 'Cantos_Fora', 'Remates_Casa', 'Remates_Fora', 
            'Remates_Baliza_Casa', 'Remates_Baliza_Fora', 'Faltas_Casa', 'Faltas_Fora'
        ]
        
        for col in colunas_num:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
            else: df[col] = np.nan
        
        df['Liga'] = df['Liga_Codigo'].astype(str).map(DICIONARIO_LIGAS)
        df['Liga'] = df['Liga'].astype('category')
        
        return df, ""
    except Exception as e:
        return pd.DataFrame(), f"❌ Erro ao abrir os dados: {e}"

# ==========================================
# BARRA LATERAL
# ==========================================
st.sidebar.header("1. Fonte de Dados")
opcao_bd = st.sidebar.radio("Base de Dados:", ["BD_A (Histórico)", "BD_B (Recente)"])
ficheiro_dados = 'BD_A.zip' if opcao_bd == "BD_A (Histórico)" else 'BD_B.xlsx'

df_dados, mensagem_erro = carregar_dados(ficheiro_dados)

st.sidebar.header("2. Configuração do Jogo")
if mensagem_erro: st.sidebar.error(mensagem_erro)

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
botao_analisar = st.sidebar.button("Executar Análise xG", type="primary", use_container_width=True)
n_simulacoes = st.sidebar.slider("Simulações Monte Carlo:", 1000, 50000, 10000)

st.sidebar.markdown("---")
st.sidebar.header("3. Comparador de Odds")
mercados_opcoes = [
    "1X2: Vitória Casa (1)", "1X2: Empate (X)", "1X2: Vitória Fora (2)", 
    "Over 0.5 HT", "Over 1.5 HT", "Over 1.5 FT", "Over 2.5 FT", "Over 3.5 FT", 
    "Under 2.5 FT", "Under 3.5 FT", "+ Golos na 1ª Parte", "Igualdade (HT = 2HT)", "+ Golos na 2ª Parte",
    "Cantos: Over 8.5", "Cantos: Over 9.5", "Cantos: Over 10.5",
    "Cantos: Under 9.5", "Cantos: Under 10.5", "Cantos: Under 11.5"
]
mercado_alvo = st.sidebar.selectbox("Mercado Alvo:", mercados_opcoes)
odd_casa_apostas = st.sidebar.number_input("Odd da Casa de Apostas:", min_value=1.01, max_value=20.0, value=1.90, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("📁 Base de Dados Pessoal")
ficheiro_historico = 'minhas_analises_guardadas.csv'
if os.path.exists(ficheiro_historico):
    with open(ficheiro_historico, 'rb') as f:
        st.sidebar.download_button(label="📥 Descarregar Histórico", data=f.read(), file_name="bd_minhas_analises.csv", mime="text/csv", type="primary")

# ==========================================
# MOTOR MATEMÁTICO (MODELO xG HÍBRIDO)
# ==========================================
if botao_analisar and not df_dados.empty:
    with st.spinner(f'A calcular Força Real (xG) para {jogo_hoje_casa} vs {jogo_hoje_fora}...'):
        
        hist_casa = df_dados[df_dados['Equipa_Casa'] == jogo_hoje_casa]
        hist_fora = df_dados[df_dados['Equipa_Fora'] == jogo_hoje_fora]
        
        m_ht_casa, m_ht_fora, m_ft_casa, m_ft_fora = 0.8, 0.5, 1.9, 1.2
        m_c_casa, m_c_fora = 5.5, 4.5
        xg_casa, xg_fora = 1.9, 1.2
        
        media_remates_casa, media_remates_baliza_casa, media_faltas_casa = 0, 0, 0
        media_remates_fora, media_remates_baliza_fora, media_faltas_fora = 0, 0, 0
        aviso_dados_avancados = False
        
        if not hist_casa.empty and not hist_fora.empty:
            m_ft_casa = hist_casa['Golos_FT_Casa'].mean()
            m_ft_fora = hist_fora['Golos_FT_Fora'].mean()
            
            if hist_casa['Golos_HT_Casa'].isna().all(): m_ht_casa, m_ht_fora = m_ft_casa * 0.45, m_ft_fora * 0.45
            else: m_ht_casa, m_ht_fora = hist_casa['Golos_HT_Casa'].mean(), hist_fora['Golos_HT_Fora'].mean()
                
            if not hist_casa['Cantos_Casa'].isna().all():
                m_c_casa = hist_casa['Cantos_Casa'].mean()
                m_c_fora = hist_fora['Cantos_Fora'].mean()
            
            # --- CÁLCULO xG ---
            if not hist_casa['Remates_Baliza_Casa'].isna().all() and not hist_fora['Remates_Baliza_Fora'].isna().all():
                media_remates_casa = hist_casa['Remates_Casa'].mean()
                media_remates_baliza_casa = hist_casa['Remates_Baliza_Casa'].mean()
                media_faltas_casa = hist_casa['Faltas_Casa'].mean()
                
                media_remates_fora = hist_fora['Remates_Fora'].mean()
                media_remates_baliza_fora = hist_fora['Remates_Baliza_Fora'].mean()
                media_faltas_fora = hist_fora['Faltas_Fora'].mean()
                
                soma_golos_casa = hist_casa['Golos_FT_Casa'].sum()
                soma_remates_b_casa = hist_casa['Remates_Baliza_Casa'].sum()
                taxa_conv_casa = (soma_golos_casa / soma_remates_b_casa) if soma_remates_b_casa > 0 else (m_ft_casa / 5)
                
                soma_golos_fora = hist_fora['Golos_FT_Fora'].sum()
                soma_remates_b_fora = hist_fora['Remates_Baliza_Fora'].sum()
                taxa_conv_fora = (soma_golos_fora / soma_remates_b_fora) if soma_remates_b_fora > 0 else (m_ft_fora / 5)
                
                xg_casa = media_remates_baliza_casa * taxa_conv_casa
                xg_fora = media_remates_baliza_fora * taxa_conv_fora
                
                lambda_casa = (m_ft_casa + xg_casa) / 2
                lambda_fora = (m_ft_fora + xg_fora) / 2
            else:
                aviso_dados_avancados = True
                lambda_casa = m_ft_casa
                lambda_fora = m_ft_fora
                xg_casa, xg_fora = m_ft_casa, m_ft_fora
        
        g_ft_casa_sim = np.random.poisson(lambda_casa, n_simulacoes)
        g_ft_fora_sim = np.random.poisson(lambda_fora, n_simulacoes)
        
        prop_ht_casa = m_ht_casa / m_ft_casa if m_ft_casa > 0 else 0.45
        prop_ht_fora = m_ht_fora / m_ft_fora if m_ft_fora > 0 else 0.45
        
        g_ht_casa_sim = np.random.binomial(g_ft_casa_sim, prop_ht_casa)
        g_ht_fora_sim = np.random.binomial(g_ft_fora_sim, prop_ht_fora)
        g_2ht_casa_sim = g_ft_casa_sim - g_ht_casa_sim
        g_2ht_fora_sim = g_ft_fora_sim - g_ht_fora_sim
        
        t_ht = g_ht_casa_sim + g_ht_fora_sim
        t_2ht = g_2ht_casa_sim + g_2ht_fora_sim
        t_ft = g_ft_casa_sim + g_ft_fora_sim
        
        ajuste_intensidade = 1.05 if (media_remates_casa + media_remates_fora) > 25 else 1.0
        c_casa_sim = np.random.poisson(m_c_casa * ajuste_intensidade, n_simulacoes)
        c_fora_sim = np.random.poisson(m_c_fora * ajuste_intensidade, n_simulacoes)
        t_cantos = c_casa_sim + c_fora_sim
        
        probs = {
            "1X2: Vitória Casa (1)": np.sum(g_ft_casa_sim > g_ft_fora_sim) / n_simulacoes * 100,
            "1X2: Empate (X)": np.sum(g_ft_casa_sim == g_ft_fora_sim) / n_simulacoes * 100,
            "1X2: Vitória Fora (2)": np.sum(g_ft_casa_sim < g_ft_fora_sim) / n_simulacoes * 100,
            "Over 0.5 HT": np.sum(t_ht > 0.5) / n_simulacoes * 100,
            "Over 1.5 HT": np.sum(t_ht > 1.5) / n_simulacoes * 100,
            "Over 1.5 FT": np.sum(t_ft > 1.5) / n_simulacoes * 100,
            "Over 2.5 FT": np.sum(t_ft > 2.5) / n_simulacoes * 100,
            "Over 3.5 FT": np.sum(t_ft > 3.5) / n_simulacoes * 100,
            "Under 2.5 FT": np.sum(t_ft < 2.5) / n_simulacoes * 100,
            "Under 3.5 FT": np.sum(t_ft < 3.5) / n_simulacoes * 100,
            "+ Golos na 1ª Parte": np.sum(t_ht > t_2ht) / n_simulacoes * 100,
            "Igualdade (HT = 2HT)": np.sum(t_ht == t_2ht) / n_simulacoes * 100,
            "+ Golos na 2ª Parte": np.sum(t_2ht > t_ht) / n_simulacoes * 100,
            "Cantos: Over 8.5": np.sum(t_cantos > 8.5) / n_simulacoes * 100,
            "Cantos: Over 9.5": np.sum(t_cantos > 9.5) / n_simulacoes * 100,
            "Cantos: Over 10.5": np.sum(t_cantos > 10.5) / n_simulacoes * 100,
            "Cantos: Under 9.5": np.sum(t_cantos < 9.5) / n_simulacoes * 100,
            "Cantos: Under 10.5": np.sum(t_cantos < 10.5) / n_simulacoes * 100,
            "Cantos: Under 11.5": np.sum(t_cantos < 11.5) / n_simulacoes * 100
        }

        probabilidade_alvo = probs[mercado_alvo]
        odd_justa = 100 / probabilidade_alvo if probabilidade_alvo > 0 else 999.99 
        vantagem_percentual = ((odd_casa_apostas / odd_justa) - 1) * 100

        dados_exportar = pd.DataFrame({
            "Data": [datetime.now().strftime("%Y-%m-%d %H:%M")], "Liga": [liga_selecionada], "Jogo": [f"{jogo_hoje_casa} vs {jogo_hoje_fora}"],
            "Mercado": [mercado_alvo], "Odd_Casa": [odd_casa_apostas], "Odd_Justa": [round(odd_justa, 2)], "EV(%)": [f"{vantagem_percentual:.1f}%"],
            "xG_Casa": [round(xg_casa, 2)], "xG_Fora": [round(xg_fora, 2)]
        })
        if os.path.exists(ficheiro_historico): dados_exportar.to_csv(ficheiro_historico, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')
        else: dados_exportar.to_csv(ficheiro_historico, mode='w', header=True, index=False, sep=';', encoding='utf-8-sig')

        # ==========================================
        # INTERFACE VISUAL - TODOS OS MERCADOS!
        # ==========================================
        st.success("✅ Simulação xG concluída e gravada na Base de Dados!")
        
        st.markdown("---")
        st.subheader("🎯 Estatísticas Avançadas (Reconhecimento de Padrão)")
        if aviso_dados_avancados:
            st.warning("Estatísticas de Remates/Faltas não disponíveis. A usar o modelo clássico.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(label=f"xG (Esperados) - {jogo_hoje_casa}", value=f"{xg_casa:.2f}")
            c2.metric(label=f"xG (Esperados) - {jogo_hoje_fora}", value=f"{xg_fora:.2f}")
            c3.metric(label="Média Faltas (Intensidade)", value=f"{(media_faltas_casa + media_faltas_fora):.1f}")
            c4.metric(label="Remates à Baliza/Jogo", value=f"{(media_remates_baliza_casa + media_remates_baliza_fora):.1f}")
            
        st.markdown("---")
        st.markdown(f"### 📈 Análise de Valor: {mercado_alvo}")
        col_odd1, col_odd2, col_odd3 = st.columns(3)
        col_odd1.metric("Odd da Casa de Apostas", f"{odd_casa_apostas:.2f}")
        col_odd2.metric("Odd Justa (Modelo xG)", f"{odd_justa:.2f}")
        if vantagem_percentual > 0: col_odd3.metric("Vantagem Encontrada (Valor)", f"+{vantagem_percentual:.1f}%", "Aposta com Valor (EV+)")
        else: col_odd3.metric("Vantagem Encontrada (Valor)", f"{vantagem_percentual:.1f}%", "- Sem Valor (EV-)")

        st.markdown("---")
        st.markdown("### ⚖️ Mercado 1X2")
        col_1, col_x, col_2 = st.columns(3)
        col_1.metric(f"Vitória {jogo_hoje_casa} (1)", f"{probs['1X2: Vitória Casa (1)']:.1f}%")
        col_x.metric("Empate (X)", f"{probs['1X2: Empate (X)']:.1f}%")
        col_2.metric(f"Vitória {jogo_hoje_fora} (2)", f"{probs['1X2: Vitória Fora (2)']:.1f}%")

        st.markdown("---")
        st.markdown("### 🚩 Mercados de Cantos")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Over 8.5 Cantos", f"{probs['Cantos: Over 8.5']:.1f}%")
        cc2.metric("Over 9.5 Cantos", f"{probs['Cantos: Over 9.5']:.1f}%")
        cc3.metric("Over 10.5 Cantos", f"{probs['Cantos: Over 10.5']:.1f}%")
        cu1, cu2, cu3 = st.columns(3)
        cu1.metric("Under 9.5 Cantos", f"{probs['Cantos: Under 9.5']:.1f}%")
        cu2.metric("Under 10.5 Cantos", f"{probs['Cantos: Under 10.5']:.1f}%")
        cu3.metric("Under 11.5 Cantos", f"{probs['Cantos: Under 11.5']:.1f}%")

        st.markdown("---")
        st.markdown("### ⏱️ Mercados ao Intervalo (HT)")
        ch1, ch2 = st.columns(2)
        ch1.metric("Over 0.5 HT", f"{probs['Over 0.5 HT']:.1f}%")
        ch2.metric("Over 1.5 HT", f"{probs['Over 1.5 HT']:.1f}%")

        st.markdown("---")
        st.markdown("### 🏁 Mercados Finais de Golos (FT)")
        cf1, cf2, cf3 = st.columns(3)
        cf1.metric("Over 1.5 FT", f"{probs['Over 1.5 FT']:.1f}%")
        cf2.metric("Over 2.5 FT", f"{probs['Over 2.5 FT']:.1f}%")
        cf3.metric("Under 2.5 FT", f"{probs['Under 2.5 FT']:.1f}%")
        
        cf4, cf5, cf6 = st.columns(3)
        cf4.metric("Over 3.5 FT", f"{probs['Over 3.5 FT']:.1f}%")
        cf5.metric("Under 3.5 FT", f"{probs['Under 3.5 FT']:.1f}%")
        cf6.empty() # Espaço vazio para manter o alinhamento

        st.markdown("---")
        st.markdown("### ⚖️ Parte com Mais Golos (HT vs 2ª Parte)")
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("+ Golos na 1ª Parte", f"{probs['+ Golos na 1ª Parte']:.1f}%")
        cm2.metric("Igualdade (Mesmo nº)", f"{probs['Igualdade (HT = 2HT)']:.1f}%")
        cm3.metric("+ Golos na 2ª Parte", f"{probs['+ Golos na 2ª Parte']:.1f}%")