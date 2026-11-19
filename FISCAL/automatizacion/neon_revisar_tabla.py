"""Solo lectura: cuánto pesa una tabla de Neon por columna, y cómo se reparten sus filas (por departamento, año y,
si existe, por la columna ESTADO). Lo corre el flujo «Neon · revisar una tabla».

    DATABASE_URL=postgresql://…  python neon_revisar_tabla.py base_expo_sunat
"""
import os
import re
import sys

from sqlalchemy import create_engine, inspect, text


def main():
    tabla = sys.argv[1]
    if not re.fullmatch(r"[a-z0-9_]+", tabla):
        sys.exit("Nombre de tabla no válido")
    u = os.environ["DATABASE_URL"]
    u = "postgresql+psycopg://" + u.split("://", 1)[1] if u.startswith(("postgres://", "postgresql://")) else u
    m = create_engine(u)
    cols = [c["name"] for c in inspect(m).get_columns(tabla)]
    out = []
    with m.connect() as cx:
        tot = cx.execute(text(f"SELECT pg_total_relation_size('\"{tabla}\"'), pg_relation_size('\"{tabla}\"'), COUNT(*) FROM \"{tabla}\"")).first()
        out += [f"## {tabla}", "", f"Total: {tot[0] / 1e6:.1f} MB · solo filas: {tot[1] / 1e6:.1f} MB · {tot[2]:,} filas", ""]
        vivo = cx.execute(text(f'SELECT SUM(pg_column_size(t.*))::bigint FROM "{tabla}" t')).scalar() or 0
        st = cx.execute(text("SELECT n_live_tup, n_dead_tup, last_vacuum, last_autovacuum, n_tup_del, n_tup_ins "
                             "FROM pg_stat_user_tables WHERE relname = :t"), {"t": tabla}).first()
        out += [f"Lo que ocupan las filas vivas: {vivo / 1e6:.1f} MB · espacio sin usar (filas borradas o huecos): "
                f"{max(tot[1] - vivo, 0) / 1e6:.1f} MB", "",
                f"Filas muertas sin limpiar: {st[1]:,} · insertadas: {st[5]:,} · borradas: {st[4]:,} · último VACUUM: {st[2] or '-'} "
                f"· último autovacuum: {st[3] or '-'}", ""]
        partes = ", ".join(f'SUM(pg_column_size("{c}"))::bigint AS "{c}"' for c in cols)
        tam = cx.execute(text(f'SELECT {partes} FROM "{tabla}"')).first()
        suma = sum(x or 0 for x in tam) or 1
        out += ["| Columna | MB | % | valores distintos |", "|---|---|---|---|"]
        for c, x in sorted(zip(cols, tam), key=lambda t: -(t[1] or 0)):
            d = cx.execute(text(f'SELECT COUNT(DISTINCT "{c}") FROM "{tabla}"')).scalar()
            out.append(f"| {c} | {(x or 0) / 1e6:.2f} | {100 * (x or 0) / suma:.1f} | {d:,} |")
        for grupo in [g for g in (["_depto", "_anio"], ["ESTADO"], ["_archivo"], ["_depto", "_anio", "_mes"]) if all(x in cols for x in g)]:
            cg = ", ".join(f'"{g}"' for g in grupo)
            filas = cx.execute(text(f'SELECT {cg}, COUNT(*) FROM "{tabla}" GROUP BY {cg} ORDER BY {cg}')).all()
            out += ["", f"### Filas por {' / '.join(grupo)}", "", "| " + " | ".join(grupo) + " | filas |", "|" + "---|" * (len(grupo) + 1)]
            out += ["| " + " | ".join(str(v) for v in f[:-1]) + f" | {f[-1]:,} |" for f in filas[:400]]
    texto = "\n".join(out)
    print(texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8").write(texto + "\n")


if __name__ == "__main__":
    main()
