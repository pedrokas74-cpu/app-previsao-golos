import pandas as pd
import os
import glob

print("A analisar a pasta 'Ligas'...")
ficheiros = glob.glob("Ligas/*.csv")

dfs = []
for f in ficheiros:
    try:
        # low_memory=False previne erros; encoding='latin1' lê carateres especiais
        df = pd.read_csv(f, low_memory=False, encoding='latin1') 
        
        # 1. TRADUZIR LIGAS EXTRA (Brasil, Japão, EUA) PARA FORMATO EUROPEU
        if 'Home' in df.columns and 'HomeTeam' not in df.columns:
            df = df.rename(columns={
                'Home': 'HomeTeam', 
                'Away': 'AwayTeam', 
                'HG': 'FTHG', 
                'AG': 'FTAG', 
                'League': 'Div'
            })
        
        # Se a liga não tiver 'Div', tenta usar o país 'Country'
        if 'Div' not in df.columns and 'Country' in df.columns:
            df = df.rename(columns={'Country': 'Div'})
            
        # 2. GARANTIR QUE AS COLUNAS HT EXISTEM (Se não existirem, enche com Vazio/NaN)
        for col in ['Div', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HTHG', 'HTAG']:
            if col not in df.columns:
                df[col] = pd.NA
                
        # 3. FILTRAR SÓ AS COLUNAS ESSENCIAIS (Limpa lixo e reduz tamanho do ficheiro)
        df = df[['Div', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HTHG', 'HTAG']]
        dfs.append(df)
        
    except Exception as e:
        print(f"Erro ao ler {f}: {e}")

# Juntar tudo e guardar
if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final = df_final.dropna(subset=['HomeTeam', 'FTHG']) # Remove linhas vazias
    df_final.to_csv("BD_A.csv", index=False)
    print(f"✅ SUCESSO! A tua BD_A.csv tem agora {len(df_final)} jogos (Incluindo Brasil, Japão, MLS, etc!).")
else:
    print("❌ Nenhum ficheiro encontrado.")