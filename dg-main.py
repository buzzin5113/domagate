import logging
import requests
import time
import paramiko
import re
import secret   # Секреты приложения
import setup    # Настройки приложения

# Глобальные переменные
v_OFFSET = 0


def ssh_runcommand(command):
    client = paramiko.SSHClient()
    # Добавление неизвестных хостов в known_hosts
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(hostname=secret.SSH_HOST,port=secret.SSH_PORT, username=secret.SSH_USER, password=secret.SSH_PASSWORD)
    stdin, stdout, stderr = client.exec_command(command)

    # Декодируем и очистим от разцветки
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
    pattern = r"^[a-zA-Z0-9.]+$"

    logging.info(f'Start command {type}')
    logging.info(f'Message: {message}')
    chat_id = message['message']['chat']['id']
    message_text = (message['message']['text'])
    message_list = message_text.strip().split()
    del message_list[0]

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
    logging.info('Start command reply')
    answer = f'Hello. It\'s {secret.BOT_NAME}. I\'m alive!'
    chat_id = message['message']['chat']['id']
    logging.info(f'Prepare. Chat_id is: {chat_id}, reply is: {answer}')
    message_send(answer, chat_id)


def command_status(message):
    logging.info('Start command status')
    command = 'ls -la /'
    chat_id = message['message']['chat']['id']

    stdout, stderr = ssh_runcommand(command)
    answer = f"""
    It's {secret.BOT_NAME}.
    Result execute command {command} on host: {secret.SSH_HOST}:
    STDOUT:
    {stdout}
    STDERR:
    {stderr}
    """

    logging.info(f'Prepare. Chat_id is: {chat_id}, reply is: {answer}')
    message_send(answer, chat_id)


def message_send(text, chat_id):
    """
    Send message to telegram
    """
    url = f'https://api.telegram.org/bot{secret.BOT_TOKEN}/sendMessage?chat_id={chat_id}&text={text}'
    logging.info('Sending message')
    responce = requests.post(url)
    if setup.DEBUG: logging.info(responce)
    if responce.status_code == 200:
        logging.info('OK. Status 200')
    else:
        logging.error(f'Error send message. Responce: {responce}')


def message_processing(message):
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
                logging.info(f'Command ADD')
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
    if data['ok']:
        count = len(data['result'])
        if count > 0:
            logging.info(f'Recive {count} messages')
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
    url = f'https://api.telegram.org/bot{secret.BOT_TOKEN}/getUpdates?offset={v_OFFSET}'
    if setup.DEBUG: logging.info(url)
    response = requests.get(url)
    if setup.DEBUG: logging.info(f'Responce: {response.content}')
    if response.status_code == 200:
        res_json = response.json()
        if setup.DEBUG: logging.info(f'JSON: {res_json}')
        json_parce(res_json)
    else:
        logging.error('Error get data from telegram API')
        return 1


def main():
    """
    Основной цикс
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