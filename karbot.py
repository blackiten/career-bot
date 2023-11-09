#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import telebot
import logging
from time import sleep
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, Message
from lib.sqlite_quiz import get_question_and_answers, get_transitions
from lib.sqlite_user import insert_to_users, select_from_users, delete_from_users


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S')

bot = telebot.TeleBot('ТОКЕН')



class User:
    """ Класс отвечающий за сущность пользователь и соответствующие ему параметры """

    def __init__(self, name: str):
        self.name: str = name
        # State пользователя минимально можно описать номером текущего и предыдущего вопросов.
        # Текущий вопрос, чтобы знать какую клаву перегенеривать.
        self.CurrentQID: int = 1
        # Чтобы ходить назад.
        self.LastQID: int = 0

        # Очки карьерных путей.
        self.career_path_points: dict[str, int] = CAREER_PATH.copy()
        # Из пути удаляем ответ на вопрос идущий после back
        self.question_path: list = [0, 1]  # example [1, 2, 3] номера вопросов.
        self.answer_career_point_path: list = [None, None]
        self.history: str = 'q1'  # example 'q1a1:q2a0'

    @staticmethod
    def get_next_question_id(answer_id: int | None, src: int) -> int | None:
        """ Находим id сделующего вопроса, зная id текущего вопроса и id-ответа """
        return next((i['dest'] for i in transition_table if i['answer_id'] == answer_id and i['source'] == src), None)

    def to_next_question(self, answer_id) -> None:
        """ Переведём стейт пользователя на шаг вперёд """
        self.LastQID = self.CurrentQID
        self.CurrentQID = self.get_next_question_id(answer_id=answer_id, src=self.CurrentQID)
        self.question_path.append(self.CurrentQID)
        self.history += f':q{self.CurrentQID}'

    def to_previous_question(self) -> None:
        """ Возвращаемся на один вопрос назад """

        # *_, b, l, c = [0, 1, 2]
        # _ => []
        # Чтобы вернуться на 1 вопрос назад, нужно быть хотя бы на 2ом вопросе.
        if len(self.question_path) < 3:
            logging.error(f'Был передан question_path длины меньше 3х: "{self.question_path}"')
            return

        *_, before_last, last, current = self.question_path

        self.CurrentQID = last
        self.LastQID = before_last
        self.question_path.pop()
        answer_career_point = self.answer_career_point_path.pop()
        if answer_career_point:
            cp_list = answer_career_point.split(',')
            for c in cp_list:
                self.career_path_points[c] -= 1

        self.history += f':q{self.CurrentQID}'

        if last in [4]:
            self.to_previous_question()

    def unpack(self) -> dict:
        """ Чтобы хранить инфу о пользователе в базе нам нужен раскукоженный dict """
        return self.__dict__


class Answer:
    def __init__(self, answer_id=0, text='', career_path=None):
        self.answer_id: int = answer_id
        self.text: str = text
        self.career_path: str | None = career_path


transition_table = get_transitions()

TO_BACK = '⬅ назад'

CAREER_PATH = {'management': 0,
               'prof.competence': 0,
               'integration': 0,
               'autonomy': 0,
               'enterprise': 0,
               'service': 0,
               }


def create_QAa() -> dict[int, list[Answer]]:
    """ Создаём структуру типа dict. Ключи - question_id. Значения - лист с вопросом и экземплярами класса Answer """
    qa_from_db = {}

    for i in range(1, 35 + 1):
        q, *answers = get_question_and_answers(i)
        answer_list = []
        for answer in answers:
            answer_id, text, career_path = answer
            answer_list.append(Answer(answer_id=answer_id, text=text, career_path=career_path))
        else:
            pass

        qa_from_db[i] = [q] + answer_list

    return qa_from_db


QA_from_db = create_QAa()


@bot.message_handler(commands=['delete'])
def forget_me(message: Message):
    nick = message.from_user.username
    chat_id = message.chat.id
    delete_from_users(chat_id=chat_id)
    bot.send_message(chat_id, text='Окей, я забыл о тебе!\nЕсли захочешь начать сначала нажми /start')


@bot.message_handler(commands=['start'])
def send_question(message: Message):
    nick = message.from_user.username
    chat_id = message.chat.id

    user = User(name=nick)
    respond = select_from_users(chat_id)
    if respond:
        d = json.loads(respond[0])
        for key, value in d.items():
            setattr(user, key, value)
    else:
        save_state(chat_id, user)
        photo = open('cotangins.jpg', 'rb')
        bot.send_photo(chat_id, photo, 'Ой... кто тут?! Эм. Кхм. Ща всё будет.')

    question_id = user.CurrentQID
    question, *answers = QA_from_db[question_id]

    if not answers:
        user.to_next_question(None)
        user.answer_career_point_path.append(None)
        save_state(chat_id, user)
        bot.send_message(chat_id, text=question)
        bot.send_chat_action(chat_id=chat_id, action='typing')
        sleep(0.5)
        send_question(message)
        return

    reply_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    if 1 != question_id:
        answers.append(Answer(text=TO_BACK))

    for answer in answers:
        reply_keyboard.add(KeyboardButton(answer.text))

    bot.send_message(message.chat.id, reply_markup=reply_keyboard, text=question)


@bot.message_handler(content_types=['text'])
def message_reply(message):
    nick = message.from_user.username
    chat_id = message.chat.id
    msg = message.text
    logging.info(f'Mr "{nick}" sent: "{msg}"')

    respond = select_from_users(chat_id)
    if respond:
        user = User(nick)
        d = json.loads(respond[0])
        for key, value in d.items():
            setattr(user, key, value)
    else:
        bot.send_message(chat_id, 'Я тебя не знаю, жми кнопку /start.')
        return

    question_id = user.CurrentQID
    q, *answers = QA_from_db[question_id]

    if msg == TO_BACK:
        user.history += f'aB'
        user.to_previous_question()
        save_state(chat_id, user)
        send_question(message)
        return

    for answer in answers:
        if answer.text == msg:
            break
    else:
        bot.send_message(message.chat.id, 'Я не понимаю.')
        return

    user.answer_career_point_path.append(answer.career_path)
    if answer.career_path:
        cp_list = answer.career_path.split(',')
        for c in cp_list:
            user.career_path_points[c] += 1

    user.history += f'a{answer.answer_id}'

    if question_id == 11:
        user.LastQID = user.CurrentQID
        if user.career_path_points['autonomy'] > user.career_path_points['management']:
            user.CurrentQID = 14
        else:
            user.CurrentQID = 12
        user.question_path.append(user.CurrentQID)
        user.history += f':q{user.CurrentQID}'
        save_state(chat_id, user)
        send_question(message)
        return

    user.to_next_question(answer.answer_id)
    save_state(chat_id, user)
    send_question(message)


def save_state(chat_id: int, user: User) -> None:
    insert_to_users(chat_id=chat_id, state=json.dumps(user.unpack()))
    print('json_user_unpack', json.dumps(user.unpack()))


def load_state(chat_id):
    respond = select_from_users(chat_id)
    if respond:
        d = json.loads(respond)
        user = User()
        for key, value in d.items():
            setattr(user, key, value)
    else:
        user = User()
        bot.send_message(chat_id, 'Я тебя не знаю, жми кнопку /start.')
    return user


if __name__ == '__main__':
    bot.infinity_polling()
