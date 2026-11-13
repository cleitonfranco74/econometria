"""Monta a base municipal (MT, MS, GO) com os 16 indicadores do IDF-MP e os controles da regressão.

Entrada : data/raw/ (coleta_apis.py e cnpj_download_filter.py)
Saída   : data/processed/base_municipal_CO.csv
"""
import unicodedata
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)
REF = pd.Timestamp("2024-12-31")


def chave(nome: str) -> str:
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode().upper()
    return "".join(ch for ch in s if ch.isalnum())


# ---------------------------------------------------------------- base IBGE + IDHM
base = pd.read_csv(RAW / "ibge.csv", dtype={"cod_ibge": str})
base["k"] = base.uf + "_" + base.municipio.map(chave)
base = base.merge(pd.read_csv(RAW / "ipea_idhm_2010.csv", dtype={"cod_ibge": str}), on="cod_ibge", how="left")

# ---------------------------------------------------------------- D1 Infraestrutura digital (Anatel, dez/2024)
ac = pd.read_csv(RAW / "anatel_acessos_202412.csv", dtype={"Código IBGE": str})
bl = ac[ac["Serviço"] == "Banda Larga Fixa"].set_index("Código IBGE")
base["acessos_blf"] = base.cod_ibge.map(bl["Acessos"])
base["I01"] = base.acessos_blf / base.domicilios_2022 * 100
cob = pd.read_csv(RAW / "anatel_cobertura_202412.csv")
cob["Código IBGE"] = cob["Código IBGE"].astype(int).astype(str)
for ind, tec in [("I02", "4G"), ("I03", "5G")]:
    base[ind] = base.cod_ibge.map(cob[cob.Tecnologia == tec].set_index("Código IBGE")["% moradores cobertos"])
base["I04"] = 1.0  # backhaul de fibra: sem base aberta localizada; artigo reporta 1 para toda a amostra

# ---------------------------------------------------------------- D2 Acesso financeiro (BCB)
ag = pd.read_csv(RAW / "bcb_agencias.csv", dtype={"MunicipioIbge": str})
ag = ag[pd.to_datetime(ag.DataInicio, dayfirst=True, errors="coerce") <= REF]
po = pd.read_csv(RAW / "bcb_postos.csv", dtype={"MunicipioIbge": str})
n = lambda df: base.cod_ibge.map(df.groupby("MunicipioIbge").size()).fillna(0)
base["n_agencias"] = n(ag)
base["n_pac"] = n(po[po.TipoPosto.str.contains("PAC")])
base["n_postos_outros"] = n(po[po.TipoPosto.str.contains("PAB|PAA|PAT")])
base["I05"] = (base.n_agencias + base.n_pac + base.n_postos_outros) / base.pop_2024 * 1e4
base["I06"] = base.n_pac / base.pop_2024 * 1e4

# ---------------------------------------------------------------- D3 Uso digital-financeiro (BCB)
pix = pd.read_csv(RAW / "bcb_pix_2024.csv", dtype={"Municipio_Ibge": str})
pixm = pix.groupby("Municipio_Ibge").agg(pix_qt_rec_pj=("QT_RecebedorPJ", "mean"),
                                         pix_pes_rec_pj=("QT_PES_RecebedorPJ", "mean"))
base = base.merge(pixm, left_on="cod_ibge", right_index=True, how="left")
est = pd.read_csv(RAW / "bcb_estban_202412.csv")
est["k"] = est.UF + "_" + est.MUNICIPIO.map(chave)
base["credito_estban"] = base.k.map(est.groupby("k")["VERBETE_160_OPERACOES_DE_CREDITO"].sum()).fillna(0)

# ---------------------------------------------------------------- D4 Ambiente empresarial (Receita/CNPJ)
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
ativos = ativos.assign(simples=ativos.cnpj_basico.isin(opt), idade=(REF - ativos.dt_ini).dt.days / 365.25)
g = ativos.groupby("k")
base["empresas_ativas"] = base.k.map(g.size())
base["ativas_simples"] = base.k.map(g.simples.sum())
base["idade_media"] = base.k.map(g.idade.mean())
base["abertas_2024"] = base.k.map(abertos.groupby("k").size()).fillna(0)
base["baixadas_2024"] = base.k.map(baixados.groupby("k").size()).fillna(0)
nao_casados = estab.loc[~estab.k.isin(base.k), "k"].nunique()
print("municípios RF sem correspondência IBGE:", nao_casados)

base["I07"] = base.pix_qt_rec_pj / base.empresas_ativas
base["I08"] = base.pix_pes_rec_pj / base.empresas_ativas * 100
base["I09"] = base.credito_estban / base.empresas_ativas / 1e3
base["I10"] = base.empresas_ativas / base.pop_2024 * 1e3
base["I11"] = base.ativas_simples / base.empresas_ativas * 100
base["I12"] = base.abertas_2024 / base.empresas_ativas * 100
base["I13"] = base.baixadas_2024 / (base.empresas_ativas + base.baixadas_2024) * 100
base["I14"] = base.idade_media

# ---------------------------------------------------------------- D5 Capital humano (Censo 2022)
base["I15"] = (base.pop25_medio_sup_inc + base.pop25_superior) / base.pop25_total * 100
base["I16_censo2022"] = base.freq_superior_2022 / base.pop_2024 * 1e3  # proxy antiga (Censo 2022)
inep = pd.read_csv(RAW / "inep_municipal.csv", dtype={"cod_ibge": str})
base = base.merge(inep, on="cod_ibge", how="left")
cols_inep = ["mat_tecnicas_2024", "mat_superior_presencial_2024", "n_cursos_presenciais_2024",
             "n_ies_presenciais_2024", "n_ies_publicas_2024", "campus", "campus_publico", "campus_qualquer",
             "campus_univ_publica", "campus_univ_federal", "campus_if", "campus_universidade"]
base[cols_inep] = base[cols_inep].fillna(0)
# I16 conforme o artigo: matrículas técnicas (Censo Escolar) + superiores presenciais (Censo Superior), INEP 2024
base["I16"] = (base.mat_tecnicas_2024 + base.mat_superior_presencial_2024) / base.pop_2024 * 1e3

# ---------------------------------------------------------------- controles
base["ln_pop"] = np.log(base.pop_2024)
base["pib_pc_2021"] = base.pib_2021_mil * 1e3 / base.pop_2021
base["ln_pib_pc"] = np.log(base.pib_pc_2021)
base["agro_va_pct"] = base.va_agro_2021_mil / base.va_total_2021_mil * 100

base.drop(columns="k").to_csv(PROC / "base_municipal_CO.csv", index=False)
print("base:", base.shape)
