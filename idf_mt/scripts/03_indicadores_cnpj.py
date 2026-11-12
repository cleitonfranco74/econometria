"""
03 - Indicadores de Ambiente Empresarial (D4) e denominadores "por empresa ativa"
a partir dos dados abertos do CNPJ (Receita Federal, snapshot jan/2025).

Data de referência: 31/12/2024. Unidade: ESTABELECIMENTO (matriz ou filial).
Situação cadastral: 01 nula, 02 ativa, 03 suspensa, 04 inapta, 08 baixada.

  I10  Empresas ativas por 1.000 hab.
  I11  % das empresas ativas optantes do Simples Nacional (inclui MEI) em 31/12/2024
  I12  Taxa de abertura 2024 = aberturas em 2024 / estoque ativo em 01/01/2024 x 100
  I13  Taxa de encerramento 2024 = baixas em 2024 / estoque ativo em 01/01/2024 x 100
  I14  Idade média (anos) das empresas ativas em 31/12/2024

Uso: python3 scripts/03_indicadores_cnpj.py  (a partir da pasta idf_mt)
Saída: dados/processados/indicadores_cnpj.csv
"""
import glob, unicodedata
import pandas as pd

BR = "dados/brutos/cnpj"
REF, INI = 20241231, 20240101


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().replace("'", " ").replace("-", " ").split())


base = pd.read_csv("dados/processados/fontes_nao_cnpj.csv")
base["chave"] = base.uf + "|" + base.municipio.map(norm)

# ---- tabela de municípios da Receita -> código IBGE (casamento por UF + nome)
mun_rf = pd.read_csv(f"{BR}/municipios_rf.csv", dtype=str)
mun_rf["nome_n"] = mun_rf.nome.map(norm)

cols = ["cnpj_basico", "situacao", "data_situacao", "data_inicio", "uf", "cod_rf_municipio"]
est = pd.concat([pd.read_csv(f, dtype=str, usecols=cols) for f in sorted(glob.glob(f"{BR}/estab_*_[0-9].csv"))])
print("estabelecimentos (UFs baixadas):", len(est))
est = est.merge(mun_rf[["cod_rf", "nome_n"]], left_on="cod_rf_municipio", right_on="cod_rf", how="left")
est["chave"] = est.uf + "|" + est.nome_n
est = est.merge(base[["chave", "cod_ibge"]], on="chave", how="inner")
print("estabelecimentos nos municípios da amostra:", len(est), "| municípios casados:", est.cod_ibge.nunique())

for c in ["data_situacao", "data_inicio"]:
    est[c] = pd.to_numeric(est[c], errors="coerce").fillna(0).astype(int)
est = est[est.data_inicio <= REF]                      # existentes até a data de referência

ativa_ref = (est.situacao == "02") | ((est.situacao != "02") & (est.data_situacao > REF))
# ativa em 01/01/2024: já aberta e ainda não baixada/inativada antes de 2024
ativa_ini = (est.data_inicio < INI) & ((est.situacao == "02") | (est.data_situacao >= INI))
abertura = est.data_inicio.between(INI, REF)
baixa = (est.situacao == "08") & est.data_situacao.between(INI, REF) & (est.data_inicio < INI)

# ---- Simples Nacional na data de referência
sim = pd.concat([pd.read_csv(f, dtype=str) for f in glob.glob(f"{BR}/simples_*.csv")]).drop_duplicates("cnpj_basico")
for c in ["data_opcao_simples", "data_exclusao_simples"]:
    sim[c] = pd.to_numeric(sim[c], errors="coerce").fillna(0).astype(int)
optante = sim[(sim.opcao_simples == "S") |
              ((sim.data_opcao_simples.between(1, REF)) & (sim.data_exclusao_simples > REF))]
optante = optante[optante.data_opcao_simples <= REF]
est["simples"] = est.cnpj_basico.isin(optante.cnpj_basico)

dt_ini = pd.to_datetime(est.data_inicio.astype(str), format="%Y%m%d", errors="coerce")
est["idade"] = (pd.Timestamp("2024-12-31") - dt_ini).dt.days / 365.25

g = est.assign(ativa_ref=ativa_ref, ativa_ini=ativa_ini, abertura=abertura, baixa=baixa)
res = pd.DataFrame({
    "empresas_ativas": g[g.ativa_ref].groupby("cod_ibge").size(),
    "estoque_ini_2024": g[g.ativa_ini].groupby("cod_ibge").size(),
    "aberturas_2024": g[g.abertura].groupby("cod_ibge").size(),
    "baixas_2024": g[g.baixa].groupby("cod_ibge").size(),
    "ativas_simples": g[g.ativa_ref & g.simples].groupby("cod_ibge").size(),
    "I14": g[g.ativa_ref].groupby("cod_ibge").idade.mean(),
}).reset_index().rename(columns={"index": "cod_ibge"})

res = base.drop(columns="chave").merge(res, on="cod_ibge", how="left")
res["I10"] = res.empresas_ativas / res.pop_2024 * 1000
res["I11"] = res.ativas_simples / res.empresas_ativas * 100
res["I12"] = res.aberturas_2024 / res.estoque_ini_2024 * 100
res["I13"] = res.baixas_2024 / res.estoque_ini_2024 * 100
# indicadores de D3 que dependem do número de empresas ativas
res["I07"] = res.pix_trans_receb_pj_mes / res.empresas_ativas      # transações Pix recebidas/mês por empresa
res["I08"] = (res.pix_pj_recebedoras_mes / res.empresas_ativas * 100).clip(upper=100)
res["I09"] = res.credito_dez24 / res.empresas_ativas / 1000         # R$ mil por empresa

res.to_csv("dados/processados/base_idf_mt.csv", index=False)
print(res[["municipio", "uf", "empresas_ativas", "I07", "I08", "I09", "I10", "I11", "I12", "I13", "I14"]]
      .round(2).to_string())
