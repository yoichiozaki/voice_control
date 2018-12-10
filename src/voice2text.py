#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import requests
import re
import sys
import json
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue

import MeCab
# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)

def listen_print_loop(responses):
    """Iterates through server responses and prints them.

    The responses passed is a generator that will block until a response
    is provided by the server.

    Each response may contain multiple results, and each result may contain
    multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
    print only the transcription for the top alternative of the top result.

    In this case, responses are provided for interim results as well. If the
    response is an interim one, print a line feed at the end of it, to allow
    the next result to overwrite it, until the response is a final one. For the
    final one, print a newline to preserve the finalized transcription.
    """
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript.encode('utf8') + overwrite_chars.encode('utf8') + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            print(transcript.encode('utf8') + overwrite_chars.encode('utf8'))
            # mlist = mecab_list(transcript)
            # print(mlist)
            # return transcript + overwrite_chars
            # Exit recognition if any of the transcribed phrases could be
            # one of our keywords.
#            if re.search(r'\b($B%P%$%P%$(B|$B$5$h$&$J$i(B|$BE75$M=Js%b!<%I=*N;(B)\b', transcript, re.I):
#                print('Exiting..')
#                break
            return transcript.encode('utf8') + overwrite_chars.encode('utf8')
            num_chars_printed = 0

def speech2text():
    # See http://g.co/cloud/speech/docs/languages
    # for a list of supported languages.
    language_code = 'ja-JP'  # a BCP-47 language tag

    client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)

        # Now, put the transcription responses to use.
        return listen_print_loop(responses)

def parse(text):
    m = MeCab.Tagger("-Ochasen")
    # m.prase('')
    node = m.parseToNode(text)
    word_list = []
    while node:
        word = node.surface
        wclass = node.feature.split(',')
        if wclass[0] != 'BOS/EOS':
            word_list.append(word)
        node = node.next
    return word_list

# def Print_entering_message():
# 	print("entering weather forecaset mode")
# 
# mainly
# def weather_forcast():
# 	Print_entering_message()
# 
# 	# Google API
# 	words = parse(speech2text())
# 	# locationID
# 	location_id = get_locationID(words)
# 	# location_id = "120030"
# 	print("locationID :" + location_id)
# 	url = 'http://weather.livedoor.com/forecast/webservice/json/v1'
# 	response = requests.get(url, params={"city": location_id})
# 	weather_data = response.json()
# 	print(weather_data)
# 	for forecast in weather_data['forecasts']:
# 	    	print(forecast['telop'])
# 
# def get_locationID(words):
# 	location_dict = {"稚内": "011000", "旭川": "012010", "留萌": "012020", "網走": "013010", 
#                     "北見": "013020", "紋別": "013030", "根室": "014010", "釧路": "014020", 
#                     "帯広": "014030", "室蘭": "015010", "浦河": "015020", "札幌": "016010", 
#                     "岩見沢": "016020", "倶知安": "016030", "函館": "017010", "江差": "017020", 
#                     "青森": "020010", "むつ": "020020", "八戸": "020030", "盛岡": "030010", 
#                     "宮古": "030020", "大船渡": "030030", "仙台": "040010", "白石": "040020", 
#                     "秋田": "050010", "横手": "050020", "山形": "060010", "米沢": "060020", 
#                     "酒田": "060030", "新庄": "060040", "福島": "070010", "小名浜": "070020", 
#                     "若松": "070030", "水戸": "080010", "土浦": "080020", "宇都宮": "090010", 
#                     "大田原": "090020", "前橋": "100010", "みなかみ": "100020", "さいたま": "110010",
#                     "熊谷": "110020", "秩父": "110030", "千葉": "120010", "銚子": "120020", 
#                     "館山": "120030", "東京": "130010", "大島": "130020", "八丈島": "130030",
#                     "父島": "130040", "横浜": "140010", "小田原": "140020", "新潟": "150010",
#                     "長岡": "150020", "高田": "150030", "相川": "150040", "富山": "160010", 
#                     "伏木": "160020", "金沢": "170010", "輪島": "170020", "福井": "180010", 
#                     "敦賀": "180020", "甲府": "190010", "河口湖": "190020", "長野": "200010",
#                     "松本": "200020", "飯田": "200030", "岐阜": "210010", "高山": "210020", 
#                     "静岡": "220010", "網代": "220020", "三島": "220030", "浜松": "220040", 
#                     "名古屋": "230010", "豊橋": "230020", "津": "240010", "尾鷲": "240020", 
#                     "大津": "250010", "彦根": "250020", "京都": "260010", "舞鶴": "260020", 
#                     "大阪": "270000", "神戸": "280010", "豊岡": "280020", "奈良": "290010", 
#                     "風屋": "290020", "和歌山": "300010", "潮岬": "300020", "鳥取": "310010", 
#                     "米子": "310020", "松江": "320010", "浜田": "320020", "西郷": "320030", 
#                     "岡山": "330010", "津山": "330020", "広島": "340010", "庄原": "340020", 
#                     "下関": "350010", "山口": "350020", "柳井": "350030", "萩": "350040", 
#                     "徳島": "360010", "日和佐": "360020", "高松": "370000", "松山": "380010", 
#                     "新居浜": "380020", "宇和島": "380030", "高知": "390010", "室戸岬": "390020", 
#                     "清水": "390030", "福岡": "400010", "八幡": "400020", "飯塚": "400030", 
#                     "久留米": "400040", "佐賀": "410010", "伊万里": "410020", "長崎": "420010", 
#                     "佐世保": "420020", "厳原": "420030", "福江": "420040", "熊本": "430010", 
#                     "阿蘇乙姫": "430020", "牛深": "430030", "人吉": "430040", "大分": "440010", 
#                     "中津": "440020", "日田": "440030", "佐伯": "440040", "宮崎": "450010", 
#                     "延岡": "450020", "都城": "450030", "高千穂": "450040", "鹿児島": "460010", 
#                     "鹿屋": "460020", "種子島": "460030", "名瀬": "460040", "那覇": "471010", 
#                     "名護": "471020", "久米島": "471030", "南大東": "472000", "宮古島": "473000", 
#                     "石垣島": "474010", "与那国島": "474020"}
# 
# 	for word in words:
# 		if word in location_dict.keys():
# 			return location_dict[word]
# 		else:
# 			continue
# 