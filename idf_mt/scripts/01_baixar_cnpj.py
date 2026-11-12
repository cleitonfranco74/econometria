"""
01 - Baixa os dados abertos do CNPJ (Receita Federal), snapshot 2025-01
(posição de referência ~ 31/12/2024), e mantém apenas os estabelecimentos
de MT, MS e GO. Cada zip é baixado, filtrado e apagado para economizar disco.
Os downloads rodam em paralelo (o servidor da Receita é lento por conexão).

Saídas (dados/brutos/cnpj/):
  estab_co_<i>.csv  -> estabelecimentos de MT/MS/GO (colunas selecionadas)
  simples_co.csv    -> opção pelo Simples Nacional das empresas acima
  municipios_rf.csv -> tabela de códigos de município da Receita
"""
import csv, glob, io, os, sys, zipfile, subprocess
from concurrent.futures import ThreadPoolExecutor

BASE = "https://arquivos.receitafederal.gov.br/public.php/webdav/2025-01/"
TOKEN = "YggdBLfdninEJX9"   # compartilhamento público da Receita (dados abertos CNPJ)
# uso: python3 01_baixar_cnpj.py <pasta_saida> [UFs separadas por vírgula] [prefixo]
OUT = sys.argv[1] if len(sys.argv) > 1 else "dados/brutos/cnpj"
UFS = set((sys.argv[2] if len(sys.argv) > 2 else "MT,MS,GO").split(","))
PREF = sys.argv[3] if len(sys.argv) > 3 else "co"          # "co" = Centro-Oeste; "mtp" = MATOPIBA
os.makedirs(OUT, exist_ok=True)


def baixar(nome):
    destino = os.path.join(OUT, nome)
    for _ in range(30):
        # -C - retoma downloads interrompidos
        r = subprocess.run(["curl", "-sS", "-L", "-C", "-", "--retry", "5", "-u", TOKEN + ":",
                            "-o", destino, BASE + nome])
        if zipfile.is_zipfile(destino):
            return destino
        if r.returncode == 33:      # servidor recusou retomada: recomeça do zero
            os.remove(destino)
        print("  incompleto, retomando:", nome, flush=True)
    raise SystemExit("Não consegui baixar " + nome)


def linhas(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        with z.open(z.namelist()[0]) as f:
            yield from csv.reader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";")


COLS = {0: "cnpj_basico", 3: "matriz_filial", 5: "situacao", 6: "data_situacao",
        10: "data_inicio", 11: "cnae", 19: "uf", 20: "cod_rf_municipio"}


def estabelecimentos(i):
    final = os.path.join(OUT, f"estab_{PREF}_{i}.csv")
    if os.path.exists(final):
        return
    nome = f"Estabelecimentos{i}.zip"
    print("baixando", nome, flush=True)
    zp = baixar(nome)
    n = 0
    with open(final + ".tmp", "w", newline="") as g:
        w = csv.writer(g); w.writerow(COLS.values())
        for row in linhas(zp):
            if len(row) > 20 and row[19] in UFS:
                w.writerow([row[k] for k in COLS]); n += 1
    os.replace(final + ".tmp", final)
    os.remove(zp)
    print(f"  {nome}: {n} estabelecimentos em MT/MS/GO", flush=True)


if not os.path.exists(os.path.join(OUT, "municipios_rf.csv")):
    zp = baixar("Municipios.zip")
    with open(os.path.join(OUT, "municipios_rf.csv"), "w", newline="") as g:
        w = csv.writer(g); w.writerow(["cod_rf", "nome"])
        for row in linhas(zp):
            w.writerow(row)
    os.remove(zp)

# Simples é baixado junto, em paralelo; filtrado ao final
with ThreadPoolExecutor(max_workers=6) as ex:
    fut_simples = ex.submit(baixar, "Simples.zip")
    list(ex.map(estabelecimentos, range(10)))
    zp_simples = fut_simples.result()

basicos = set()
for f in glob.glob(os.path.join(OUT, f"estab_{PREF}_*.csv")):
    with open(f) as h:
        for row in csv.DictReader(h):
            basicos.add(row["cnpj_basico"])

with open(os.path.join(OUT, f"simples_{PREF}.csv"), "w", newline="") as g:
    w = csv.writer(g)
    w.writerow(["cnpj_basico", "opcao_simples", "data_opcao_simples", "data_exclusao_simples",
                "opcao_mei", "data_opcao_mei", "data_exclusao_mei"])
    for row in linhas(zp_simples):
        if row[0] in basicos:
            w.writerow(row)
os.remove(zp_simples)
print("FIM", flush=True)
