from telegram import Update, WebAppInfo
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, InlineQueryHandler, CallbackContext, CommandHandler
from telegram.constants import ParseMode


from uuid import uuid4 as uuid
from urllib.parse import quote_plus
from txtai import Embeddings

import logging
from dotenv import load_dotenv
import pandas as pd
import os
import requests

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
URL_QUIZ_LIST = os.getenv('URL_QUIZ_LIST')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

embeddings = Embeddings()
embeddings.load('src/embeddings/english')

def get_similar_words(word):
    words = [result['text'].capitalize() for result in embeddings.search(word, 5)]
    return words

def free_dictionary_api(word):
    url = f'https://api.dictionaryapi.dev/api/v2/entries/en_US/{word}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()[0]
    if response.status_code == 404:
        return response.json()

def get_word_definition(word):
    dictionary = free_dictionary_api(word)
    
    word_definition = {
        'word': word.capitalize(),
        'phonetics': [],
        'meanings': []
    }

    if 'title' in dictionary:
        word_definition['meanings'].append(dictionary['title'])
        return word_definition
    
    if not dictionary:
        word_definition['meanings'].append('An error occurred. Wait a few seconds and try again. If the error persists, contact the developer.')
        return word_definition

    try:
        word_definition['word'] = dictionary['word'].capitalize()
    except KeyError:
        breakpoint()

    for phonetic in dictionary['phonetics']:
        if 'text' in phonetic:
            word_definition['phonetics'].append(phonetic['text'])

    index = 1
    for part in dictionary['meanings']:
        for meaning in part['definitions']:
            word_definition['meanings'].append(f"{index}: {part['partOfSpeech']}. {meaning['definition']}")
            index += 1

    return word_definition

def definition_message(word_definition):
    message = ''
    
    message += f"*{word_definition['word']}*\n"
    if word_definition['phonetics']:
        message += f"{', '.join(word_definition['phonetics'])}\n"
    message += '\n'
    message += '\n'.join(word_definition['meanings'])

    return message

def query_result_dictionary(sentence):
    sentence = sentence.capitalize()
    sentence_id = uuid()
    url_youglish = f'https://youglish.com/pronounce/{quote_plus(sentence)}/english'
    
    if sentence.isalpha():
        word = sentence
        word_definition = get_word_definition(word)
        message = definition_message(word_definition)
        description = '\n'.join(word_definition['meanings'])
    else:
        message = f"*{sentence}*"
        description = ''

    result = {
        'id': sentence_id,
        'sentence': sentence,
        'description': description,
        'message': message,
        'url': url_youglish
    }

    return result

async def inline_query(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query.capitalize()

    # CASES
    # EMPTY
    if not query:
        queries = []
        #TODO return webInfoApp to the group
    # WORD
    elif query.isalpha():
        queries = get_similar_words(query)
        if query in queries: queries.remove(query)

        queries.insert(0, query)
        queries = queries[:5]
    # SENTENCE
    else:
        queries = [query]


    results = []
    for query in queries:
        result = query_result_dictionary(query)

        # button to redirect to the 'Duolingo Brasil' group
        keyboard = [
            [InlineKeyboardButton('💬 Duolingo Brazil UN', url='https://t.me/Duolingo_Brazil_UN')],
            [InlineKeyboardButton('🔍 Youglish', url=result['url'])]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        results.append(
            InlineQueryResultArticle(
                id=result['id'],
                title=result['sentence'],
                description=result['description'],
                input_message_content=InputTextMessageContent(result['message'], parse_mode='Markdown'),
                url=result['url'],
                # reply youglish button
                reply_markup=reply_markup,
            )
        )

    await update.inline_query.answer(results)

def get_quiz(quiz_id):
    df = pd.read_excel(URL_QUIZ_LIST, sheet_name='quiz', index_col='id')
    df['correct_option'] = df['correct_option'].fillna(0)
    df = df.fillna('')
    
    df['options'] = df[['option1', 'option2', 'option3', 'option4']].apply(lambda x: x.dropna().tolist(), axis=1)
    df = df.drop(columns=['option1', 'option2', 'option3', 'option4'])
    df['correct_option'] = df['correct_option'] - 1

    quiz = df.loc[quiz_id].to_dict()
    return quiz

async def send_poll(update: Update, context: CallbackContext):
    param = context.args[0]
    if not param.isnumeric():
        return
    
    quiz_id = int(param)

    quiz = get_quiz(quiz_id)

    await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        type='quiz',
        question=quiz['question'],
        options=quiz['options'],
        correct_option_id=quiz['correct_option'],
        explanation=quiz['explanation'],
    )


def main() -> None:
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    bot.add_handler(InlineQueryHandler(inline_query))
    bot.add_handler(CommandHandler('quiz', send_poll))

    bot.run_polling()

if __name__ == '__main__':
    main()