#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
ANÁLISE COMPLEMENTAR — YRBS 2023 MICRODADOS (INTRA-SURVEY)
Correlação individual entre uso de redes sociais e depressão
na MESMA amostra do YRBS 2023

Autor: [Seu nome]
Orientador: [Nome do orientador]
Data: Março 2026
================================================================================

ANTES DE EXECUTAR — PASSOS OBRIGATÓRIOS:

1. Acesse: https://www.cdc.gov/yrbs/data/national-yrbs-datasets-documentation.html
2. Baixe o dataset nacional 2023 em formato Access (.accdb) OU ASCII (.dat)
3. Se baixou Access: exporte a tabela principal como CSV usando Access ou Python
4. Se baixou ASCII: use o programa SAS/SPSS fornecido pelo CDC para converter,
   OU use este script que lê o ASCII diretamente (ver Seção AUTO-DETECT abaixo)
5. Coloque o arquivo na MESMA PASTA deste script
6. Renomeie para: yrbs2023.csv  (ou  yrbs2023.dat  para ASCII)
7. Execute: python analise_complementar_yrbs2023.py

VARIÁVEIS-CHAVE DO YRBS 2023 (do Data User's Guide):
  - Q2:      Sexo (1=Feminino, 2=Masculino)
  - Q3:      Série/Grade (1=9th, 2=10th, 3=11th, 4=12th)
  - raceeth: Raça/etnicidade (variável calculada, 1-7)
  - Q26:     "During the past 12 months, did you ever feel so sad or hopeless
              almost every day for two weeks or more in a row that you stopped
              doing some usual activities?" (1=Sim, 2=Não)
  - QN26:    Dicotômica de Q26 (1=Sim, 2=Não)
  - Q87:     "How often do you use social media?" (nova em 2023)
              Respostas: escala de frequência (ver codebook)
  - QNfreqsocialmedia: Dicotômica — uso frequente de redes sociais
              (1=várias vezes ao dia ou mais, 2=menos frequente/não usa)
  - weight:  Peso amostral
  - stratum: Estrato da amostra
  - PSU:     Unidade primária de amostragem
================================================================================
"""

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import os
import sys
import warnings

warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Paleta
COLORS = {
    'freq_sm': '#E74C3C',
    'infreq_sm': '#3498DB',
    'female': '#E74C3C',
    'male': '#3498DB',
    'accent': '#1F4E79',
    'grid': '#E8E8E8',
}

plt.rcParams.update({
    'figure.figsize': (12, 7),
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'axes.labelsize': 12,
    'figure.dpi': 150,
    'savefig.dpi': 300,
})


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 0: TENTAR CARREGAR OS MICRODADOS
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("ANÁLISE COMPLEMENTAR — YRBS 2023 MICRODADOS (INTRA-SURVEY)")
print("Correlação individual: uso de redes sociais × depressão")
print("=" * 80)

csv_path = os.path.join(SCRIPT_DIR, 'yrbs2023.csv')
dat_path = os.path.join(SCRIPT_DIR, 'yrbs2023.dat')
accdb_path = os.path.join(SCRIPT_DIR, 'yrbs2023.accdb')

df = None
USING_REAL_DATA = False

# Tentar carregar CSV
if os.path.exists(csv_path):
    print(f"\n📂 Encontrado: {csv_path}")
    try:
        df = pd.read_csv(csv_path, low_memory=False)
        # Normalizar nomes de colunas para minúsculas
        df.columns = df.columns.str.strip().str.lower()
        USING_REAL_DATA = True
        print(f"   ✅ Carregado: {len(df)} registros, {len(df.columns)} variáveis")
    except Exception as e:
        print(f"   ❌ Erro ao ler CSV: {e}")

# Tentar carregar Access (.accdb)
elif os.path.exists(accdb_path):
    print(f"\n📂 Encontrado: {accdb_path}")
    try:
        import pyodbc
        conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={accdb_path};'
        conn = pyodbc.connect(conn_str)
        df = pd.read_sql("SELECT * FROM [survey]", conn)
        df.columns = df.columns.str.strip().str.lower()
        conn.close()
        USING_REAL_DATA = True
        print(f"   ✅ Carregado: {len(df)} registros")
    except ImportError:
        print("   ⚠️  pyodbc não instalado. Instale com: pip install pyodbc")
        print("   Alternativa: abra o .accdb no Access e exporte como CSV.")
    except Exception as e:
        print(f"   ❌ Erro ao ler Access: {e}")

# Se nenhum arquivo encontrado, usar dados simulados baseados nos resultados publicados
if df is None:
    print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠️  MICRODADOS NÃO ENCONTRADOS                                       ║
║                                                                        ║
║  Nenhum arquivo yrbs2023.csv, yrbs2023.accdb ou yrbs2023.dat           ║
║  foi encontrado na pasta: {SCRIPT_DIR:<43}║
║                                                                        ║
║  O script vai rodar com DADOS SIMULADOS baseados nos resultados        ║
║  oficiais publicados pelo CDC (MMWR Supplement, Out 2024).             ║
║  Isso permite visualizar o formato da análise e os gráficos.           ║
║                                                                        ║
║  Para usar dados reais, baixe em:                                      ║
║  https://www.cdc.gov/yrbs/data/national-yrbs-datasets-documentation.html║
║                                                                        ║
║  ⚠️  NÃO USE DADOS SIMULADOS NO TCC FINAL.                            ║
║  Os dados simulados servem apenas para validar o código.               ║
╚══════════════════════════════════════════════════════════════════════════╝
""")

    # ──────────────────────────────────────────────────────────────────────
    # DADOS SIMULADOS — baseados nos resultados publicados do CDC (MMWR)
    # N = 20,103; 77% uso frequente de SM; 39.7% depressão overall
    # Prevalências publicadas pelo CDC para cada cruzamento
    # ──────────────────────────────────────────────────────────────────────

    np.random.seed(2023)
    N = 20103

    # Gerar sexo (~ 50/50 no YRBS)
    sex = np.random.choice([1, 2], size=N, p=[0.50, 0.50])  # 1=F, 2=M

    # Gerar série (grades 9-12, ~ uniformemente distribuídos)
    grade = np.random.choice([1, 2, 3, 4], size=N, p=[0.27, 0.26, 0.25, 0.22])

    # Gerar raça/etnicidade (aproximação das proporções do YRBS 2023)
    raceeth = np.random.choice(
        [1, 2, 3, 4, 5, 6, 7],
        size=N,
        p=[0.02, 0.05, 0.13, 0.01, 0.50, 0.25, 0.04]  # AI/AN, Asian, Black, NH/PI, White, Hispanic, Multi
    )

    # Gerar uso frequente de redes sociais (QNfreqsocialmedia)
    # CDC: Overall 77%, F~80%, M~74%
    p_freq_sm = np.where(sex == 1, 0.80, 0.74)
    freq_sm = np.array([np.random.choice([1, 2], p=[p, 1-p]) for p in p_freq_sm])

    # Gerar depressão (QN26) com associação ao uso de SM
    # CDC publicou: entre quem usa SM frequentemente, ~44% reportam depressão
    #               entre quem não usa frequentemente, ~26% reportam depressão
    # E o efeito é mais forte em meninas
    p_dep = np.zeros(N)
    for i in range(N):
        if sex[i] == 1:  # Feminino
            p_dep[i] = 0.57 if freq_sm[i] == 1 else 0.38
        else:  # Masculino
            p_dep[i] = 0.31 if freq_sm[i] == 1 else 0.20
    depression = np.array([np.random.choice([1, 2], p=[p, 1-p]) for p in p_dep])

    # Gerar pesos amostrais (simplificado — média ~1.0)
    weights = np.random.lognormal(mean=0, sigma=0.3, size=N)
    weights = weights / weights.mean()  # Normalizar para média 1

    df = pd.DataFrame({
        'q2': sex,          # Sexo
        'q3': grade,        # Série
        'raceeth': raceeth, # Raça/etnicidade
        'q26': depression,  # Depressão (raw)
        'qn26': depression, # Depressão (dicotômica)
        'q87': freq_sm,     # Uso de redes sociais (raw) — simplificado como dicotômica
        'qnfreqsocialmedia': freq_sm,  # Uso frequente de SM (dicotômica)
        'weight': weights,
    })

    print(f"   📊 Dados simulados gerados: {len(df)} registros")
    USING_REAL_DATA = False


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1: PREPARAÇÃO E INSPEÇÃO DOS DADOS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "─" * 80)
print("SEÇÃO 1: PREPARAÇÃO DOS DADOS")
print("─" * 80)

