from flask import Flask, render_template, request, Response, redirect, url_for, flash
import mysql.connector
import os
import requests
from sklearn import svm

train_data = []
train_labels = []
test_data = []
test_labels = []

with open('poker-hand-training-true.data', 'r') as train_file:
    for line in train_file:
        current_line = line.rstrip('\n')
        data = current_line.split(',')
        hand_data = []
        for i in range(10):
            hand_data.append(int(data[i]))
        train_labels.append(int(data[10]))
        train_data.append(hand_data)

with open('poker-hand-testing.data', 'r') as test_file:
    for line in test_file:
        current_line = line.rstrip('\n')
        data = current_line.split(',')
        hand_data = []
        for i in range(10):
            hand_data.append(int(data[i]))
        test_labels.append(int(data[10]))
        test_data.append(hand_data)

classifier = svm.SVC()
classifier.fit(train_data, train_labels)

app = Flask(__name__)

host = os.environ.get('MYSQL_HOST')
database = os.environ.get('MYSQL_DATABASE')
password = os.environ.get('MYSQL_PASSWORD')
user = os.environ.get('MYSQL_USER')

cnx = mysql.connector.connect(host=host, database=database, user=user, password=password)
cursor = cnx.cursor()

@app.route('/index')
def index():
    query = 'SELECT * FROM players;'
    cursor.execute(query)
    return render_template('index.html', cursor=cursor)

@app.route('/add')
def add():
    return render_template('add.html')

@app.route('/post', methods=['POST'])
def post():
    name = request.form['name']
    country = request.form['country']

    query = 'INSERT INTO players (name, country) VALUES (%s, %s);'
    data = (name, country)
    cursor.execute(query, data)
    return redirect('/index')

@app.route('/delete', methods=['POST'])
def delete():
    name = request.form['name']

    query = 'DELETE FROM players WHERE name=%s;'
    cursor.execute(query, (name,))
    return redirect('/index')

@app.route('/details')
def details():
    name = request.args.get('name')
    query = 'SELECT * FROM players WHERE name=%s;'
    cursor.execute(query, (name,))
    data = cursor.fetchone()
    if data:
        player_country = data[1]

        country_json = requests.get('https://restcountries.eu/rest/v2/name/' + player_country + '?fullText=true')

        if country_json.status_code == 404:
            continent = 'unknown continent'
            code = 'US'
            capital = 'unknown capital'
            population = 'unknown population'
            flag = ''

            return render_template('details.html',
                                   name=name,
                                   country=player_country,
                                   continent=continent,
                                   capital=capital,
                                   population=population,
                                   flag=flag)

        country = country_json.json()

        continent = country[0]['region']
        code = country[0]['alpha2Code']
        capital = country[0]['capital']
        population = country[0]['population']
        flag = 'https://www.countryflags.io/' + code + '/shiny/64.png'

        if capital == '':
            capital = 'unknown capital'

        # print(country[0]['latlng'])
        #
        # latitude = country[0]['latlng'][0]
        # longitude = country[0]['latlng'][1]

        latitude_longitude = country[0]['latlng']
        latitude_longitude.append('unknown')
        latitude_longitude.append('unknown')

        latitude = latitude_longitude[0]
        longitude = latitude_longitude[1]

        sunlight_json = requests.get('https://api.sunrise-sunset.org/json?lat=' + str(latitude) + '&lng=' + str(longitude))



        sunlight_data = sunlight_json.json()
        sunrise = 'unknown'
        sunset = 'unknown'
        if sunlight_data['status'] == 'OK':
            sunrise = sunlight_data['results']['sunrise']
            sunset = sunlight_data['results']['sunset']

        return render_template('details.html',
                               name=name,
                               country=player_country,
                               continent=continent,
                               capital=capital,
                               population=population,
                               flag=flag,
                               sunrise=sunrise,
                               sunset=sunset)
    else:
        return redirect('/error')

@app.route('/play')
def play():
    query = 'SELECT COUNT(name) from players;'
    cursor.execute(query)
    count = cursor.fetchone()
    number_of_players = count[0]
    return render_template('play.html', number_of_players=number_of_players)

@app.route('/game')
def game():
    deck_data = requests.get('https://deckofcardsapi.com/api/deck/new/shuffle')
    deck = deck_data.json()
    deck_id = deck['deck_id']

    query = 'SELECT COUNT(name) from players;'
    cursor.execute(query)
    count = cursor.fetchone()
    number_of_players = count[0]

    hands = []
    card_images = []

    for i in range(number_of_players):
        hand_data = requests.get('https://deckofcardsapi.com/api/deck/' + deck_id + '/draw/?count=5')
        hand_json = hand_data.json()
        hand = []
        hand_images = []
        for j in range(5):
            hand.append(hand_json['cards'][j]['suit'])
            hand.append(hand_json['cards'][j]['value'])
            hand_images.append(hand_json['cards'][j]['image'])
        hands.append(hand)
        card_images.append(hand_images)

    translated_hands = []

    for hand in hands:
        translated_hand = []
        for card in hand:
            if card == 'ACE':
                translated_hand.append(1)
            elif card == '2':
                translated_hand.append(2)
            elif card == '3':
                translated_hand.append(3)
            elif card == '4':
                translated_hand.append(4)
            elif card == '5':
                translated_hand.append(5)
            elif card == '6':
                translated_hand.append(6)
            elif card == '7':
                translated_hand.append(7)
            elif card == '8':
                translated_hand.append(8)
            elif card == '9':
                translated_hand.append(9)
            elif card == '10':
                translated_hand.append(10)
            elif card == 'JACK':
                translated_hand.append(11)
            elif card == 'QUEEN':
                translated_hand.append(12)
            elif card == 'KING':
                translated_hand.append(13)
            elif card == 'HEARTS':
                translated_hand.append(1)
            elif card == 'SPADES':
                translated_hand.append(2)
            elif card == 'DIAMONDS':
                translated_hand.append(3)
            elif card == 'CLUBS':
                translated_hand.append(4)
        translated_hands.append(translated_hand)

    winners = []
    best_hand = 0

    predictions = classifier.predict(translated_hands)
    print(predictions)
    for i in range(len(predictions)):
        if predictions[i] > best_hand:
            best_hand = predictions[i]
            winners.clear()
            winners.append(i)
        elif predictions[i] == best_hand:
            winners.append(i)

    print(winners)

    # for i in range(len(translated_hands)):
    #     input = []
    #     input.append(translated_hands[i])
    #     output = classifier.predict(input)
    #     prediction = output[0]
    #
    #     if prediction > best_hand:
    #         best_hand = prediction
    #         winners.clear()
    #         winners.append(i)
    #     elif prediction == best_hand:
    #         winners.append(i)

    return render_template('game.html', hands=hands, winners=winners, card_images=card_images, number_of_players=number_of_players)

@app.route('/error')
def error():
    return render_template('error.html')

if __name__ == '__main__':
    app.run(debug=True)

# query = 'DELETE FROM players;'
# cursor.execute(query)

cnx.commit()
cursor.close()
cnx.close()