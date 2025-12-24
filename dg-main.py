import logging
import requests
import time
import paramiko
import re
import secret   # Секреты приложения
import setup    # Настройки приложения

# Глобальные переменные
# Оффсет при приемке новых сообщений. По умолчанию бот получает все команды за последние 24 часа, чтобы получать только
# новые необходимо в запросе передать ?offset=<значение последнего обработтаного сообщения + 1>
# Достаточно передать один раз, в последующих запросах offset необязателен до получения нового сообщения
v_OFFSET = 0


def ssh_runcommand(command):
    """
    Подключаем по SSH и выполняем команду на роутере
    """
    client = paramiko.SSHClient()
    # Добавление неизвестных хостов в known_hosts
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(hostname=secret.SSH_HOST,port=secret.SSH_PORT, username=secret.SSH_USER, password=secret.SSH_PASSWORD)
    stdin, stdout, stderr = client.exec_command(command)

    # Декодируем и очистим от разцветки
    # TODO: чистится не полностью, исправить
    out_stdout = stdout.read().decode()
    out_stdout = re.sub('\[[0-9;]+[a-zA-Z]', '', out_stdout)
    out_stderr = stderr.read().decode()
    out_stderr = re.sub('\[[0-9;]+[a-zA-Z]', '', out_stderr)

    return out_stdout, out_stderr


def logging_setup():
    """
    Настройка логгирования
    """
    handlers = [logging.FileHandler('./logs/post{0}.log'.format(time.strftime("%Y%m%d-%H%M%S")), 'a', 'utf-8'),
                logging.StreamHandler()]
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                        level=logging.INFO,
                        datefmt='%Y%m%d %H%M%S',
                        handlers=handlers)


def github_check(message, type):
    pass


def command_domain(message, type):
    if setup.USE_GITHUB:
        logging.info("Use GitHub. Go to Git Hub function...")
        github_check(message, type)
    else:
        logging.info("Not use GitHub, go to execute command...")
        command_kvas(message, type)


def command_kvas(message, type):
    # regex для домена: цифры, буквы и точка
    pattern = r"^[a-zA-Z0-9.]+$"

    logging.info(f'Start command {type}')
    logging.info(f'Message: {message}')
    chat_id = message['message']['chat']['id']
    message_text = (message['message']['text'])
    # Превращаем тело сообщения в список, т.к.
    # В одной команде можем обработать несколько доменов
    message_list = message_text.strip().split()
    # Удаляем саму команду
    del message_list[0]

    # М теперь для каждого домена в списке
    for domain in message_list:
        message_send(f'Try to {type} domain {domain} to KVAS', chat_id)
        if re.fullmatch(pattern, domain):
            command = f'kvas {type} {domain} -y'
            logging.info(f'Add domain {domain} to kvas with commad: {command}')
            stdout, stderr = ssh_runcommand(command)

            answer = f"""
            It's {secret.BOT_NAME}.
            Result {type} domain to kvas with command {command} on host: {secret.SSH_HOST}:
            STDOUT:
            {stdout}
            STDERR:
            {stderr}
            """

            logging.info(f'Prepare. Chat_id is: {chat_id}, reply is: {answer}')
            message_send(answer, chat_id)
        else:
            logging.info(f'Domain {domain} not verify regex pattern')
            message_send(f'Domain {domain} not verify regex pattern', chat_id)


def command_reply(message):
    """
    Ответ на команду /reply
    Проверка alive
    """
    logging.info('Start command reply')
    answer = f'Hello. It\'s {secret.BOT_NAME}. I\'m alive!'
    chat_id = message['message']['chat']['id']
    logging.info(f'Prepare. Chat_id is: {chat_id}, reply is: {answer}')
    message_send(answer, chat_id)


def command_status(message):
    """
    Команда /status. Проверяем что доступен SSH
    """
    logging.info('Start command status')
    command = 'ls -la /'
    chat_id = message['message']['chat']['id']

    stdout, stderr = ssh_runcommand(command)
    answer = f"""
    It's {secret.BOT_NAME}.
    Result execute command {command} on host: {secret.SSH_HOST}:
    STDOUT:
    ```{stdout}```
    STDERR:
    {stderr}
    """

    logging.info(f'Prepare. Chat_id is: {chat_id}, reply is: {answer}')
    message_send(answer, chat_id)


def message_send(text, chat_id):
    """
    Отправляем сообщения в телеграм
    """
    # Максимальный размер 4096 байт
    text = text[:4095]
    url = f'https://api.telegram.org/bot{secret.BOT_TOKEN}/sendMessage?chat_id={chat_id}&parseMode=MarkdownV2&text={text}'
    logging.info('Sending message')
    responce = requests.post(url)
    if setup.DEBUG: logging.info(responce)
    if responce.status_code == 200:
        logging.info('OK. Status 200')
    else:
        logging.error(f'Error send message. Responce: {responce}')


def message_processing(message):
    """
    Обрабатываем сообщения
    """
    # Проверка от кого сообщение
    username = message['message']['from']['username']
    logging.info(f'Message from {username}')
    if username in secret.USERS:
        logging.info(f'User {username} allowed to send command')
        # Поиск команды
        message_text = (message['message']['text'])
        command = message_text.strip().split()[0]
        logging.info(f'Command is {command}')
        match command:
            case '/add':
                logging.info(f'Command ADD')
                command_kvas(message, 'add')
            case '/del':
                logging.info(f'Command DEL')
                command_kvas(message, 'del')
            case '/reply':
                logging.info('Command REPLY')
                command_reply(message)
            case '/status':
                logging.info('Command STATUS')
                command_status(message)
            case _:
                logging.info(f'Command {command} not found')

    else:
        logging.info('User {username} NOT allowed to send command. Skip message.')


def json_parce(data):
    """
    Парсим сообщения из телеграма
    """
    if data['ok']:
        # Если длина словаря > 0 значит сообщения есть
        count = len(data['result'])
        if count > 0:
            logging.info(f'Recive {count} messages')
            # Цикл по словарю, обрабатываем по одному сообщению
            for message in data['result']:
                # Передадим сообщение на обработку
                message_processing(message)
                # В глобальную переменную пишем новое значение offset
                global v_OFFSET
                v_OFFSET = message['update_id'] + 1

        else:
            logging.info('No new messages')
    else:
        logging.error(f'In JSON key ok is not True')


def telegram_get_updates():
    """
    Получаем новые сообщения отправленные напрямую боту или в каналы на которые он подписан
    """
    url = f'https://api.telegram.org/bot{secret.BOT_TOKEN}/getUpdates?offset={v_OFFSET}'
    if setup.DEBUG: logging.info(url)
    response = requests.get(url)
    if setup.DEBUG: logging.info(f'Responce: {response.content}')
    if response.status_code == 200:
        res_json = response.json()
        if setup.DEBUG: logging.info(f'JSON: {res_json}')
        # Парсим ответ в случае успешного запроса
        json_parce(res_json)
    else:
        logging.error('Error get data from telegram API')
        return 1


def main():
    """
    Основной цикл
    """
    # Настроим логгинг
    logging_setup()
    logging.info("Starting")
    while 1:
        # Проверяем новые сообщения каждые UPDATE_TIMER
        logging.info("Try get updates")
        telegram_get_updates()
        time.sleep(setup.UPDATE_TIMER)
    return 0


if __name__ == "__main__":
    main()
