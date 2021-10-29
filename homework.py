import logging
import os
import requests
import time
from dotenv import load_dotenv
import telegram
import sys

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w'
)

logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)

RETRY_TIME = 5
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


def check_tokens():
    """"проверяет обязательные переменные окружения"""
    no_tokens_msg = (
        'Программа принудительно остановлена. '
        'Отсутствует обязательная переменная окружения:')
    tokens_bool = True
    if PRACTICUM_TOKEN is None:
        tokens_bool = False
        logger.critical(
            f'{no_tokens_msg} PRACTICUM_TOKEN')
    if TELEGRAM_TOKEN is None:
        tokens_bool = False
        logger.critical(
            f'{no_tokens_msg} TELEGRAM_TOKEN')
    if CHAT_ID is None:
        tokens_bool = False
        logger.critical(
            f'{no_tokens_msg} CHAT_ID')
    return tokens_bool


def send_message(bot, message):
    """"отправляет сообщение"""
    try:
        logger.info(f'bot send message {message}')
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as error:
        logger.error(f'Error in send message: {error}')


def get_api_answer(url, current_timestamp):
    """"отправляет запрос к API практикума"""
    url = ENDPOINT
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=headers, params=payload)
        if response.status_code != 200:
            logging.error('Ошибка эндпоинта')
            raise Exception('Эндпоинт недоступен')
    except requests.exceptions.RequestException:
        logging.error('сетевая ошибка')
        raise Exception('ошибка сети')
    return response.json()


def parse_status(homework):
    """"проверяет статус"""
    verdict = HOMEWORK_STATUSES[homework.get('status')]
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise Exception('имя задания отсутствует')
    if verdict is None:
        raise Exception('нет результата')
    logger.info(f'итоговый результат: {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """"получает ответ"""
    homeworks = response.get('homeworks')
    current_timestamp = response.get('current_date')
    if homeworks is None:
        logger.error('задание отсутствует')
        raise Exception('Задание отсутствует')
    for homework in homeworks:
        status = homework.get('status')
        if status in HOMEWORK_STATUSES.keys():
            return homework
        else:
            logger.error('недокументированный статус ДЗ')
            raise Exception('недокументированный статус ДЗ')
    return {'homeworks': homeworks,
            'current_timestamp': current_timestamp
            }


def main():
    """связующая функция"""
    if not check_tokens():
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    errors = True
    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            time.sleep(RETRY_TIME)
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logging.error(message, exc_info=True)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
