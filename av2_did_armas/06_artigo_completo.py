"""Gera o artigo completo revisado (AV2 PROFNIT) com os dados municipais reais, usando o .docx original como molde."""
import copy, json, sys
import numpy as np, pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ORIG, OUT = sys.argv[1], sys.argv[2]
R = json.load(open('resultados_municipal.json')); r = R['res']; I = R['info']; ES = R['es']
CS = json.load(open('cs_resultados.json')); FT = json.load(open('fronteira_tratamento.json'))
SD = json.load(open('resultados_sdid.json')); SJ = json.load(open('resultados_soja.json')); CSJ = json.load(open('resultados_cs_soja.json'))
df = pd.read_csv('AV2_painel_municipal_Brasil.csv')

def f(x, d=3):
    return f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.').replace('-', '\u2212')
def st(p): return '***' if p < .01 else '**' if p < .05 else '*' if p < .10 else ''
def pv(p): return '< 0,001' if p < .001 else f(p, 3)

# ---------------- molde: abre o original, guarda o Quadro 1 e limpa o corpo
doc = Document(ORIG)
body = doc.element.body
quadro = copy.deepcopy(doc.tables[0]._tbl)
for el in list(body):
    if el.tag != qn('w:sectPr'): body.remove(el)
TNR = 'Times New Roman'

def para(runs, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY, style=None, after=6, italic=False):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    p.alignment = align; p.paragraph_format.space_after = Pt(after)
    if isinstance(runs, str): runs = [(runs, False)]
    for txt, b in runs:
        x = p.add_run(txt); x.bold = b; x.italic = italic; x.font.size = Pt(size); x.font.name = TNR
    return p
def T(txt): return para(txt)                                   # parágrafo comum
def L(lead, txt): return para([(lead, True), (txt, False)])    # parágrafo com rótulo em negrito
def BUL(lead, txt=''): return para([(lead, True), (txt, False)], size=11.5, style='List Bullet', after=3)
def SEC(txt): return para([(txt, True)], align=WD_ALIGN_PARAGRAPH.LEFT, after=6)
def CAP(txt): return para([(txt, True)], size=10.5, align=WD_ALIGN_PARAGRAPH.LEFT, after=3)
def NOTE(txt): return para(txt, size=8.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=10)
def EQ(txt): return para([(txt, False)], align=WD_ALIGN_PARAGRAPH.CENTER, italic=True)
def FIG(path, w=15.5):
    doc.add_picture(path, width=Cm(w)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

def _cell_fmt(cell, txt, bold=False, header=False, align='center', size=9):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), '1F3864' if header else 'FFFFFF'); tcPr.append(shd)
    v = OxmlElement('w:vAlign'); v.set(qn('w:val'), 'center'); tcPr.append(v)
    p = cell.paragraphs[0]; p.text = ''
    p.alignment = {'center': WD_ALIGN_PARAGRAPH.CENTER, 'left': WD_ALIGN_PARAGRAPH.LEFT}[align]
    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
    x = p.add_run(txt); x.font.name = TNR; x.font.size = Pt(9.5 if header else size); x.bold = bold or header
    if header: x.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
def TABLE(header, rows, widths, bold_first_col=False, bold_rows=()):
    t = doc.add_table(rows=1, cols=len(header)); t.autofit = False
    tblPr = t._tbl.tblPr
    jc = OxmlElement('w:jc'); jc.set(qn('w:val'), 'center'); tblPr.append(jc)
    b = OxmlElement('w:tblBorders')
    for side, val, sz, col in [('top', 'single', '8', '1F3864'), ('bottom', 'single', '8', '1F3864'), ('insideH', 'single', '4', 'D9D9D9'),
                               ('left', 'none', '0', 'auto'), ('right', 'none', '0', 'auto'), ('insideV', 'none', '0', 'auto')]:
        e = OxmlElement(f'w:{side}'); e.set(qn('w:val'), val); e.set(qn('w:sz'), sz); e.set(qn('w:space'), '0'); e.set(qn('w:color'), col); b.append(e)
    tblPr.append(b)
    for i, h in enumerate(header): _cell_fmt(t.rows[0].cells[i], h, header=True, align='left' if i == 0 else 'center')
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            _cell_fmt(cells[i], str(v), bold=(i == 0 and bold_first_col) or ri in bold_rows, align='left' if i == 0 else 'center')
    for j, col in enumerate(t.columns):
        col.width = Cm(widths[j])
        for c in col.cells: c.width = Cm(widths[j])
    return t

