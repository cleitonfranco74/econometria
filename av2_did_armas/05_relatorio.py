import json
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
R = json.load(open('resultados_municipal.json')); CS = json.load(open('cs_resultados.json')); r = R['res']; I = R['info']
doc = Document(); doc.styles['Normal'].font.name = 'Times New Roman'; doc.styles['Normal'].font.size = Pt(11)
def H(t, l=1): doc.add_heading(t, level=l)
def P(t, it=False):
    p = doc.add_paragraph(); x = p.add_run(t); x.italic = it; p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
def B(t): doc.add_paragraph(t, style='List Bullet')
def f(x, d=3): return f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
def st(p): return '***' if p < .01 else '**' if p < .05 else '*' if p < .10 else ''
def table(rows, header, w0=6.0):
    t = doc.add_table(rows=1, cols=len(header)); t.style = 'Light Grid Accent 1'; t.autofit = False
    for i, h in enumerate(header): t.rows[0].cells[i].text = h
    for row in rows:
        c = t.add_row().cells
        for i, v in enumerate(row): c[i].text = str(v)
    wr = (16.5 - w0) / (len(header) - 1)
    for j, col in enumerate(t.columns): col.width = Cm(w0 if j == 0 else wr)
    for row in t.rows:
        for j, c in enumerate(row.cells):
            c.width = Cm(w0 if j == 0 else wr)
            for pp in c.paragraphs:
                for rr in pp.runs: rr.font.size = Pt(8.5)
def line(k, lab=None): x = r[k]; return [lab or k, f(x['coef']) + st(x['p']), f(x['se']), f(x['p'], 4), f"[{f(x['lo'],2)}; {f(x['hi'],2)}]", f"{x['n']:,}".replace(',', '.')]
doc.add_heading('AV2 – DiD com dados MUNICIPAIS reais: armas legais (SINARM/PF) e homicídios, 2015–2024', 0)
P('Versão municipal do projeto. Substitui as Seções 4 (Dados), 6 (Resultados) e 7 (Robustez). Gerado em 26/11/2026.', it=True)
H('1. Fonte municipal do tratamento (encontrada no GitHub)')
P('Os registros de CACs do Exército (SIGMA) continuam sem recorte municipal público. A fonte municipal que existe é o SINARM, da Polícia Federal: os dados abertos “REGISTROS_com_categoria” trazem cada registro de arma de fogo por ano e mês de emissão, UF, município, categoria do proprietário (Cidadão, Servidor Público, Caçador de Subsistência), espécie e calibre. Os arquivos oficiais ficam em servicos.dpf.gov.br/dadosabertos/SINARM_CSV/REGISTROS/, servidor que recusa conexões de fora do Brasil; por isso usamos a cópia pública integral desses CSVs no GitHub (repositório yurilq/IBMEC_DESENVOLVIMENTO_AGENTE_2026, pasta DADOS_SINARM/REGISTROS), com o mesmo cabeçalho do arquivo oficial.')
P('Validação: (i) 99,99% dos 979.601 registros de 2015–2025 foram associados a um código IBGE (5.560 municípios); (ii) por UF, a soma dos novos registros 2018–2022 tem correlação de 0,89 com o aumento do estoque de registros ativos do SINARM publicado pelo FBSP (Anuário 2023, Tab. 47); (iii) a série nacional reproduz o choque regulatório: ~63–75 mil novos registros de civis por ano em 2015–2019, 131 mil (2020), 165 mil (2021), 114 mil (2022) e ~21 mil/ano após o Decreto 11.615/2023 (Figura 1). Recomenda-se, na versão final, baixar os arquivos diretamente do servidor da PF (acessível no Brasil) e rodar 01_painel_municipal.py para confirmar.')
P('Atenção conceitual: o SINARM mede armas registradas por civis para defesa pessoal (posse), não CACs. Os decretos de 2019 (Dec. 9.685/2019 em diante) flexibilizaram exatamente a posse, de modo que a variável é uma medida direta do choque — mas o texto do projeto deve trocar “CACs” por “registros de armas por civis (SINARM)” ou tratar CACs como mecanismo complementar.')
H('2. Painel e variáveis')
P(f"Painel balanceado com todos os {I['n_mun']:,} municípios brasileiros × 10 anos (2015–2024) = 55.700 observações. Arquivo: AV2_painel_municipal_Brasil.csv (dicionário no .xlsx).".replace(',', '.'))
table([
 ['delta_reg_pc (tratamento principal)', 'Novos registros de armas por civis 2019–2022 por mil habitantes (pop. 2018)', 'SINARM/PF; IBGE'],
 ['intens_reg', 'delta_reg_pc winsorizado (p1–p99) e normalizado Min-Max [0,1], como no projeto', 'Elaboração própria'],
 ['ano_primeiro_salto (coorte C&S)', '1º ano de 2019–2021 em que a taxa anual de registros ≥ 2× a média 2015–18 (≥ 3 registros); 0 = nunca', 'SINARM/PF'],
 ['fronteira_ativa', 'Desmatamento 2015–2018 (% da área) acima da mediana nacional', 'MapBiomas Col. 11'],
 ['taxa_homic_af / ab / outros; transito; covid', 'Óbitos por 100 mil (X93–X95; X99; X85–X92,X96–X98,Y00–Y09; V01–V89; B34.2), residência', 'SIM/DATASUS'],
 ['Controles', 'log VAB agro per capita real (IPCA 2022), log densidade, mortalidade COVID-19', 'IBGE/SIDRA'],
], ['Variável', 'Definição', 'Fonte'], w0=4.5)
doc.add_picture('fig1_registros_sinarm.png', width=Cm(15.5))
P('Figura 1 – Novos registros de armas por civis por mil habitantes (SINARM/PF). Fonte: PF; IBGE.', it=True)
H('3. Resultados')
H('Tabela 3 – TWFE contínuo: Y = homicídios por arma de fogo / 100 mil', 2)
keys = ['(1) TWFE s/ controles, ponderado pop', '(2) TWFE c/ controles, ponderado pop', '(3) Fronteira: ΔREG×Pós', '(3) Fronteira: ΔREG×Pós×Fronteira',
        '(4) Reversão: ΔREG×Pós2019', '(4) Reversão: ΔREG×Pós2023', '(5) Poisson (contagem, offset pop)', '(6) Intensidade Min-Max [0,1]', '(7) Sem ponderação',
        '(8) Tendência por linha de base (pre_reg×ano)', '(9) EF UF×ano', '(10) Excesso sobre 2015-18', '(11) Só os 50 municípios do projeto', '(12) Municípios ≥ 20 mil hab.']
