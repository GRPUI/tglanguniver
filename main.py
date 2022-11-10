import logging
import typing
import aiosqlite
import re

from functools import lru_cache

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

API_TOKEN = '5357001066:AAFCgaB4DnaQxDHpIH_7Dia7-5DVTGO8H-0'

# db = sqlite3.connect('database.db', check_same_thread=False)
# sql = db.cursor()

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

cb = CallbackData('language', 'action')


class Search(StatesGroup):
    request = State()


def standardization(text):
    text = re.sub(r"[`!?.:;,'\"()-]", "", str(text).lower())
    return text


async def searcher(language, word):
    global sql
    result = await sql.execute(f'SELECT text, id FROM {language}_content')
    all_info = await result.fetchall()

    info = list(map(lambda x: x[0], all_info))
    ids = list(map(lambda x: x[1], all_info))
    matches = []
    for _id, page in enumerate(info):
        page = standardization(page).lower()
        if word in str(page).split(" "):
            matches.append(_id + 1)
    if not matches:
        return False
    return matches


def get_languages():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton('Python', callback_data=cb.new(action='python')),
        types.InlineKeyboardButton('SQL', callback_data=cb.new(action='sql'))
    ).row(
        types.InlineKeyboardButton('C++', callback_data=cb.new(action='cpp')),
        types.InlineKeyboardButton('C#', callback_data=cb.new(action='csharp'))
    )


@lru_cache()
def get_menu():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("Назад", callback_data=cb.new(action='back')),
        types.InlineKeyboardButton("Вперёд", callback_data=cb.new(action='next'))
    ).row(types.InlineKeyboardButton("Темы", callback_data=cb.new(action='topic'))).row(
        types.InlineKeyboardButton("Меню", callback_data=cb.new(action='menu'))).row(
        types.InlineKeyboardButton("Поиск", callback_data=cb.new(action='search')))


@lru_cache()
def search_refuce():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("Отмена", callback_data=cb.new(action="search_refuce")))


def progress_checker(progress, lang):
    for name in progress[0].split(';'):
        if lang in name:
            return name
    return False


async def content_getter(language, page):
    global sql
    text = await (await sql.execute(f"SELECT text FROM {language}_content WHERE id = {page}")).fetchone()
    return text[0]


async def topic_getter(lang):
    global sql
    return await (await sql.execute(f'SELECT theme FROM {lang}_content GROUP BY theme ORDER BY id')).fetchall(), await (
        await sql.execute(
            f'SELECT id FROM {lang}_content GROUP BY theme ORDER BY id')).fetchall()


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    current_state = await state.get_state()
    if current_state:
        await state.finish()
    await message.answer('Приветствую! Я бот для изучения языков программирования и не только\n'
                         'Выбирай язык из списка ниже :)',
                         reply_markup=get_languages())


