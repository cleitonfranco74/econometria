import sys, zipfile, io, pandas as pd, os, subprocess
import sys; D=sys.argv[1]
out=[]
for y in range(2015,2025):
    f=f'{D}/{y}.zip'
    if not os.path.exists(f):
        subprocess.run(['curl','-s','-m','900','--retry','3','-o',f,f'https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM/csv/Mortalidade_Geral_{y}_csv.zip'],check=True)
    z=zipfile.ZipFile(f); n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
    head=z.open(n).readline().decode('latin1')
    sep=';' if head.count(';')>head.count(',') else ','
    df=pd.read_csv(z.open(n),sep=sep,usecols=lambda c:c.strip('"').upper() in ('CODMUNRES','CAUSABAS'),dtype=str,encoding='latin1')
    df.columns=[c.upper().strip('"') for c in df.columns]
    c=df.CAUSABAS.str[:3]; c4=df.CAUSABAS.fillna('')
    df['af']=c.isin(['X93','X94','X95'])
    df['ab']=c.eq('X99')
    df['outros']=c.isin([f'X{i}' for i in range(85,93)]+['X96','X97','X98']+[f'Y0{i}' for i in range(10)])
    df['transito']=c4.str[0].eq('V') & (c.str[1:3].astype(str).str.isdigit()) & (pd.to_numeric(c.str[1:3],errors='coerce')<=89)
    df['covid']=c4.str.startswith('B342')
    df['mun6']=df.CODMUNRES.str[:6]
    g=df.groupby('mun6')[['af','ab','outros','transito','covid']].sum().reset_index(); g['ano']=y
    out.append(g); print(y,n,len(df),g[['af','ab','transito']].sum().to_dict(),flush=True)
    os.remove(f)
pd.concat(out).to_csv(f'{D}/sim_mun.csv',index=False)
