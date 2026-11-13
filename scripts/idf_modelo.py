"""Constrói os indicadores do IDF-MT, calcula o índice e estima os modelos probit do artigo.

Entrada : data/raw/ (gerado por coleta_apis.py e cnpj_download_filter.py)
Saída   : data/processed/indicadores_idf.csv, data/processed/idf_resultados.csv,
          resultados/*.csv|txt
"""
import sys
import unicodedata
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
RES = ROOT / "resultados" / (sys.argv[1] if len(sys.argv) > 1 else "principal")
PROC.mkdir(parents=True, exist_ok=True)
RES.mkdir(parents=True, exist_ok=True)

POP_MIN, POP_MAX = 50_000, 600_000
CAPITAIS = {"5103403", "5002704", "5208707"}
# Variante "sem_metro": exclui periferias metropolitanas de GO (RM de Goiânia e Entorno do DF/RIDE),
# tentativa de aproximar os 14 municípios goianos do artigo (lista não publicada).
PERIFERIA_METRO = {"5201405", "5220454", "5221403", "5208806",  # Aparecida, Sen. Canedo, Trindade, Goianira
                   "5200258", "5212501", "5221858", "5217609",  # Águas Lindas, Luziânia, Valparaíso, Planaltina
                   "5215231", "5205497", "5219753"}             # Novo Gama, Cid. Ocidental, Sto. Ant. Descoberto
AMOSTRA = sys.argv[1] if len(sys.argv) > 1 else "principal"
REF = pd.Timestamp("2024-12-31")

DIM = {
    "D1": ["I01", "I02", "I03", "I04"],
    "D2": ["I05", "I06"],
    "D3": ["I07", "I08", "I09"],
    "D4": ["I10", "I11", "I12", "I13", "I14"],
    "D5": ["I15", "I16"],
}
PESOS_DELPHI = {"D1": .25, "D2": .20, "D3": .25, "D4": .15, "D5": .15}
NEGATIVOS = {"I13"}
NOMES = {
    "I01": "BL fixa/100 dom", "I02": "4G (% moradores)", "I03": "5G (% moradores)", "I04": "Backhaul fibra",
    "I05": "PA financeiro/10 mil hab", "I06": "PAC cooperativas/10 mil hab", "I07": "Pix PJ trans./empresa/mês",
    "I08": "Empresas recebedoras Pix (%)", "I09": "Crédito/empresa (R$ mil)", "I10": "Empresas ativas/1000 hab",
    "I11": "Optantes Simples (%)", "I12": "Taxa de abertura (%)", "I13": "Taxa de encerramento (%)",
    "I14": "Idade média (anos)", "I15": "25+ com médio completo+ (%)", "I16": "Freq. ensino superior/1000 hab",
}


def chave(nome: str) -> str:
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode().upper()
    return "".join(ch for ch in s if ch.isalnum())


# ---------------------------------------------------------------- base municipal
ibge = pd.read_csv(RAW / "ibge.csv", dtype={"cod_ibge": str})
ibge["k"] = ibge.uf + "_" + ibge.municipio.map(chave)
idhm = pd.read_csv(RAW / "ipea_idhm_2010.csv", dtype={"cod_ibge": str})
base = ibge.merge(idhm, on="cod_ibge", how="left")

# ---------------------------------------------------------------- Anatel (D1)
ac = pd.read_csv(RAW / "anatel_acessos_202412.csv", dtype={"Código IBGE": str})
bl = ac[ac["Serviço"] == "Banda Larga Fixa"].set_index("Código IBGE")
base["acessos_blf"] = base.cod_ibge.map(bl["Acessos"])
base["I01"] = base.acessos_blf / base.domicilios_2022 * 100  # acessos por 100 domicílios (Censo 2022)
cob = pd.read_csv(RAW / "anatel_cobertura_202412.csv", dtype={"Código IBGE": str})
for ind, tec in [("I02", "4G"), ("I03", "5G")]:
    c = cob[cob.Tecnologia == tec].set_index("Código IBGE")["% moradores cobertos"]
    base[ind] = base.cod_ibge.map(c)