table([line(k) for k in keys], ['Especificação', 'β', 'EP', 'p', 'IC 95%', 'N'])
P('Nota: EF de município e ano (em (9), município e UF×ano); EP agrupados por município; (1)–(6), (8)–(10) ponderados pela população. β = efeito de +1 novo registro por mil hab. em 2019–22 (exceto (6): de 0 a 1 na escala Min-Max; (5): semi-elasticidade de Poisson). * p<0,10; ** p<0,05; *** p<0,01.', it=True)
b = r['(2) TWFE c/ controles, ponderado pop']; ef = b['coef'] * (I['p75'] - I['p25'])
P(f"Interpretação (coluna 2): β = {f(b['coef'])} (EP {f(b['se'])}; p = {f(b['p'],3)}). Cada novo registro de arma por mil habitantes em 2019–2022 está associado a +{f(b['coef'],2)} homicídios por arma de fogo por 100 mil hab./ano após 2019. Passar do 1º para o 3º quartil de exposição ({f(I['p25'],2)} → {f(I['p75'],2)} registros/mil) implica +{f(ef,2)} óbitos/100 mil, cerca de {f(100*ef/I['mean_af'],1)}% da taxa média ponderada ({f(I['mean_af'],2)}). Na escala Min-Max do projeto (col. 6), ir de 0 a 1 equivale a +{f(r['(6) Intensidade Min-Max [0,1]']['coef'],2)} óbitos/100 mil. O Poisson (col. 5) indica +{f(100*r['(5) Poisson (contagem, offset pop)']['coef'],1)}% nos homicídios por arma de fogo por registro/mil. A interação com fronteira agrícola é nula (o efeito não é maior na fronteira) e o termo pós-2023 não indica reversão até 2024. Na amostra original de 50 municípios o efeito não é detectável (col. 11) — o tamanho amostral era insuficiente.")
H('Tabela 4 – Callaway & Sant’Anna (2021): adoção escalonada', 2)
rows = []
for k, lab in [('taxa_homic_af|not_yet_treated', 'Homic. AF – controle: ainda não tratados'), ('taxa_homic_af|never_treated', 'Homic. AF – controle: nunca tratados'),
               ('taxa_obitos_transito|not_yet_treated', 'Placebo trânsito – ainda não tratados'), ('taxa_obitos_transito|never_treated', 'Placebo trânsito – nunca tratados')]:
    s = CS[k]['simple'][0]; rows.append([lab, f(float(s[1])), f(float(s[2])), f"[{f(float(s[3]),2)}; {f(float(s[4]),2)}]"])
