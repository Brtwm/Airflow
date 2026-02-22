from transformers import pipeline
import pandas as pd
import logging
import click

LABELS = [
    "Crypto",
    "SEC",
    "Dividend",
    "Economics",
    "Oil or Gas",
    "IPO",
    "Politics",
    "Buffet",
    "Stock",
    "Other",
]

logging.basicConfig(level=logging.INFO)

@click.command()
@click.option('--data_path', help='Path to the input data csv file')
@click.option('--pred_path', help='Path to save the output JSON file')
def model_predict(data_path: str, pred_path: str) -> None:
    logging.info('Loading model')
    model_hf = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device=-1)
    logging.info('Model loaded successfully')


    logging.info(f'Reading data from "{data_path}"...')
    df = pd.read_csv(data_path, sep='\t')
    logging.info('Data read successfully.')

    texts_for_pred = (df.title).tolist()

    logging.info('Performing prediction...')
    pred = model_hf(texts_for_pred, LABELS, multi_label=False)
    logging.info('Prediction complete.')

    df['label'] = [x['labels'][0] for x in pred]

    logging.info(f'Saving the predictions to "{pred_path}"...')
    df.T.to_json(pred_path)
    logging.info('Prediction saved successfully.')

if __name__ == '__main__':
    model_predict()