# I04 (backhaul de fibra): sem arquivo aberto localizado; o artigo reporta valor 1 em todos
# os municípios da amostra (DP = 0). Mantido como constante e excluído da normalização.
base["I04"] = 1.0

# ---------------------------------------------------------------- BCB (D2, D3)
ag = pd.read_csv(RAW / "bcb_agencias.csv", dtype={"MunicipioIbge": str})
ag = ag[pd.to_datetime(ag.DataInicio, dayfirst=True, errors="coerce") <= REF]
po = pd.read_csv(RAW / "bcb_postos.csv", dtype={"MunicipioIbge": str})
pac = po[po.TipoPosto.str.contains("PAC")]
pa_outros = po[po.TipoPosto.str.contains("PAB|PAA|PAT")]
base["n_agencias"] = base.cod_ibge.map(ag.groupby("MunicipioIbge").size()).fillna(0)
base["n_pac"] = base.cod_ibge.map(pac.groupby("MunicipioIbge").size()).fillna(0)
base["n_postos_outros"] = base.cod_ibge.map(pa_outros.groupby("MunicipioIbge").size()).fillna(0)
base["I05"] = (base.n_agencias + base.n_pac + base.n_postos_outros) / base.pop_2024 * 1e4
base["I06"] = base.n_pac / base.pop_2024 * 1e4

pix = pd.read_csv(RAW / "bcb_pix_2024.csv", dtype={"Municipio_Ibge": str})
pixm = pix.groupby("Municipio_Ibge").agg(pix_qt_rec_pj=("QT_RecebedorPJ", "mean"),
                                         pix_pes_rec_pj=("QT_PES_RecebedorPJ", "mean"))
base = base.merge(pixm, left_on="cod_ibge", right_index=True, how="left")

est = pd.read_csv(RAW / "bcb_estban_202412.csv")
est["k"] = est.UF + "_" + est.MUNICIPIO.map(chave)
base["credito_estban"] = base.k.map(est.groupby("k")["VERBETE_160_OPERACOES_DE_CREDITO"].sum()).fillna(0)

# ---------------------------------------------------------------- Receita Federal / CNPJ (D4)
with zipfile.ZipFile(RAW / "cnpj" / "Municipios.zip") as z:
    rfm = pd.read_csv(z.open(z.namelist()[0]), sep=";", header=None, encoding="latin-1",
                      names=["mun_rf", "nome"], dtype=str)
estab = pd.concat(pd.read_csv(f, dtype=str) for f in sorted((RAW / "cnpj").glob("Estabelecimentos*_CO.csv.gz")))
estab = estab.merge(rfm, on="mun_rf", how="left")
estab["k"] = estab.uf + "_" + estab.nome.map(chave)
estab["dt_ini"] = pd.to_datetime(estab.data_inicio, format="%Y%m%d", errors="coerce")
estab["dt_sit"] = pd.to_datetime(estab.data_situacao, format="%Y%m%d", errors="coerce")
ativos = estab[(estab.situacao == "02") & (estab.dt_ini <= REF)]
abertos = estab[estab.dt_ini.dt.year == 2024]
baixados = estab[(estab.situacao == "08") & (estab.dt_sit.dt.year == 2024)]

simples = pd.read_csv(RAW / "cnpj" / "Simples_CO.csv.gz", dtype=str)
opt = set(simples.loc[simples.opcao_simples == "S", "cnpj_basico"])
ativos = ativos.assign(simples=ativos.cnpj_basico.isin(opt),
                       idade=(REF - ativos.dt_ini).dt.days / 365.25)
g = ativos.groupby("k")
base["empresas_ativas"] = base.k.map(g.size())
base["ativas_simples"] = base.k.map(g.simples.sum())
base["idade_media"] = base.k.map(g.idade.mean())
base["abertas_2024"] = base.k.map(abertos.groupby("k").size()).fillna(0)
base["baixadas_2024"] = base.k.map(baixados.groupby("k").size()).fillna(0)