table(rows, ['Estimação', 'ATT agregado', 'EP', 'IC 95%'])
c = I['coortes']
P(f"Nota: coortes 2019 ({c.get('2019')} mun.), 2020 ({c.get('2020')}), 2021 ({c.get('2021')}); nunca tratados: {c.get('0')}. Ponderado pela população; período-base variável.", it=True)
doc.add_picture('fig3_callaway_santanna.png', width=Cm(15.5))
P('Figura 3 – ATT por tempo relativo ao 1º salto de registros (C&S, controle “ainda não tratados”).', it=True)
H('Tabela 5 – Event study TWFE (base 2018)', 2)
es = R['es']; rows = []
for y in range(2015, 2025):
    if y == 2018: rows.append(['2018 (ref.)', '0', '—', '0', '—']); continue
    a = es['taxa_homic_af']['coefs'][str(y)]; t = es['taxa_obitos_transito']['coefs'][str(y)]
    rows.append([str(y), f(a[0]) + st(a[4]), f(a[1]), f(t[0]) + st(t[4]), f(t[1])])
rows.append(['Wald pré 2015–17', f"F={f(es['taxa_homic_af']['F'],2)}", f"p={f(es['taxa_homic_af']['p'],3)}", f"F={f(es['taxa_obitos_transito']['F'],2)}", f"p={f(es['taxa_obitos_transito']['p'],3)}"])
table(rows, ['Ano', 'Homic. AF δ_t', 'EP', 'Trânsito δ_t', 'EP'], w0=4)
doc.add_picture('fig2_event_study_twfe.png', width=Cm(16))
H('4. Robustez')
table([line(k) for k in ['R1 DDD: AF vs arma branca', 'R2 Placebo: óbitos no trânsito', 'R3 Placebo temporal (2017)', 'R4 Tratamento binário (Q4)',
                          'R5 Homicídios arma branca', 'R6 Homicídios outros meios', 'R7 Subamostra fronteira', 'R8 Subamostra consolidados']],
      ['Teste', 'Coef.', 'EP', 'p', 'IC 95%', 'N'])
P(f"A tripla diferença (AF vs. arma branca no mesmo município-ano) é positiva e significativa (β = {f(r['R1 DDD: AF vs arma branca']['coef'])}; p = {f(r['R1 DDD: AF vs arma branca']['p'],3)}) e homicídios por arma branca não respondem (R5) — o aumento é específico do meio arma de fogo, coerente com o canal de disponibilidade. O tratamento binário (quartil superior × Pós) dá +{f(r['R4 Tratamento binário (Q4)']['coef'],2)} óbitos/100 mil.")
H('5. Ameaças à identificação (devem constar no texto)')
B(f"Tendências pré-tratamento: no event study TWFE os coeficientes de 2015–2017 são positivos e o teste conjunto rejeita a nulidade (p = {f(es['taxa_homic_af']['p'],3)}); 2018 foi um ano de queda generalizada de homicídios. No C&S, os períodos −4 a −1 não são significativos (só o −5, estimado apenas para a coorte 2021). Especificações que controlam tendências por linha de base de registros (col. 8) ou por UF×ano (col. 9) aumentam o efeito, o que reduz a preocupação de que ele seja só tendência prévia.")
B(f"Placebo de trânsito: o TWFE contínuo é positivo (β = {f(r['R2 Placebo: óbitos no trânsito']['coef'])}; p = {f(r['R2 Placebo: óbitos no trânsito']['p'],3)}), concentrado em 2021–2024, sugerindo algum fator comum (p.ex., crescimento econômico/rodoviário em municípios do agro que também compraram mais armas). No C&S o placebo não é significativo. Deve ser reportado como limitação.")
B('Causalidade reversa: municípios em que a violência aumentava podem ter demandado mais armas. O desenho usa a variação de oferta legal induzida pelos decretos, EF de município e a DDD, mas não a elimina; um instrumento (p.ex., densidade de clubes de tiro/lojas antes de 2019) seria um avanço.')
B('Fronteira agrícola: o choque de registros foi maior na fronteira (Figura 1), mas o efeito marginal por registro não difere entre fronteira e consolidados.')
B('Denominador: 2022 usa o Censo (menor que as estimativas anteriores) e 2023 é interpolado; os EF de ano absorvem a quebra média.')
B('Desfecho de crimes patrimoniais rurais: sem série municipal pública; retirado.')
H('Arquivos', 2)
for t in ['AV2_painel_municipal_Brasil.csv / .xlsx – painel 5.570 × 10 e dicionário', '01_painel_municipal.py – montagem', '02_estima_municipal.py – TWFE, event study, DDD, placebos (pyfixest)',
          '03_callaway_santanna.py – C&S (pacote differences)', 'AV2_SCRIPT_municipal.R – replicação em R (fixest + did)', 'resultados_municipal.json, cs_resultados.json – todos os números']: B(t)
doc.save('AV2_PROFNIT_Resultados_Municipais.docx')
