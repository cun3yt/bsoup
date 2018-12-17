from bs4 import BeautifulSoup as bs
import datetime
from tinydb import TinyDB, Query
import urllib3
import xlsxwriter
import os
import re
import sys
from google.cloud import storage, firestore, texttospeech


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



def upload_blob(source_file_name, destination_blob_name):
    bucket_name = 'beautiful-soup'
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)
    blob.make_public()

    print('File {} uploaded to {}, public url: {}.'.format(
        source_file_name,
        destination_blob_name,
        blob.public_url))

    return blob.public_url


def get_output_folder(date_str):
    return 'output_files/{}'.format(date_str)


def make_soup(url):
    http = urllib3.PoolManager()
    r = http.request("GET", url)
    return bs(r.data,'lxml')


def number_replace(symbol, name, text):
    def _fn(matchobj):
        return "{} {}{}".format(matchobj.group(1), name, matchobj.group(2))
    return re.sub(r"(\d+){}([\s\.\,\;])".format(symbol), _fn, text)


def around_symbol_replace(text):
    def _fn(matchobj):
        return "around {}{}".format(matchobj.group('dollar_sign'),
                                    matchobj.group('number'))
    return re.sub(r"~(?P<dollar_sign>\$?)(?P<number>[\d+])", _fn, text)


def to_list(date_str):
    url = 'https://www.launchticker.com/archive/{}'.format(date_str)
    pieces = []

    print("url: ", url)
    soup = make_soup(url)
    results = soup.find_all("td", style=re.compile(r'border: 1px solid.*?border-bottom: none'))

    for result in results:
        text = result.getText().strip()

        text_lower = text.lower()
        if "this week in startups" in text_lower and "episode" in text_lower:
            continue

        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', ' ', text)
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r' - Link', ' ', text)
        text = re.sub(r'  ', ' ', text)

        text = text.strip()
        text = "{}.".format(text) if text[-1] != '.' else text

        text = re.sub(r'; ', ';<break time="400ms"/>', text)
        text = re.sub(r', ', ',<break time="150ms"/>', text)
        text = number_replace('[Mm]', 'million', text)
        text = number_replace('[Bb]', 'billion', text)
        text = number_replace('[Kk]', 'thousand', text)
        text = around_symbol_replace(text)

        pieces.append(text)

    return pieces


def synthesize_ssml(ssml, output_file, lang_name='en-US-Wavenet-A'):
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.types.SynthesisInput(ssml=ssml)

    voice = texttospeech.types.VoiceSelectionParams(
        language_code='en-US', name=lang_name)

    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)

    response = client.synthesize_speech(input_text, voice, audio_config)

    with open(output_file, 'wb') as out:
        out.write(response.audio_content)
        print('Audio content written to file "{}"'.format(output_file))


def create_output_directory(date_str):
    output_folder = get_output_folder(date_str)
    if os.path.exists(output_folder):
        print('"{}" directory already exists, passing'.format(output_folder))
        return
    os.makedirs(output_folder)


def extract_voice(date_str):
    lang_names = ['en-US-Wavenet-F', 'en-US-Wavenet-A', ]
    number_of_names = len(lang_names)
    output_folder = get_output_folder(date_str)

    lst = to_list(date_str)
    output_filenames = []

    print("total: {}".format(len(lst)))

    lst.insert(0, "We have {} news for you. Let's go! ".format(len(lst)))

    for ind, piece in enumerate(lst, start=0):
        filename = "out_{}.mp3".format(ind)
        output_file = "{}/{}".format(output_folder, filename)

        if ind == 1:
            piece = "Our <say-as interpret-as='ordinal'>1</say-as> news:<break time='500ms' /> {}".format(piece)

        if ind == len(lst)-1:
            piece = "Last, but not least: <break time='600ms' /> {}".format(piece)

        print(piece)
        # todo: move the audio file below to an appropriate location
        ssml = "<speak>{}<audio src='https://s3-us-west-1.amazonaws.com/caressa-prod/development-related/DropItLikeItsHotFX01.wav'></audio></speak>".format(piece)
        lang_name = lang_names[ind % number_of_names]

        print(output_file, lang_name)
        synthesize_ssml(ssml, output_file, lang_name)
        upload_blob(output_file, output_file)
        output_filenames.append(filename)

    return output_filenames


def store_indexes(date_str, output_filenames, force=False):
    db = firestore.Client()
    d_ref = db.collection('tech-delivery').document(date_str)

    if (not force) and d_ref.get().exists:
        print('{} exists, passing it...'.format(date_str))
        return

    log = ("forced" if force else "doesn't exists") + ", creating: {}".format(date_str)
    print(log)
    d_ref.set({
        'date': date_str,
        'folder': get_output_folder(date_str),
        'files': output_filenames,
    })


def main(date_str):
    create_output_directory(date_str)
    output_filenames = extract_voice(date_str)
    store_indexes(date_str, output_filenames, force=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python parse.py date')
        print('`date` examples: ')
        print('  2018-11-08: morning issue')
        print('  2018-11-08_1: afternoon issue')
        exit(1)

    date_str = sys.argv[1]
    main(date_str=date_str)