base["I07"] = base.pix_qt_rec_pj / base.empresas_ativas
base["I08"] = base.pix_pes_rec_pj / base.empresas_ativas * 100
base["I09"] = base.credito_estban / base.empresas_ativas / 1e3
base["I10"] = base.empresas_ativas / base.pop_2024 * 1e3
base["I11"] = base.ativas_simples / base.empresas_ativas * 100
base["I12"] = base.abertas_2024 / base.empresas_ativas * 100
base["I13"] = base.baixadas_2024 / (base.empresas_ativas + base.baixadas_2024) * 100
base["I14"] = base.idade_media

# ---------------------------------------------------------------- Capital humano (D5)
base["I15"] = (base.pop25_medio_sup_inc + base.pop25_superior) / base.pop25_total * 100
base["I16"] = base.freq_superior_2022 / base.pop_2024 * 1e3  # proxy: Censo 2022 (ver README)

# ---------------------------------------------------------------- controles do probit
base["ln_pop"] = np.log(base.pop_2024)
base["pib_pc_2021"] = base.pib_2021_mil * 1e3 / base.pop_2021
base["ln_pib_pc"] = np.log(base.pib_pc_2021)
base["agro_va_pct"] = base.va_agro_2021_mil / base.va_total_2021_mil * 100
base.to_csv(PROC / "base_municipal_CO.csv", index=False)

# ---------------------------------------------------------------- amostra
am = base[(base.pop_2024 >= POP_MIN) & (base.pop_2024 <= POP_MAX) & ~base.cod_ibge.isin(CAPITAIS)].copy()
if AMOSTRA == "sem_metro":
    am = am[~am.cod_ibge.isin(PERIFERIA_METRO)].copy()
am = am.sort_values(["uf", "municipio"]).reset_index(drop=True)
IND = [i for d in DIM.values() for i in d]
falt = am[IND].isna().sum()
assert falt.sum() == 0, f"indicadores faltantes:\n{falt[falt > 0]}"
am[["cod_ibge", "municipio", "uf", "pop_2024"] + IND].to_csv(RES / "indicadores_idf.csv", index=False)


# ---------------------------------------------------------------- índice
def normaliza(df):
    out = pd.DataFrame(index=df.index)
    for c in IND:
        x = df[c].astype(float)
        if x.std() == 0:  # constante (I04): sem poder discriminante, fora da média da dimensão
            continue
        x = x.clip(x.quantile(.01), x.quantile(.99))
        z = (x - x.min()) / (x.max() - x.min())
        out[c] = 1 - z if c in NEGATIVOS else z
    return out


def subindices(norm):
    return pd.DataFrame({d: norm[[i for i in ii if i in norm]].mean(axis=1) for d, ii in DIM.items()})


def geo(S, w):
    w = pd.Series(w)[S.columns]
    return 100 * np.exp((np.log(S.clip(lower=1e-6)) * w).sum(axis=1) / w.sum())


def arit(S, w):
    w = pd.Series(w)[S.columns]
    return 100 * (S * w).sum(axis=1) / w.sum()


norm = normaliza(am)
S = subindices(norm)
am = pd.concat([am, S.add_prefix("S_")], axis=1)
am["IDF"] = geo(S, PESOS_DELPHI)
n_zero = int((S == 0).any(axis=1).sum())
am["faixa"] = pd.qcut(am.IDF, 4, labels=["Baixa", "Média-baixa", "Média-alta", "Alta"])

# robustez
iguais = {d: .2 for d in DIM}
Sz = (S - S.mean()) / S.std()
ev, evec = np.linalg.eigh(np.corrcoef(Sz.T))
load = np.abs(evec[:, -1])
pesos_acp = dict(zip(S.columns, load ** 2 / (load ** 2).sum()))
alt = pd.DataFrame({"Delphi (ref.)": am.IDF, "Pesos iguais": geo(S, iguais),
                    "ACP": geo(S, pesos_acp), "Aritmética": arit(S, PESOS_DELPHI)})
