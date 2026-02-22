import pendulum
from airflow.decorators import dag
from airflow.operators.python import PythonOperator  # Актуальный путь импорта
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

# Импорт кастомной функции. В реальном проекте файл utils.py
# должен лежать в папке plugins/ или рядом с DAG в dags/
from utils import aggregate_predictions

# В production константы всегда выделяют заглавными буквами.
# Добавлен начальный слеш в RAW_DATA_PATH для формирования абсолютного пути.
RAW_DATA_PATH = "/opt/airflow/data/raw/data__{{ ds }}.csv"
PRED_DATA_PATH = "/opt/airflow/data/predict/labels__{{ ds }}.json"
RESULT_DATA_PATH = "/opt/airflow/data/predict/result__{{ ds }}.json"

# Базовые аргументы для DockerOperator
dockerops_kwargs = {
    "mount_tmp_dir": False,
    "mounts": [
        Mount(
            # Используем r-префикс (raw string), чтобы Windows-пути с обратными
            # слешами (\) не вызывали ошибку Unicode escape.
            source=r"C:\Users\belon\PycharmProjects\Airflow_test\data",
            target="/opt/airflow/data/",
            type='bind'
        )
    ],
    'retries': 1,
    'api_version': 'auto',  # Версию API надежнее передавать строкой
    'docker_url': 'tcp://docker-socket-proxy:2375',  # Добавлена пропущенная запятая
    'network_mode': 'bridge',
}


# Используем pendulum вместо устаревшего days_ago
@dag(
    dag_id="financial_news",
    start_date=pendulum.datetime(2026, 2, 21, tz="UTC"),
    schedule_interval="@daily",
    catchup=False,
    tags=["ds", "nlp", "news_processing"]
)
def taskflow():
    # Task 1: Загрузка сырых данных в формате CSV
    news_load = DockerOperator(
        task_id="news_load",
        container_name="task__news_load",
        image="data_loader:latest",
        command=f"python data_load.py --data_path {RAW_DATA_PATH}",
        **dockerops_kwargs
    )

    # Task 2: Предсказание модели (NLP разметка)
    news_label = DockerOperator(
        task_id="news_label",
        container_name="task__news_label",
        image="model-prediction:latest",  # Исправлена опечатка (было 'iamge')
        command=f"python model_predict.py --data_path {RAW_DATA_PATH} --pred_path {PRED_DATA_PATH}",
        **dockerops_kwargs
    )

    # Task 3: Агрегация результатов
    news_by_topic = PythonOperator(
        task_id="news_by_topic",
        python_callable=aggregate_predictions,
        op_kwargs={
            'pred_data_path': PRED_DATA_PATH,
            'result_data_path': RESULT_DATA_PATH,
        },
    )

    # Задаем строгую последовательность выполнения задач (Pipeline)
    news_load >> news_label >> news_by_topic


# Инициализация графа
financial_news_dag = taskflow()