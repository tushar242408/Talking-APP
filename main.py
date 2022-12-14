import random
import json
import pickle
import numpy as np
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
from flask import Flask, request,jsonify
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import SGD
from tensorflow.keras.models import load_model

import warnings

warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning)
lemmatizer = WordNetLemmatizer()
intents = json.loads(open('intents.json').read())
words = []
classes = []
documents = []
ignore_letter = []
for intent in intents['intents']:
    for pattern in intent['patterns']:
        word_list = word_tokenize(text=pattern)
        words.extend(word_list)
        documents.append((word_list, intent['tag']))
        if intent['tag'] not in classes:
            classes.append(intent['tag'])

words = [lemmatizer.lemmatize(word) for word in words if word not in ignore_letter]

words = sorted(set(words))
classes = sorted(set(classes))
pickle.dump(words, open('words.pkl', 'wb'))

training = []
output_empty = [0] * len(classes)

for doc in documents:
    bag = []
    word_patterns = doc[0]
    word_patterns = [lemmatizer.lemmatize(word.lower()) for word in word_patterns]
    for word in words:
        bag.append(1) if word in word_patterns else bag.append(0)

    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1
    training.append([bag, output_row])

random.shuffle(training)

training = np.array(training)
train_x = list(training[:, 0])
train_y = list(training[:, 1])
model = Sequential()
model.add(Dense(128, input_shape=(len(train_x[0]),), activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(64, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(len(train_y[0]), activation='softmax'))

sgd = SGD(learning_rate=0.01, momentum=0.9, nesterov=True)
model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

hist = model.fit(np.array(train_x), np.array(train_y), epochs=200, batch_size=5, verbose=1)


def save_model(model_name=None):
    if model_name is None:
        model.save(f"{model_name}.h5", hist)
        pickle.dump(words, open(f'{model_name}_words.pkl', 'wb'))
        pickle.dump(classes, open(f'{model_name}_classes.pkl', 'wb'))
    else:
        model.save(f"{model_name}.h5", hist)
        pickle.dump(words, open(f'{model_name}_words.pkl', 'wb'))
        pickle.dump(classes, open(f'{model_name}_classes.pkl', 'wb'))


def _clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words


def _bag_of_words(sentence, words):
    sentence_words = _clean_up_sentence(sentence)
    bag = [0] * len(words)
    for s in sentence_words:
        for i, word in enumerate(words):
            if word == s:
                bag[i] = 1
    return np.array(bag)


def _predict_class(sentence):
    p = _bag_of_words(sentence, words)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.1
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]

    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({'intent': classes[r[0]], 'probability': str(r[1])})
    return return_list


def _get_response(ints, intents_json):
    try:
        tag = ints[0]['intent']
        list_of_intents = intents_json['intents']
        for i in list_of_intents:
            if i['tag'] == tag:
                result = random.choice(i['responses'])
                break
    except IndexError:
        result = "I don't understand!"
    return result

app = Flask(__name__)


@app.route('/api/chatBotAPi', methods=['Get'])
def chatBotAPi():
    while True:
        messgae = str(request.args['Query'])
        ints = _predict_class(messgae)
        res = _get_response(ints, intents)

        d={'response':res}

        return  jsonify(d)

app.run()





