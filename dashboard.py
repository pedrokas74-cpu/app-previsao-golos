import streamlit as st
import pandas as pd
import numpy as np
import os

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Previsão de Golos", page_icon="⚽", layout="wide")
st.title("⚽ Dashboard Inteligente de Golos (Monte Carlo)")

# ==========================================
# BARRA LATERAL - ESCOLHA DE BD E JOGO
# ==========================================
st.sidebar.header("1. Fonte de Dados")
opcao_bd = st.sidebar.radio(
    "Seleciona a Base de Dados:", 
    ["BD_A (Histórico Completo)", "BD_B (Recente)"]
)

# Agora procuramos o ficheiro ZIP em vez do CSV
if opcao_bd == "BD_A (Histórico Completo)":
    ficheiro_dados = 'BD_A.zip'
else:
    ficheiro_dados = 'BD_B.xlsx'

st.sidebar.header("2. Configuração do Jogo")
jogo_hoje_casa = st.sidebar.text_input("Equipa da Casa", "Estoril")
jogo_hoje_fora = st.sidebar.text_input("Equipa Visitante", "Famalicao")
n_simulacoes = st.sidebar.slider("Número de Simulações", 1000, 50000, 10000)

st.sidebar.markdown("---")
st.sidebar.header("3. Comparador de Odds (Encontrar Valor)")
mercado_alvo = st.sidebar.selectbox("Mercado que queres testar:", 
                                    ["Over 1.5 FT", "Over 2.5 FT", "Over 3.5 FT", "Under 2.5 FT", "Under 3.5 FT"])
odd_casa_apostas = st.sidebar.number_input("Odd da Casa de Apostas (ex: 1.90):", min_value=1.01, max_value=20.0, value=1.90, step=0.01)