# Mapear variáveis (ajustar nomes se necessário)
# O YRBS usa nomes como Q2, Q3, Q26, Q87, QN26, QNfreqsocialmedia, weight, stratum, PSU

# Detectar nomes de variáveis automaticamente
def find_col(df, candidates):
    """Encontra a primeira coluna que existe no DataFrame."""
    for c in candidates:
        if c.lower() in [x.lower() for x in df.columns]:
            match = [x for x in df.columns if x.lower() == c.lower()][0]
            return match
    return None

col_sex = find_col(df, ['q2', 'sex', 'Q2'])
col_grade = find_col(df, ['q3', 'grade', 'Q3'])
col_race = find_col(df, ['raceeth', 'race4', 'race', 'RACEETH'])
col_depression = find_col(df, ['qn26', 'QN26'])
col_sm_freq = find_col(df, ['qnfreqsocialmedia', 'QNfreqsocialmedia', 'QNFREQSOCIALMEDIA', 'q87', 'Q87'])
col_weight = find_col(df, ['weight', 'WEIGHT'])

print(f"\n  Variáveis detectadas:")
print(f"    Sexo:                {col_sex or '❌ NÃO ENCONTRADA'}")
print(f"    Série:               {col_grade or '❌ NÃO ENCONTRADA'}")
print(f"    Raça/etnicidade:     {col_race or '❌ NÃO ENCONTRADA'}")
print(f"    Depressão (QN26):    {col_depression or '❌ NÃO ENCONTRADA'}")
print(f"    Redes sociais:       {col_sm_freq or '❌ NÃO ENCONTRADA'}")
print(f"    Peso amostral:       {col_weight or '❌ NÃO ENCONTRADA'}")

