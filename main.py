import logging
import typing
import sqlite3

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified

API_TOKEN = '5357001066:AAFCgaB4DnaQxDHpIH_7Dia7-5DVTGO8H-0'

db = sqlite3.connect('database.db', check_same_thread=False)
sql = db.cursor()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

cb = CallbackData('language', 'action')


def get_languages():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton('Python', callback_data=cb.new(action='python')),
        types.InlineKeyboardButton('SQL', callback_data=cb.new(action='sql'))
    ).row(
        types.InlineKeyboardButton('C++', callback_data=cb.new(action='cpp')),
        types.InlineKeyboardButton('C#', callback_data=cb.new(action='csharp'))
    )


def get_menu():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("Назад", callback_data=cb.new(action='back')),
        types.InlineKeyboardButton("Вперёд", callback_data=cb.new(action='next'))
    ).row(types.InlineKeyboardButton("Меню", callback_data=cb.new(action='menu'))
          ).row(types.InlineKeyboardButton("Темы", callback_data=cb.new(action='topic')))


def progress_checker(progress, lang):
    for name in progress[0].split(';'):
        if lang in name:
            return name
    return False


def content_getter(language, page):
    text = sql.execute(f"SELECT text FROM {language}_content WHERE id = {page}").fetchone()[0]
    return text


def topic_getter(lang):
    return sql.execute(f'SELECT theme FROM {lang}_content GROUP BY theme ORDER BY id').fetchall(), sql.execute(
        f'SELECT id FROM {lang}_content GROUP BY theme ORDER BY id').fetchall()


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer('Приветствую! Я бот для изучения языков программирования и не только\n'
                         'Выбирай язык из списка ниже :)',
                         reply_markup=get_languages())


@dp.callback_query_handler(cb.filter())
async def callback(query: types.CallbackQuery, callback_data: typing.Dict[str, str]):
    logging.info('Got this callback data: %r', callback_data)
    await query.answer()
    callback_data_action = callback_data['action']
    if callback_data_action in ["python", "sql", "cpp", "csharp"]:
        progress = sql.execute("SELECT progress FROM users WHERE id = ?", (query.from_user.id,)).fetchone()
        name = None
        if progress:
            name = progress_checker(progress, callback_data_action)
        text = ''
        page = 1
        if not progress or name is False:
            text = content_getter(callback_data_action, page)
            if not progress:
                sql.execute("INSERT INTO users(id, progress, last_opened) VALUES(?,?,?)",
                            (int(query.from_user.id), f"{callback_data_action}-1;", callback_data_action))
            else:
                sql.execute("UPDATE users SET progress = ?, last_opened = ? WHERE id = ?",
                            (progress[0] + f"{callback_data_action}-1;", callback_data_action, query.from_user.id))
            db.commit()
        else:
            page = int(str(name).split("-")[1])
            text = content_getter(callback_data_action, page)
            sql.execute("UPDATE users SET last_opened = ? WHERE id = ?", (callback_data_action, query.from_user.id))
            db.commit()
        await bot.edit_message_text(text,
                                    query.from_user.id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_menu())
    if callback_data_action == "menu":
        await bot.edit_message_text('Приветствую! Я бот для изучения языков программирования и не только\n'
                                    'Выбирай язык из списка ниже :)',
                                    query.from_user.id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_languages())
    if callback_data_action in ["back", "next"]:
        progress = sql.execute("SELECT progress FROM users WHERE id = ?", (query.from_user.id,)).fetchone()
        language = sql.execute("SELECT last_opened FROM users WHERE id = ?", (query.from_user.id,)).fetchone()[0]
        name = progress_checker(progress, language)
        page = int(str(name).split("-")[1])
        if callback_data_action == "back":
            if page == 1:
                return
            new_page = page - 1
        elif page < sql.execute(f"SELECT COUNT(*) FROM {language}_content").fetchone()[0]:
            new_page = page + 1
        progress = str(progress[0]).replace(name, f'{language}-{new_page}')
        sql.execute("UPDATE users SET progress = ?, last_opened = ? WHERE id = ?",
                    (progress, language, query.from_user.id))
        db.commit()
        text = content_getter(language, new_page)
        await bot.edit_message_text(text,
                                    query.from_user.id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_menu())
    if callback_data_action == "topic":
        language = sql.execute("SELECT last_opened FROM users WHERE id = ?", (query.from_user.id,)).fetchone()[0]
        topic_list = list(map(lambda x: x[0], topic_getter(language)[0]))
        topic_ids = list(map(lambda x: x[0], topic_getter(language)[1]))
        topic_inline = types.InlineKeyboardMarkup()
        for count in range(len(topic_ids)):
            topic, ids = topic_list[count], topic_ids[count]
            topic_inline.row(types.InlineKeyboardButton(topic, callback_data=cb.new(action=f'topic-{ids}')))
        await bot.edit_message_text("Темы:",
                                    query.from_user.id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=topic_inline)
    if callback_data_action.startswith("topic-"):
        language = sql.execute("SELECT last_opened FROM users WHERE id = ?", (query.from_user.id,)).fetchone()[0]
        text = content_getter(language, callback_data_action.split('-')[1])
        await bot.edit_message_text(text,
                                    query.from_user.id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_menu())
        progress = sql.execute("SELECT progress FROM users WHERE id = ?", (query.from_user.id,)).fetchone()
        name = progress_checker(progress, language)
        progress = str(progress[0]).replace(name, f'{language}-{callback_data_action.split("-")[1]}')
        sql.execute("UPDATE users SET progress = ?, last_opened = ? WHERE id = ?",
                    (progress, language, query.from_user.id))
        db.commit()


@dp.errors_handler(exception=MessageNotModified)
async def message_not_modified_handler(update, error):
    return True


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
