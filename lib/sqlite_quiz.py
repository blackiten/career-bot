import sqlite3
import os.path


DB_NAME = 'quiz.db'


def create_tables():
    """ Создание базы данных и таблиц """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Создание таблицы вопросов
    c.execute('''CREATE TABLE IF NOT EXISTS questions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 question TEXT)''')

    # Создание таблицы ответов
    c.execute('''CREATE TABLE IF NOT EXISTS answers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 question_id INTEGER,
                 answer TEXT,
                 FOREIGN KEY (question_id) REFERENCES questions(id))''')

    conn.commit()
    conn.close()


def add_question(question, answers):
    """ Добавление вопроса и вариантов ответа в базу данных """
    conn = sqlite3.connect('quiz.db')
    c = conn.cursor()

    # Добавление вопроса
    c.execute("INSERT INTO questions (question) VALUES (?)", (question,))
    question_id = c.lastrowid

    # Добавление вариантов ответа
    for answer in answers:
        c.execute("INSERT INTO answers (question_id, answer) VALUES (?, ?)", (question_id, answer))

    conn.commit()
    conn.close()


def get_question_and_answers(question_number) -> list:
    """ Получение вопроса и вариантов ответа по номеру вопроса """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT id, question FROM questions WHERE id=?", (question_number,))
    question_id, question = c.fetchone()

    c.execute("SELECT id, answer, career_path FROM answers WHERE question_id=?", (question_id,))
    answers = c.fetchall()

    conn.close()
    """ Example returned date.
    ['Выбери утверждение, которое тебе ближе.', 
    (6, 'Хочу курировать работу других, иметь возможно влиять на процессы и людей на всех уровнях.', 'management'), 
    (7, 'Мне важно развиваться в конкретной технической или моей профессиональной сфере.', 'prof.competence'), 
    (8, 'Главное, чтобы карьера критично не мешала моей личной жизни и моим хобби.', 'integration')]
    """
    return [question] + answers


def get_transition(question_id, answer_id) -> dict:
    """ Только одной """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT answer_id, source, dest FROM transitions WHERE source=? and answer_id=?",
              (question_id, answer_id, ))
    answer_id, source, dest = c.fetchall()
    conn.close()

    return {'answer_id': answer_id, 'source': source, 'dest': dest}


def get_transitions() -> list[dict[str, None]]:
    """ Всех """
    transition_list = []
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT answer_id, source, dest FROM transitions")
    for transition in c.fetchall():
        answer_id, source, dest = transition
        transition_list.append({'answer_id': answer_id, 'source': source, 'dest': dest})
    conn.close()
    return transition_list


def first_run():
    """ ATTENTION!!! Действия могут быть деструктивны! """
    # Создание таблиц и добавление данных, если они еще не существуют

    if os.path.exists(DB_NAME):
        raise RuntimeError(f'File {DB_NAME} already exists, rm this file for create new db with that name.')

    create_tables()

    # Пример добавления вопросов и ответов
    add_question("Привет! Я — Тако, career help бот.",
                 ['Привет! Давай скорее начнём :)',
                  'Привет! Расскажи, пожалуйста, подробнее о карьерной помощи.',
                  ])
    add_question('В Бегете достаточно много мероприятий, направленных на помощь в проф. реализации: проекты, митапы, '
                 'практики, внутренние конкурсы и карьерные консультации. Основная задача Тако - помочь тебе заранее '
                 'определиться с вектором роста.',
                 ['Супер, давай скорее начнем :)'])
    add_question('Ты можешь закрепить за ответами свой телеграм, а можешь выбрать оставаться анонимным, и я не буду '
                 'привязывать его к результатам. Как тебе комфортнее?',
                 ['Да, Тако, можешь запомнить мой телеграм.',
                  'Тако, оставь, пожалуйста, наш разговор анонимным.',
                  ])

    # Пример использования функции для получения вопроса и вариантов ответа
    question_number = 1
    result = get_question_and_answers(question_number)
    print(result)
