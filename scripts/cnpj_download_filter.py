"""Baixa os arquivos do CNPJ (Receita Federal, dados abertos) e filtra MT/MS/GO.

Fonte: compartilhamento público da Receita (Nextcloud/SERPRO), acesso por WebDAV.
Snapshot 2025-01 = cadastro na posição de dez/2024 / jan/2025.

Uso: python scripts/cnpj_download_filter.py Estabelecimentos3 [Simples ...]
"""
import csv
import gzip
import io
import subprocess
import sys
import zipfile
from pathlib import Path

SHARE = "YggdBLfdninEJX9"
SNAPSHOT = "2025-01"
BASE = f"https://arquivos.receitafederal.gov.br/public.php/webdav/{SNAPSHOT}"
UFS = {"MT", "MS", "GO"}
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "cnpj"
OUT.mkdir(parents=True, exist_ok=True)

# Colunas mantidas do arquivo Estabelecimentos (layout RFB)
EST_COLS = {0: "cnpj_basico", 3: "matriz_filial", 5: "situacao", 6: "data_situacao",
            10: "data_inicio", 11: "cnae", 19: "uf", 20: "mun_rf"}


def download(name: str) -> Path:
    zpath = OUT / f"{name}.zip"
    if zpath.exists() and zipfile.is_zipfile(zpath):
        return zpath
    for attempt in range(5):
        r = subprocess.run(["curl", "-sS", "-f", "-C", "-", "--retry", "5", "-u", f"{SHARE}:",
                            "-o", str(zpath), f"{BASE}/{name}.zip"])
        if r.returncode == 0 and zipfile.is_zipfile(zpath):
            return zpath
    raise RuntimeError(f"falha ao baixar {name}")


def filter_est(zpath: Path, name: str):
    out = OUT / f"{name}_CO.csv.gz"
    n = 0
    with zipfile.ZipFile(zpath) as z, gzip.open(out, "wt", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(EST_COLS.values())
        member = z.namelist()[0]
        with z.open(member) as fi:
            for row in csv.reader(io.TextIOWrapper(fi, encoding="latin-1"), delimiter=";"):
                if len(row) > 20 and row[19] in UFS:
                    w.writerow([row[i] for i in EST_COLS])
                    n += 1
    print(name, "linhas CO:", n, flush=True)


def filter_simples(zpath: Path, cnpjs: set):
    out = OUT / "Simples_CO.csv.gz"
    with zipfile.ZipFile(zpath) as z, gzip.open(out, "wt", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["cnpj_basico", "opcao_simples", "data_opcao", "data_exclusao", "opcao_mei"])
        with z.open(z.namelist()[0]) as fi:
            for row in csv.reader(io.TextIOWrapper(fi, encoding="latin-1"), delimiter=";"):
                if row and row[0] in cnpjs:
                    w.writerow(row[:4] + [row[4]])


def main(names):
    for name in names:
        if name.startswith("Estabelecimentos"):
            if (OUT / f"{name}_CO.csv.gz").exists():
                continue
            z = download(name)
            filter_est(z, name)
            z.unlink()
        elif name == "Simples":
            z = download(name)
            cnpjs = set()
            for f in sorted(OUT.glob("Estabelecimentos*_CO.csv.gz")):
                with gzip.open(f, "rt", encoding="utf-8") as fi:
                    next(fi)
                    for line in fi:
                        cnpjs.add(line.split(",", 1)[0])
            filter_simples(z, cnpjs)
            z.unlink()
        else:
            download(name)


if __name__ == "__main__":
    main(sys.argv[1:])
