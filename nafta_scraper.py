"""
nafta_scraper.py - NAFTABOT
Descarga el CSV oficial de precios en surtidor del gobierno argentino,
consolida el historico diario y genera los JSONs para el dashboard.
"""
import pandas as pd, requests, io, os, json
from datetime import datetime
from pathlib import Path

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
    r = requests.get(URL_CSV, timeout=60)
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
    # solo columnas que necesitamos
    cols = [c for c in COLS_KEEP if c in df.columns]
    return df[cols].copy()

def consolidar(df_nuevo, hoy, dolar):
    df_nuevo["fecha_descarga"] = hoy
    df_nuevo["precio_usd"] = (df_nuevo["precio"] / dolar).round(4)
    df_nuevo["dolar_bn"] = dolar

    if HISTORICO.exists():
        dh = pd.read_csv(HISTORICO, low_memory=False)
        dh["fecha_descarga"] = pd.to_datetime(dh["fecha_descarga"]).dt.strftime("%Y-%m-%d")
        # no duplicar el dia de hoy
        dh = dh[dh["fecha_descarga"] != hoy]
        df_final = pd.concat([dh, df_nuevo], ignore_index=True)
    else:
        df_final = df_nuevo

    df_final.to_csv(HISTORICO, index=False)
    print("Historico: " + str(len(df_final)) + " registros totales")
    return df_final

def generar_filtros(df_vigentes):
    filtros = {
        "provincias":  sorted(df_vigentes["provincia"].dropna().unique().tolist()),
        "localidades": sorted(df_vigentes["localidad"].dropna().unique().tolist()),
        "empresas":    sorted(df_vigentes["empresabandera"].dropna().unique().tolist()),
        "productos":   sorted(df_vigentes["producto"].dropna().unique().tolist()),
    }
    (DIR_DATA / "filtros.json").write_text(
        json.dumps(filtros, ensure_ascii=False, indent=2), encoding="utf-8")
    print("filtros.json ok - " + str(len(filtros["provincias"])) + " provincias")

def generar_vigentes(df_vigentes, df_hist, dolar):
    """JSON liviano con los precios vigentes de hoy + variacion respecto al dia anterior."""
    df2 = df_hist.copy()
    df2["fecha_descarga"] = pd.to_datetime(df2["fecha_descarga"]).dt.strftime("%Y-%m-%d")
    fechas = sorted(df2["fecha_descarga"].unique())

    # Precios del dia anterior por clave
    precios_ant = {}
    if len(fechas) >= 2:
        fecha_ant = fechas[-2]
        df_ant = df2[df2["fecha_descarga"] == fecha_ant]
        for _, row in df_ant.iterrows():
            key = str(row["provincia"]) + "|" + str(row["localidad"]) + "|" + str(row.get("empresabandera","")) + "|" + str(row["producto"])
            precios_ant[key] = float(row["precio"])

    rows = []
    for _, row in df_vigentes.iterrows():
        key = str(row["provincia"]) + "|" + str(row["localidad"]) + "|" + str(row.get("empresabandera","")) + "|" + str(row["producto"])
        precio = float(row["precio"])
        ant = precios_ant.get(key)
        var_dia = round((precio - ant) / ant * 100, 2) if ant and ant > 0 else None
        rows.append({
            "provincia":     row["provincia"],
            "localidad":     row["localidad"],
            "empresa":       row.get("empresa",""),
            "empresabandera":row.get("empresabandera",""),
            "producto":      row["producto"],
            "precio":        precio,
            "precio_usd":    round(precio / dolar, 2),
            "var_dia":       var_dia,
        })

    (DIR_DATA / "vigentes.json").write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    print("vigentes.json ok - " + str(len(rows)) + " registros")

def generar_stats(df_hist):
    df2 = df_hist.copy()
    df2["fecha_descarga"] = pd.to_datetime(df2["fecha_descarga"]).dt.strftime("%Y-%m-%d")
    grp = df2.groupby(["fecha_descarga","provincia","localidad","empresabandera","producto"])["precio"].mean().reset_index()
    grp["precio"] = grp["precio"].round(2)
    stats = {}
    for _, row in grp.iterrows():
        prov=row["provincia"]; prod=row["producto"]; emp=row["empresabandera"]; loc=row["localidad"]
        if prov not in stats: stats[prov]={}
        if prod not in stats[prov]: stats[prov][prod]={}
        if emp not in stats[prov][prod]: stats[prov][prod][emp]=[]
        stats[prov][prod][emp].append({"fecha":row["fecha_descarga"],"precio":row["precio"],"localidad":loc})
    (DIR_DATA/"stats.json").write_text(json.dumps(stats,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("stats.json ok - " + str(len(stats)) + " provincias")

def generar_resumen(df_vigentes, df_hist, dolar, hoy):
    por_producto = df_vigentes.groupby("producto")["precio"].mean().round(2).to_dict()
    variaciones = {}
    df2 = df_hist.copy()
    df2["fecha_descarga"] = pd.to_datetime(df2["fecha_descarga"]).dt.strftime("%Y-%m-%d")
    fechas = sorted(df2["fecha_descarga"].unique())
    if len(fechas) >= 2:
        df_ant = df2[df2["fecha_descarga"] == fechas[-2]]
        for prod, p_hoy in por_producto.items():
            ant = df_ant[df_ant["producto"] == prod]["precio"].mean()
            if pd.notna(ant) and ant > 0:
                variaciones[prod] = round((p_hoy - ant) / ant * 100, 2)
    resumen = {
        "fecha_actualizacion": hoy, "dolar_bn": dolar,
        "total_registros":  len(df_vigentes),
        "total_estaciones": df_vigentes.groupby(["empresa","localidad"]).ngroups,
        "precios_promedio": por_producto, "variaciones_dia": variaciones,
        "provincias_count": df_vigentes["provincia"].nunique(),
        "empresas_count":   df_vigentes["empresabandera"].nunique(),
    }
    (DIR_DATA/"resumen.json").write_text(json.dumps(resumen,ensure_ascii=False,indent=2),encoding="utf-8")
    print("resumen.json ok")
    for prod, precio in por_producto.items():
        v = variaciones.get(prod)
        vstr = (" (+" if v and v>0 else " (") + str(v) + "%)" if v is not None else ""
        print("  " + prod[:40] + ": $" + str(precio) + vstr)

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
    df_vigentes = get_vigentes(df)
    df_hist = consolidar(df_vigentes, hoy, dolar)
    df_hist["fecha_descarga"] = pd.to_datetime(df_hist["fecha_descarga"]).dt.strftime("%Y-%m-%d")
    generar_filtros(df_vigentes)
    generar_vigentes(df_vigentes, df_hist, dolar)
    generar_stats(df_hist)
    generar_resumen(df_vigentes, df_hist, dolar, hoy)
    print("NAFTABOT ok - " + str(datetime.now()))

if __name__ == "__main__":
    main()