@dp.callback_query_handler(cb.filter(), state="*")
async def callback(query: types.CallbackQuery, callback_data: typing.Dict[str, str], state: FSMContext):
    global sql, db
    await query.answer()
    user_id = query.from_user.id
    callback_data_action = callback_data['action']
    if callback_data_action in ["python", "sql", "cpp", "csharp"]:
        progress = await (await sql.execute("SELECT progress FROM users WHERE id = ?", (user_id,))).fetchone()
        name = None
        if progress:
            name = progress_checker(progress, callback_data_action)
        text = ''
        page = 1
        if not progress or name is False:
            text = await content_getter(callback_data_action, page)
            if not progress:
                await sql.execute("INSERT INTO users(id, progress, last_opened) VALUES(?,?,?)",
                                  (int(user_id), f"{callback_data_action}-1;", callback_data_action))
            else:
                await sql.execute("UPDATE users SET progress = ?, last_opened = ? WHERE id = ?",
                                  (progress[0] + f"{callback_data_action}-1;", callback_data_action, user_id))
            await db.commit()
        else:
            page = int(str(name).split("-")[1])
            text = await content_getter(callback_data_action, page)
            await sql.execute("UPDATE users SET last_opened = ? WHERE id = ?", (callback_data_action, user_id))
            await db.commit()
        await bot.edit_message_text(text,
                                    user_id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_menu())
    if callback_data_action == "menu":
        await bot.edit_message_text('Приветствую! Я бот для изучения языков программирования и не только\n'
                                    'Выбирай язык из списка ниже :)',
                                    user_id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_languages())
    if callback_data_action in ["back", "next"]:
        progress = await (await sql.execute("SELECT progress FROM users WHERE id = ?", (user_id,))).fetchone()
        language = await (await sql.execute("SELECT last_opened FROM users WHERE id = ?", (user_id,))).fetchone()
        language = language[0]
        name = progress_checker(progress, language)
        page = int(str(name).split("-")[1])

        page_count = await (await sql.execute(f"SELECT COUNT(*) FROM {language}_content")).fetchone()
        page_count = page_count[0]

        if callback_data_action == "back":
            if page == 1:
                return
            new_page = page - 1
        elif page < page_count:
            new_page = page + 1
        progress = str(progress[0]).replace(name, f'{language}-{new_page}')
        await sql.execute("UPDATE users SET progress = ?, last_opened = ? WHERE id = ?",
                          (progress, language, user_id))
        await db.commit()
        text = await content_getter(language, new_page)
        await bot.edit_message_text(text,
                                    user_id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_menu())
    if callback_data_action == "topic":
        language = await (await sql.execute("SELECT last_opened FROM users WHERE id = ?", (user_id,))).fetchone()
        language = language[0]
        topics = await topic_getter(language)
        topic_list = list(map(lambda x: x[0], topics[0]))
        topic_ids = list(map(lambda x: x[0], topics[1]))
        topic_inline = types.InlineKeyboardMarkup()
        for count in range(len(topic_ids)):
            topic, ids = topic_list[count], topic_ids[count]
            topic_inline.row(types.InlineKeyboardButton(topic, callback_data=cb.new(action=f'topic-{ids}')))
        topic_inline.row(types.InlineKeyboardButton("К тексту 🔙", callback_data=cb.new(action='to_text')))
        await bot.edit_message_text("Темы:",
                                    user_id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=topic_inline)
    if callback_data_action.startswith("topic-"):
        language = await (await sql.execute("SELECT last_opened FROM users WHERE id = ?", (user_id,))).fetchone()
        language = language[0]
        text = await content_getter(language, callback_data_action.split('-')[1])
        await bot.edit_message_text(text,
                                    user_id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_menu())
        progress = await (await sql.execute("SELECT progress FROM users WHERE id = ?", (user_id,))).fetchone()
        name = progress_checker(progress, language)
        progress = str(progress[0]).replace(name, f'{language}-{callback_data_action.split("-")[1]}')
        await sql.execute("UPDATE users SET progress = ?, last_opened = ? WHERE id = ?",
                          (progress, language, user_id))
        await db.commit()
    if callback_data_action in ["to_text", "search_refuce"]:
        current_state = await state.get_state()
        if current_state:
            await state.finish()
        progress = await (await sql.execute("SELECT progress FROM users WHERE id = ?", (user_id,))).fetchone()
        language = await (await sql.execute("SELECT last_opened FROM users WHERE id = ?", (user_id,))).fetchone()
        language = language[0]
        name = progress_checker(progress, language)
        page = int(str(name).split("-")[1])
        text = await content_getter(language, page)
        await bot.edit_message_text(text,
                                    user_id,
                                    query.message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=get_menu())
    if callback_data_action == "search":
        await bot.edit_message_text("Введите ключевое слово: ", user_id,
                                    query.message.message_id, reply_markup=search_refuce())
        await Search.request.set()


@dp.message_handler(state=Search.request)
async def send_search(message: types.Message):
    global sql, db
    language = await (
        await sql.execute("SELECT last_opened FROM users WHERE id = ?", (message.from_user.id,))).fetchone()
    language = language[0]
    indexes = await searcher(language, str(message.text).lower())
    if not indexes:
        await message.answer("Ничего не найдено")
        return
    topics = []
    topic_inline = types.InlineKeyboardMarkup()
    for index in indexes:
        topic = await (await sql.execute(f"SELECT theme FROM {language}_content WHERE id = ?", (index,))).fetchone()
        topic = topic[0]
        topics.append(topic)
    for count in range(len(indexes)):
        topic, ids = topics[count], indexes[count]
        topic_inline.row(types.InlineKeyboardButton(topic, callback_data=cb.new(action=f'topic-{ids}')))
    await message.answer(f"Вот что найдено по запросу: {message.text}", reply_markup=topic_inline)


@dp.errors_handler(exception=MessageNotModified)
async def message_not_modified_handler(update, error):
    return True


async def on_startup(dp: Dispatcher):
    global sql, db
    db = await aiosqlite.connect('database.db', check_same_thread=False)
    sql = await db.cursor()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
