#!/usr/bin/env bash
# Baixa os insumos públicos para dados/brutos/. Rodar de dentro de moratoria_soja/.
set -e; D=dados/brutos; mkdir -p $D
# IBGE: lista de municípios
curl -s https://servicodados.ibge.gov.br/api/v1/localidades/municipios -o $D/ibge_municipios.json
# IBGE/PAM (SIDRA 5457): soja (c782 = 40124) - área plantada (8331), área colhida (216), quantidade produzida (214), 1995-2024
for y in $(seq 1995 2024); do
  curl -s "https://apisidra.ibge.gov.br/values/t/5457/n6/all/v/8331,216,214/p/$y/c782/40124" -o $D/pam_soja_$y.json
done
# IBGE: área territorial dos municípios (Censo 2022, SIDRA 4714)
curl -s "https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/6318/p/2022" -o $D/area_municipios.json
# MapBiomas Coleção 11: desmatamento anual por município e bioma (1987-2025)
curl -sL "https://brasil.mapbiomas.org/wp-content/uploads/sites/3/2026/10/MAPBIOMAS-BRAZIL-DEFORESTATION-ANNUAL-MUNICIPALITY-COLLECTION_11.xlsx" -o $D/mapbiomas_desmatamento_municipio.xlsx
echo "ok"
