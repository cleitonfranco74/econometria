# Moratória da Soja: produção, desmatamento e (des)acoplamento na Amazônia

Projeto de pesquisa em andamento. Pergunta central: **a Moratória da Soja desacoplou a expansão da soja do desmatamento na
Amazônia, e esse desacoplamento deslocou o desmatamento para o Cerrado?**

## 1. Contexto

A Moratória da Soja, firmada em 2006 por *tradings* e associações do setor, compromete os signatários a não comprar soja
produzida em áreas do **bioma Amazônia** desmatadas após a data de corte (originalmente 2006; segundo a literatura, passou a
julho de 2008 — **conferir** em Gibbs et al., 2015). O **Cerrado não é coberto**, o que gera um grupo de comparação natural e um
risco de vazamento.

## 2. Hipóteses

1. **Desacoplamento**: após a moratória, a área e a produção de soja continuam crescendo na Amazônia, enquanto o desmatamento
   primário cai (expansão sobre áreas já abertas, sobretudo pastagens).
2. **Efeito causal**: o desmatamento primário cai mais na Amazônia do que no Cerrado comparável.
3. **Vazamento**: parte da expansão e do desmatamento migra para o Cerrado (Matopiba) e para municípios fora do alcance das
   *tradings* signatárias.
4. **Deslocamento indireto** (extensão): a soja ocupa pastagens e o gado avança sobre a floresta.
5. **Violência** (extensão, ligada ao projeto `av2_did_armas`): o vazamento para o Cerrado acompanha mais conflitos e homicídios.

## 3. Estratégia empírica

| Desenho | Unidades | Tratamento | Efeitos fixos | Comentário |
|---|---|---|---|---|
| **(a) Dentro da divisa** (principal) | parte amazônica e parte de cerrado de cada município que tem os dois biomas | parte amazônica × pós-2006 | município × bioma, município × ano | absorve qualquer choque do município no ano (prefeitura, preços, crédito municipal, lista de municípios prioritários) |
| (b) Amazônia vs. Cerrado | municípios sojicultores antes de 2006, só Amazônia ou só Cerrado | Amazônia × pós-2006 | município, UF × ano | grupos muito diferentes; pré-tendências |
| (c) Exposição às *tradings* (v2) | municípios da Amazônia | participação das signatárias nas compras de soja (Trase), adoção escalonada | Callaway & Sant'Anna | como em Gollnow et al. (SSRN 4006677) |
| (d) Aptidão agrícola (v2) | áreas aptas vs. não aptas à soja | aptidão × pós | — | como em Heilmayr et al. (2020) |

Resultados: desmatamento primário e total (MapBiomas), área plantada, área colhida, produção e produtividade de soja (PAM);
extensões: conversão pastagem → soja (transições do MapBiomas), rebanho bovino (PPM), homicídios (SIM).

## 4. Dados (`00_baixar_dados.sh`, `01_painel.py`)

| Fonte | Conteúdo | Período |
|---|---|---|
| IBGE/PAM (SIDRA 5457) | soja: área plantada, colhida, produção | 1995–2024 |
| MapBiomas Col. 11 | desmatamento anual por município **e bioma** (vegetação primária e secundária) | 1987–2025 |
| IBGE | municípios, área territorial | 2022 |

Painéis gerados em `dados/processados/`:
- `painel_municipio_ano.csv` — 5.570 municípios × 1995–2024; classificação em Amazônia, Cerrado ou divisa (≥ 5% do desmatamento
  acumulado em cada bioma); sojicultor pré-moratória = média ≥ 1.000 ha de soja em 2001–2005.
- `painel_municipio_bioma_ano.csv` — 84 municípios da divisa × 2 partes × 1995–2024.

**Limitação desta versão**: a composição de biomas do município é aproximada pelo desmatamento acumulado. A versão 2 deve usar a
tabela de cobertura do MapBiomas por município e bioma (hospedada no Google Drive, não acessível nesta sessão), que também traz a
área de soja por bioma dentro do município.

## 5. Resultados preliminares (`02_analise_preliminar.py`)

Municípios sojicultores antes da moratória: 36 na Amazônia, 299 no Cerrado, 30 na divisa.

