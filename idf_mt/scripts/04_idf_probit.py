"""
04 - Cálculo do IDF-MT, testes de robustez e modelos probit (M1-M4).

Segue a metodologia do artigo (seções 3.4 a 3.6):
  * winsorização P1/P99 -> normalização min-max (0-1); I13 invertido
  * subíndice de cada dimensão = média simples dos indicadores normalizados
  * IDF = 100 x prod(S_k ^ w_k), pesos Delphi (25/20/25/15/15)
  * faixas por quartis; robustez: pesos iguais, pesos ACP, média aritmética
  * probit: y = 1 se IDF > mediana; M1..M4; efeitos marginais na média;
    Pseudo-R2 de McFadden; % de classificação correta (corte 0,5)

Uso: python3 scripts/04_idf_probit.py  (a partir da pasta idf_mt)
Saídas em resultados/
"""
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

pd.set_option("display.width", 200)
OUT = "resultados"
df = pd.read_csv("dados/processados/base_idf_mt.csv")

DIM = {
    "D1": ["I01", "I02", "I03", "I04"],
    "D2": ["I05", "I06"],
    "D3": ["I07", "I08", "I09"],
    "D4": ["I10", "I11", "I12", "I13", "I14"],
    "D5": ["I15", "I16"],
}
NEGATIVOS = ["I13"]
PESOS_DELPHI = {"D1": .25, "D2": .20, "D3": .25, "D4": .15, "D5": .15}
ROTULO = {
    "I01": "BL fixa/100 dom", "I02": "4G (% moradores)", "I03": "5G (% moradores)",
    "I04": "Backhaul (presença)", "I05": "PA fin./10 mil hab", "I06": "Coop./10 mil hab",
    "I07": "Pix receb. PJ/mês por empresa", "I08": "Empresas recebedoras Pix (%)",
    "I09": "Crédito/empresa (R$ mil)", "I10": "Empresas ativas/1000 hab",
    "I11": "Simples Nacional (%)", "I12": "Tx. abertura (%)", "I13": "Tx. encerramento (%)",
    "I14": "Idade média (anos)", "I15": "Adultos 25+ médio+ (%)",
    "I16": "Pessoas 18+ estudando/1000 hab (proxy)",
}
INDS = [i for d in DIM.values() for i in d]

# ------------------------------------------------------------ Quadro 4: descritivas
desc = df[INDS].agg(["mean", "std", "min", "max"]).T
desc["cv_%"] = desc["std"] / desc["mean"] * 100
desc.insert(0, "indicador", desc.index.map(ROTULO))
desc.round(2).to_csv(f"{OUT}/q4_descritivas_indicadores.csv")
print("\nQuadro 4 - Descritivas\n", desc.round(2).to_string())

# ------------------------------------------------------------ normalização
norm = pd.DataFrame(index=df.index)
excluidos = []
for i in INDS:
    x = df[i].astype(float)
    p1, p99 = np.percentile(x, [1, 99])
    x = x.clip(p1, p99)
    if x.max() == x.min():               # sem variância (ex.: I04) -> não discrimina
        excluidos.append(i)
        continue
    z = (x - x.min()) / (x.max() - x.min())
    norm[i] = 1 - z if i in NEGATIVOS else z
print("\nIndicadores sem variância (excluídos da normalização):", excluidos)

S = pd.DataFrame({d: norm[[i for i in ins if i in norm]].mean(axis=1) for d, ins in DIM.items()})
EPS = 0.01   # piso para a média geométrica (evita IDF = 0 quando um subíndice é exatamente 0)
n_piso = int((S < EPS).sum().sum())
print(f"Subíndices abaixo do piso {EPS} (ajustados só na média geométrica): {n_piso}")


def idf_geom(S, w):
    w = pd.Series(w) / sum(w.values())
    return 100 * np.exp((np.log(S.clip(lower=EPS)) * w).sum(axis=1))


def idf_arit(S, w):
    w = pd.Series(w) / sum(w.values())
    return 100 * (S * w).sum(axis=1)


df = pd.concat([df, S.add_prefix("S_")], axis=1)
df["IDF"] = idf_geom(S, PESOS_DELPHI)