# ======================================================================= CAPA
para([('UNIVERSIDADE DO ESTADO DE MATO GROSSO (UNEMAT)\nPROGRAMA DE PÓS-GRADUAÇÃO EM PROPRIEDADE INTELECTUAL E TRANSFERÊNCIA DE TECNOLOGIA PARA A INOVAÇÃO (PROFNIT)\nDISCIPLINA: PESQUISA TECNOLÓGICA QUALITATIVA E QUANTITATIVA (STATS) – T01', True)], size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
para([('FLEXIBILIZAÇÃO DO ACESSO A ARMAS DE FOGO E HOMICÍDIOS NOS MUNICÍPIOS BRASILEIROS E NA FRONTEIRA AGRÍCOLA: EVIDÊNCIA DE DIFERENÇAS EM DIFERENÇAS COM REGISTROS DO SINARM (2015–2024)', True)], size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
para('2ª Avaliação (AV2) – Projeto Empírico com Diferenças em Diferenças (DiD)\nDocente: Prof. Dr. Cleiton Franco\nSinop – MT | Novembro de 2026', size=11, align=WD_ALIGN_PARAGRAPH.CENTER)

b2 = r['(2) TWFE c/ controles, ponderado pop']; ef_iqr = b2['coef'] * (I['p75'] - I['p25'])
cs_nyt = [float(x) for x in CS['taxa_homic_af|not_yet_treated']['simple'][0][1:5]]
cs_nev = [float(x) for x in CS['taxa_homic_af|never_treated']['simple'][0][1:5]]
cs_tr = [float(x) for x in CS['taxa_obitos_transito|not_yet_treated']['simple'][0][1:5]]
coh = I['coortes']; nmun = I['n_mun']

# ======================================================================= 1. INTRODUÇÃO
SEC('1. INTRODUÇÃO')
T('Entre 2019 e 2022, o Brasil experimentou a mais profunda alteração regulatória no controle de armas de fogo desde a promulgação do Estatuto do Desarmamento (Lei nº 10.826/2003). Por meio de uma sequência de decretos presidenciais e portarias do Comando do Exército, o governo federal flexibilizou a comprovação de efetiva necessidade para a posse de armas por civis, ampliou os limites de aquisição de armamentos e munições e estendeu o acesso a calibres restritos para Caçadores, Atiradores Desportivos e Colecionadores (CACs). Como resultado, o número de Certificados de Registro de CACs ativos no SIGMA/Exército saltou de 117.467 em 2018 para 783.385 em 2022, e os novos registros de armas de fogo por civis no SINARM/Polícia Federal passaram de cerca de 75 mil por ano em 2018–2019 para 131 mil em 2020 e 165 mil em 2021, recuando para cerca de 21 mil por ano após o Decreto nº 11.615/2023, que reverteu parcialmente a flexibilização.')
T('A expansão do acesso a armas legais ocorreu de forma geograficamente heterogênea, sendo proporcionalmente mais intensa nos municípios da fronteira agrícola da Amazônia Legal e do Matopiba. Nessas localidades, propriedades rurais isoladas de elevado valor patrimonial, baixa presença policial e conflitos fundiários recorrentes criaram forte demanda por autodefesa armada. Sob a ótica da economia do crime de Gary Becker (1968), essa injeção de armas legais produz previsões teoricamente ambíguas: pelo efeito de dissuasão, a maior probabilidade de a vítima estar armada eleva o custo esperado do crime; pelo efeito de disponibilidade, o maior estoque de armas em circulação aumenta a letalidade de conflitos interpessoais e agrários, elevando os homicídios por arma de fogo.')
L('Pergunta causal: ', 'Qual é o efeito causal da expansão municipal dos registros de armas de fogo por civis, induzida pelos decretos federais de flexibilização de 2019–2022 (e parcialmente revertida em 2023), sobre a taxa de homicídios por arma de fogo nos municípios brasileiros, e esse efeito é mais intenso na fronteira agrícola?')
L('Hipótese: ', 'Sob predominância do efeito de disponibilidade de Becker (1968), municípios com maior expansão per capita de registros de armas após 2019 apresentam aumento estatisticamente significativo da taxa de homicídios por arma de fogo (β > 0), efeito específico ao meio arma de fogo (não observado em homicídios por arma branca), possivelmente amplificado na fronteira agrícola ativa e atenuado após a restrição imposta pelo Decreto nº 11.615/2023.')
L('Objetivo geral: ', 'Estimar o efeito causal da flexibilização do acesso a armas de fogo, medida pelos registros municipais do SINARM, sobre a letalidade violenta (homicídios por arma de fogo) entre 2015 e 2024, empregando Diferenças em Diferenças com intensidade de tratamento contínua e adoção escalonada.')
L('Objetivos específicos: ', 'Os objetivos específicos compreendem:')
BUL('Mensuração da exposição: ', 'Quantificar a intensidade municipal de exposição ao choque regulatório (ΔREG_i, novos registros de armas por civis em 2019–2022 por mil habitantes) e classificar os municípios em fronteira agrícola ativa versus consolidados a partir do desmatamento observado pelo MapBiomas.')
BUL('Diagnóstico dinâmico e escalonado: ', 'Verificar a hipótese de tendências paralelas no período pré-intervenção (2015–2018) e estimar a trajetória dinâmica dos efeitos (2019–2024) via Event Study e estimador de Callaway e Sant’Anna (2021).')
BUL('Isolamento de mecanismos e robustez: ', 'Isolar o canal de disponibilidade por meio de Tripla Diferença (DDD), comparando homicídios por arma de fogo e por arma branca nos mesmos municípios, e testar a sensibilidade dos achados por placebos temporais e de resultado.')
L('Justificativa e contribuição para o PROFNIT: ', 'A avaliação rigorosa de políticas públicas de segurança, regulação de produtos controlados e governança territorial dialoga diretamente com a linha de gestão pública, políticas regulatórias e transferência de tecnologia aplicada ao monitoramento territorial no âmbito do PROFNIT/UNEMAT. O trabalho integra quatro bases governamentais abertas (SINARM/PF, SIM/DATASUS, IBGE e MapBiomas) em um painel municipal reprodutível, mostrando como dados públicos podem subsidiar o desenho de políticas regulatórias territorialmente focalizadas em Mato Grosso e na Amazônia Legal.')

# ======================================================================= 2. INTERVENÇÃO
SEC('2. A INTERVENÇÃO')
T('A intervenção avaliada consiste no ciclo regulatório federal de flexibilização do acesso a armas de fogo e munições iniciado em janeiro de 2019 e parcialmente revertido em julho de 2023. Diferentemente de programas com adesão voluntária local, os decretos federais alteraram simultaneamente o marco normativo em todo o território nacional, gerando um choque de oferta legal de armamentos cuja absorção local variou conforme a estrutura produtiva, fundiária e cultural de cada município.')
L('Regra de atribuição e exposição ao tratamento: ', 'Embora a norma tenha vigorado nacionalmente a partir de 2019, a intensidade com que cada município foi atingido depende da expansão local dos registros de armas de fogo por civis. A exposição é medida por ΔREG_i = (novos registros de armas por civis no SINARM entre 2019 e 2022) / (população de 2018) × 1.000. Como os registros de CACs do SIGMA/Exército não são divulgados por município (o Exército informa dispor apenas de dados por Região Militar), o SINARM, que registra as armas de posse de civis – justamente o objeto do Decreto nº 9.685/2019 –, é a medida municipal disponível do choque. Para a análise com adoção escalonada (Callaway & Sant’Anna, 2021), define-se a coorte G_i ∈ {2019, 2020, 2021} como o primeiro ano em que a taxa anual de novos registros do município atingiu ao menos o dobro de sua média de 2015–2018.')
CAP('Quadro 1 – Cronologia documental e marco legal da intervenção (2019–2023)')
body.insert(body.index(body[-1]) if body[-1].tag == qn('w:sectPr') else len(body), quadro)
# ajusta a linha de 2022 do quadro
for tc in quadro.iter(qn('w:t')):
    if 'Pico histórico' in (tc.text or ''): tc.text = 'Pico histórico (783 mil CRs de CAC; 165 mil novos registros SINARM em 2021)'
    if (tc.text or '').startswith('Início do choque'): tc.text = 'Início do choque (Pós_2019 = 1)'
# move o quadro para antes do sectPr
sect = body.find(qn('w:sectPr')); body.remove(quadro); sect.addprevious(quadro)
NOTE('Fonte: Elaboração própria a partir da legislação federal publicada no Diário Oficial da União (DOU); FBSP (2023); SINARM/PF.')
T('A Figura 1 mostra a resposta mensal dos registros ao ciclo regulatório. Os novos registros de armas por civis no SINARM oscilavam entre 4 e 8 mil por mês até 2019; a aceleração ganha força a partir de meados de 2020 (mais de 13 mil por mês), atinge o pico em 2021 (até 16 mil por mês) e desaba a partir do fim de 2022, estabilizando-se em cerca de 2 mil por mês após os Decretos nº 11.366/2023 e nº 11.615/2023. A defasagem entre os decretos de 2019 e a aceleração de 2020 indica que o choque se materializou gradualmente – por isso a intensidade é medida pelo acumulado de 2019 a 2022 e as coortes são definidas pelo primeiro salto de cada município.')
CAP('Figura 1 – Novos registros mensais de armas de fogo por civis no Brasil e marcos regulatórios (jan/2015–jun/2026)')
FIG('fig_registros_mensais.png', 16)
NOTE('Nota: soma nacional mensal dos registros da categoria “Cidadão” no SINARM, por mês de emissão. Linhas verticais: Decretos nº 9.685 (jan/2019), nº 9.785 (mai/2019), nº 10.627 a 10.630 (fev/2021), nº 11.366 (jan/2023) e nº 11.615 (jul/2023). Fonte: Elaboração própria a partir de SINARM/PF.')

# ======================================================================= 3. LITERATURA (mantida)
SEC('3. REVISÃO DE LITERATURA')
T('A literatura econômica sobre o nexo entre regulação de armas de fogo e criminalidade estrutura-se a partir do modelo de escolha racional de Becker (1968), segundo o qual potenciais infratores ponderam os benefícios esperados do delito contra os custos esperados (probabilidade de detecção, reação da vítima e severidade da punição). A partir desse arcabouço, diversos estudos empíricos investigaram qual canal prevalece na prática:')
BUL('Lott e Mustard (1997): ', 'Utilizando dados em painel dos condados norte-americanos (1977–1992) e modelos de efeitos fixos bidirecionais (TWFE), avaliaram o impacto de leis estaduais de porte velado (right-to-carry), encontrando reduções nos crimes violentos e argumentando que a possibilidade de vítimas armadas gera efeito de dissuasão.')
BUL('Duggan (2001): ', 'Empregando dados em painel por estado e condado nos Estados Unidos, com vendas de revistas especializadas como proxy da posse local de armas, mostrou que aumentos na posse de armas elevam significativamente os homicídios por arma de fogo, sem reduzir crimes contra a propriedade.')
BUL('Cook e Ludwig (2006): ', 'Usando a fração de suicídios cometidos com arma de fogo como proxy do estoque local de armas, documentaram que a maior prevalência de armas nos domicílios aumenta a taxa de homicídios, confirmando o canal de disponibilidade.')
BUL('Souza et al. (2007): ', 'Avaliando o Estatuto do Desarmamento e a campanha nacional de entrega voluntária de armas, identificaram reduções na mortalidade e nas internações por arma de fogo nos anos subsequentes à restrição legal.')
BUL('Cerqueira e Mello (2012): ', 'Explorando a variação espacial na intensidade do desarmamento após 2003 nos municípios paulistas, estimaram que menos armas em circulação reduziram os homicídios por arma de fogo, sem efeito detectável sobre crimes contra a propriedade.')
BUL('Baculi et al. (2021): ', 'Com dados em painel das regiões brasileiras, registros de armas do SINARM e homicídios do SIM/DATASUS, estimados por efeitos fixos e GMM-sistema, encontraram relação direta entre a entrada de armas legais e os homicídios, com exceção do Sul e do Nordeste, onde a relação é inversa.')
BUL('Wakim (2025): ', 'Empregando Diferenças em Diferenças em um painel dos 27 estados brasileiros entre 1996 e 2022, mostrou que as políticas de controle de armas tiveram efeitos regionalmente divergentes, associadas à redução da violência letal no Sudeste e ao aumento dos homicídios no Nordeste.')
BUL('Literatura recente sobre o ciclo 2019–2022: ', 'Relatórios do Fórum Brasileiro de Segurança Pública (FBSP, 2022; 2023) documentaram a expansão sem precedentes dos registros de CACs e de posse de armas. Não foram encontrados, porém, estudos que estimem efeitos causais da flexibilização de 2019–2022 em nível municipal – lacuna que este trabalho busca preencher.')
BUL('Moreno-Louzada e Menezes-Filho (2024): ', 'Explorando a variação municipal na rentabilidade potencial da soja e o momento da liberação da soja geneticamente modificada em um desenho de Diferenças em Diferenças, mostraram que a expansão da soja elevou significativamente as taxas de homicídio nos municípios brasileiros – evidência que motiva a análise da fronteira da soja como grupo tratado neste trabalho.')
T('Do ponto de vista metodológico, o trabalho incorpora os avanços recentes da literatura de DiD com adoção escalonada e efeitos heterogêneos (Goodman-Bacon, 2021; De Chaisemartin e D’Haultfœuille, 2020; Sun e Abraham, 2021; Callaway e Sant’Anna, 2021), que mostram que o estimador TWFE tradicional pode ser enviesado quando o momento e a intensidade do tratamento variam entre unidades, e o Synthetic Difference-in-Differences (Arkhangelsky et al., 2021). Na avaliação de políticas de armas, Ben-Michael et al. (2024) recomendam justamente combinar DiD com adoção escalonada e controles sintéticos; até onde foi possível verificar, este é o primeiro trabalho a aplicar o SDID às políticas de armas no Brasil.')

# ======================================================================= 4. DADOS
SEC('4. DADOS')
T(f'A base de dados final (AV2_painel_municipal_Brasil.csv) estrutura-se como um painel municipal balanceado cobrindo todos os N = {nmun:,} municípios brasileiros ao longo de T = 10 anos (2015 a 2024), totalizando N × T = 55.700 observações (4 períodos pré-tratamento, 2015–2018, e 6 pós-tratamento, 2019–2024). Os municípios são classificados como de fronteira agrícola ativa (2.785) quando a área desmatada entre 2015 e 2018, em proporção da área municipal, supera a mediana nacional, e como consolidados (2.785) caso contrário. A amostra de 50 municípios proposta originalmente (25 da fronteira – como Sinop, Sorriso, Lucas do Rio Verde, Altamira e Balsas – e 25 do Centro-Sul) é mantida como subamostra de robustez.'.replace(',', '.'))
L('Fontes e links de acesso: ', 'As fontes públicas oficiais utilizadas são:')
BUL('SINARM / Polícia Federal: ', 'dados abertos “REGISTROS_com_categoria” (servicos.dpf.gov.br/dadosabertos/SINARM_CSV/REGISTROS), com cada registro de arma de fogo por ano e mês de emissão, UF, município e categoria do proprietário. Como o servidor da PF não aceita conexões de fora do Brasil, os arquivos foram obtidos de cópias públicas idênticas no GitHub (repositórios yurilq/IBMEC_DESENVOLVIMENTO_AGENTE_2026 e AdrielCout/DadosPorteDeArmasBrasil, cujos arquivos de 2024–2025 são idênticos byte a byte). 99,99% dos 979.601 registros de 2015–2025 foram associados ao código IBGE; por UF, a soma de novos registros 2018–2022 tem correlação de 0,89 com o aumento do estoque ativo publicado pelo FBSP (2023, Tab. 47).')
BUL('DATASUS / SIM (Ministério da Saúde): ', 'microdados de óbitos “Mortalidade_Geral” 2015–2024 (OpenDataSUS), agregados por município de residência: agressão com arma de fogo (CID-10 X93–X95), arma branca (X99), outros meios (X85–X92, X96–X98, Y00–Y09), acidentes de transporte terrestre (V01–V89) e COVID-19 (B34.2).')
BUL('Projeto MapBiomas (Coleção 11): ', 'desmatamento anual por município (perda de vegetação nativa), utilizado para medir a taxa de desmatamento 2015–2018 e definir a fronteira agrícola ativa.')
BUL('IBGE / SIDRA: ', 'estimativas populacionais (Tab. 6579), Censo 2022 (Tab. 4714: população e área), Valor Adicionado Bruto da agropecuária (PIB dos Municípios, Tab. 5938) e IPCA (Tab. 1737).')
BUL('Fórum Brasileiro de Segurança Pública: ', 'Anuários 2022 e 2023, para os totais nacionais de CACs e a validação dos registros do SINARM por UF.')
L('Tratamento aplicado às variáveis: ', 'As variáveis de resultado foram convertidas em taxas por 100 mil habitantes. O VAB agropecuário foi deflacionado pelo IPCA (dezembro de 2022) e transformado em logaritmo per capita; a densidade demográfica também entra em logaritmo. A população de 2023, ano sem estimativa oficial, foi interpolada geometricamente entre o Censo 2022 e a estimativa de 2024; o VAB de 2024, ainda não publicado, repete o de 2023. A intensidade ΔREG_i é usada em sua unidade natural (registros por mil habitantes) e, para comparação com a proposta original, também normalizada em [0,1] via Min-Max após winsorização nos percentis 1 e 99.')
CAP('Tabela 1 – Síntese das variáveis utilizadas na estimação econométrica (Painel 2015–2024)')
TABLE(['Variável', 'Definição operacional', 'Unidade', 'Fonte', 'Papel no modelo'], [
    ['cod_ibge', 'Código IBGE de 7 dígitos do município (i)', 'Código', 'IBGE', 'EF α_i e cluster'],
    ['ano', 'Ano da observação (2015–2024)', 'Ano', '—', 'EF λ_t'],
    ['delta_reg_pc', 'Novos registros de armas por civis 2019–2022 por mil hab. (pop. 2018)', 'Reg./mil hab.', 'SINARM/PF; IBGE', 'Intensidade ΔREG_i'],
    ['intens_reg', 'delta_reg_pc winsorizado (p1–p99) e normalizado Min-Max', 'Índice [0,1]', 'Elaboração própria', 'Intensidade alternativa'],
    ['pos_2019 / pos_2023', 'Dummies de período (t ≥ 2019; t ≥ 2023)', 'Binária', 'Legislação', 'Pós_t; reversão'],
    ['ano_primeiro_salto', '1º ano 2019–21 com taxa de registros ≥ 2× a média 2015–18 (0 = nunca)', 'Ano', 'SINARM/PF', 'Coorte C&S'],
    ['fronteira_ativa', 'Desmatamento 2015–18 (% da área) > mediana nacional', 'Binária', 'MapBiomas Col. 11', 'Heterogeneidade'],
    ['taxa_homic_af', 'Óbitos por agressão com arma de fogo (X93–X95)', 'Óbitos/100 mil', 'SIM/DATASUS', 'Resultado principal'],
    ['taxa_homic_ab', 'Óbitos por agressão com arma branca (X99)', 'Óbitos/100 mil', 'SIM/DATASUS', 'Controle DDD'],
    ['taxa_obitos_transito', 'Óbitos em acidentes de transporte terrestre (V01–V89)', 'Óbitos/100 mil', 'SIM/DATASUS', 'Placebo de resultado'],
    ['log_vab_agro_pc', 'Log do VAB agropecuário real per capita (IPCA dez/2022)', 'ln(R$)', 'IBGE', 'Controle X_it'],
    ['log_densidade_pop', 'Log da densidade demográfica', 'ln(hab./km²)', 'IBGE', 'Controle X_it'],
    ['taxa_mortalidade_covid', 'Óbitos por COVID-19 (B34.2)', 'Óbitos/100 mil', 'SIM/DATASUS', 'Controle X_it'],
], [3.3, 5.6, 2.2, 2.6, 2.8], bold_first_col=True)
NOTE('Nota: o dicionário completo das 38 colunas da base consta na planilha AV2_painel_municipal_Brasil.xlsx (aba Dicionario). Fonte: Elaboração própria.')

# ======================================================================= 5. ESTRATÉGIA
SEC('5. ESTRATÉGIA EMPÍRICA')
T('Como os decretos de flexibilização foram editados em âmbito federal a partir de 2019, a identificação causal explora a variação transversal contínua na intensidade com que cada município absorveu o choque (ΔREG_i) antes e depois de 2019. O modelo de efeitos fixos bidirecionais (TWFE) é especificado como:')
EQ('Y_it = α_i + λ_t + β · (ΔREG_i × Pós_t) + X_it′γ + ε_it')
T('Em que cada termo representa:')
BUL('Y_it: ', 'taxa de homicídios por arma de fogo por 100 mil habitantes do município i no ano t.')
BUL('α_i: ', 'efeitos fixos de município, que absorvem características locais invariantes no tempo (geografia, cultura histórica de armas, instituições locais).')
BUL('λ_t: ', 'efeitos fixos de ano, que controlam choques nacionais, mudanças na legislação penal e choques agregados da pandemia de COVID-19.')
BUL('ΔREG_i × Pós_t: ', 'interação DiD contínua; β mede o efeito de um novo registro de arma por mil habitantes sobre a taxa de homicídios por arma de fogo após 2019.')
BUL('X_it e ε_it: ', 'controles variantes no tempo (log do VAB agropecuário per capita, log da densidade e mortalidade por COVID-19) e termo de erro, com erros-padrão agrupados por município (5.570 clusters). As regressões são ponderadas pela população, para que municípios muito pequenos – cujas taxas oscilam fortemente com um único óbito – não dominem a estimativa.')
T('Para avaliar se o efeito é maior na fronteira agrícola, adiciona-se a interação tripla ΔREG_i × Pós_t × Fronteira_i; para captar a reversão parcial, adiciona-se ΔREG_i × Pós2023_t. Como alternativa que respeita a natureza de contagem do resultado, estima-se também um modelo de Poisson com efeitos fixos e o logaritmo da população como offset.')
L('Event Study e Adoção Escalonada: ', 'Para testar a hipótese de tendências paralelas (2015–2018) e mapear a dinâmica dos efeitos – incluindo a inflexão após o Decreto nº 11.615/2023 –, estima-se o Event Study com 2018 (k = −1) como referência:')
EQ('Y_it = α_i + λ_t + Σ_{t ≠ 2018} δ_t · (ΔREG_i × 1[Ano = t]) + X_it′γ + ε_it')
T('Considerando que a aceleração dos registros ocorreu de forma escalonada entre municípios (coortes 2019, 2020 e 2021) e que o TWFE pode ser enviesado na presença de efeitos heterogêneos (Goodman-Bacon, 2021), estima-se também o modelo de Callaway e Sant’Anna (2021), usando como comparação os municípios ainda não tratados (not-yet-treated) e, alternativamente, os nunca tratados.')
L('Synthetic Difference-in-Differences (SDID): ', 'Como verificação adicional da hipótese de tendências paralelas, estima-se o SDID de Arkhangelsky et al. (2021), que combina o DiD com o controle sintético: os municípios de comparação recebem pesos (ω) escolhidos para reproduzir a trajetória pré-2019 dos tratados, e os anos pré-tratamento recebem pesos (λ) que privilegiam os períodos mais parecidos com o pós-tratamento. Como o SDID exige tratamento binário com adoção em bloco, os grupos são definidos de três formas: (a) quartil superior versus quartil inferior de ΔREG_i; (b) coorte que saltou em 2019 versus municípios nunca tratados; e (c) fronteira da soja versus municípios produtores de soja consolidados. Os erros-padrão são obtidos por bootstrap de municípios (200 réplicas), e os resultados são comparados com o DiD simples e o controle sintético (SC).')
L('Fronteira da soja como grupo tratado: ', 'Define-se como fronteira da soja o município com ao menos 1.000 hectares de soja em 2018 (IBGE/PAM), área de soja crescente em pelo menos 50% entre 2010 e 2018 e desmatamento 2015–2018 acima da mediana nacional (MapBiomas). Os grupos de comparação são os municípios sem produção relevante de soja e os produtores consolidados. Estima-se Y_it = α_i + λ_t + θ·(FronteiraSoja_i × Pós_t) + X_it′γ + ε_it, bem como a tripla interação ΔREG_i × Pós_t × FronteiraSoja_i.')
L('Hipótese de identificação e ameaças: ', 'A identificação repousa sobre a premissa de que, na ausência dos decretos, municípios com alta e baixa expansão de registros teriam seguido trajetórias paralelas de homicídios por arma de fogo. As principais ameaças são: (i) causalidade reversa (municípios mais violentos demandarem mais armas), mitigada pelos efeitos fixos de município, pela especificação com tendências por linha de base de registros e pelo placebo temporal em 2017; e (ii) choques locais concomitantes (crescimento econômico, pandemia), abordados pela Tripla Diferença (DDD), que compara homicídios por arma de fogo (AF_m = 1) e por arma branca (AF_m = 0) dentro do mesmo município e ano:')
EQ('Y_imt = α_im + λ_mt + θ_it + β_DDD · (ΔREG_i × AF_m × Pós_t) + ε_imt')

# ======================================================================= 6. RESULTADOS
SEC('6. RESULTADOS')
u = df.drop_duplicates('cod_ibge')
def grp(g, per):
    s = g[g.pos_2019 == (1 if per == 'pos' else 0)]
    w = lambda a, b: s[a].sum() / s[b].sum()
    return s
rows = []
specs = [('Municípios', None), ('Intensidade ΔREG_i (reg./mil hab.)', 'delta_reg_pc'), ('Novos registros de armas/mil hab./ano', 'reg_cidadao_1000'),
         ('Homicídios arma de fogo (/100 mil)', 'taxa_homic_af'), ('Homicídios arma branca (/100 mil)', 'taxa_homic_ab'), ('Óbitos trânsito – placebo (/100 mil)', 'taxa_obitos_transito'),
         ('Homic. AF – taxa agregada (/100 mil)', 'agg_af')]
cells = {}
for fa in (0, 1):
    for per in (0, 1):
        s = df[(df.fronteira_ativa == fa) & (df.pos_2019 == per)]; col = []
        for lab, v in specs:
            if v is None: col.append(f'{s.cod_ibge.nunique():,}'.replace(',', '.'))
            elif v == 'agg_af': col.append(f(s.af.sum() / s['pop'].sum() * 1e5, 2))
            else: col.append(f'{f(s[v].mean(), 2)} ({f(s[v].std(), 2)})')
        cells[(fa, per)] = col
tot = []
for lab, v in specs:
    if v is None: tot.append(f'{nmun:,}'.replace(',', '.'))
    elif v == 'agg_af': tot.append(f(df.af.sum() / df['pop'].sum() * 1e5, 2))
    else: tot.append(f'{f(df[v].mean(), 2)} ({f(df[v].std(), 2)})')
for i, (lab, v) in enumerate(specs):
    rows.append([lab, cells[(0, 0)][i], cells[(0, 1)][i], cells[(1, 0)][i], cells[(1, 1)][i], tot[i]])
ag = {k: df[(df.fronteira_ativa == k[0]) & (df.pos_2019 == k[1])] for k in [(0, 0), (0, 1), (1, 0), (1, 1)]}
r_reg = {k: v.reg_cidadao.sum() / v['pop'].sum() * 1000 for k, v in ag.items()}
r_af = {k: v.af.sum() / v['pop'].sum() * 1e5 for k, v in ag.items()}
T(f'A Tabela 2 sintetiza as estatísticas descritivas por grupo territorial e período. A fronteira agrícola ativa absorveu o choque com mais intensidade: a taxa agregada de novos registros de armas por civis passou de {f(r_reg[(1,0)],2)} para {f(r_reg[(1,1)],2)} por mil habitantes ao ano (+{f(100*(r_reg[(1,1)]/r_reg[(1,0)]-1),0)}%), contra {f(r_reg[(0,0)],2)} para {f(r_reg[(0,1)],2)} nos municípios consolidados (+{f(100*(r_reg[(0,1)]/r_reg[(0,0)]-1),0)}%) (Figura 2). Os homicídios por arma de fogo, por sua vez, caíram em ambos os grupos – de {f(r_af[(1,0)],2)} para {f(r_af[(1,1)],2)} por 100 mil na fronteira e de {f(r_af[(0,0)],2)} para {f(r_af[(0,1)],2)} nos consolidados –, acompanhando a queda nacional observada a partir de 2018. A questão causal é, portanto, se a queda foi menor onde mais armas entraram em circulação.')
CAP('Tabela 2 – Estatísticas descritivas por grupo territorial e período (Painel 2015–2024)')
TABLE(['Variável', 'Consolidados Pré (2015–18)', 'Consolidados Pós (2019–24)', 'Fronteira Pré (2015–18)', 'Fronteira Pós (2019–24)', 'Total (N = 55.700)'], rows, [4.4, 2.4, 2.4, 2.4, 2.4, 2.4], bold_first_col=True)
NOTE('Nota: médias simples entre municípios, com desvio-padrão entre parênteses; a última linha traz a taxa agregada do grupo (óbitos totais / população total). Fronteira agrícola ativa: desmatamento 2015–2018 acima da mediana nacional (MapBiomas). Fonte: Elaboração própria a partir de SINARM/PF, SIM/DATASUS, IBGE e MapBiomas.')
CAP('Figura 2 – Novos registros de armas de fogo por civis por mil habitantes, por grupo territorial (2015–2024)')
FIG('fig1_registros_sinarm.png')
NOTE('Nota: taxa agregada de novos registros (categoria “Cidadão”) do SINARM por mil habitantes. Linhas verticais marcam os decretos de flexibilização (2019) e a restrição parcial pelo Decreto nº 11.615/2023. Fonte: Elaboração própria a partir de SINARM/PF e IBGE.')
CAP('Figura 3 – Homicídios por arma de fogo por quartil de expansão dos registros (2015–2024)')
FIG('fig_tendencias_quartis.png')
NOTE('Nota: taxa agregada de homicídios por arma de fogo (óbitos/100 mil) nos municípios do 1º e do 4º quartil de ΔREG_i. Fonte: Elaboração própria a partir de SIM/DATASUS, SINARM/PF e IBGE.')

def cf(k): x = r[k]; return f"{f(x['coef'])}{st(x['p'])}", f"({f(x['se'])})"
c1, c2, c3, c3i, c4, c4i, c5 = (cf(k) for k in ['(1) TWFE s/ controles, ponderado pop', '(2) TWFE c/ controles, ponderado pop', '(3) Fronteira: ΔREG×Pós',
                                              '(3) Fronteira: ΔREG×Pós×Fronteira', '(4) Reversão: ΔREG×Pós2019', '(4) Reversão: ΔREG×Pós2023', '(5) Poisson (contagem, offset pop)'])
cs_txt = (f"{f(cs_nyt[0])}{st(2*(1-__import__('scipy.stats',fromlist=['norm']).norm.cdf(abs(cs_nyt[0]/cs_nyt[1]))))}", f"({f(cs_nyt[1])})")
T3 = [['ΔREG_i × Pós_2019', c1[0], c2[0], c3[0], c4[0], c5[0], cs_txt[0]],
      ['', c1[1], c2[1], c3[1], c4[1], c5[1], cs_txt[1]],
      ['ΔREG_i × Pós_2019 × Fronteira_i', '—', '—', c3i[0], '—', '—', '—'], ['', '', '', c3i[1], '', '', ''],
      ['ΔREG_i × Pós_2023', '—', '—', '—', c4i[0], '—', '—'], ['', '', '', '', c4i[1], '', ''],
      ['Controles variantes no tempo', 'Não', 'Sim', 'Sim', 'Sim', 'Sim', 'Não'],
      ['Efeitos fixos de município e ano', 'Sim', 'Sim', 'Sim', 'Sim', 'Sim', '—'],
      ['Ponderação', 'Pop.', 'Pop.', 'Pop.', 'Pop.', 'Offset', 'Pop.'],
      ['Observações (N × T)', '55.700', '55.700', '55.700', '55.700', f"{r['(5) Poisson (contagem, offset pop)']['n']:,}".replace(',', '.'), '55.700'],
      ['Clusters (municípios)', '5.570', '5.570', '5.570', '5.570', '5.084', '5.570']]
CAP('Tabela 3 – Efeito da expansão dos registros de armas sobre homicídios por arma de fogo (2015–2024)')
TABLE(['Variável explicativa', '(1) TWFE s/ controles', '(2) TWFE c/ controles', '(3) Fronteira', '(4) Reversão 2023', '(5) Poisson', '(6) Callaway & Sant’Anna'], T3,
      [4.4, 2.0, 2.0, 2.0, 2.0, 2.0, 2.2], bold_first_col=False, bold_rows=())
NOTE('Nota: variável dependente: homicídios por arma de fogo por 100 mil habitantes (coluna 5: contagem de óbitos, Poisson com offset ln(pop); coeficiente = semi-elasticidade). ΔREG_i em novos registros por mil habitantes (2019–2022). Coluna (6): ATT agregado do estimador de Callaway e Sant’Anna (2021) para as coortes 2019–2021, grupo de comparação “ainda não tratados”, ATT em óbitos/100 mil. Erros-padrão agrupados por município entre parênteses. Os municípios sem nenhum homicídio por arma de fogo no período saem do Poisson. * p<0,10; ** p<0,05; *** p<0,01. Fonte: Elaboração própria.')
x6 = r['(6) Intensidade Min-Max [0,1]']; x5 = r['(5) Poisson (contagem, offset pop)']
L('Interpretação econômica na unidade de Y: ', f"Na especificação principal (coluna 2), β = {f(b2['coef'])} (EP = {f(b2['se'])}; p = {pv(b2['p'])}). Cada novo registro de arma por mil habitantes entre 2019 e 2022 está associado a um aumento de {f(b2['coef'],2)} homicídios por arma de fogo por 100 mil habitantes ao ano no período pós-2019. Passar do 1º para o 3º quartil de exposição ({f(I['p25'],2)} → {f(I['p75'],2)} registros por mil habitantes) implica +{f(ef_iqr,2)} óbitos por 100 mil, cerca de {f(100*ef_iqr/I['mean_af'],1)}% da taxa média ponderada da amostra ({f(I['mean_af'],2)}); um desvio-padrão de ΔREG_i ({f(I['sd_delta'],2)}) corresponde a +{f(b2['coef']*I['sd_delta'],2)} óbitos por 100 mil. Na escala Min-Max proposta originalmente, ir do menor ao maior grau de exposição equivale a +{f(x6['coef'],2)} óbitos por 100 mil (p = {pv(x6['p'])}). O modelo de Poisson (coluna 5) indica aumento de {f(100*x5['coef'],2)}% nos homicídios por arma de fogo por registro adicional por mil habitantes (p = {pv(x5['p'])}).")
T(f"O estimador de adoção escalonada de Callaway e Sant’Anna (2021) (coluna 6) corrobora o achado: os municípios que tiveram um salto de registros apresentaram, em média, {f(cs_nyt[0],2)} homicídios por arma de fogo a mais por 100 mil habitantes (EP = {f(cs_nyt[1],2)}; IC 95%: {f(cs_nyt[2],2)} a {f(cs_nyt[3],2)}), resultado praticamente idêntico quando o grupo de comparação são os municípios nunca tratados (ATT = {f(cs_nev[0],2)}; EP = {f(cs_nev[1],2)}). As coortes são formadas por {coh.get('2019')} municípios em 2019, {coh.get('2020')} em 2020 e {coh.get('2021')} em 2021, com {coh.get('0')} nunca tratados.")
T(f"Quanto à heterogeneidade territorial (coluna 3), a interação com a fronteira agrícola é negativa e não significativa ({f(r['(3) Fronteira: ΔREG×Pós×Fronteira']['coef'])}; p = {pv(r['(3) Fronteira: ΔREG×Pós×Fronteira']['p'])}): cada registro adicional tem efeito semelhante na fronteira e nos municípios consolidados. Ou seja, a fronteira agrícola importa porque recebeu mais armas, e não porque cada arma seja mais letal lá. De forma consistente, um DiD que define a fronteira como grupo tratado mostra que ela teve expansão maior de registros (+{f(FT['fronteira_registros'][0],3)} por mil hab./ano; p {pv(FT['fronteira_registros'][2])}), mas nenhuma diferença detectável nos homicídios por arma de fogo ({f(FT['fronteira_pond'][0],2)}; EP = {f(FT['fronteira_pond'][1],2)}; p = {pv(FT['fronteira_pond'][2])}), pois a classificação binária mistura municípios com doses muito distintas. Por fim, o termo de reversão (coluna 4) é positivo e não significativo ({f(r['(4) Reversão: ΔREG×Pós2023']['coef'])}; p = {pv(r['(4) Reversão: ΔREG×Pós2023']['p'])}): até 2024 não há sinal de que a restrição de 2023 tenha revertido o efeito, o que é coerente com a permanência do estoque de armas acumulado em 2019–2022.")

es = ES['taxa_homic_af']['coefs']; et = ES['taxa_obitos_transito']['coefs']
cse = {int(float(x[0])): [float(v) for v in x[1:5]] for x in CS['taxa_homic_af|not_yet_treated']['event']}
rows = []
for y in range(2015, 2025):
    k = y - 2019
    cs_cell = f(cse[k][0], 3) if k in cse else '—'
    if y == 2018:
        rows.append(['2018 (Ref.)', 'k = −1', '0,000', '—', '0,000', '—', f(cse[-1][0], 3) if -1 in cse else '—']); continue
    a = es[str(y)]; t = et[str(y)]
    rows.append([str(y), f'k = {k:+d}'.replace('+', '+').replace('-', '−'), f(a[0]) + st(a[4]), f(a[1]), f(t[0]) + st(t[4]), f(t[1]), cs_cell])
rows.append(['Teste conjunto pré', '2015–2017', f"F = {f(ES['taxa_homic_af']['F'],3)}", f"p = {f(ES['taxa_homic_af']['p'],4)}", f"F = {f(ES['taxa_obitos_transito']['F'],3)}", f"p = {f(ES['taxa_obitos_transito']['p'],4)}", '—'])
CAP('Tabela 4 – Estimativas dinâmicas do Event Study e teste conjunto pré-tratamento (Base = 2018)')
TABLE(['Ano (t)', 'Período', 'Homic. AF (δ_t)', 'EP', 'Trânsito – placebo (δ_t)', 'EP', 'C&S: ATT por k*'], rows, [2.4, 1.9, 2.4, 1.7, 2.7, 1.7, 2.6], bold_first_col=True)
NOTE('Nota: Event Study TWFE com efeitos fixos de município e ano, controles e ponderação pela população; erros-padrão agrupados por município (N = 55.700; 5.570 clusters); 2018 omitido. *Última coluna: ATT do estimador de Callaway e Sant’Anna por tempo relativo ao primeiro salto de registros (k), com período-base variável, alinhado à linha cujo k coincide (k = −1 é o ano anterior ao salto). Teste de Wald para H0: δ_2015 = δ_2016 = δ_2017 = 0. * p<0,10; ** p<0,05; *** p<0,01. Fonte: Elaboração própria.')
CAP('Figura 4 – Event Study TWFE: coeficientes dinâmicos (δ_t) e IC 95% (Base = 2018)')
FIG('fig2_event_study_twfe.png', 16)
NOTE('Nota: coeficientes por +1 registro por mil habitantes, com IC de 95% (erros-padrão agrupados por município). Fonte: Elaboração própria a partir de SIM/DATASUS, SINARM/PF e IBGE.')
CAP('Figura 5 – Callaway e Sant’Anna (2021): ATT por tempo relativo ao primeiro salto de registros')
FIG('fig3_callaway_santanna.png')
NOTE('Nota: grupo de comparação “ainda não tratados”, ponderação pela população, IC de 95%. Fonte: Elaboração própria.')
pre = [es[str(y)] for y in (2015, 2016, 2017)]; post = [es[str(y)] for y in range(2019, 2025)]
T(f"O Event Study (Tabela 4 e Figura 4) mostra coeficientes pós-2019 positivos e significativos em todos os anos, entre {f(min(p[0] for p in post),2)} e {f(max(p[0] for p in post),2)} óbitos por 100 mil por registro adicional por mil habitantes, com os maiores valores em 2022–2023, auge do estoque acumulado. Os coeficientes pré-tratamento, porém, também são positivos ({f(pre[0][0],2)}, {f(pre[1][0],2)} e {f(pre[2][0],2)} em 2015–2017), e o teste conjunto rejeita a nulidade ao nível de 5% (F = {f(ES['taxa_homic_af']['F'],2)}; p = {f(ES['taxa_homic_af']['p'],3)}). Isso indica que parte da diferença reflete 2018 ter sido um ano de queda particularmente acentuada dos homicídios nos municípios de alta exposição. No estimador de Callaway e Sant’Anna (Figura 5), que compara cada coorte com seus próprios anos pré-salto, os períodos k = −4 a k = −1 não são estatisticamente diferentes de zero, enquanto os ATTs pós-salto são positivos e crescentes, o que reforça a interpretação causal.")

sr = SJ['res']; nS = SJ['n']; ss = SJ['sdid']
def lin(k): x = sr[k]; return f"{f(x['coef'])}{st(x['p'])}", f(x['se']), pv(x['p'])
def lsd(k, m='sdid'): x = ss[k][m]; return f"{f(x['tau'])}{st(x['p'])}", f(x['se']), pv(x['p'])
def lcs(k): x = CSJ[k]; return f"{f(x['att'])}{st(x['p'])}", f(x['se']), pv(x['p'])
cse_ = CSJ['Escalonado (salto de registros) – controle ainda não tratados']; cco = CSJ['coortes_escalonado']
L('Fronteira da soja como grupo tratado: ', f"Foram identificados {nS['Fronteira da soja']} municípios na fronteira da soja (concentrados em RS, MT, TO, GO, MG, SC e MA), {nS['Soja consolidada']} produtores consolidados e {nS['Sem soja']} sem produção relevante. A Tabela 6 mostra que a fronteira da soja teve expansão adicional de registros de armas após 2019 (primeiro estágio positivo e significativo nas duas comparações). Contra os municípios sem soja, o DiD indica +{f(sr['DiD homic. AF vs. sem soja']['coef'],2)} homicídios por arma de fogo por 100 mil (p {pv(sr['DiD homic. AF vs. sem soja']['p'])}), mas o Event Study revela tendência de alta já antes de 2019 (teste conjunto pré: p = {f(sr['Event study vs. sem soja']['p'],3)}), típica da interiorização da violência. O SDID, que reequilibra a trajetória pré-2019, estima +{f(ss['SDID vs. sem soja']['sdid']['tau'],2)} (p {pv(ss['SDID vs. sem soja']['sdid']['p'])}) contra os municípios sem soja e +{f(ss['SDID vs. soja consolidada']['sdid']['tau'],2)} (p = {pv(ss['SDID vs. soja consolidada']['sdid']['p'])}) contra a soja consolidada, a comparação mais limpa, pois isola a expansão recente de municípios com a mesma base produtiva. Homicídios por arma branca não se alteram. A tripla interação mostra que o efeito por registro adicional é maior na fronteira da soja (+{f(sr['DDD: ΔREG × Pós × Fronteira da soja (todos)']['coef'],2)} por registro/mil hab.; p = {pv(sr['DDD: ΔREG × Pós × Fronteira da soja (todos)']['p'])}). Quando os municípios tratados são ponderados pela população, porém, os efeitos do SDID deixam de ser significativos, indicando que o resultado é puxado pelos municípios pequenos e médios da fronteira.")
T(f"O estimador de Callaway e Sant’Anna (2021), que compara cada coorte com seus próprios anos pré-tratamento, confirma o efeito na fronteira da soja. Na versão escalonada – em que cada município da fronteira entra no tratamento no ano de seu primeiro salto de registros de armas ({cco.get('2019.0')} em 2019, {cco.get('2020.0')} em 2020 e {cco.get('2021.0')} em 2021), tendo como controles os produtores de soja consolidados e os ainda não tratados –, o ATT é de +{f(cse_['att'],2)} homicídios por arma de fogo por 100 mil (EP = {f(cse_['se'],2)}; p = {pv(cse_['p'])}), sem nenhum coeficiente pré-tratamento significativo, e permanece praticamente igual com ponderação pela população (+{f(CSJ['Escalonado (salto de registros) – controle ainda não tratados, pond.']['att'],2)}; p = {pv(CSJ['Escalonado (salto de registros) – controle ainda não tratados, pond.']['p'])}). O efeito surge no ano do salto e cresce nos anos seguintes. Com tratamento em bloco em 2019, o ATT é de +{f(CSJ['Bloco 2019 vs. sem soja']['att'],2)} contra os municípios sem soja (p {pv(CSJ['Bloco 2019 vs. sem soja']['p'])}) e de +{f(CSJ['Bloco 2019 vs. soja consolidada']['att'],2)} contra a soja consolidada (p = {pv(CSJ['Bloco 2019 vs. soja consolidada']['p'])}); o placebo com homicídios por arma branca é nulo em todas as versões. O efeito na fronteira da soja (cerca de +2,4) supera o efeito médio nacional (+{f(cs_nyt[0],2)}), em linha com a tripla interação.")
CAP('Tabela 6 – Fronteira da soja como grupo tratado: DiD, Event Study, SDID e Callaway e Sant’Anna')
rows6 = [['1º estágio: novos registros/mil hab./ano', *lin('1º estágio: registros/mil hab. vs. sem soja'), *lin('1º estágio: registros/mil hab. vs. soja consolidada')],
         ['DiD TWFE – homic. AF (ponderado pop.)', *lin('DiD homic. AF vs. sem soja'), *lin('DiD homic. AF vs. soja consolidada')],
         ['DiD TWFE – homic. AF (sem ponderação)', *lin('DiD homic. AF vs. sem soja (sem ponderação)'), *lin('DiD homic. AF vs. soja consolidada (sem ponderação)')],
         ['Placebo: homicídios por arma branca', *lin('Placebo arma branca vs. sem soja'), *lin('Placebo arma branca vs. soja consolidada')],
         ['Event Study: teste conjunto pré (p)', f"F = {f(sr['Event study vs. sem soja']['F'],2)}", '—', f(sr['Event study vs. sem soja']['p'],3), f"F = {f(sr['Event study vs. soja consolidada']['F'],2)}", '—', f(sr['Event study vs. soja consolidada']['p'],3)],
         ['SDID – homic. AF', *lsd('SDID vs. sem soja'), *lsd('SDID vs. soja consolidada')],
         ['SDID – tratados ponderados pela pop.', *lsd('SDID vs. sem soja (tratados ponderados)'), *lsd('SDID vs. soja consolidada (tratados ponderados)')],
         ['C&S – bloco 2019 (nunca tratados)', *lcs('Bloco 2019 vs. sem soja'), *lcs('Bloco 2019 vs. soja consolidada')],
         ['C&S – bloco 2019, ponderado pop.', *lcs('Bloco 2019 vs. sem soja – ponderado pop.'), *lcs('Bloco 2019 vs. soja consolidada – ponderado pop.')],
         ['C&S – placebo arma branca (bloco)', *lcs('Placebo arma branca: bloco 2019 vs. sem soja'), *lcs('Placebo arma branca: bloco 2019 vs. soja consolidada')],
         ['C&S – escalonado pelo salto de registros', '—', '', '', *lcs('Escalonado (salto de registros) – controle ainda não tratados')],
         ['C&S – escalonado, ponderado pop.', '—', '', '', *lcs('Escalonado (salto de registros) – controle ainda não tratados, pond.')],
         ['Municípios tratados / controle', f"{nS['Fronteira da soja']} / {nS['Sem soja']}", '', '', f"{nS['Fronteira da soja']} / {nS['Soja consolidada']}", '', '']]
TABLE(['Especificação', 'vs. sem soja: coef.', 'EP', 'p', 'vs. soja consolidada: coef.', 'EP', 'p'], rows6, [4.6, 2.2, 1.4, 1.5, 2.6, 1.4, 1.5], bold_first_col=True)
NOTE(f"Nota: fronteira da soja = ≥ 1.000 ha de soja em 2018, área de soja +50% entre 2010 e 2018 e desmatamento 2015–18 acima da mediana. DiD com EF de município e ano, controles e EP agrupados por município; SDID com EP por bootstrap de municípios (200 réplicas). C&S = Callaway e Sant’Anna (2021), período-base variável; no escalonado, coortes definidas pelo 1º salto de registros de armas e controles ainda não tratados + soja consolidada (fronteira sem salto excluída). Tripla interação ΔREG × Pós × Fronteira da soja (todos os municípios): {f(sr['DDD: ΔREG × Pós × Fronteira da soja (todos)']['coef'])}{st(sr['DDD: ΔREG × Pós × Fronteira da soja (todos)']['p'])} (EP {f(sr['DDD: ΔREG × Pós × Fronteira da soja (todos)']['se'])}). * p<0,10; ** p<0,05; *** p<0,01. Fonte: Elaboração própria a partir de IBGE/PAM, MapBiomas, SINARM/PF e SIM/DATASUS.")

# ======================================================================= 7. ROBUSTEZ
SEC('7. ROBUSTEZ')
T('Para avaliar a credibilidade causal dos resultados, foram conduzidos os seguintes testes: (i) Tripla Diferença (DDD) comparando homicídios por arma de fogo e por arma branca no mesmo município e ano; (ii) placebo de resultado com óbitos no trânsito; (iii) placebo temporal antecipando o choque para 2017 na amostra pré-tratamento; (iv) especificação binária com o quartil superior de exposição; (v) especificações alternativas de controle de tendências e de amostra.')
rk = [('R1 DDD: AF vs arma branca', '1. Tripla Diferença (DDD)', 'AF vs. arma branca (ΔREG × AF × Pós)'),
      ('R2 Placebo: óbitos no trânsito', '2. Placebo de resultado', 'Óbitos no trânsito (V01–V89)'),
      ('R3 Placebo temporal (2017)', '3. Placebo temporal (2017)', 'Choque fictício em 2017 (2015–2018)'),
      ('R4 Tratamento binário (Q4)', '4. Tratamento binário (Q4)', 'Quartil superior de ΔREG × Pós'),
      ('R5 Homicídios arma branca', '5. Homicídios por arma branca', 'Mesma especificação da col. (2)'),
      ('R6 Homicídios outros meios', '6. Homicídios por outros meios', 'Mesma especificação da col. (2)'),
      ('(8) Tendência por linha de base (pre_reg×ano)', '7. Tendências por linha de base', 'Registros 2015–18 × EF de ano'),
      ('(9) EF UF×ano', '8. EF de UF × ano', 'Choques estaduais anuais'),
      ('(10) Excesso sobre 2015-18', '9. Intensidade em excesso', 'ΔREG − registros 2015–18'),
      ('(7) Sem ponderação', '10. Sem ponderação', 'Todos os municípios, peso igual'),
      ('(12) Municípios ≥ 20 mil hab.', '11. Municípios ≥ 20 mil hab.', 'Sem ponderação'),
      ('R7 Subamostra fronteira', '12. Só fronteira agrícola', 'Ponderado pela população'),
      ('R8 Subamostra consolidados', '13. Só consolidados', 'Ponderado pela população'),
      ('(11) Só os 50 municípios do projeto', '14. Amostra original (50 mun.)', 'Sem ponderação')]
rows = [[lab, desc, f(r[k]['coef']) + st(r[k]['p']), f(r[k]['se']), pv(r[k]['p']), f"{r[k]['n']:,}".replace(',', '.')] for k, lab, desc in rk]
rows.append(['15. C&S – placebo trânsito', 'ATT agregado, ainda não tratados', f(cs_tr[0]), f(cs_tr[1]), pv(2 * (1 - __import__('scipy.stats', fromlist=['norm']).norm.cdf(abs(cs_tr[0] / cs_tr[1])))), '55.700'])
CAP('Tabela 5 – Testes de robustez: Tripla Diferença (DDD), Placebos e Especificações Alternativas')
TABLE(['Teste de robustez', 'Especificação / variável dependente', 'Coeficiente', 'EP cluster', 'p-valor', 'Obs. (N)'], rows, [4.0, 4.4, 2.0, 1.7, 1.7, 1.6], bold_first_col=True)
NOTE('Nota: todas as regressões incluem efeitos fixos de unidade e tempo (DDD: município×meio, ano×meio e município×ano) e erros-padrão agrupados por município. Salvo indicação, controles e ponderação pela população como na coluna (2) da Tabela 3. * p<0,10; ** p<0,05; *** p<0,01. Fonte: Elaboração própria.')
d1 = r['R1 DDD: AF vs arma branca']; d2 = r['R2 Placebo: óbitos no trânsito']; d3 = r['R3 Placebo temporal (2017)']; d5 = r['R5 Homicídios arma branca']; d6 = r['R6 Homicídios outros meios']
T(f"O coeficiente da DDD é positivo e significativo ({f(d1['coef'])}; p = {pv(d1['p'])}), e os homicídios por arma branca não respondem à expansão dos registros ({f(d5['coef'])}; p = {pv(d5['p'])}): o aumento da letalidade é específico ao meio arma de fogo, o que descarta explicações baseadas em tendências gerais de violência e é coerente com o canal de disponibilidade. Homicídios por outros meios apresentam pequeno aumento ({f(d6['coef'])}; p = {pv(d6['p'])}), cerca de um quinto do efeito sobre arma de fogo. O tratamento binário (quartil superior × Pós) indica +{f(r['R4 Tratamento binário (Q4)']['coef'],2)} óbitos por 100 mil (p {pv(r['R4 Tratamento binário (Q4)']['p'])}). Os controles mais exigentes – tendências por linha de base de registros e efeitos fixos de UF × ano – elevam o coeficiente para cerca de {f(r['(9) EF UF×ano']['coef'],2)}, o que afasta a hipótese de que o resultado se deva apenas a diferenças regionais de tendência. O efeito é positivo tanto na fronteira quanto nos consolidados e persiste em municípios com 20 mil habitantes ou mais.")
T(f"Dois resultados pedem cautela. Primeiro, o placebo de resultado com óbitos no trânsito é positivo e significativo no TWFE ({f(d2['coef'])}; p = {pv(d2['p'])}), com efeito concentrado em 2021–2024, o que sugere algum choque concomitante (por exemplo, crescimento econômico e do tráfego em municípios do agronegócio que também compraram mais armas); no estimador de Callaway e Sant’Anna esse placebo não é significativo (ATT = {f(cs_tr[0],2)}; EP = {f(cs_tr[1],2)}). Segundo, o placebo temporal de 2017 é negativo e marginalmente significativo ({f(d3['coef'])}; p = {pv(d3['p'])}), refletindo a queda dos homicídios em 2018 já discutida. Na amostra original de 50 municípios, o efeito não é detectável ({f(r['(11) Só os 50 municípios do projeto']['coef'])}; p = {pv(r['(11) Só os 50 municípios do projeto']['p'])}): com tão poucas unidades, a precisão é insuficiente para detectar efeitos dessa magnitude, o que justifica a expansão para o universo de municípios.")

L('Synthetic Difference-in-Differences: ', 'A Tabela 7 e a Figura 6 apresentam o SDID, que compara os grupos tratados com controles sintéticos ajustados à trajetória pré-2019.')
def sdrow(lab, k, extra=''):
    x = SD[k]; o = [lab]
    for m in ('sdid', 'did', 'sc'): o += [f"{f(x[m]['tau'],2)}{st(x[m]['p'])}", f"({f(x[m]['se'],2)})"]
    return o + [f"{x['N1']} / {x['N0']}"]
rows7 = [sdrow('Q4 vs. Q1 – todos os municípios', 'A'), sdrow('Q4 vs. Q1 – tratados ponderados pela pop.', 'A2'),
         sdrow('Q4 vs. Q1 – municípios ≥ 20 mil hab.', 'B'), sdrow('Q4 vs. Q1 – ≥ 20 mil, tratados ponderados', 'B2'),
         sdrow('Coorte 2019 vs. nunca tratados', 'C'), sdrow('Coorte 2019 vs. nunca tratados – ≥ 20 mil hab.', 'C2'),
         sdrow('Placebo arma branca: Q4 vs. Q1 – ≥ 20 mil', 'D'), sdrow('Placebo trânsito: Q4 vs. Q1 – ≥ 20 mil', 'E')]
CAP('Tabela 7 – Synthetic Difference-in-Differences: homicídios por arma de fogo (/100 mil)')
TABLE(['Tratados vs. controles', 'SDID', 'EP', 'DiD', 'EP', 'SC', 'EP', 'N (T / C)'], rows7, [4.2, 1.9, 1.2, 1.9, 1.2, 1.9, 1.2, 1.8], bold_first_col=True)
NOTE('Nota: SDID de Arkhangelsky et al. (2021), com pesos de unidades e de tempo estimados nos anos 2015–2018 e tratamento em bloco a partir de 2019; DiD = pesos uniformes; SC = controle sintético sem pesos de tempo. EP por bootstrap de municípios (200 réplicas) entre parênteses. Q4/Q1 = quartis superior/inferior de ΔREG_i. * p<0,10; ** p<0,05; *** p<0,01. Fonte: Elaboração própria.')
CAP('Figura 6 – SDID: trajetórias dos tratados e dos controles sintéticos')
FIG('fig_sdid.png', 16.5)
NOTE('Nota: linhas tracejadas = controle sintético do SDID (média ponderada dos controles mais o ajuste de nível do período de referência); barras cinzas = pesos de tempo λ. Fonte: Elaboração própria.')
T(f"Os resultados do SDID são sensíveis à definição dos grupos. Na comparação por coortes entre municípios com 20 mil habitantes ou mais – a mais próxima do desenho de Callaway e Sant’Anna –, o efeito é de +{f(SD['C2']['sdid']['tau'],2)} homicídios por 100 mil (EP {f(SD['C2']['sdid']['se'],2)}), com ajuste pré-tratamento quase perfeito (Figura 6, painel esquerdo). Na comparação entre o quartil superior e o inferior de registros, porém, o SDID é nulo ({f(SD['B']['sdid']['tau'],2)}; EP {f(SD['B']['sdid']['se'],2)}) e, ponderando os tratados pela população, chega a ser negativo ({f(SD['A2']['sdid']['tau'],2)}; EP {f(SD['A2']['sdid']['se'],2)}). Os municípios do quartil inferior concentram-se em regiões (sobretudo no Nordeste) cuja dinâmica de homicídios difere da dos municípios que mais registraram armas (Sul e Centro-Oeste), e quatro anos pré-tratamento são pouco para o SDID reequilibrar essas diferenças. Os placebos (arma branca e trânsito) são nulos no SDID. Em síntese, o SDID confirma o efeito positivo quando a comparação é feita entre municípios semelhantes – coortes de adoção e fronteira da soja versus soja consolidada –, mas não na comparação bruta entre extremos da distribuição, o que recomenda cautela na interpretação da magnitude.")

# ======================================================================= 8. DISCUSSÃO
SEC('8. DISCUSSÃO E LIMITAÇÕES')
T(f"Os achados empíricos alinham-se às evidências de Duggan (2001), Cook e Ludwig (2006) e Cerqueira e Mello (2012): a ampliação do estoque de armas legais em circulação elevou os homicídios por arma de fogo pelo canal de disponibilidade. A magnitude, contudo, é moderada: no estimador mais robusto à heterogeneidade (Callaway e Sant’Anna), cerca de {f(cs_nyt[0],1)} óbitos por 100 mil habitantes, aproximadamente {f(100*cs_nyt[0]/I['mean_af'],0)}% da taxa média. Esse efeito ocorreu em um período de queda nacional dos homicídios, de modo que a flexibilização não reverteu a tendência de queda, mas a desacelerou nos municípios mais expostos. Na fronteira agrícola definida pelo desmatamento, o efeito por arma adicional não é maior; na fronteira da soja – onde a expansão da área plantada se combina com desmatamento recente –, porém, o efeito por registro é maior o SDID contra os produtores consolidados indica cerca de {f(SJ['sdid']['SDID vs. soja consolidada']['sdid']['tau'],1)} homicídios por arma de fogo a mais por 100 mil e o Callaway e Sant’Anna escalonado, cerca de {f(CSJ['Escalonado (salto de registros) – controle ainda não tratados']['att'],1)}, o que dá suporte parcial à hipótese de amplificação territorial ligada à expansão do agronegócio.")
L('Delimitação do alcance e limitações: ', 'Quanto às limitações e à validade externa:')
BUL('(i) Medida de tratamento: ', 'o SINARM cobre as armas de posse de civis registradas na Polícia Federal, e não os CACs, cujos registros no SIGMA/Exército não são divulgados por município. O efeito estimado refere-se, portanto, à expansão da posse civil; o canal dos CACs permanece como mecanismo complementar não mensurado.')
BUL('(ii) Tendências pré-tratamento e placebo: ', 'o teste conjunto pré-tratamento do Event Study TWFE e o placebo de trânsito indicam que parte da associação pode refletir choques locais concomitantes; os resultados do estimador de Callaway e Sant’Anna e das especificações com controles de tendência são menos sujeitos a esse viés, mas não o eliminam.')
BUL('(iii) Causalidade reversa: ', 'municípios onde a violência crescia podem ter demandado mais armas. Um instrumento para a demanda local de armas anterior a 2019 (por exemplo, a densidade de clubes de tiro e lojas de armas) seria um avanço.')
BUL('(iv) Mecanismo: ', 'o modelo estima o efeito líquido agregado sobre as taxas municipais, não permitindo distinguir se os homicídios adicionais foram cometidos com armas registradas ou com armas desviadas do mercado legal para o ilícito.')
BUL('(v) Desfecho patrimonial e horizonte: ', 'a hipótese de dissuasão sobre crimes patrimoniais rurais não pôde ser testada, pois não há série municipal pública de roubos e furtos em propriedades rurais; e o horizonte pós-restrição (2023–2024) ainda é curto para avaliar a dissipação do estoque acumulado.')
BUL('(vi) Sensibilidade do SDID: ', 'o SDID confirma o efeito nas comparações entre grupos semelhantes, mas é nulo ou negativo na comparação entre o quartil superior e o inferior de registros; com apenas quatro anos pré-tratamento, os pesos sintéticos têm pouca informação para equilibrar regiões muito diferentes.')
BUL('(vii) Fonte dos dados do SINARM: ', 'os arquivos foram obtidos de cópias públicas no GitHub, validadas contra o FBSP; recomenda-se, na versão final, baixá-los diretamente da Polícia Federal (acesso a partir do Brasil) e reexecutar os scripts.')

# ======================================================================= 9. CONSIDERAÇÕES FINAIS
SEC('9. CONSIDERAÇÕES FINAIS')
T(f"Em resposta à pergunta causal, a flexibilização do acesso a armas de fogo entre 2019 e 2022 causou um aumento moderado dos homicídios por arma de fogo nos municípios brasileiros mais expostos: cada novo registro de arma por mil habitantes elevou a taxa de homicídios por arma de fogo em cerca de {f(b2['coef'],2)} óbitos por 100 mil ao ano, e os municípios que tiveram salto de registros apresentaram, em média, {f(cs_nyt[0],2)} óbitos a mais por 100 mil. O efeito é específico às mortes por arma de fogo, é mais intenso na fronteira da soja – que concentrou a expansão das armas –, mostra-se sensível à escolha do grupo de comparação no SDID e não apresentou reversão até 2024, apesar da restrição imposta pelo Decreto nº 11.615/2023.")
T('Como implicação para a gestão pública, os resultados indicam que a expansão da posse civil de armas tem custo em vidas mensurável e persistente, mesmo depois da reversão normativa, porque o estoque acumulado permanece em circulação. Recomenda-se manter regras rigorosas de concessão de posse e porte, aprimorar a rastreabilidade das armas já registradas (integração SINARM–SIGMA, cuja gestão passou à Polícia Federal em 2023) e publicar os registros de CACs por município, permitindo avaliações mais completas. Em Mato Grosso e na Amazônia Legal, onde a expansão das armas foi mais intensa, o monitoramento territorial com dados abertos – como o painel construído neste trabalho – pode orientar o policiamento e a fiscalização de armas de forma focalizada.')

# ======================================================================= REFERÊNCIAS
SEC('REFERÊNCIAS')
refs = [
 'ANGRIST, J. D.; PISCHKE, J.-S. Mostly harmless econometrics: an empiricist’s companion. Princeton: Princeton University Press, 2009.',
 'ARKHANGELSKY, D.; ATHEY, S.; HIRSHBERG, D. A.; IMBENS, G. W.; WAGER, S. Synthetic difference-in-differences. American Economic Review, v. 111, n. 12, p. 4088–4118, 2021.',
 'BACULI, A. L.; RIBEIRO, M. R.; LEOCÁDIO, A. L. M.; FERREIRA, C. R. Uma nota sobre homicídios e a entrada de armas legais nas regiões brasileiras. Revista Brasileira de Economia, v. 75, n. 1, 2021. Disponível em: https://periodicos.fgv.br/rbe/article/view/80108. Acesso em: 26 nov. 2026.',
 'BECKER, G. S. Crime and punishment: an economic approach. Journal of Political Economy, v. 76, n. 2, p. 169–217, 1968.',
 'BEN-MICHAEL, E.; DOUCETTE, M. L.; FELLER, A.; McCOURT, A. D.; STUART, E. A. Statistical methods to estimate the impact of gun policy on gun violence. arXiv, 2404.11506, 2024. Disponível em: https://arxiv.org/abs/2404.11506. Acesso em: 26 nov. 2026.',
 'BRASIL. Decreto nº 9.685, de 15 de janeiro de 2019. Altera o Decreto nº 5.123, de 1º de julho de 2004. Brasília, DF: Presidência da República, 2019.',
 'BRASIL. Decreto nº 11.615, de 21 de julho de 2023. Regulamenta a Lei nº 10.826, de 22 de dezembro de 2003. Brasília, DF: Presidência da República, 2023.',
 'BRASIL. Ministério da Saúde. Sistema de Informações sobre Mortalidade (SIM): microdados Mortalidade Geral 2015–2024. Brasília: OpenDataSUS, 2026. Disponível em: https://dadosabertos.saude.gov.br/dataset/sim. Acesso em: 26 nov. 2026.',
 'BRASIL. Polícia Federal. Sistema Nacional de Armas (SINARM): dados abertos – registros de armas de fogo com categoria. Brasília: PF, 2026. Disponível em: https://servicos.dpf.gov.br/dadosabertos/SINARM_CSV/. Acesso em: 26 nov. 2026.',
 'CALLAWAY, B.; SANT’ANNA, P. H. C. Difference-in-differences with multiple time periods. Journal of Econometrics, v. 225, n. 2, p. 200–230, 2021.',
 'CERQUEIRA, D.; MELLO, J. M. P. Menos armas, menos crimes. Brasília: IPEA, 2012. (Texto para Discussão, n. 1721).',
 'COOK, P. J.; LUDWIG, J. The social costs of gun ownership. Journal of Public Economics, v. 90, n. 1–2, p. 379–391, 2006.',
 'DE CHAISEMARTIN, C.; D’HAULTFŒUILLE, X. Two-way fixed effects estimators with heterogeneous treatment effects. American Economic Review, v. 110, n. 9, p. 2964–2996, 2020.',
 'DUGGAN, M. More guns, more crime. Journal of Political Economy, v. 109, n. 5, p. 1086–1114, 2001.',
 'FÓRUM BRASILEIRO DE SEGURANÇA PÚBLICA. Anuário Brasileiro de Segurança Pública 2022. São Paulo: FBSP, 2022.',
 'FÓRUM BRASILEIRO DE SEGURANÇA PÚBLICA. Anuário Brasileiro de Segurança Pública 2023. São Paulo: FBSP, 2023.',
 'GOODMAN-BACON, A. Difference-in-differences with variation in treatment timing. Journal of Econometrics, v. 225, n. 2, p. 254–277, 2021.',
 'IBGE. Sistema IBGE de Recuperação Automática (SIDRA): tabelas 1737, 4714, 5457, 5938 e 6579. Rio de Janeiro: IBGE, 2026. Disponível em: https://sidra.ibge.gov.br. Acesso em: 26 nov. 2026.',
 'LOTT, J. R.; MUSTARD, D. B. Crime, deterrence, and right-to-carry concealed handguns. Journal of Legal Studies, v. 26, n. 1, p. 1–68, 1997.',
 'MORENO-LOUZADA, L.; MENEZES-FILHO, N. Technical change in agriculture and homicides: the case of genetically-modified soy seeds in Brazil. Economics Letters, v. 234, 111502, 2024. DOI: 10.1016/j.econlet.2023.111502.',
 'PROJETO MAPBIOMAS. Coleção 11 da série anual de mapas de cobertura e uso da terra do Brasil: desmatamento por município. 2026. Disponível em: https://brasil.mapbiomas.org/estatisticas/. Acesso em: 26 nov. 2026.',
 'SOUZA, M. F. M. et al. Reductions in firearm-related mortality and hospitalizations in Brazil after gun control. Health Affairs, v. 26, n. 2, p. 575–584, 2007.',
 'SUN, L.; ABRAHAM, S. Estimating dynamic treatment effects in event studies with heterogeneous treatment effects. Journal of Econometrics, v. 225, n. 2, p. 175–199, 2021.',
 'WAKIM, V. R. Firearms policy and regional structures: how Brazil responds in divergent ways. Crime, Law and Social Change, v. 83, n. 1, art. 58, 2025. DOI: 10.1007/s10611-025-10247-0.']
for x in refs: para(x, size=11, align=WD_ALIGN_PARAGRAPH.LEFT, after=4)

# ======================================================================= APÊNDICES
SEC('APÊNDICE A – SCRIPT COMENTADO EM R (AV2_SCRIPT_municipal.R)')
for line in open('AV2_SCRIPT_municipal.R', encoding='utf-8').read().splitlines():
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(0)
    x = p.add_run(line if line else ' '); x.font.name = 'Courier New'; x.font.size = Pt(8)
SEC('APÊNDICE B – ARQUIVOS DE REPLICAÇÃO')
for a, b in [('AV2_painel_municipal_Brasil.csv / .xlsx: ', 'painel 5.570 municípios × 2015–2024 e dicionário de variáveis.'),
             ('01_painel_municipal.py: ', 'montagem do painel a partir das fontes oficiais.'),
             ('02_estima_municipal.py e 03_callaway_santanna.py: ', 'estimações TWFE, Poisson, Event Study, DDD, placebos e Callaway e Sant’Anna (Python).'),
             ('08_sdid.py e 09_fronteira_soja.py: ', 'SDID (Arkhangelsky et al., 2021) e análise com a fronteira da soja como grupo tratado.'),
             ('AV2_SCRIPT_municipal.R: ', 'replicação em R (fixest e did).')]:
    BUL(a, b)
doc.save(OUT); print('ok', OUT)