| Média anual | Amazônia 2001–05 | Amazônia 2009–13 | Cerrado 2001–05 | Cerrado 2009–13 |
|---|---|---|---|---|
| Área de soja (mil ha) | 356 | 1.223 (+244%) | 7.219 | 8.941 (+24%) |
| Produção (mil t) | 1.030 | 3.823 (+271%) | 18.987 | 26.295 (+38%) |
| Desmatamento primário (mil ha) | 375 | 69 (**−82%**) | 662 | 415 (−37%) |

| DiD (Poisson, desmatamento primário) | Coef. | EP | Efeito |
|---|---|---|---|
| **(a) Divisa: parte amazônica × pós-2006** | **−0,795** | 0,111 | **−55%** |
| (a) Divisa, só municípios sojicultores | −0,658 | 0,120 | −48% |
| (b) Amazônia vs. Cerrado, EF UF × ano | −0,165 | 0,184 | n.s. |
| (b) Amazônia vs. Cerrado, EF ano | −0,718 | 0,135 | −51% |

- No desenho da divisa, **nenhum coeficiente pré-2006 é significativo** e a queda é significativa em todos os anos de 2009 a 2020
  (`resultados/fig_event_study.png`).
- No desenho (b), há pré-tendências significativas (1998–2001), e o efeito some com EF de UF × ano.
- A soja mais que triplica na Amazônia enquanto o desmatamento primário despenca (`resultados/fig_trajetorias.png`):
  produção e desmatamento **não** caminharam juntos após a moratória.

## 6. Principal ameaça à identificação

A queda começa em **2009**, não em 2006. Em 2008 entraram em vigor outras políticas: a data de corte revisada da própria
moratória, a lista de municípios prioritários do PPCDAm (municipal — absorvida pelos EF município × ano no desenho da divisa) e a
restrição de crédito rural no bioma Amazônia (Resolução CMN/BACEN nº 3.545/2008 — **conferir alcance**), que, por ser definida
pelo bioma do imóvel, **não** é absorvida pelos efeitos fixos. Separar a moratória da restrição de crédito é o desafio central;
caminhos: (i) explorar a exposição às *tradings* signatárias (Trase), que varia dentro da Amazônia; (ii) comparar áreas aptas e
não aptas à soja dentro da parte amazônica (o crédito vale para toda atividade; a moratória, só para soja); (iii) usar o
desmatamento para soja versus para pastagem como resultado.

## 7. Próximos passos

1. Obter a tabela de cobertura do MapBiomas por município e bioma (soja e pastagem por bioma) e as transições pastagem → soja.
2. Dados da Trase (compras por *trading* e município) para o desenho (c).
3. Rebanho bovino (PPM/IBGE) para o deslocamento indireto.
4. Inferência com poucos clusters no desenho da divisa (84 municípios): *wild cluster bootstrap*.
5. Vazamento: testar se municípios do Cerrado próximos à divisa aceleraram desmatamento após 2006.

## 8. Referências e recursos

- Gibbs, H. K. et al. (2015). Brazil's Soy Moratorium. *Science*, 347(6220), 377–378. doi:10.1126/science.aaa0181
- Heilmayr, R., Rausch, L. L., Munger, J., Gibbs, H. K. (2020). Brazil's Amazon Soy Moratorium reduced deforestation.
  *Nature Food*, 1(12), 801–810. doi:10.1038/s43016-020-00194-5 — dados de replicação: Harvard Dataverse, doi:10.7910/DVN/LE42B1;
  replicação parcial em github.com/Liamxu0106/ASM-replication
- Assunção, J., Gandour, C., Rocha, R. (2015). Deforestation slowdown in the Brazilian Amazon: prices or policies?
  *Environment and Development Economics*, 20(6), 697–722. doi:10.1017/S1355770X15000078
- Gollnow, F., Cammelli, F., Carlson, K., Garrett, R. Gaps in adoption limit the current and potential effectiveness of
  zero-deforestation supply chain policies for soy. SSRN 4006677 — código: github.com/floriangollnow/zdc_brazil
- Código do MapBiomas para desmatamento associado à soja: github.com/dh-conciani/AMZ_SoybeanMoratorium