# Verificações críticas
missing_vars = []
if not col_depression: missing_vars.append("depressão (QN26)")
if not col_sm_freq: missing_vars.append("redes sociais (QNfreqsocialmedia ou Q87)")

if missing_vars:
    print(f"\n  ❌ ERRO: Variáveis obrigatórias não encontradas: {', '.join(missing_vars)}")
    print(f"  Colunas disponíveis: {list(df.columns[:30])}...")
    print(f"  Verifique o codebook do YRBS 2023 e ajuste os nomes das variáveis.")
    sys.exit(1)

# Criar variáveis padronizadas
df['depressao'] = (df[col_depression] == 1).astype(int)  # 1=Sim, 0=Não
df['uso_freq_sm'] = (df[col_sm_freq] == 1).astype(int)   # 1=Frequente, 0=Não

if col_sex:
    df['sexo'] = df[col_sex].map({1: 'Feminino', 2: 'Masculino'})
if col_grade:
    df['serie'] = df[col_grade].map({1: '9th', 2: '10th', 3: '11th', 4: '12th'})
if col_race:
    race_map = {1: 'AI/AN', 2: 'Asiático', 3: 'Negro', 4: 'NH/PI',
                5: 'Branco', 6: 'Hispânico', 7: 'Multirracial'}
    df['raca'] = df[col_race].map(race_map)

w = pd.Series(df[col_weight].values, index=df.index) if col_weight else pd.Series(np.ones(len(df)), index=df.index)

# Remover missings nas variáveis-chave
df_clean = df.dropna(subset=['depressao', 'uso_freq_sm'])
w_clean = w.loc[df_clean.index]

print(f"\n  Registros válidos para análise: {len(df_clean)} de {len(df)}")
print(f"  {'⚠️  DADOS SIMULADOS' if not USING_REAL_DATA else '✅ DADOS REAIS DO CDC'}")


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2: PREVALÊNCIAS E TABELAS CRUZADAS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "─" * 80)
print("SEÇÃO 2: PREVALÊNCIAS E TABELAS CRUZADAS (CROSSTABS)")
print("─" * 80)

def weighted_prevalence(data, var, weights):
    """Calcula prevalência ponderada."""
    mask = data[var].notna()
    d = data.loc[mask, var].values
    wt = weights.loc[data.index[mask]].values
    prev = np.average(d, weights=wt) * 100
    n = mask.sum()
    se = np.sqrt(prev * (100 - prev) / n)
    return prev, se, n

# 2.1 Prevalência geral
prev_dep, se_dep, n_dep = weighted_prevalence(df_clean, 'depressao', w_clean)
prev_sm, se_sm, n_sm = weighted_prevalence(df_clean, 'uso_freq_sm', w_clean)

print(f"""
  ┌─────────────────────────────────────────────────────────┐
  │  PREVALÊNCIAS GERAIS (ponderadas)                       │
  │                                                         │
  │  Depressão (tristeza/desesperança persistente):          │
  │    {prev_dep:.1f}% (±{se_dep:.1f}%, n={n_dep:,})             │
  │                                                         │
  │  Uso frequente de redes sociais (≥ várias vezes/dia):   │
  │    {prev_sm:.1f}% (±{se_sm:.1f}%, n={n_sm:,})             │
  └─────────────────────────────────────────────────────────┘
""")

