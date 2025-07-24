"""
================================================
    Блок: Импорт библиотек и функций
================================================
"""
import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

# базовая настройка страницы
st.set_page_config(page_title="ROSMAN Dashboard", layout="wide")
st.title("📦 Анализ продаж по заказам")

# путь к исходному .csv 
data_path = Path(__file__).parent / "orders.csv"

try:
    # читаем файл, приводим выручку к числу (убираем пробелы и запятую заменяем на точку)
    df = pd.read_csv(data_path, sep=";", parse_dates=["Date"])
    df["SumS"] = df["SumS"].astype(str).str.replace(" ", "").str.replace(",", ".").astype(float)
except Exception as e:
    st.error(f"Ошибка при чтении данных: {e}")
    st.stop()

# переименовываем ключевые колонки сразу (до фильтрации)
df.rename(columns={
    "ID": "Артикул",
    "Date": "Дата",
    "Amount": "Количество, шт",
    "SumS": "Выручка, руб"
}, inplace=True)

# боковая панель — фильтры по артикулу и диапазону дат
st.sidebar.header("🔍 Фильтры")
unique_ids = df["Артикул"].unique()
selected_ids = st.sidebar.multiselect("Выберите артикулы", unique_ids, default=unique_ids)
date_range = st.sidebar.date_input("Укажите период", [df["Дата"].min(), df["Дата"].max()])

# фильтрация основного датафрейма по условиям
filtered_df = df[
    (df["Артикул"].isin(selected_ids)) &
    (df["Дата"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))
]

# выводим три базовые метрики
st.metric("Общее количество продаж", int(filtered_df["Количество, шт"].sum()))
st.metric("Общая выручка", f"{filtered_df['Выручка, руб'].sum():,.2f} ₽")
avg_price = filtered_df['Выручка, руб'].sum() / filtered_df['Количество, шт'].sum() if filtered_df['Количество, шт'].sum() > 0 else 0
st.metric("Средняя цена", f"{avg_price:.2f} ₽")

# создаём отдельный срез на февраль 2025 — только он пойдёт в графики
df_february = filtered_df[
    (filtered_df["Дата"].dt.month == 2) &
    (filtered_df["Дата"].dt.year == 2025)
]

# === График: количество продаж по дням (Февраль 2025) ===
st.subheader("📊 Количество продаж по дням — Февраль 2025")

daily_amount = (
    df_february.groupby("Дата")["Количество, шт"]
    .sum()
    .reset_index()
    .sort_values("Дата")
)

amount_chart = alt.Chart(daily_amount).mark_line(point=True).encode(
    x=alt.X("Дата:T", title="Дата"),
    y=alt.Y("Количество, шт:Q", title="Штук"),
    tooltip=[alt.Tooltip("Дата:T"), alt.Tooltip("Количество, шт:Q", format=",.0f")]
).properties(width=900, height=300)

st.altair_chart(amount_chart, use_container_width=True)

# график: выручка по дням (Февраль 2025) 
st.subheader("💵 Выручка по дням — Февраль 2025")

daily_sum = (
    df_february.groupby("Дата")["Выручка, руб"]
    .sum()
    .reset_index()
    .sort_values("Дата")
)

sum_chart = alt.Chart(daily_sum).mark_line(point=True).encode(
    x=alt.X("Дата:T", title="Дата"),
    y=alt.Y("Выручка, руб:Q", title="₽"),
    tooltip=[alt.Tooltip("Дата:T"), alt.Tooltip("Выручка, руб:Q", format=",.2f")]
).properties(width=900, height=300)

st.altair_chart(sum_chart, use_container_width=True)

# === Блок: Юнит-экономика ===
st.header("🧮 Unit-экономика")

# выбор конкретного артикула (на весь период)
article_id = st.selectbox("Выберите артикул", df["Артикул"].unique())
df_art = df[df["Артикул"] == article_id]

# пересчитываем среднюю цену только по выбранному артикулу
avg_price = df_art["Выручка, руб"].sum() / df_art["Количество, шт"].sum() if df_art["Количество, шт"].sum() > 0 else 0
st.write(f"**Средняя цена продажи:** {avg_price:.2f} ₽")

# === Пользовательский ввод параметров для юнит-экономики ===
st.subheader("📥 Параметры")

with st.form("unit_calc"):
    col1, col2, col3 = st.columns(3)

    # блок 1 — стоимость, комиссии, возвраты
    with col1:
        cost = st.number_input("Себестоимость (₽)", value=100.0)
        commission = st.number_input("Комиссия маркетплейса (%)", value=21.0)
        acquiring = st.number_input("Эквайринг (%)", value=1.9)
        return_rate = st.number_input("Доля возвратов (%)", value=7.0)

    # блок 2 — НДС, хранение, обратка
    with col2:
        vat_rate = st.number_input("НДС (%)", value=10.0)
        storage_days = st.number_input("Срок хранения (дней)", value=30)
        storage_cost_per_l = st.number_input("Хранение за 1л/день (₽)", value=0.07)
        reverse_logistics = st.number_input("Обратная логистика (₽)", value=50.0)

    # блок 3 — габариты и коэффициент склада
    with col3:
        dimensions = st.text_input("Габариты товара (мм, через x)", value="13x263x202")
        warehouse_coeff = st.number_input("Коэффициент склада (%)", value=160.0)

    submitted = st.form_submit_button("📊 Рассчитать")

# расчёт по кнопке 
if submitted:
    try:
        l, w, h = [int(x) for x in dimensions.lower().split("x")]
        volume_l = (l * w * h) / 1_000_000  # перевод объема в литры
    except:
        st.error("❌ Неверный формат габаритов. Используйте формат: 13x263x202")
        st.stop()

    warehouse_k = warehouse_coeff / 100

    # расчёт промежуточных затрат
    price_wo_vat = avg_price / (1 + vat_rate / 100)
    commission_fee = price_wo_vat * (commission / 100)
    acquiring_fee = price_wo_vat * (acquiring / 100)
    delivery_fee = (38 + 9.5 * max(volume_l - 1, 0)) * warehouse_k
    storage_fee = (storage_cost_per_l + storage_cost_per_l * max(volume_l - 1, 0)) * warehouse_k * storage_days
    return_loss = price_wo_vat * (return_rate / 100) + reverse_logistics * (return_rate / 100)

    total_cost = cost + commission_fee + acquiring_fee + delivery_fee + storage_fee + return_loss
    profit = price_wo_vat - total_cost

    # вывод результата
    st.subheader("📊 Результат")
    if profit >= 0:
        st.success(f"💰 **Прибыль с единицы:** {profit:.2f} ₽")
    else:
        st.error(f"🔻 **Убыток с единицы:** {profit:.2f} ₽")
