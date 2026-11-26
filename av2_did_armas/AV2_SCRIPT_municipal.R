# ==============================================================================
# PROFNIT/UNEMAT - AV2: DiD MUNICIPAL com dados reais (Brasil, 5.570 municípios, 2015-2024)
# Tratamento: novos registros de armas por civis (SINARM/PF) 2019-22 por mil hab.
# ==============================================================================
library(readr); library(dplyr); library(tidyr); library(fixest); library(did)
df <- read_csv("AV2_painel_municipal_Brasil.csv", show_col_types = FALSE) %>%
  mutate(did = delta_reg_pc * pos_2019, did_23 = delta_reg_pc * pos_2023,
         did_front = did * fronteira_ativa, did_int = intens_reg * pos_2019,
         did_bin = tratamento_quartil_sup * pos_2019)
ctrl <- "log_vab_agro_pc + log_densidade_pop + taxa_mortalidade_covid"
f <- function(y, x) as.formula(paste(y, "~", x, "+", ctrl, "| cod_ibge + ano"))

# Tabela 3
m1 <- feols(taxa_homic_af ~ did | cod_ibge + ano, df, weights = ~pop, cluster = ~cod_ibge)
m2 <- feols(f("taxa_homic_af", "did"), df, weights = ~pop, cluster = ~cod_ibge)
m3 <- feols(f("taxa_homic_af", "did + did_front"), df, weights = ~pop, cluster = ~cod_ibge)
m4 <- feols(f("taxa_homic_af", "did + did_23"), df, weights = ~pop, cluster = ~cod_ibge)
m5 <- fepois(af ~ did + log_vab_agro_pc + log_densidade_pop + taxa_mortalidade_covid | cod_ibge + ano,
             df, offset = ~log(pop), cluster = ~cod_ibge)
m6 <- feols(f("taxa_homic_af", "did_int"), df, weights = ~pop, cluster = ~cod_ibge)
etable(m1, m2, m3, m4, m5, m6)

# Callaway & Sant'Anna (2021): coortes 2019/2020/2021 (0 = nunca tratado)
cs <- att_gt(yname = "taxa_homic_af", tname = "ano", idname = "cod_ibge", gname = "ano_primeiro_salto",
             data = df, control_group = "notyettreated", weightsname = "pop")
aggte(cs, type = "simple"); ggdid(aggte(cs, type = "dynamic"))

# Event study (ref. 2018) e teste pré
es <- feols(as.formula(paste("taxa_homic_af ~ i(ano, delta_reg_pc, ref = 2018) +", ctrl, "| cod_ibge + ano")),
            df, weights = ~pop, cluster = ~cod_ibge)
wald(es, keep = "ano::201[5-7]"); iplot(es)

# Robustez: DDD, placebos, binário
ddd <- df %>% pivot_longer(c(taxa_homic_af, taxa_homic_ab), names_to = "meio", values_to = "y") %>%
  mutate(af = as.integer(meio == "taxa_homic_af"), ddd = delta_reg_pc * af * pos_2019)
r1 <- feols(y ~ ddd | cod_ibge^af + ano^af + cod_ibge^ano, ddd, weights = ~pop, cluster = ~cod_ibge)
r2 <- feols(f("taxa_obitos_transito", "did"), df, weights = ~pop, cluster = ~cod_ibge)
r3 <- feols(taxa_homic_af ~ I(delta_reg_pc * (ano >= 2017)) + log_vab_agro_pc + log_densidade_pop | cod_ibge + ano,
            filter(df, ano <= 2018), weights = ~pop, cluster = ~cod_ibge)
r4 <- feols(f("taxa_homic_af", "did_bin"), df, weights = ~pop, cluster = ~cod_ibge)
etable(r1, r2, r3, r4)