rho = alt.corr(method="spearman")

# ---------------------------------------------------------------- probit
am["y"] = (am.IDF > am.IDF.median()).astype(int)
specs = {
    "M1": ["idhm_2010", "ln_pop"],
    "M2": ["idhm_2010", "ln_pop", "ln_pib_pc"],
    "M4*": ["idhm_2010", "ln_pop", "ln_pib_pc", "agro_va_pct"],
}
linhas, txt = [], []
for m, xs in specs.items():
    X = sm.add_constant(am[xs])
    try:
        r = sm.Probit(am.y, X).fit(disp=0, maxiter=200)
    except Exception as e:  # separação perfeita etc.
        txt.append(f"{m}: falhou ({e})")
        continue
    me = r.get_margeff(at="mean")
    acc = ((r.predict(X) > .5).astype(int) == am.y).mean() * 100
    txt += [f"===== {m} =====", str(r.summary()), str(me.summary()), f"% classificação correta: {acc:.1f}", ""]
    for v in ["const"] + xs:
        linhas.append({"modelo": m, "variavel": v, "coef": r.params[v], "ep": r.bse[v], "p": r.pvalues[v],
                       "efeito_marginal_media": me.margeff[xs.index(v)] if v in xs else np.nan})
    linhas.append({"modelo": m, "variavel": "Pseudo-R2 McFadden", "coef": r.prsquared})
    linhas.append({"modelo": m, "variavel": "% classificação correta", "coef": acc})
    linhas.append({"modelo": m, "variavel": "n", "coef": r.nobs})

# ---------------------------------------------------------------- saídas
am.to_csv(RES / "idf_resultados.csv", index=False)
desc = am[IND].agg(["mean", "std", "min", "max"]).T
desc["CV (%)"] = desc["std"] / desc["mean"] * 100
desc.insert(0, "indicador", desc.index.map(NOMES))
desc.round(2).to_csv(RES / "quadro4_descritivas.csv")
grupo = pd.concat([
    am.groupby("faixa", observed=True).agg(n=("IDF", "size"), IDF=("IDF", "mean"), IDHM=("idhm_2010", "mean"),
                                           pop_mil=("pop_2024", lambda s: s.mean() / 1e3),
                                           pib_pc_mil=("pib_pc_2021", lambda s: s.mean() / 1e3)),
    am.groupby("uf").agg(n=("IDF", "size"), IDF=("IDF", "mean"), IDHM=("idhm_2010", "mean"),
                         pop_mil=("pop_2024", lambda s: s.mean() / 1e3),
                         pib_pc_mil=("pib_pc_2021", lambda s: s.mean() / 1e3))])
grupo.round(3).to_csv(RES / "quadro6_grupos.csv")
rho.round(3).to_csv(RES / "quadro5_spearman.csv")
pd.DataFrame(linhas).to_csv(RES / "quadro7_probit.csv", index=False)
(RES / "probit_saida.txt").write_text("\n".join(txt))

print(f"Amostra: n = {len(am)} ({am.uf.value_counts().to_dict()})")
print(f"Municípios com algum subíndice = 0: {n_zero}")
print(f"IDF: média {am.IDF.mean():.2f}, DP {am.IDF.std():.2f}, mín {am.IDF.min():.2f} "
      f"({am.loc[am.IDF.idxmin(), 'municipio']}), máx {am.IDF.max():.2f} ({am.loc[am.IDF.idxmax(), 'municipio']})")
print("Pesos ACP:", {k: round(v, 3) for k, v in pesos_acp.items()})
print("\nQuadro 4\n", desc.round(2).to_string())
print("\nSubíndices (médias)\n", S.mean().round(3).to_string())
print("\nQuadro 5\n", rho.round(3).to_string())
print("\nQuadro 6\n", grupo.round(3).to_string())
print("\nQuadro 7\n", pd.DataFrame(linhas).round(4).to_string())
print("\nRanking\n", am.sort_values("IDF", ascending=False)[["municipio", "uf", "IDF", "faixa"]].round(2).to_string())
