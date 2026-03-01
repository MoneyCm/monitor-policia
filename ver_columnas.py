import pandas as pd
files = ["HOMICIDIO INTENCIONAL.xlsx", "SECUESTRO.xlsx"]
for f in files:
    print(f"\n{'='*50}\n{f}\n{'='*50}")
    df = pd.read_excel(f)
    print("📋 Columnas:", list(df.columns))
    print(f"📈 Total filas: {len(df)}")