# faixas por quartis
q = df.IDF.quantile([.25, .5, .75]).values
df["faixa"] = pd.cut(df.IDF, [-np.inf, *q, np.inf], labels=["Baixa", "Média-baixa", "Média-alta", "Alta"])

# ------------------------------------------------------------ robustez (Quadro 5)
Z = (S - S.mean()) / S.std()
autoval, autovet = np.linalg.eigh(np.corrcoef(Z.T))
pc1 = autovet[:, -1]
pesos_acp = dict(zip(S.columns, pc1 ** 2 / (pc1 ** 2).sum()))
var_pc1 = autoval[-1] / autoval.sum()
rob = pd.DataFrame({
    "Delphi (ref.)": df.IDF,
    "Pesos iguais": idf_geom(S, {d: .2 for d in DIM}),
    "ACP": idf_geom(S, pesos_acp),
    "Aritmética": idf_arit(S, PESOS_DELPHI),
})
spear = rob.corr(method="spearman")
pvals = pd.DataFrame([[spearmanr(rob[a], rob[b]).pvalue for b in rob] for a in rob], rob.columns, rob.columns)
spear.round(3).to_csv(f"{OUT}/q5_spearman_robustez.csv")
print("\nPesos ACP:", {k: round(v, 3) for k, v in pesos_acp.items()}, f"| var. explicada PC1 = {var_pc1:.3f}")
print("\nQuadro 5 - Spearman\n", spear.round(3).to_string(), "\n p-valor máx:", pvals.values.max())

# ------------------------------------------------------------ resultados agregados
print(f"\nIDF médio = {df.IDF.mean():.2f} (DP = {df.IDF.std():.2f}); "
      f"mín = {df.IDF.min():.2f} ({df.loc[df.IDF.idxmin(), 'municipio']}); "
      f"máx = {df.IDF.max():.2f} ({df.loc[df.IDF.idxmax(), 'municipio']})")
print(df.faixa.value_counts().reindex(["Baixa", "Média-baixa", "Média-alta", "Alta"]).to_string())
print("\nMédias dos subíndices:\n", S.mean().round(3).to_string())

ranking = df.sort_values("IDF", ascending=False)[
    ["municipio", "uf", "IDF", "faixa", *[f"S_{d}" for d in DIM]]].reset_index(drop=True)
ranking.index += 1
ranking.round(3).to_csv(f"{OUT}/idf_ranking.csv", index_label="posicao")
print("\nRanking\n", ranking.round(2).to_string())

# ------------------------------------------------------------ Quadro 6: por grupo
df["pop_mil"] = df.pop_2024 / 1000
df["pib_pc_mil"] = df.pib_pc_2021 / 1000
agg = {"IDF": "mean", "idhm_2010": "mean", "pop_mil": "mean", "pib_pc_mil": "mean"}
g1 = df.groupby("faixa", observed=True).agg(n=("IDF", "size"), **{k: (k, v) for k, v in agg.items()})
g2 = df.groupby("uf").agg(n=("IDF", "size"), **{k: (k, v) for k, v in agg.items()})
q6 = pd.concat([g1.iloc[::-1], g2.loc[["MT", "MS", "GO"]]])
q6.round(3).to_csv(f"{OUT}/q6_grupos.csv")
print("\nQuadro 6\n", q6.round(3).to_string())

# ------------------------------------------------------------ probit (Quadro 7)
df["y"] = (df.IDF > df.IDF.median()).astype(int)
df["ln_pop"] = np.log(df.pop_2024)
df["ln_pibpc"] = np.log(df.pib_pc_2021)
MODELOS = {
    "M1": ["idhm_2010", "ln_pop"],
    "M2": ["idhm_2010", "ln_pop", "ln_pibpc"],
    "M3": ["idhm_2010", "ln_pop", "campus"],
    "M4": ["idhm_2010", "ln_pop", "ln_pibpc", "campus", "agro_va_pct"],
}
NOMES = {"const": "Constante", "idhm_2010": "IDHM", "ln_pop": "ln(Pop)", "ln_pibpc": "ln(PIB p.c.)",
         "campus": "Campus", "agro_va_pct": "Agropecuária (% VA)"}