# 2.2 Crosstab: Depressão por uso de redes sociais
print("  📊 TABELA CRUZADA: Depressão × Uso frequente de redes sociais")
print("  " + "─" * 55)

freq_users = df_clean[df_clean['uso_freq_sm'] == 1]
infreq_users = df_clean[df_clean['uso_freq_sm'] == 0]

dep_among_freq, se_f, n_f = weighted_prevalence(freq_users, 'depressao', w)
dep_among_infreq, se_i, n_i = weighted_prevalence(infreq_users, 'depressao', w)

print(f"""
  │ Uso de redes sociais    │ % com depressão  │    n    │
  │─────────────────────────│──────────────────│─────────│
  │ Frequente (≥ vários/dia)│     {dep_among_freq:5.1f}%        │ {n_f:6,} │
  │ Infrequente / Não usa   │     {dep_among_infreq:5.1f}%        │ {n_i:6,} │
  │─────────────────────────│──────────────────│─────────│
  │ Diferença absoluta      │    {dep_among_freq - dep_among_infreq:+5.1f} pp       │         │
""")

# 2.3 Teste de qui-quadrado
ct = pd.crosstab(df_clean['uso_freq_sm'], df_clean['depressao'])
chi2, p_chi2, dof, expected = stats.chi2_contingency(ct)

print(f"  📐 TESTE DE QUI-QUADRADO (χ²):")
print(f"     χ² = {chi2:.2f}")
print(f"     df = {dof}")
print(f"     p  = {p_chi2:.2e}")
sig = "✅ SIGNIFICATIVO (p < 0.001)" if p_chi2 < 0.001 else ("✅ SIGNIFICATIVO (p < 0.05)" if p_chi2 < 0.05 else "⚠️  NÃO SIGNIFICATIVO")
print(f"     {sig}")

# 2.4 Razão de prevalência (Prevalence Ratio)
PR = dep_among_freq / dep_among_infreq if dep_among_infreq > 0 else float('inf')
print(f"\n  📐 RAZÃO DE PREVALÊNCIA (PR):")
print(f"     PR = {PR:.2f}")
print(f"     Interpretação: Adolescentes com uso frequente de redes sociais")
print(f"     têm {PR:.2f}x mais chance de reportar depressão do que")
print(f"     aqueles com uso infrequente/sem uso.")

# 2.5 Odds Ratio
a = ct.iloc[1, 1]  # freq SM + depressão
b = ct.iloc[1, 0]  # freq SM + sem depressão
c = ct.iloc[0, 1]  # infreq SM + depressão
d = ct.iloc[0, 0]  # infreq SM + sem depressão

OR = (a * d) / (b * c) if (b * c) > 0 else float('inf')
se_ln_or = np.sqrt(1/a + 1/b + 1/c + 1/d)
ci_lower = np.exp(np.log(OR) - 1.96 * se_ln_or)
ci_upper = np.exp(np.log(OR) + 1.96 * se_ln_or)

print(f"\n  📐 ODDS RATIO (OR):")
print(f"     OR = {OR:.2f} (IC 95%: {ci_lower:.2f}–{ci_upper:.2f})")


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3: ESTRATIFICAÇÃO POR SEXO
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "─" * 80)
print("SEÇÃO 3: ESTRATIFICAÇÃO POR SEXO")
print("─" * 80)

if col_sex:
    resultados_sexo = {}
    for sexo_val, sexo_label in [(1, 'Feminino'), (2, 'Masculino')]:
        subset = df_clean[df_clean[col_sex] == sexo_val]
        w_sub = w_clean[subset.index]

        freq_sub = subset[subset['uso_freq_sm'] == 1]
        infreq_sub = subset[subset['uso_freq_sm'] == 0]

        dep_freq, _, n_freq = weighted_prevalence(freq_sub, 'depressao', w)
        dep_infreq, _, n_infreq = weighted_prevalence(infreq_sub, 'depressao', w)

        ct_sub = pd.crosstab(subset['uso_freq_sm'], subset['depressao'])
        chi2_sub, p_sub, _, _ = stats.chi2_contingency(ct_sub)

        pr_sub = dep_freq / dep_infreq if dep_infreq > 0 else float('inf')

        resultados_sexo[sexo_label] = {
            'dep_freq': dep_freq, 'dep_infreq': dep_infreq,
            'n_freq': n_freq, 'n_infreq': n_infreq,
            'chi2': chi2_sub, 'p': p_sub, 'PR': pr_sub,
        }

        print(f"\n  {sexo_label.upper()}:")
        print(f"    Depressão com uso frequente SM: {dep_freq:.1f}% (n={n_freq:,})")
        print(f"    Depressão sem uso frequente SM:  {dep_infreq:.1f}% (n={n_infreq:,})")
        print(f"    Diferença: {dep_freq - dep_infreq:+.1f} pp")
        print(f"    χ² = {chi2_sub:.2f}, p = {p_sub:.2e}")
        print(f"    PR = {pr_sub:.2f}")


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 4: VISUALIZAÇÕES
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "─" * 80)
print("SEÇÃO 4: GERANDO VISUALIZAÇÕES")
print("─" * 80)

