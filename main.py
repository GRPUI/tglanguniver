import telebot  # библиотека PyTelegramBotAPI
from telebot import TeleBot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import urllib3  # библиотека для работы с URL
import os  # библиотека для работы с ОС
import random  # библиотека рандом
import sqlite3  # библиотека для работы с БД SQL
import time  # библиотека для работы со временем
import schedule  # библиотека для работы с хронами(задачами, которые повторяются время от времени)
import threading  # библиотека для многопоточной работы
from datetime import datetime, timedelta

# подключение токена бота

bot: TeleBot = telebot.TeleBot('5357001066:AAFCgaB4DnaQxDHpIH_7Dia7-5DVTGO8H-0')  # подключение токена

# подключение БД

db = sqlite3.connect('database.db', check_same_thread=False)  # подключение БД
sql = db.cursor()

# создание таблицы

sql.execute("""CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id	INT,
lvl	INT
)""")

db.commit()

# создание inline-кнопок

inline_lvl = InlineKeyboardMarkup()
inline_lvl.row_width = 1
inline_lvl.add(InlineKeyboardButton("Я новичок", callback_data="newbie"),
               InlineKeyboardButton("Уже писал простой код", callback_data="notBad"),
               InlineKeyboardButton("Знаю на хорошем уровне", callback_data="master"))

inline_langs = InlineKeyboardMarkup()
inline_langs.row_width = 2
inline_langs.add(InlineKeyboardButton("Python", callback_data='py'),
                 InlineKeyboardButton("C++", callback_data='C'),
                 InlineKeyboardButton("Java", callback_data='java'),
                 InlineKeyboardButton("JavaScript", callback_data='js'),
                 InlineKeyboardButton("R", callback_data='R'),
                 InlineKeyboardButton("SQL", callback_data='sql'))

inline_page_buttons = InlineKeyboardMarkup()
inline_page_buttons.row_width = 2
inline_page_buttons.add(InlineKeyboardButton("Назад", callback_data='back'),
                        InlineKeyboardButton("Вперёд", callback_data='next'),
                        InlineKeyboardButton("Главное меню", callback_data='main'),
                        InlineKeyboardButton("Темы", callback_data='theme'))
inline_page_buttons.row_width = 1
inline_page_buttons.add(InlineKeyboardButton("Тесты", callback_data='tests'))

inline_mainMenu = InlineKeyboardMarkup()
inline_mainMenu.row_width = 2
inline_mainMenu.add(InlineKeyboardButton("Главное меню", callback_data='main'))


# функция открытия тестов по прогрессу


def testOpener(page, user_id, lang):
    sql.execute("SELECT test FROM testOpener WHERE page = ? AND lang = ?", (page, lang.lower()))
    test = sql.fetchone()
    sql.execute(f"SELECT test FROM {lang.capitalize()}PROGRESS WHERE user_id = ?", (user_id,))
    prevTest = sql.fetchone()[0]
    if test and prevTest < test[0]:
        sql.execute(f"UPDATE {lang.capitalize()}PROGRESS SET test = ? WHERE user_id = ?", (test[0], user_id))
        db.commit()


# обработка команды start


@bot.message_handler(commands='start')
def mainMenu(message):
    sql.execute("SELECT user_id FROM users WHERE user_id = ?", (message.from_user.id,))
    check = sql.fetchall()
    if not check:
        bot.send_message(message.chat.id, 'Приветствую! Я бот для изучения языков программирования :)\n'
                                          'Скажи, ты уже имеешь представление о языках программирования?',
                         reply_markup=inline_lvl, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, 'С возвращением!\nНе могу дождаться, чтобы узнать что ты веберешь :)\nP.S.'
                                          ' Я сохраняю твой прогресс, так что можешь не переживать,'
                                          ' что придётся искать где остановился.',
                         reply_markup=inline_langs, parse_mode="Markdown")


# обработка текстовых сообщений


@bot.message_handler(content_types=['text'])
def messages(message):
    pass


# обработка call из inline-кнопок

def insert_user(f):
    def wrapper(*args, **kwargs):
        call = args[0]

        levels = ['newbie', 'notBad', 'master']
        if call.data in levels:
            sql.execute("INSERT INTO users(user_id, lvl) VALUES(?,?)", (call.from_user.id, levels.index(call.data) + 1))
            db.commit()
        return f(*args, **kwargs)

    return wrapper


send_start_message = {
    'newbie': 'Хорошо! Я бы посоветовал начать с *Python*, затем *SQL*. Однако ты в праве выбирать свой путь :)',
    'notBad': 'Хорошо! Я бы посоветовал начать с *Python*, затем *SQL*. Однако ты в праве выбирать свой путь :)',
    'master': 'Ого, не ожидал такой встречи. Ну что ж выбирай с чем хочешь ознакомится :)'
}


