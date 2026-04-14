#!/usr/bin/env python3
# Recorre data/metadata/*.json y arma un CSV único con métricas de cada captura.

import os, json, csv, glob
from datetime import datetime

BASE = os.path.dirname(__file__)
META_DIR = os.path.join(BASE, "..", "data", "metadata")
RAW_DIR  = os.path.join(BASE, "..", "data", "raw")
OUT_DIR  = os.path.join(BASE, "..", "data", "processed")
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    files = sorted(glob.glob(os.path.join(META_DIR, "*.json")))
    if not files:
        print("No hay JSON en data/metadata/")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = os.path.join(OUT_DIR, f"measurements_{ts}.csv")

    # Campos “comunes” que podrían existir
    fields = [
        "timestamp","image_path","tag","brightness_level",
        "exposure_us","gain","width","height",
        "min","max","mean","std","pct_sat_255","pct_black_0"
    ]

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for jpath in files:
            with open(jpath, "r") as jf:
                j = json.load(jf)

            row = {k: j.get(k) for k in fields}  # top-level directo
            # Algunos scripts guardaron métricas dentro de "metrics"
            if row.get("mean") is None and isinstance(j.get("metrics"), dict):
                for k in ("min","max","mean","std","pct_sat_255","pct_black_0"):
                    row[k] = j["metrics"].get(k)

            # Algunos scripts guardaron parámetros dentro de "camera"
            if row.get("exposure_us") is None and isinstance(j.get("camera"), dict):
                for k in ("exposure_us","gain","width","height"):
                    row[k] = j["camera"].get(k)

            # Imagen asociada si falta
            if not row.get("image_path"):
                # inferir a partir del nombre base
                base = os.path.splitext(os.path.basename(jpath))[0]
                candidates = glob.glob(os.path.join(RAW_DIR, base + ".*"))
                row["image_path"] = candidates[0] if candidates else None

            w.writerow(row)

    print("CSV listo:", out_csv)

if __name__ == "__main__":
    main()