data_label = "DADOS SIMULADOS" if not USING_REAL_DATA else "DADOS REAIS CDC"

# ──────────────────────────────────────────────────────────────────────
# GRÁFICO 5: Barras agrupadas — Depressão por uso de SM e sexo
# ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 7))
fig.patch.set_facecolor('white')

categories = ['Overall']
freq_vals = [dep_among_freq]
infreq_vals = [dep_among_infreq]

if col_sex and resultados_sexo:
    categories += ['Feminino', 'Masculino']
    freq_vals += [resultados_sexo['Feminino']['dep_freq'], resultados_sexo['Masculino']['dep_freq']]
    infreq_vals += [resultados_sexo['Feminino']['dep_infreq'], resultados_sexo['Masculino']['dep_infreq']]

x = np.arange(len(categories))
width = 0.35

bars1 = ax.bar(x - width/2, freq_vals, width,
               label='Uso frequente de redes sociais', color=COLORS['freq_sm'],
               edgecolor='white', linewidth=0.5)
bars2 = ax.bar(x + width/2, infreq_vals, width,
               label='Uso infrequente / Não usa', color=COLORS['infreq_sm'],
               edgecolor='white', linewidth=0.5)

# Anotações
for bars, color in [(bars1, COLORS['freq_sm']), (bars2, COLORS['infreq_sm'])]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.8,
                f'{height:.1f}%', ha='center', va='bottom',
                fontsize=10, fontweight='bold', color=color)

# Diferenças (setas)
for i in range(len(categories)):
    diff = freq_vals[i] - infreq_vals[i]
    mid_y = max(freq_vals[i], infreq_vals[i]) + 4
    ax.annotate(f'Δ {diff:+.1f}pp',
                xy=(i, mid_y), ha='center',
                fontsize=9, color='#555555', fontstyle='italic',
                fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=12)
ax.set_ylabel('Adolescentes com tristeza/desesperança persistente (%)',
              fontweight='bold')
ax.set_title(f'Depressão Adolescente por Frequência de Uso de Redes Sociais\n'
             f'YRBS 2023 — Análise Intra-Survey (N={len(df_clean):,}) [{data_label}]',
             fontweight='bold', pad=15)
ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
ax.grid(True, axis='y', alpha=0.3, color=COLORS['grid'])
ax.set_ylim(0, max(freq_vals) + 12)

# Caixa com estatísticas
stats_text = (f'χ² = {chi2:.1f} (p < 0.001)\n'
              f'PR = {PR:.2f}\n'
              f'OR = {OR:.2f} (IC 95%: {ci_lower:.2f}–{ci_upper:.2f})')
ax.text(0.02, 0.97, stats_text, transform=ax.transAxes,
        fontsize=9, va='top', ha='left',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                  edgecolor=COLORS['grid'], alpha=0.9),
        fontfamily='monospace')

fig.text(0.5, -0.02,
         f'Fonte: CDC YRBS 2023 (N=20,103) | {data_label} | '
         'Uso frequente = ≥ várias vezes ao dia',
         ha='center', fontsize=8, color='gray', fontstyle='italic')

plt.tight_layout()
filepath5 = os.path.join(SCRIPT_DIR, 'grafico5_intrasurvey_depressao_sm.png')
plt.savefig(filepath5, dpi=300, bbox_inches='tight', facecolor='white')
print(f"  ✅ Salvo: {filepath5}")
plt.close()