@bot.callback_query_handler(func=lambda call: True)
@insert_user
def callback(call):
    if call.data in send_start_message.keys():
        bot.edit_message_text(send_start_message[call.data], call.message.chat.id, call.message.id,
                              reply_markup=inline_langs, parse_mode="Markdown")

    if call.data in ['py', 'C', 'java', 'js', 'R', 'sql']:
        sql.execute(f'SELECT lastReaded FROM {str(call.data).capitalize()}PROGRESS WHERE user_id = ?',
                    (call.from_user.id,))
        fetch = sql.fetchone()

        page, activity_column = 1, '1'
        if fetch:
            page = fetch[0]
            activity_column = f'{str(call.data).capitalize()}-{page}'
        else:
            sql.execute(f'INSERT INTO {str(call.data).capitalize()}PROGRESS VALUES(?,?,?)', (call.from_user.id, 0, 1))
            db.commit()

        sql.execute('INSERT INTO activity VALUES(?,?)', (call.from_user.id, activity_column))
        db.commit()

        sql.execute(f'SELECT Text FROM {str(call.data).capitalize()}Materials WHERE Page = ?', (page,))
        Text = sql.fetchall()[0]

        bot.edit_message_text(Text, call.message.chat.id, call.message.id, reply_markup=inline_page_buttons,
                              parse_mode="Markdown")
        return

    if call.data == 'main':
        bot.edit_message_text('Чем займёмся сейчас?', call.message.chat.id, call.message.id, reply_markup=inline_langs,
                              parse_mode="Markdown")
        sql.execute('DELETE FROM activity WHERE user_id = ?', (call.from_user.id,))
        db.commit()

        return

    if call.data == 'back':
        sql.execute('SELECT last_readed FROM activity WHERE user_id = ?', (call.from_user.id,))
        activity = str(sql.fetchone()[0])
        prefix = (activity.split('-'))[0]
        activity = int((activity.split('-'))[1]) - 1
        page = 1
        if activity != 0:
            page = activity
            sql.execute(f'UPDATE {prefix.capitalize()}PROGRESS SET lastReaded = lastReaded-1 WHERE user_id = ?',
                        (call.from_user.id,))
            sql.execute('UPDATE activity SET last_Readed = ? WHERE user_id = ?',
                        (f'{prefix}-{activity}', call.from_user.id))
            db.commit()
        sql.execute(f'SELECT Text FROM {prefix.capitalize()}Materials WHERE Page = ?', (page,))
        Text = sql.fetchall()[0]
        bot.edit_message_text(Text, call.message.chat.id, call.message.id, reply_markup=inline_page_buttons,
                              parse_mode="Markdown")
        return

    if call.data == "next":
        sql.execute('SELECT last_readed FROM activity WHERE user_id = ?', (call.from_user.id,))
        activity = str(sql.fetchone()[0])
        prefix = (activity.split('-'))[0]
        activity = int((activity.split('-'))[1]) + 1
        sql.execute(f'SELECT Page FROM {prefix.capitalize()}Materials')
        width = len(sql.fetchall())
        if activity <= width:
            sql.execute(f'SELECT Text FROM {prefix.capitalize()}Materials WHERE Page = ?', (activity,))
            Text = sql.fetchall()[0]
            bot.edit_message_text(Text, call.message.chat.id, call.message.id, reply_markup=inline_page_buttons,
                                  parse_mode="Markdown")
            sql.execute(f'UPDATE {prefix.capitalize()}PROGRESS SET lastReaded = lastReaded + 1 WHERE user_id = ?',
                        (call.from_user.id,))
            sql.execute('UPDATE activity SET last_Readed = ? WHERE user_id = ?',
                        (f'{prefix}-{activity}', call.from_user.id))
            db.commit()
            testOpener(activity, call.from_user.id, prefix)

        return

    if call.data == 'tests':
        sql.execute('SELECT last_readed FROM activity WHERE user_id = ?', (call.from_user.id,))
        activity = str(sql.fetchone()[0])
        lang = (activity.split('-'))[0]
        sql.execute(f"SELECT test FROM {lang.capitalize()}PROGRESS WHERE user_id = ?", (call.from_user.id,))
        available = (sql.fetchone())[0]
        tests = InlineKeyboardMarkup()
        tests.row_width = 2
        for test in range(1, available + 1):
            tests.add(InlineKeyboardButton(f'Раздел {test}', callback_data=f'{lang}tests_{test}'))
        tests.add(InlineKeyboardButton('Главное меню', callback_data='main'))
        bot.edit_message_text('По какому разделу хочешь пройти тест?', call.message.chat.id, call.message.id,
                              reply_markup=tests, parse_mode="Markdown")
        return

    if str(call.data).split('tests_')[0] in ['Py', 'C', 'java', 'js', 'R', 'sql'] and str(call.data).split('tests_')[
        1] != '':
        numTest = (str(call.data).split('_'))[1]
        lang = (str(call.data).split('tests_'))[0]
        sql.execute(f"SELECT question FROM {lang.capitalize()}Test{numTest} WHERE num = ?", (1,))
        question = sql.fetchone()[0]
        answ = InlineKeyboardMarkup()
        answ.row_width = 3
        for n in range(3):
            sql.execute(f"SELECT answer{n + 1} FROM {lang.capitalize()}Test{numTest} WHERE num = ?", (1,))
            ans = (sql.fetchone())[0]
            answ.add(InlineKeyboardButton(ans, callback_data=f'{lang}tst-{numTest}-1-{n + 1}'))
        bot.edit_message_text(question, call.message.chat.id, call.message.id, reply_markup=answ)
        sql.execute(f"SELECT right FROM {lang}Test{numTest} WHERE num = ?", (1,))

        return

    if str(call.data).split('tst')[0] in ['Py', 'C', 'java', 'js', 'R', 'sql']:
        lang = (str(call.data).split('tst'))[0]
        testNum = str(call.data).split('-')[1]
        questionNum = int(str(call.data).split('-')[2])
        ansNum = int(str(call.data).split('-')[3])
        sql.execute(f"SELECT right FROM {lang}Test{testNum} WHERE num = ?", (questionNum,))
        right = (sql.fetchone())[0]
        if ansNum == right:
            if questionNum == 5:
                bot.edit_message_text('Всё верно! Я даже не сомневался в тебе! Так дежать!', call.message.chat.id,
                                      call.message.id, reply_markup=inline_mainMenu)
            else:
                sql.execute(f"SELECT question FROM {lang}Test{testNum} WHERE num = ?", (questionNum + 1,))
                question = sql.fetchone()[0]
                answ = InlineKeyboardMarkup()
                answ.row_width = 3
                for n in range(3):
                    sql.execute(f"SELECT answer{n + 1} FROM {lang}Test{testNum} WHERE num = ?", (questionNum + 1,))
                    ans = (sql.fetchone())[0]
                    answ.add(InlineKeyboardButton(ans, callback_data=f'{lang}tst-{testNum}-{questionNum + 1}-{n + 1}'))
                bot.edit_message_text(question, call.message.chat.id, call.message.id, reply_markup=answ)
        else:
            bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text="Неверно :(")

    if call.data == "theme" or str(call.data).startswith("module-"):
        try:
            call_name = 'module'
            sql.execute('SELECT last_readed FROM activity WHERE user_id = ?', (call.from_user.id,))
            activity = str(sql.fetchone()[0]).split('-')[0]
            if str(call.data).startswith("module-"):
                sql.execute(f'SELECT Theme FROM {activity}Materials WHERE Module = ? GROUP BY Theme ORDER BY Page',
                            (str(call.data).split('-')[1],))
                call_name = 'show'
            else:
                sql.execute(f'SELECT Module FROM {activity}Materials GROUP BY Module ORDER BY Page')
            modules = sql.fetchall()
            inline_themes = InlineKeyboardMarkup()
            inline_lvl.row_width = 1
            for theme in modules:
                if theme[0] is not None:
                    inline_themes.add(InlineKeyboardButton(text=theme[0], callback_data=f'{call_name}-{theme[0]}'))
            inline_themes.add(InlineKeyboardButton(text="Главное меню", callback_data='main'))
            if str(call.data).startswith("module-"):
                bot.edit_message_text('Темы модуля:', call.message.chat.id, call.message.id, reply_markup=inline_themes)
                return
            bot.edit_message_text('Выберите модуль:', call.message.chat.id, call.message.id,  reply_markup=inline_themes)
            return
        except sqlite3.OperationalError:
            bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text="К сожалению, эта функция не доступна.")

    if str(call.data).startswith('show'):
        theme = str(call.data).split('-')[1]
        sql.execute('SELECT last_readed FROM activity WHERE user_id = ?', (call.from_user.id,))
        activity = str(sql.fetchone()[0]).split('-')[0]
        sql.execute(f'SELECT Text, PAGE FROM {activity.capitalize()}Materials WHERE Theme = ?', (theme,))
        iterable = sql.fetchone()
        text = iterable[0]
        page = iterable[1]
        bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=inline_page_buttons,
                              parse_mode="Markdown")
        sql.execute(f'UPDATE activity SET last_Readed = ? WHERE user_id = ?', (f'{activity}-{page}', call.from_user.id))
        sql.execute(f'UPDATE {activity.capitalize()}PROGRESS SET lastReaded = ? WHERE user_id = ?',
                    (page, call.from_user.id))
        db.commit()


# проверка если код запущен напрямую
if __name__ == '__main__':
    # бесконечная провека сообщений
    bot.infinity_polling()
