import html
import logging
from pathlib import Path

import click
import feedparser
import pandas as pd
import requests

# Обновил ссылку на актуальный RSS-канал CNBC Top News. Старая могла быть отключена.
NEWS_FEED_URL = "https://search.cnbc.com/rs/search/combinedcms/view.xml?profile=120000000&id=100003114"
COLUMNS_TO_SAVE = ['id', 'published', 'title', 'summary']

# Настройка логирования: в production всегда добавляем время и уровень важности сообщения
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@click.command()
@click.option('--data_path', required=True, help='Path to the input data CSV file')
def data_load(data_path: str) -> None:
    logging.info(f'Fetching financial news from {NEWS_FEED_URL}...')

    # 1. Защита от блокировок: маскируемся под обычный браузер
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # Использование requests позволяет жестко контролировать таймауты и заголовки
        response = requests.get(NEWS_FEED_URL, headers=headers, timeout=15)
        # Если сервер вернул ошибку (например, 404 или 500), скрипт упадет здесь,
        # и Airflow поймет, что задача провалена.
        response.raise_for_status()

        # Парсим уже полученный сырой текст
        news_feed = feedparser.parse(response.content)

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while fetching data: {e}")
        # Специальная команда click.Abort() корректно завершает скрипт с кодом ошибки
        raise click.Abort()

        # 2. Валидация данных: проверяем, что новости реально пришли
    if not news_feed.entries:
        logging.error('The RSS feed is empty. The site might have blocked the request or changed the structure.')
        raise ValueError('No entries found in the RSS feed.')

    logging.info(f'Successfully fetched {len(news_feed.entries)} news entries.')

    df = pd.DataFrame(news_feed.entries)

    # Проверяем, что в ответе есть нужные нам колонки (защита от изменения API источника)
    missing_cols = [col for col in COLUMNS_TO_SAVE if col not in df.columns]
    if missing_cols:
        logging.error(f"Missing expected columns in the feed: {missing_cols}")
        raise KeyError(f"Missing columns: {missing_cols}")

    df = df[COLUMNS_TO_SAVE]

    # 3. Безопасная очистка данных для передачи в NLP модель
    # errors='coerce' превратит нечитаемые даты в NaT (Not a Time) вместо падения всего скрипта
    df['published'] = pd.to_datetime(df['published'], errors='coerce')

    # Заполняем пропуски пустой строкой, чтобы метод .map не упал на значениях None/NaN
    df['title'] = df['title'].fillna('').map(html.unescape)
    df['summary'] = df['summary'].fillna('').map(html.unescape)

    # 4. Создание директорий: гарантируем, что папка существует перед сохранением
    output_path = Path(data_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logging.info(f'Saving the processed data to "{output_path}"...')
    df.to_csv(output_path, sep='\t', index=False)
    logging.info('Data saved successfully.')


if __name__ == '__main__':
    data_load()