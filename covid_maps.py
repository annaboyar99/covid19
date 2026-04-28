"""
Три визуализации по covid.db:
- карта: еженедельный % прирост (country_wise_latest, колонка «1 week % increase»);
- карта: заболеваемость на 100 тыс. («Statistics Country»);
- bar: регионы по смертности, по убыванию («Statistics Region»).
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px

DB_PATH = Path(__file__).with_name("covid.db")
OUT_WEEKLY = Path(__file__).with_name("map_weekly_increase.html")
OUT_MORBIDITY = Path(__file__).with_name("map_morbidity_per_100k.html")
OUT_REGIONS = Path(__file__).with_name("bar_region_mortality.html")

COUNTRY_NAMES_FOR_PLOTLY: dict[str, str] = {
    "us": "United States",
    "taiwan*": "Taiwan",
    "burma": "Myanmar",
    "czechia": "Czech Republic",
    "congo (brazzaville)": "Republic of the Congo",
    "congo (kinshasa)": "Democratic Republic of the Congo",
    "cote d'ivoire": "Ivory Coast",
    "north macedonia": "North Macedonia",
    "holy see": "Vatican",
    "korea, north": "North Korea",
    "korea, south": "South Korea",
}


def plotly_country_name(raw: str) -> str:
    key = raw.strip().lower()
    if key in COUNTRY_NAMES_FOR_PLOTLY:
        return COUNTRY_NAMES_FOR_PLOTLY[key]
    if key.endswith("*"):
        key = key.rstrip("*").strip()
        if key in COUNTRY_NAMES_FOR_PLOTLY:
            return COUNTRY_NAMES_FOR_PLOTLY[key]
    return raw.strip()


def quote_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def geo_layout() -> dict:
    return {
        "geo": dict(
            showland=True,
            showocean=True,
            oceancolor="rgb(230, 245, 255)",
            showlakes=True,
            lakecolor="rgb(230, 245, 255)",
        ),
        "margin": dict(l=0, r=0, t=50, b=0),
    }


def weekly_increase_map(connection: sqlite3.Connection) -> None:
    t = quote_identifier("country_wise_latest")
    country_c = quote_identifier("Country/Region")
    region_c = quote_identifier("WHO Region")
    pct_c = quote_identifier("1 week % increase")
    query = f"""
        SELECT
            {country_c} AS country,
            MAX({region_c}) AS who_region,
            AVG(CAST({pct_c} AS REAL)) AS week_pct_increase
        FROM {t}
        WHERE {country_c} IS NOT NULL
          AND TRIM({country_c}) <> ''
          AND {pct_c} IS NOT NULL
        GROUP BY {country_c}
    """
    df = pd.read_sql_query(query, connection)
    df["location"] = df["country"].map(plotly_country_name)
    vis = df.rename(columns={"who_region": "Регион ВОЗ"})

    fig = px.choropleth(
        vis,
        locations="location",
        locationmode="country names",
        color="week_pct_increase",
        scope="world",
        title="Еженедельный прирост заболеваемости (% к предыдущей неделе)",
        color_continuous_scale="YlOrRd",
        labels={
            "week_pct_increase": "% за неделю",
            "location": "Страна (карта)",
        },
        hover_name="country",
        hover_data={
            "location": False,
            "Регион ВОЗ": True,
            "week_pct_increase": ":.2f",
        },
    )
    fig.update_layout(**geo_layout())
    fig.write_html(OUT_WEEKLY, include_plotlyjs="cdn")
    print(f"Сохранено: {OUT_WEEKLY}")


def morbidity_100k_map(connection: sqlite3.Connection) -> None:
    t = quote_identifier("Statistics Country")
    country_c = quote_identifier("Country")
    region_c = quote_identifier("WHO region")
    morb_c = quote_identifier("Morbidity per 100 thousand")
    query = f"""
        SELECT
            {country_c} AS country,
            MAX({region_c}) AS who_region,
            MAX(CAST({morb_c} AS REAL)) AS morbidity_100k
        FROM {t}
        WHERE {country_c} IS NOT NULL
          AND TRIM({country_c}) <> ''
          AND {morb_c} IS NOT NULL
        GROUP BY {country_c}
    """
    df = pd.read_sql_query(query, connection)
    df["location"] = df["country"].map(plotly_country_name)
    vis = df.rename(columns={"who_region": "Регион ВОЗ"})

    fig = px.choropleth(
        vis,
        locations="location",
        locationmode="country names",
        color="morbidity_100k",
        scope="world",
        title="Заболеваемость на 100 тыс. населения",
        color_continuous_scale="YlOrRd",
        labels={
            "morbidity_100k": "Случаев / 100 тыс.",
            "location": "Страна (карта)",
        },
        hover_name="country",
        hover_data={
            "location": False,
            "Регион ВОЗ": True,
            "morbidity_100k": ":.1f",
        },
    )
    fig.update_layout(**geo_layout())
    fig.write_html(OUT_MORBIDITY, include_plotlyjs="cdn")
    print(f"Сохранено: {OUT_MORBIDITY}")


def region_mortality_bar(connection: sqlite3.Connection) -> None:
    t = quote_identifier("Statistics Region")
    region_c = quote_identifier("Region")
    mort_c = quote_identifier("Mortality")
    query = f"""
        SELECT
            {region_c} AS region,
            CAST({mort_c} AS REAL) AS mortality
        FROM {t}
        WHERE {region_c} IS NOT NULL
          AND TRIM({region_c}) <> ''
          AND {mort_c} IS NOT NULL
        ORDER BY mortality DESC
    """
    df = pd.read_sql_query(query, connection)
    # сортировка: большие значения — сверху (categoryorder)
    fig = px.bar(
        df,
        x="mortality",
        y="region",
        orientation="h",
        title="Смертность по регионам ВОЗ (по убыванию)",
        labels={"mortality": "Смертность", "region": "Регион"},
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        margin=dict(l=0, r=0, t=50, b=0),
    )
    fig.write_html(OUT_REGIONS, include_plotlyjs="cdn")
    print(f"Сохранено: {OUT_REGIONS}")


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    try:
        weekly_increase_map(connection)
        morbidity_100k_map(connection)
        region_mortality_bar(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