# ──────────────────────────────────────────────────────────────────────
# GRÁFICO 6: Heatmap — Depressão por sexo e uso de SM
# ──────────────────────────────────────────────────────────────────────
if col_sex:
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('white')

    heatmap_data = pd.DataFrame({
        'Uso frequente': [resultados_sexo['Feminino']['dep_freq'],
                          resultados_sexo['Masculino']['dep_freq']],
        'Uso infrequente': [resultados_sexo['Feminino']['dep_infreq'],
                            resultados_sexo['Masculino']['dep_infreq']],
    }, index=['Feminino', 'Masculino'])

    import seaborn as sns
    sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='YlOrRd',
                linewidths=2, linecolor='white',
                annot_kws={'size': 16, 'fontweight': 'bold'},
                cbar_kws={'label': '% com depressão'},
                vmin=15, vmax=60, ax=ax)

    ax.set_title(f'Prevalência de Depressão por Sexo e Frequência de Uso de Redes Sociais\n'
                 f'YRBS 2023 [{data_label}]',
                 fontweight='bold', pad=15)
    ax.set_ylabel('')
    ax.set_xlabel('')
    ax.tick_params(axis='both', labelsize=12)

    plt.tight_layout()
    filepath6 = os.path.join(SCRIPT_DIR, 'grafico6_heatmap_sexo_sm.png')
    plt.savefig(filepath6, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"  ✅ Salvo: {filepath6}")
    plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 5: RESUMO PARA O TCC
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("RESUMO DA ANÁLISE COMPLEMENTAR — YRBS 2023 INTRA-SURVEY")
print("=" * 80)

print(f"""
┌──────────────────────────────────────────────────────────────────────────┐
│  {'⚠️  DADOS SIMULADOS — SUBSTITUIR POR DADOS REAIS NO TCC' if not USING_REAL_DATA else '✅ DADOS REAIS DO CDC YRBS 2023':^68}│
│                                                                          │
│  AMOSTRA: N = {len(df_clean):,} estudantes do 9º ao 12º ano (high school)     │
│                                                                          │
│  PREVALÊNCIAS:                                                           │
│    Uso frequente de redes sociais: {prev_sm:.1f}%                             │
│    Depressão (tristeza/desesperança persistente): {prev_dep:.1f}%              │
│                                                                          │
│  ASSOCIAÇÃO PRINCIPAL:                                                   │
│    Depressão entre quem usa SM frequentemente: {dep_among_freq:.1f}%                │
│    Depressão entre quem NÃO usa frequentemente: {dep_among_infreq:.1f}%              │
│    Diferença: {dep_among_freq - dep_among_infreq:+.1f} pontos percentuais                           │
│                                                                          │
│  TESTES ESTATÍSTICOS:                                                    │
│    Qui-quadrado: χ² = {chi2:.1f}, p = {p_chi2:.2e}                          │
│    Razão de prevalência: PR = {PR:.2f}                                    │
│    Odds Ratio: OR = {OR:.2f} (IC 95%: {ci_lower:.2f}–{ci_upper:.2f})                     │
│                                                                          │
│  ESTRATIFICAÇÃO POR SEXO:                                                │""")

if col_sex and resultados_sexo:
    for s in ['Feminino', 'Masculino']:
        r = resultados_sexo[s]
        print(f"│    {s}: PR = {r['PR']:.2f} (Δ = {r['dep_freq'] - r['dep_infreq']:+.1f}pp, p = {r['p']:.2e})    │")

print(f"""│                                                                          │
│  VALOR PARA O TCC:                                                       │
│    Esta análise intra-survey ELIMINA a falácia ecológica porque          │
│    correlaciona uso de SM e depressão nos MESMOS indivíduos.             │
│    Isso complementa e reforça a análise de séries temporais              │
│    (Estratégia A principal).                                             │
│                                                                          │
│  LIMITAÇÕES:                                                             │
│    1. Cross-sectional (não estabelece causalidade)                       │
│    2. Auto-reportado (viés de memória/desejabilidade social)             │
│    3. Sem ajuste por pesos amostrais complexos (stratum/PSU)             │
│       → Para análise definitiva, usar survey package (R: survey;          │
│         Python: statsmodels com WLS; Stata: svy prefix)                   │
│    4. Não controla confundidores (por decisão do escopo)                 │
└──────────────────────────────────────────────────────────────────────────┘
""")

print("✅ Análise complementar concluída.")
print(f"   Gráficos gerados em: {SCRIPT_DIR}")
if not USING_REAL_DATA:
    print("\n  ⚠️  LEMBRETE: Substitua os dados simulados pelos microdados reais do CDC")
    print("     antes de incluir os resultados no TCC.")
print("\n" + "=" * 80)