# ==========================================
# BOTÃO DE ANÁLISE E MOTOR MATEMÁTICO
# ==========================================
if st.sidebar.button("Analisar Jogo e Odds", type="primary"):
    
    with st.spinner(f'A processar {opcao_bd} e a gerar cenários...'):
        
        media_ht_casa, media_ht_fora = 0.8, 0.5 
        media_ft_casa, media_ft_fora = 1.9, 1.2
        usou_exemplo = True
        
        # Procura o ficheiro correto
        ficheiro_real = None
        if os.path.exists(ficheiro_dados):
            ficheiro_real = ficheiro_dados
        elif os.path.exists('BD_A.csv') and opcao_bd == "BD_A (Histórico Completo)":
            ficheiro_real = 'BD_A.csv' # Fallback caso estejas a testar no PC e ainda tenhas o CSV
            
        if ficheiro_real:
            try:
                # O PANDAS LÊ ZIP E CSV AUTOMATICAMENTE
                if ficheiro_real.endswith('.zip') or ficheiro_real.endswith('.csv'):
                    df = pd.read_csv(ficheiro_real)
                else:
                    df = pd.read_excel(ficheiro_real)
                
                df = df.rename(columns={
                    'HomeTeam': 'Equipa_Casa',
                    'AwayTeam': 'Equipa_Fora',
                    'HTHG': 'Golos_HT_Casa',
                    'HTAG': 'Golos_HT_Fora',
                    'FTHG': 'Golos_FT_Casa',
                    'FTAG': 'Golos_FT_Fora'
                })
                
                hist_casa = df[df['Equipa_Casa'] == jogo_hoje_casa]
                hist_fora = df[df['Equipa_Fora'] == jogo_hoje_fora]
                
                if not hist_casa.empty and not hist_fora.empty:
                    media_ht_casa = hist_casa['Golos_HT_Casa'].mean()
                    media_ht_fora = hist_fora['Golos_HT_Fora'].mean()
                    media_ft_casa = hist_casa['Golos_FT_Casa'].mean()
                    media_ft_fora = hist_fora['Golos_FT_Fora'].mean()
                    usou_exemplo = False
            except Exception as e:
                st.error(f"Erro ao ler o ficheiro: {e}")
        
        # --- SIMULAÇÃO MONTE CARLO ---
        golos_ht_casa_sim = np.random.poisson(media_ht_casa, n_simulacoes)
        golos_ht_fora_sim = np.random.poisson(media_ht_fora, n_simulacoes)
        total_ht = golos_ht_casa_sim + golos_ht_fora_sim
        
        golos_ft_casa_sim = np.random.poisson(media_ft_casa, n_simulacoes)
        golos_ft_fora_sim = np.random.poisson(media_ft_fora, n_simulacoes)
        total_ft = golos_ft_casa_sim + golos_ft_fora_sim
        
        # --- CÁLCULO DE PROBABILIDADES ---
        prob_o05_ht = np.sum(total_ht > 0.5) / n_simulacoes * 100
        prob_o15_ht = np.sum(total_ht > 1.5) / n_simulacoes * 100
        
        probs = {
            "Over 1.5 FT": np.sum(total_ft > 1.5) / n_simulacoes * 100,
            "Over 2.5 FT": np.sum(total_ft > 2.5) / n_simulacoes * 100,
            "Over 3.5 FT": np.sum(total_ft > 3.5) / n_simulacoes * 100,
            "Under 2.5 FT": np.sum(total_ft < 2.5) / n_simulacoes * 100,
            "Under 3.5 FT": np.sum(total_ft < 3.5) / n_simulacoes * 100
        }

        cenarios_placar = [f"{c}-{f}" for c, f in zip(golos_ft_casa_sim, golos_ft_fora_sim)]
        top_placares = pd.Series(cenarios_placar).value_counts(normalize=True).head(5) * 100

        # ==========================================
        # ANÁLISE DE VALOR (EV+)
        # ==========================================
        probabilidade_alvo = probs[mercado_alvo]
        
        if probabilidade_alvo > 0:
            odd_justa = 100 / probabilidade_alvo
        else:
            odd_justa = 999.99 
        
        vantagem_percentual = ((odd_casa_apostas / odd_justa) - 1) * 100

        # ==========================================
        # INTERFACE VISUAL DE RESULTADOS
        # ==========================================
        st.markdown("---")
        st.subheader(f"Resultados para: {jogo_hoje_casa} vs {jogo_hoje_fora}")
        
        if usou_exemplo:
            st.warning(f"⚠️ Ficheiro não encontrado ou equipas sem histórico. A usar médias de exemplo.")
        else:
            st.success(f"✅ A ler dados de: {ficheiro_real}")
        
        st.markdown(f"### 📈 Análise de Valor: {mercado_alvo}")
        
        col_odd1, col_odd2, col_odd3 = st.columns(3)
        col_odd1.metric("Odd da Casa de Apostas", f"{odd_casa_apostas:.2f}")
        col_odd2.metric("Odd Justa (Matemática)", f"{odd_justa:.2f}")
        
        if vantagem_percentual > 0:
            col_odd3.metric("Vantagem Encontrada (Valor)", f"+{vantagem_percentual:.1f}%", "Aposta com Valor (EV+)")
            st.info("💡 **Conclusão:** O modelo indica que a casa de apostas está a pagar mais do que a probabilidade real exige. Matematicamente, esta aposta tem valor a longo prazo.")
        else:
            col_odd3.metric("Vantagem Encontrada (Valor)", f"{vantagem_percentual:.1f}%", "- Sem Valor (EV-)")
            st.error("🛑 **Conclusão:** A odd da casa de apostas é demasiado baixa para o risco. Matematicamente, a longo prazo, perderás dinheiro com esta aposta.")

        st.markdown("---")
        
        st.markdown("### ⏱️ Mercados ao Intervalo (HT)")
        col1, col2, col3 = st.columns(3)
        col1.metric(label="Over 0.5 HT", value=f"{prob_o05_ht:.1f}%")
        col2.metric(label="Over 1.5 HT", value=f"{prob_o15_ht:.1f}%")
        
        st.markdown("---")
        
        st.markdown("### 🏁 Mercados Finais (FT)")
        col4, col5, col6 = st.columns(3)
        col4.metric(label="Over 1.5 FT", value=f"{probs['Over 1.5 FT']:.1f}%")
        col5.metric(label="Over 2.5 FT", value=f"{probs['Over 2.5 FT']:.1f}%")
        col6.metric(label="Over 3.5 FT", value=f"{probs['Over 3.5 FT']:.1f}%")
        
        col7, col8, col9 = st.columns(3)
        col7.metric(label="Under 2.5 FT", value=f"{probs['Under 2.5 FT']:.1f}%")
        col8.metric(label="Under 3.5 FT", value=f"{probs['Under 3.5 FT']:.1f}%")

        st.markdown("---")

        st.markdown("### 🎯 Top 5: Resultado Correto (FT)")
        cols_placar = st.columns(5)
        for i, (placar, prob) in enumerate(top_placares.items()):
            cols_placar[i].metric(label=f"Placar {placar}", value=f"{prob:.1f}%")