print(f"\ny = 1 (IDF > mediana {df.IDF.median():.2f}): {df.y.sum()} de {len(df)}")


def estrelas(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .10 else ""


tab, efeitos, resumo = {}, [], []
for m, xs in MODELOS.items():
    X = sm.add_constant(df[xs])
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r = sm.Probit(df.y, X).fit(disp=0, maxiter=200)
        avisos = [str(a.message) for a in w]
    sep = any("separation" in a.lower() for a in avisos) or r.prsquared > .99
    pred = (r.predict(X) >= .5).astype(int)
    acerto = (pred == df.y).mean() * 100
    col = {}
    for v in X.columns:
        col[NOMES[v]] = f"{r.params[v]:.3f}{estrelas(r.pvalues[v])}\n({r.bse[v]:.3f})"
    col["Pseudo-R² McFadden"] = f"{r.prsquared:.3f}"
    col["% Classificação correta"] = f"{acerto:.1f}"
    col["Log-verossimilhança"] = f"{r.llf:.2f}"
    col["LR chi² (p)"] = f"{r.llr:.2f} ({r.llr_pvalue:.4f})"
    col["AIC"] = f"{r.aic:.2f}"
    col["n"] = str(int(r.nobs))
    tab[m] = col
    me_media = r.get_margeff(at="mean").summary_frame()
    me_ame = r.get_margeff(at="overall").summary_frame()
    for v in xs:
        efeitos.append({"modelo": m, "variavel": NOMES[v],
                        "EM_na_media": me_media.loc[v, "dy/dx"], "p_EM_media": me_media.loc[v, "Pr(>|z|)"],
                        "EM_medio_AME": me_ame.loc[v, "dy/dx"], "p_AME": me_ame.loc[v, "Pr(>|z|)"]})
    resumo.append(f"{m}: separação perfeita/quase perfeita = {sep}; avisos = {set(avisos) or '-'}")
    print(f"\n===== {m} =====\n", r.summary2().tables[1].round(4).to_string())

ordem = ["Constante", "IDHM", "ln(Pop)", "ln(PIB p.c.)", "Campus", "Agropecuária (% VA)",
         "Pseudo-R² McFadden", "% Classificação correta", "Log-verossimilhança", "LR chi² (p)", "AIC", "n"]
q7 = pd.DataFrame(tab).reindex(ordem).fillna("—")
q7.to_csv(f"{OUT}/q7_probit.csv")
ef = pd.DataFrame(efeitos)
ef.round(4).to_csv(f"{OUT}/q7b_efeitos_marginais.csv", index=False)
print("\nQuadro 7 - Probit (coef., erro-padrão entre parênteses; *** p<0,01 ** p<0,05 * p<0,10)\n",
      q7.replace("\n", " ", regex=True).to_string())
print("\nEfeitos marginais\n", ef.round(4).to_string())
print("\n".join(resumo))

# correlações entre regressores (multicolinearidade)
cor = df[["idhm_2010", "ln_pop", "ln_pibpc", "campus", "agro_va_pct"]].corr().round(3)
cor.to_csv(f"{OUT}/correlacao_regressores.csv")
print("\nCorrelação entre regressores\n", cor.to_string())

df.drop(columns=["pop_mil", "pib_pc_mil"]).round(6).to_csv(f"{OUT}/base_final_com_idf.csv", index=False)
norm.add_suffix("_norm").assign(municipio=df.municipio).round(4).to_csv(f"{OUT}/indicadores_normalizados.csv", index=False)

with pd.ExcelWriter(f"{OUT}/IDF_MT_resultados.xlsx") as xw:
    df.drop(columns=["pop_mil", "pib_pc_mil"]).to_excel(xw, "Base", index=False)
    desc.round(3).to_excel(xw, "Q4 Descritivas")
    ranking.round(3).to_excel(xw, "Ranking IDF", index_label="posicao")
    spear.round(3).to_excel(xw, "Q5 Spearman")
    q6.round(3).to_excel(xw, "Q6 Grupos")
    q7.to_excel(xw, "Q7 Probit")
    ef.round(4).to_excel(xw, "Q7b Efeitos marginais", index=False)
    cor.to_excel(xw, "Correl. regressores")
print("\nArquivos salvos em", OUT)
