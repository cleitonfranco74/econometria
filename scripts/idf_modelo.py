"""IDF-MP: cálculo do índice, robustez e modelos de determinantes (versão do artigo IDF-MP).

Uso: python scripts/idf_modelo.py [amostra]
     amostra = "artigo" (padrão; 33 municípios) ou "todos" (50-600 mil, só sem capitais; 42)
Entrada: data/processed/base_municipal_CO.csv (build_indicadores.py)
Saída  : resultados/<amostra>/
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings("ignore")
AMOSTRA = sys.argv[1] if len(sys.argv) > 1 else "artigo"
ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "resultados" / AMOSTRA
RES.mkdir(parents=True, exist_ok=True)

POP_MIN, POP_MAX = 50_000, 600_000
CAPITAIS = {"5103403", "5002704", "5208707"}
# Municípios goianos da RIDE-DF ("entorno de Brasília") com mais de 50 mil hab.
ENTORNO_DF = {"5200258", "5212501", "5221858", "5217609", "5215231",
              "5205497", "5219753", "5208004", "5206206"}

DIM = {"D1": ["I01", "I02", "I03", "I04"], "D2": ["I05", "I06"], "D3": ["I07", "I08", "I09"],
       "D4": ["I10", "I11", "I12", "I13", "I14"], "D5": ["I15", "I16"]}
IND = [i for v in DIM.values() for i in v]
PESOS_DELPHI = {"D1": .25, "D2": .20, "D3": .25, "D4": .15, "D5": .15}
NEGATIVOS = {"I13"}
NOMES = {
    "I01": "BL fixa/100 dom", "I02": "4G (% moradores)", "I03": "5G (% moradores)", "I04": "Backhaul fibra",
    "I05": "PA financeiro/10 mil hab", "I06": "PAC cooperativas/10 mil hab", "I07": "Pix PJ trans./empresa/mês",
    "I08": "Empresas recebedoras Pix (%)", "I09": "Crédito/empresa (R$ mil)", "I10": "Empresas ativas/1000 hab",
    "I11": "Optantes Simples (%)", "I12": "Taxa de abertura (%)", "I13": "Taxa de encerramento (%)",
    "I14": "Idade média (anos)", "I15": "25+ com médio completo+ (%)", "I16": "Matrículas técnicas e superiores/1000 hab"}
out_txt = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out_txt.append(s)


def estrelas(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .10 else ""


# ---------------------------------------------------------------- amostra
base = pd.read_csv(ROOT / "data" / "processed" / "base_municipal_CO.csv", dtype={"cod_ibge": str})
am = base[(base.pop_2024 >= POP_MIN) & (base.pop_2024 <= POP_MAX) & ~base.cod_ibge.isin(CAPITAIS)]
if AMOSTRA == "artigo":
    am = am[~am.cod_ibge.isin(ENTORNO_DF)]
am = am.sort_values(["uf", "municipio"]).reset_index(drop=True)
assert am[IND].notna().all().all(), am[IND].isna().sum()
N = len(am)
log(f"Amostra '{AMOSTRA}': n = {N} {am.uf.value_counts().to_dict()}")
am[["cod_ibge", "municipio", "uf", "pop_2024"] + IND].to_csv(RES / "indicadores_brutos.csv", index=False)


# ---------------------------------------------------------------- índice
def normaliza(df, metodo="minmax"):
    out = pd.DataFrame(index=df.index)
    for c in IND:
        x = df[c].astype(float)
        if x.std() == 0:  # I04 constante: sem variação, não entra
            continue
        x = x.clip(x.quantile(.01), x.quantile(.99))
        z = (x - x.min()) / (x.max() - x.min()) if metodo == "minmax" else (x - x.mean()) / x.std()
        out[c] = (1 - z if metodo == "minmax" else -z) if c in NEGATIVOS else z
    return out


def subindices(norm):
    return pd.DataFrame({d: norm[[i for i in v if i in norm]].mean(axis=1) for d, v in DIM.items()})


def geo(S, w):
    w = pd.Series(w)[S.columns] / sum(w.values())
    return 100 * np.exp((np.log(S.clip(lower=1e-6)) * w).sum(axis=1))


def arit(S, w):
    w = pd.Series(w)[S.columns] / sum(w.values())
    return 100 * (S * w).sum(axis=1)


def cronbach(X):
    X = X.dropna(axis=1)
    k = X.shape[1]
    if k < 2:
        return np.nan
    return k / (k - 1) * (1 - X.var(ddof=1).sum() / X.sum(axis=1).var(ddof=1))


norm = normaliza(am)
S = subindices(norm)
n_zero = int((S == 0).any(axis=1).sum())
am = pd.concat([am, S.add_prefix("S_")], axis=1)
am["IDF"] = geo(S, PESOS_DELPHI)
am["faixa"] = pd.qcut(am.IDF, 4, labels=["Baixa", "Média-baixa", "Média-alta", "Alta"])
am["faixa_n"] = am.faixa.cat.codes
am["alta"] = (am.IDF > am.IDF.median()).astype(int)
log(f"Municípios com algum subíndice = 0 (truncado em 1e-6 na média geométrica): {n_zero}")

# Quadro A — descritivas dos 16 indicadores
desc_ind = am[IND].agg(["mean", "std", "min", "max"]).T
desc_ind["CV (%)"] = desc_ind["std"] / desc_ind["mean"] * 100
desc_ind.insert(0, "indicador", desc_ind.index.map(NOMES))
desc_ind.round(2).to_csv(RES / "quadroA_descritivas_indicadores.csv")

# Quadro 4 — IDF e subíndices + alfa de Cronbach
q4 = pd.concat([am.IDF, S], axis=1).agg(["mean", "std", "min", "max"])
q4.loc["alfa_cronbach"] = [np.nan] + [cronbach(norm[[i for i in v if i in norm]]) for v in DIM.values()]
q4.index = ["Média", "Desvio-padrão", "Mínimo", "Máximo", "Alfa de Cronbach"]
q4.round(3).to_csv(RES / "quadro4_idf_subindices.csv")
log("\nQuadro 4 — IDF-MP e subíndices\n" + q4.round(3).to_string())

# Quadro 5 — robustez do ranking
Sz = (S - S.mean()) / S.std()
ev, evec = np.linalg.eigh(np.corrcoef(Sz.T))
load = np.abs(evec[:, -1])
pesos_pca = dict(zip(S.columns, load ** 2 / (load ** 2).sum()))
alt = pd.DataFrame({
    "Pesos iguais, agregação geométrica": geo(S, {d: .2 for d in DIM}),
    "Pesos por PCA, agregação geométrica": geo(S, pesos_pca),
    "Pesos Delphi, agregação aritmética": arit(S, PESOS_DELPHI),
    "Normalização por escore z (agregação aritmética)": arit(subindices(normaliza(am, "z")), PESOS_DELPHI)})
rk = am.IDF.rank(ascending=False)
q5 = pd.DataFrame({"rho_Spearman": [stats.spearmanr(am.IDF, alt[c])[0] for c in alt],
                   "variacao_media_posicoes": [(rk - alt[c].rank(ascending=False)).abs().mean() for c in alt]},
                  index=alt.columns)
q5.round(3).to_csv(RES / "quadro5_robustez_ranking.csv")
log("\nPesos PCA:", {k: round(v, 3) for k, v in pesos_pca.items()})
log("\nQuadro 5 — Robustez do ranking\n" + q5.round(3).to_string())

# ---------------------------------------------------------------- determinantes
am["pop_mil"] = am.pop_2024 / 1e3
am["pib_pc_mil"] = am.pib_pc_2021 / 1e3
q6 = am[["idhm_2010", "pop_mil", "pib_pc_mil", "campus", "agro_va_pct"]].agg(["mean", "std", "min", "max"]).T
q6["corr_IDF"] = [am[c].corr(am.IDF) for c in q6.index]
q6.index = ["IDHM (2010)", "População 2024 (mil)", "PIB per capita 2021 (R$ mil)",
            "Campus de ensino superior presencial (proporção)", "Agropecuária no VA 2021 (%)"]
q6.round(3).to_csv(RES / "quadro6_explicativas.csv")
log("\nQuadro 6 — Variáveis explicativas\n" + q6.round(3).to_string())

# Quadro 7 — MQO com erros HC3. Campus = curso superior presencial no município (Censo Superior 2024).
specs = {"M1": "IDF ~ idhm_2010 + ln_pop",
         "M2": "IDF ~ idhm_2010 + ln_pop + ln_pib_pc",
         "M3": "IDF ~ idhm_2010 + ln_pop + ln_pib_pc + campus",
         "M4": "IDF ~ idhm_2010 + ln_pop + ln_pib_pc + campus + agro_va_pct",
         "M5": "IDF ~ idhm_2010 + ln_pop + ln_pib_pc + campus + agro_va_pct + C(uf)"}
VARS = ["Intercept", "idhm_2010", "ln_pop", "ln_pib_pc", "campus", "agro_va_pct", "C(uf)[T.MS]", "C(uf)[T.MT]"]
q7, fits = {}, {}
for m, f in specs.items():
    r = smf.ols(f, am).fit(cov_type="HC3")
    fits[m] = r
    X = r.model.exog
    vif = max(variance_inflation_factor(X, i) for i in range(1, X.shape[1])) if X.shape[1] > 2 else np.nan
    col = {}
    for v in VARS:
        if v in r.params:
            col[v] = f"{r.params[v]:.2f}{estrelas(r.pvalues[v])} ({r.bse[v]:.2f})"
    col.update({"R² ajustado": f"{r.rsquared_adj:.3f}", "AIC": f"{r.aic:.1f}", "BIC": f"{r.bic:.1f}",
                "VIF máximo": f"{vif:.2f}", "N": int(r.nobs)})
    q7[m] = col
q7 = pd.DataFrame(q7).reindex(VARS + ["R² ajustado", "AIC", "BIC", "VIF máximo", "N"]).fillna("—")
q7.to_csv(RES / "quadro7_mqo.csv")
log("\nQuadro 7 — MQO (VD: IDF-MP 0-100), EP robustos HC3; *** p<0,01 ** p<0,05 * p<0,10\n" + q7.to_string())
for m in fits:
    log(f"\n===== {m} =====\n{fits[m].summary()}")

# Diagnósticos do M1
m1 = fits["M1"]
m1_ols = smf.ols(specs["M1"], am).fit()
bp = het_breuschpagan(m1_ols.resid, m1_ols.model.exog)
reset = linear_reset(m1_ols, power=2, use_f=True)
sw = stats.shapiro(m1_ols.resid)
cook = m1_ols.get_influence().cooks_distance[0]
infl = am.loc[cook > 4 / N, ["municipio", "uf"]].assign(cook=cook[cook > 4 / N])
diag = pd.Series({"Breusch-Pagan LM (p)": bp[1], "RESET Ramsey F (p)": float(reset.pvalue),
                  "Shapiro-Wilk W": sw.statistic, "Shapiro-Wilk (p)": sw.pvalue,
                  "Limiar Cook 4/n": 4 / N})
diag.round(4).to_csv(RES / "diagnosticos_M1.csv")
log("\nDiagnósticos M1\n" + diag.round(4).to_string())
log("Observações influentes (Cook > 4/n):\n" + infl.round(3).to_string())
log(f"Leitura M1: +0,01 no IDHM => {m1.params.idhm_2010 / 100:.2f} pontos; dobrar a população => "
    f"{np.log(2) * m1.params.ln_pop:.2f} pontos")
am["resid_M1"] = m1_ols.resid
am["IDF_esperado_M1"] = m1_ols.fittedvalues

# Regressões por dimensão (M1)
dim_rows = {}
for d in DIM:
    am[f"{d}x100"] = am[f"S_{d}"] * 100
    r = smf.ols(f"{d}x100 ~ idhm_2010 + ln_pop", am).fit(cov_type="HC3")
    dim_rows[d] = {v: f"{r.params[v]:.2f}{estrelas(r.pvalues[v])} ({r.bse[v]:.2f})" for v in r.params.index} | \
                  {"R² ajustado": f"{r.rsquared_adj:.3f}"}
qd = pd.DataFrame(dim_rows)
qd.to_csv(RES / "apendice_regressoes_dimensao.csv")
log("\nApêndice — M1 por dimensão (subíndice x100), HC3\n" + qd.to_string())

# Quadro 8 — robustez com VD discreta (especificação M1)
X = sm.add_constant(am[["idhm_2010", "ln_pop"]])
q8 = {}
q8["MQO (índice contínuo)"] = {v: f"{m1.params[v]:.2f}{estrelas(m1.pvalues[v])} ({m1.bse[v]:.2f})"
                               for v in ["idhm_2010", "ln_pop"]} | {"Ajuste": f"R² aj. = {m1.rsquared_adj:.3f}"}
try:
    pr = sm.Probit(am.alta, X).fit(disp=0, cov_type="HC0", maxiter=200)
    me = pr.get_margeff(at="overall")
    q8["Probit (efeito marginal médio)"] = {
        v: f"{me.margeff[i]:.3f}{estrelas(me.pvalues[i])} ({me.margeff_se[i]:.3f})"
        for i, v in enumerate(["idhm_2010", "ln_pop"])} | {"Ajuste": f"Pseudo-R² = {pr.prsquared:.3f}"}
    acc = ((pr.predict(X) > .5) == am.alta).mean() * 100
    log(f"\nProbit: % classificação correta = {acc:.1f}\n{pr.summary()}")
except Exception as e:
    q8["Probit (efeito marginal médio)"] = {"Ajuste": f"falhou: {e}"}
lpm = sm.OLS(am.alta, X).fit(cov_type="HC3")
q8["Probabilidade linear"] = {v: f"{lpm.params[v]:.3f}{estrelas(lpm.pvalues[v])} ({lpm.bse[v]:.3f})"
                              for v in ["idhm_2010", "ln_pop"]} | {"Ajuste": f"R² = {lpm.rsquared:.3f}"}
ol = OrderedModel(am.faixa_n, am[["idhm_2010", "ln_pop"]], distr="logit").fit(method="bfgs", disp=0, maxiter=1000)
ll0 = OrderedModel(am.faixa_n, np.zeros((N, 1)) + np.arange(N)[:, None] * 0, distr="logit") if False else None
null_ll = np.sum(np.log(am.faixa_n.value_counts(normalize=True).reindex(am.faixa_n).values))
pseudo_ol = 1 - ol.llf / null_ll
# razões de chance: IDHM por +0,01 (escala do índice), ln(pop) por unidade
or_idhm, or_pop = np.exp(ol.params.idhm_2010 * .01), np.exp(ol.params.ln_pop)
q8["Logit ordenado (razão de chance)"] = {
    "idhm_2010": f"{or_idhm:.3f}{estrelas(ol.pvalues.idhm_2010)} (coef {ol.params.idhm_2010:.2f}; EP {ol.bse.idhm_2010:.2f})",
    "ln_pop": f"{or_pop:.3f}{estrelas(ol.pvalues.ln_pop)} (coef {ol.params.ln_pop:.2f}; EP {ol.bse.ln_pop:.2f})",
    "Ajuste": f"Pseudo-R² = {pseudo_ol:.3f}"}
log(f"\nLogit ordenado\n{ol.summary()}")
# Teste de Brant aproximado: logits binários acumulados, Wald de igualdade das inclinações
bins = []
for j in range(1, 4):
    yb = (am.faixa_n >= j).astype(int)
    try:
        bins.append(sm.Logit(yb, X).fit(disp=0, maxiter=200))
    except Exception:
        bins = []
        break
if len(bins) == 3:
    b = np.concatenate([r.params[1:].values for r in bins])
    V = np.zeros((6, 6))
    for i, r in enumerate(bins):
        V[2 * i:2 * i + 2, 2 * i:2 * i + 2] = r.cov_params().values[1:, 1:]
    D = np.array([[1, 0, -1, 0, 0, 0], [0, 1, 0, -1, 0, 0], [1, 0, 0, 0, -1, 0], [0, 1, 0, 0, 0, -1]])
    w = (D @ b) @ np.linalg.pinv(D @ V @ D.T) @ (D @ b)
    q8["Logit ordenado (razão de chance)"]["Brant aprox. (p)"] = f"{stats.chi2.sf(w, 4):.3f}"
q8 = pd.DataFrame(q8)
q8.to_csv(RES / "quadro8_robustez_discreta.csv")
log("\nQuadro 8 — Robustez com VD discreta (M1)\n" + q8.to_string())

# Robustez adicional da regressão
rob = {}
for c in alt:
    am["_y"] = alt[c]
    r = smf.ols("_y ~ idhm_2010 + ln_pop", am).fit(cov_type="HC3")
    rob[f"MQO, índice: {c}"] = r
r = smf.ols(specs["M1"], am[cook <= 4 / N]).fit(cov_type="HC3")
rob["MQO sem influentes (Cook > 4/n)"] = r
qr = smf.quantreg(specs["M1"], am).fit(q=.5)
rob["Regressão quantílica (mediana)"] = qr
qrob = pd.DataFrame({k: {v: f"{r.params[v]:.2f}{estrelas(r.pvalues[v])} ({r.bse[v]:.2f})"
                         for v in ["idhm_2010", "ln_pop"]} | {"N": int(r.nobs)} for k, r in rob.items()}).T
qrob.to_csv(RES / "robustez_regressao.csv")
log("\nRobustez da regressão (M1)\n" + qrob.to_string())

# ---------------------------------------------------------------- saídas finais
cols = ["cod_ibge", "municipio", "uf", "pop_2024", "idhm_2010", "pib_pc_2021", "agro_va_pct",
        "S_D1", "S_D2", "S_D3", "S_D4", "S_D5", "IDF", "faixa", "IDF_esperado_M1", "resid_M1"]
res = am[cols].sort_values("IDF", ascending=False)
res.to_csv(RES / "idf_ranking.csv", index=False)
log("\nRanking IDF-MP\n" + res.round(3).to_string(index=False))
log(f"\nIDF-MP: média {am.IDF.mean():.2f}; DP {am.IDF.std():.2f}; mín {am.IDF.min():.2f} "
    f"({am.loc[am.IDF.idxmin(), 'municipio']}); máx {am.IDF.max():.2f} ({am.loc[am.IDF.idxmax(), 'municipio']})")
log("Faixas:", am.faixa.value_counts().sort_index().to_dict())
(RES / "saida_completa.txt").write_text("\n".join(out_txt))
