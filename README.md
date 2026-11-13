# IDF-MT — Índice de Inclusão Digital-Financeira dos Pequenos Negócios

Reprodução, com dados públicos baixados por API, do artigo *"Índice de Inclusão Digital-Financeira dos
Pequenos Negócios (IDF-MT): Desenvolvimento e Validação em Municípios Médios do Centro-Oeste Brasileiro"*.

## Como rodar

```bash
pip install pandas numpy scipy statsmodels
python scripts/coleta_apis.py                 # IBGE, BCB, Anatel, Ipeadata  (~2 min)
python scripts/cnpj_download_filter.py Estabelecimentos0 ... Estabelecimentos9   # Receita (~5,5 GB, filtra MT/MS/GO)
python scripts/cnpj_download_filter.py Simples
python scripts/idf_modelo.py principal        # amostra principal (n = 42)
python scripts/idf_modelo.py sem_metro        # variante sem periferias metropolitanas de GO (n = 31)
```

`data/raw/` não vai para o Git (arquivos grandes; é regenerado pelos scripts). As bases tratadas
ficam em `data/processed/` e os quadros do artigo em `resultados/<amostra>/`.

## Fontes e APIs

| Ind. | Indicador | Fonte / endpoint | Referência |
|---|---|---|---|
| I01 | Acessos BL fixa por 100 domicílios | Anatel, *Meu Município* (`dadosabertos/paineis_de_dados/meu_municipio/meu_municipio.zip`) ÷ domicílios ocupados Censo 2022 (SIDRA 4712) | dez/2024 |
| I02 | Cobertura 4G (% moradores) | Anatel, *Meu Município – Cobertura*, operadora "Todas", tecnologia 4G | dez/2024 |
| I03 | Cobertura 5G (% moradores) | idem, tecnologia 5G | dez/2024 |
| I04 | Backhaul de fibra | **não localizado em dados abertos**; o artigo reporta valor 1 para todos (DP = 0) → mantido constante e fora da normalização | — |
| I05 | Pontos de atendimento financeiro / 10 mil hab. | BCB Olinda `Informes_Agencias` + `Informes_PostosDeAtendimento` (agências, PAB, PAA, PAT, PAC) | cadastro atual; agências com início ≤ 2024 |
| I06 | Pontos de cooperativas / 10 mil hab. | BCB Olinda `Informes_PostosDeAtendimento` (PAC) | cadastro atual |
| I07 | Transações Pix recebidas por PJ, por empresa ativa (média mensal) | BCB Olinda `Pix_DadosAbertos/TransacoesPixPorMunicipio` (`QT_RecebedorPJ`) | jan–dez/2024 |
| I08 | % de empresas recebedoras de Pix | idem (`QT_PES_RecebedorPJ`, média mensal) ÷ empresas ativas | 2024 |
| I09 | Saldo de crédito por empresa ativa (R$ mil) | BCB ESTBAN municipal, verbete 160 (`/content/estatisticas/estatistica_bancaria_estban/municipio/202412_ESTBAN.csv.zip`) | dez/2024 |
| I10 | Empresas ativas / 1.000 hab. | Receita Federal, CNPJ dados abertos (WebDAV público), estabelecimentos situação 02 | snapshot 2025-01 |
| I11 | % optantes do Simples | Receita, arquivo Simples | snapshot 2025-01 |
| I12 | Taxa de abertura (%) | estabelecimentos com início de atividade em 2024 ÷ ativos | 2024 |
| I13 | Taxa de encerramento (%) (−) | estabelecimentos baixados (situação 08) em 2024 ÷ (ativos + baixados) | 2024 |
| I14 | Idade média das empresas ativas | data de início de atividade, em 31/12/2024 | 2024 |
| I15 | 25+ com médio completo ou mais (%) | IBGE SIDRA 10061 (Censo 2022) | 2022 |
| I16 | Matrículas no ensino superior / 1.000 hab. | **proxy**: pessoas 18+ que frequentavam graduação/pós, SIDRA 10059 (Censo 2022) | 2022 |

Controles do probit: IDHM 2010 (Ipeadata `ADH_IDHM`), ln(população 2024) (SIDRA 6579),
ln(PIB per capita 2021) e % do VA agropecuário 2021 (SIDRA 5938; 2021 é o último ano com VA municipal no SIDRA).

## Diferenças em relação ao artigo (importante)

1. **Amostra.** O artigo não lista os 33 municípios. A regra declarada (50–600 mil hab., sem capitais)
   com a estimativa de população 2024 reproduz exatamente MT = 13 e MS = 6, mas dá **GO = 23** (o artigo tem 14).
   Por isso há duas amostras: `principal` (n = 42) e `sem_metro` (n = 31, exclui RM de Goiânia e Entorno do DF).
2. **I16 / Campus (INEP).** O servidor `download.inep.gov.br` envia cadeia TLS incompleta e o download foi
   bloqueado neste ambiente; I16 usa a proxy do Censo 2022 e a variável *Campus* (M3, M4) não foi construída.
   O modelo `M4*` é o M4 sem Campus.
3. **I04 (backhaul)** não entra (constante).
4. Agências e postos vêm do cadastro vigente do BCB (não há série histórica por API); agências abertas
   depois de 2024 foram excluídas, mas encerramentos ocorridos depois de 2024 não podem ser revertidos.
5. A normalização segue o artigo (winsorização P1/P99, min-max, I13 invertido, média aritmética por dimensão,
   média geométrica ponderada com pesos Delphi 25/20/25/15/15). Subíndices iguais a zero são truncados em 1e-6
   na média geométrica (o script informa quantos municípios caem nesse caso).
