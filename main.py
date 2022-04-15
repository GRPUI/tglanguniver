import telebot  # библиотека PyTelegramBotAPI
from telebot import TeleBot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import urllib3  # библиотека для работы с URL
import os  # библиотека для работы с ОС
import random  # библиотека рандом
import sqlite3  # библиотека для работы с БД SQL
import time  # библиотека для работы со временем
import schedule
import threading
from datetime import datetime, timedelta

bot: TeleBot = telebot.TeleBot('1540498139:AAE9BneM9X96cedwKV1Wt8jekIhIvuvF7gU')  # подключение токена

db = sqlite3.connect('database.db', check_same_thread=False)  # подключение БД
sql = db.cursor()

sql.execute("""CREATE TABLE IF NOT EXISTS users (
	user_id	INT,
	lvl	INT
)""")

db.commit()

inline_lvl = InlineKeyboardMarkup()
inline_lvl.row_width = 1
inline_lvl.add(InlineKeyboardButton("Я новичок", callback_data="newbie"),
               InlineKeyboardButton("Уже писал простой код", callback_data="notBad"),
               InlineKeyboardButton("Знаю на хорошем уровне", callback_data="master"))

inline_langs = InlineKeyboardMarkup()
inline_langs.row_width = 2
inline_langs.add(InlineKeyboardButton("Python", callback_data='py'),
                 InlineKeyboardButton("C++", callback_data='C++'),
                 InlineKeyboardButton("Java", callback_data='java'),
                 InlineKeyboardButton("JavaScript", callback_data='js'),
                 InlineKeyboardButton("Node.js", callback_data='nd'),
                 InlineKeyboardButton("SQL", callback_data='sql'))

inline_page_buttons = InlineKeyboardMarkup()
inline_page_buttons.row_width = 2
inline_page_buttons.add(InlineKeyboardButton("Назад", callback_data='back'),
                        InlineKeyboardButton("Вперёд", callback_data='next'),
                        InlineKeyboardButton("Главное меню", callback_data='main'))




@bot.message_handler(commands='start')
def mainMenu(message):
    sql.execute("SELECT user_id FROM users WHERE user_id = ?", (message.from_user.id,))
    check = sql.fetchall()
    if not check:
        bot.send_message(message.chat.id, 'Приветствую! Я бот для изучения языков программирования :)'
                                          'Скажи ты уже имеешь представление о языках программирования?',
                         reply_markup=inline_lvl)
    else:
        bot.send_message(message.chat.id, 'С возвращением!\nНе могу дождаться, чтобы узнать что ты веберешь :)\nP.S.'
                                          ' Я сохраняю твой прогресс, так что можешь не переживать,'
                                          ' что придётся искать место где остановился.', reply_markup=inline_langs)

@bot.message_handler(content_types=['text'])
def messages(message):
    pass


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    print(call.data)
    if call.data == "newbie":
        sql.execute("INSERT INTO users VALUES(?,?)", (call.from_user.id, 1))
        db.commit()
        bot.edit_message_text("Хорошо! Я бы посоветовал начать с Python, затем SQL."
                              " Однако ты в праве выбирать свой путь :)", call.message.chat.id, call.message.id,
                              reply_markup=inline_langs)
    elif call.data == "notBad":
        sql.execute("INSERT INTO users VALUES(?,?)", (call.from_user.id, 2))
        db.commit()
        bot.edit_message_text("Хорошо! Я бы посоветовал начать с Python, затем SQL."
                              " Однако ты в праве выбирать свой путь :)", call.message.chat.id, call.message.id,
                              reply_markup=inline_langs)
    elif call.data == "master":
        sql.execute("INSERT INTO users VALUES(?,?)", (call.from_user.id, 3))
        db.commit()
        bot.edit_message_text("Ого, не ожидал такой встречи. Ну что ж выбирай с чем хочешь ознакомится :)",
                              call.message.chat.id, call.message.id, reply_markup=inline_langs)

    if call.data == 'py':
        sql.execute('INSERT INTO activity VALUES(?,?)', (call.from_user.id, 1))
        db.commit()
        sql.execute('SELECT Text FROM PyMaterials WHERE Page = 1')
        Text = sql.fetchall()[0]
        bot.edit_message_text(Text, call.message.chat.id, call.message.id, reply_markup=inline_page_buttons)

    if call.data == 'main':
        bot.edit_message_text('Чем займёмся сейчас?', call.message.chat.id, call.message.id, reply_markup=inline_langs)

    if call.data == 'back':
        sql.execute('SELECT last_readed FROM activity WHERE user_id = ?', (call.from_user.id,))
        activity = int((sql.fetchone()[0]))-1
        if activity != 0:
            sql.execute('SELECT Text FROM PyMaterials WHERE Page = ?', (activity,))
            Text = sql.fetchall()[0]
            bot.edit_message_text(Text, call.message.chat.id, call.message.id, reply_markup=inline_page_buttons)
        else:
            sql.execute('SELECT Text FROM PyMaterials WHERE Page = 1')
            Text = sql.fetchall()[0]
            bot.edit_message_text(Text, call.message.chat.id, call.message.id, reply_markup=inline_page_buttons)

    if call.data == "next":
        sql.execute('SELECT last_readed FROM activity WHERE user_id = ?', (call.from_user.id,))
        print(sql.fetchone())
        activity = int((sql.fetchone()[0]))+1
        sql.execute('SELECT Text FROM PyMaterials WHERE Page = ?', (activity,))
        Text = sql.fetchall()[0]
        bot.edit_message_text(Text, call.message.chat.id, call.message.id, reply_markup=inline_page_buttons)


if __name__ == '__main__':
    bot.infinity_polling()
