import pandas as pd, requests, io, os, json
import urllib3
from datetime import datetime
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL_CSV = "https://datos.energia.gob.ar/dataset/1c181390-5045-475e-94dc-410429be4b17/resource/80ac25de-a44a-4445-9215-090cf55cfda5/download/precios-en-surtidor-resolucin-3142016.csv"
DOLAR_URL = "https://api.comparadolar.ar/usd"
HISTORICO = Path("data/historico.csv")
DIR_DATA  = Path("data")
DIR_DATA.mkdir(exist_ok=True)

COLS_KEEP = ["fecha_vigencia","provincia","localidad","empresa","empresabandera","producto","precio"]

def obtener_dolar():
    try:
        bn = next((x for x in requests.get(DOLAR_URL, timeout=10).json()
                   if x.get("slug") == "banco-nacion"), None)
        return float(bn["ask"]) if bn else 1.0
    except Exception:
        return 1.0

def descargar_csv():
    print("Descargando CSV oficial...")
    r = requests.get(URL_CSV, timeout=60, verify=False)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content), decimal=",", encoding="utf-8", low_memory=False)
    print("  Columnas: " + str(list(df.columns)))
    print("  Filas: " + str(len(df)))
    return df

def limpiar(df):
    df.columns = [c.strip().lower() for c in df.columns]
    for c in ["provincia","localidad","empresa","empresabandera","producto"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    df["precio"] = pd.to_numeric(df["precio"], errors="coerce")
    df["fecha_vigencia"] = pd.to_datetime(df["fecha_vigencia"], errors="coerce")
    df = df.dropna(subset=["precio","fecha_vigencia"])
    cols = [c for c in COLS_KEEP if c in df.columns]
    return df[cols].copy()

def consolidar(df_nuevo, hoy, dolar):
    df_nuevo["fecha_descarga"] = hoy
    df_nuevo["precio_usd"] = (df_nuevo["precio"] / dolar).round(4)
    df_nuevo["dolar_bn"] = dolar

    if HISTORICO.exists():
        dh = pd.read_csv(HISTORICO, low_memory=False)
        dh["fecha_descarga"] = pd.to_datetime(dh["fecha_descarga"]).dt.strftime("%Y-%m-%d")
        dh = dh[dh["fecha_descarga"] != hoy]
        df_final = pd.concat([dh, df_nuevo], ignore_index=True)
    else:
        df_final = df_nuevo

    df_final.to_csv(HISTORICO, index=False)
    print("Historico: " + str(len(df_final)) + " registros totales")
    return df_final

def generar_filtros(df):
    hoy_df = df[df["fecha_descarga"] == df["fecha_descarga"].max()]
    filtros = {
        "provincias":  sorted(hoy_df["provincia"].dropna().unique().tolist()),
        "localidades": sorted(hoy_df["localidad"].dropna().unique().tolist()),
        "empresas":    sorted(hoy_df["empresabandera"].dropna().unique().tolist()),
        "productos":   sorted(hoy_df["producto"].dropna().unique().tolist()),
    }
    (DIR_DATA / "filtros.json").write_text(
        json.dumps(filtros, ensure_ascii=False, indent=2), encoding="utf-8")
    print("filtros.json ok")

def generar_stats(df):
    df2 = df.copy()
    df2["fecha_descarga"] = pd.to_datetime(df2["fecha_descarga"]).dt.strftime("%Y-%m-%d")

    grp = df2.groupby(["fecha_descarga","provincia","localidad","empresabandera","producto"])["precio"].mean().reset_index()
    grp["precio"] = grp["precio"].round(2)

    stats = {}
    for _, row in grp.iterrows():
        prov = row["provincia"]
        prod = row["producto"]
        emp  = row["empresabandera"]
        loc  = row["localidad"]
        if prov not in stats: stats[prov] = {}
        if prod not in stats[prov]: stats[prov][prod] = {}
        if emp not in stats[prov][prod]: stats[prov][prod][emp] = []
        stats[prov][prod][emp].append({"fecha": row["fecha_descarga"], "precio": row["precio"], "localidad": loc})

    (DIR_DATA / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    print("stats.json ok - " + str(len(stats)) + " provincias")

def generar_resumen(df, dolar):
    df2 = df.copy()
    df2["fecha_descarga"] = pd.to_datetime(df2["fecha_descarga"]).dt.strftime("%Y-%m-%d")
    ultima_fecha = df2["fecha_descarga"].max()
    df_hoy = df2[df2["fecha_descarga"] == ultima_fecha]

    por_producto = df_hoy.groupby("producto")["precio"].mean().round(2).to_dict()

    variaciones = {}
    fechas = sorted(df2["fecha_descarga"].unique())
    if len(fechas) >= 2:
        fecha_ant = fechas[-2]
        df_ant = df2[df2["fecha_descarga"] == fecha_ant]
        for prod, p_hoy in por_producto.items():
            ant = df_ant[df_ant["producto"] == prod]["precio"].mean()
            if pd.notna(ant) and ant > 0:
                variaciones[prod] = round((p_hoy - ant) / ant * 100, 2)

    resumen = {
        "fecha_actualizacion": ultima_fecha,
        "dolar_bn": dolar,
        "total_registros": len(df_hoy),
        "total_estaciones": df_hoy.groupby(["empresa","localidad"]).ngroups,
        "precios_promedio": por_producto,
        "variaciones_dia": variaciones,
        "provincias_count": df_hoy["provincia"].nunique(),
        "empresas_count":   df_hoy["empresabandera"].nunique(),
    }
    (DIR_DATA / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print("resumen.json ok")

def main():
    print("NAFTABOT iniciando - " + str(datetime.now()))
    dolar = obtener_dolar()
    print("Dolar BN: " + str(dolar))
    hoy = datetime.now().strftime("%Y-%m-%d")

    try:
        df_raw = descargar_csv()
    except Exception as e:
        print("Error descarga: " + str(e)); return

    df = limpiar(df_raw)
    print("Registros limpios: " + str(len(df)))

    df_hist = consolidar(df, hoy, dolar)
    df_hist["fecha_descarga"] = pd.to_datetime(df_hist["fecha_descarga"]).dt.strftime("%Y-%m-%d")

    generar_filtros(df_hist)
    generar_stats(df_hist)
    generar_resumen(df_hist, dolar)

    print("NAFTABOT ok - " + str(datetime.now()))

if __name__ == "__main__":
    main()
