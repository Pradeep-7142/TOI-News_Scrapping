
# Import useful libraries and extensions
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_oauthlib.client import OAuth
from flask import abort
import psycopg2
from urllib.request import urlopen
from bs4 import BeautifulSoup
from urllib.parse import quote
import re
from werkzeug.urls import url_quote, url_unquote, url_encode
import nltk
nltk.download('all')
from nltk import sent_tokenize, word_tokenize, pos_tag
from nltk.corpus import stopwords
import json
from textblob import TextBlob
from datetime import datetime
import string

# Initilisation of the flask app and setting the privacy terms
app = Flask(__name__)
app.secret_key = '949ddniaki_auh8w8472989280'
ADMIN_PASSWORD = 'jnv@pradeep'

# Google authentication
# Do not forgate to add these three credentials from your google console
google_client_id = "13934746983-m0ic6is950tr9k15269sr0kuab2504ns.apps.googleusercontent.com"
google_client_secret = "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"
google_redirect_uri = "https://deploy-gn0p.onrender.com/login/authorized"

oauth = OAuth(app)
google = oauth.remote_app(
    'google',
    consumer_key=google_client_id,
    consumer_secret=google_client_secret,
    request_token_params={
        'scope': 'email profile',
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

# Define the tokengetter function
@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')

# Database Configuration and connecting with the render database
db_config = {
    'dbname': 'my_database_0gza',
    'user': 'my_database_0gza_user',
    'password': 's9qVRJarMky5udtlGJpJDYkQ2jvQj1qs',
    'host': 'dpg-cniativ79t8c73br4tmg-a',
    'port': '5432'
}

# Function to check is the url is ending with .cms to avoid raw urls of adds
def is_cms_url(url):
    return url.lower().endswith('.cms')

# Function to create table in the database if not exists to save user data
def create_users_table():
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        table_name = 'users'
        create_table_query = f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE
            )
        '''
        cursor.execute(create_table_query)
        connection.commit()

    except Exception as e:
        print("Error creating 'users' table:", e)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# Function to create the 'News_data' table if not exist
def create_news_data_table():
    try:  # to avoid the crash of the code
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        # lines to connect with the database
        table_name = 'News_data'
        create_table_query = f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                date_time TIMESTAMP,
                url_entered VARCHAR(255),
                sentiment_of_news VARCHAR(50),
                sent_count INTEGER,
                word_count INTEGER,
                stop_count INTEGER,
                post_json JSON,
                need_to_know TEXT,
                cleaned_text VARCHAR

            )
        '''
        cursor.execute(create_table_query)
        connection.commit()
        
    except Exception as e:
        print("Error creating 'News_data' table:", e)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Function to insert the data into the table
def insert_data_into_table(date_time, url_entered, sentiment_of_news, sent_count, word_count, stop_count, post_json, need_to_know,cleaned_text ):
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        table_name = 'News_data'
        query = f"INSERT INTO {table_name} (date_time, url_entered, sentiment_of_news, sent_count, word_count, stop_count, post_json, need_to_know, cleaned_text) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"

        cursor.execute(query, (date_time, url_entered, sentiment_of_news, sent_count, word_count, stop_count, post_json, need_to_know, cleaned_text))
        connection.commit()

    except Exception as e:
        print("Error inserting data into the table:", e)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Function to get all the data from the table 
def get_all_users():
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        table_name = 'users'
        query = f"SELECT * FROM {table_name}"

        cursor.execute(query)
        data = cursor.fetchall()

        return data

    except Exception as e:
        print("Error retrieving data from the 'users' table:", e)
        return []

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Function to get the data from another table
def get_all_data_from_table():
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        table_name = 'News_data'
        query = f"SELECT * FROM {table_name}"

        cursor.execute(query)
        data = cursor.fetchall()

        return data

    except Exception as e:
        print("Error retrieving data from the table:", e)
        return []
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Route for entering the password
@app.route("/password", methods=['GET', 'POST'])
def password():
    create_users_table()  # Ensure the 'users' table exists
    return render_template("password.html")

# Main Routes for the first page of the website
@app.route('/')
def index():
    global url
    if 'google_token' in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# Route to initiate the login process
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['url'] = request.form['url']
        return google.authorize(callback=url_for('authorized', _external=True))

    return render_template('index.html')

# Function to check if the user is authenticated
@app.route('/login/authorized')
def authorized():
    response = google.authorized_response()
    if response is None or response.get('access_token') is None:
        return 'Login failed.'

    session['google_token'] = (response['access_token'], '')
    user_info = google.get('userinfo')

    # Connect to the PostgreSQL database
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    # Ensure the 'users' table exists
    create_users_table()

    # Check if the user already exists in the database
    existing_user = None
    cur.execute("SELECT * FROM users WHERE email = %s", (user_info.data.get('email'),))
    existing_user = cur.fetchone()

    if not existing_user:
        # If the user doesn't exist, insert a new record into the users table
        cur.execute("INSERT INTO users (name, email) VALUES (%s, %s)",
                    (user_info.data.get('given_name'), user_info.data.get('email')))
        conn.commit()

    return redirect(url_for('portal'))

# Route to logout the user
@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return redirect(url_for('index'))

# funtion to do all the cleanning and other function with the news text
@app.route("/portal")
def portal():
    try:
        create_news_data_table()  # Ensure the 'News_data' table exists

        date_time = ""
        url_entered = ""
        sentiment_of_news = ""
        sent_count = ""
        word_count = ""
        stop_count = ""
        post_json = ""
        need_to_know = ""
        cleaned_text = ""
        #url = session.get('url')
        url = session.get('url', '')

        if not url:
            # Handle the case where 'url' is not present in the session
            return render_template("index.html", error_message="URL not provided in session.")
        if is_cms_url(url):
            # Process the URL only if it ends with .cms
            date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            url_entered = url
            html = urlopen(url_entered).read().decode('utf8')
            soup = BeautifulSoup(html, 'html.parser')
            results = soup.find(id="app")

            # classes used to get the text from the news article
            class_names = ['_s30J clearfix', 'sbFea', 'LErKb paywall', 'E8VGP', 'ULEYK', 'readmore_span', 'KB5o3', 'Normal',
                            'summary', 'synopsisit psgallery', "slideclass"]
            merged_text = ""
            for class_name in class_names:
                elements_with_class = soup.find_all(class_=class_name)
                for element in elements_with_class:
                    merged_text += element.get_text()
            if merged_text:
                text1 = merged_text
            # Removes all hindi words from the news article
            def remove_hindi_words(text):
                hindi_pattern = re.compile(u'[\u0900-\u097F]+')
                text_without_hindi = hindi_pattern.sub('', text)
                return text_without_hindi

            text = merged_text
            text_without_hindi = remove_hindi_words(text)
            # To remove Non english letters or words from the text
            def clean_text(text):
                cleaned_text = re.sub(r'[^{}{}.]'.format(string.ascii_letters, string.whitespace), '', text)
                return cleaned_text

            text2 = clean_text(text_without_hindi)

            sentence = text2
            tagged_sent = pos_tag(sentence.split())
            # To find the famous proper nouns for further exploration
            def extract_names(text):
                person_pattern = r"(?P<name>[A-Z][a-z]+(?: [A-Z][a-z]+)*)\b"
                place_pattern = r"(?P<name>[A-Z][a-z]+\s[A-Z][a-z]+)\b"
                organization_pattern = r"(?P<name>[A-Z][a-z]+(?: [A-Z][a-z]+)*)\s(?:Group|Company|Organization|Institution)\b"
                # selection of the words having some specific patteren
                person_regex = re.compile(person_pattern)
                place_regex = re.compile(place_pattern)
                organization_regex = re.compile(organization_pattern)

                person_matches = person_regex.findall(text)
                place_matches = place_regex.findall(text)
                organization_matches = organization_regex.findall(text)

                all_matches = list(set(person_matches + place_matches + organization_matches))

                return all_matches

            list_new = []
            names = extract_names(text_without_hindi)
            for i in names:
                if len(i) >= 15:
                    if i not in list_new:
                        list_new.append(i)
            need_to_know = list_new
            # To remove some subscript from the text to get the correct word count
            cleaned_text = text2.lower()
            cleaned_text1 = re.sub(r'[^\w\s]|(\d+)(st|nd|rd|th)?\b', '', cleaned_text)
            
            # To calculate the sentiment of the text
            def analyze_sentiment(text):
                blob = TextBlob(text)
                sentiment_polarity = blob.sentiment.polarity

                if sentiment_polarity > 0:
                    sentiment = 'Positive'
                elif sentiment_polarity < 0:
                    sentiment = 'Negative'
                else:
                    sentiment = 'Neutral'

                return sentiment

            text_to_analyze = cleaned_text1
            sentiment_of_news = analyze_sentiment(text_to_analyze)
            
            # Initilisation of the tokenisation of the text
            sent_count = len(sent_tokenize(cleaned_text))
            word_list = word_tokenize(cleaned_text)
            punct = [".", ",", "?", "!"]
            word_list = [word for word in word_list if word not in punct]
            word_count = len(word_list)
            stop_count = len([word for word in word_tokenize(cleaned_text) if word.lower() in set(stopwords.words('english'))])

            post_list = nltk.pos_tag(word_list, tagset="universal")

            post_dic = {}
            for i in post_list:
                if i[1] not in post_dic:
                    post_dic[i[1]] = 1
                else:
                    post_dic[i[1]] += 1
            post_json = json.dumps(post_dic)

            tagged_words = pos_tag(word_tokenize(cleaned_text))

            insert_data_into_table(date_time, url_entered, sentiment_of_news, sent_count, word_count, stop_count, post_json, need_to_know,cleaned_text)
            print("Data inserted successfully!")
        # representing the data on the Index Page
        return render_template("index.html",
                               msg_dt=date_time, msg_ur=url_entered, msg_cl=cleaned_text,
                               msg_se=sentiment_of_news,
                               msg_sn=sent_count, msg_wo=word_count,
                               msg_sp=stop_count, msg_cn=post_json, msg_di=need_to_know)

    except Exception as e:
        print("Error in /portal route:", e)
        abort(500)  # Internal Server Error

# To get the stored data of the user
@app.route("/stored_data", methods=['GET', 'POST'])
def stored_data():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            user_data = get_all_users()
            news_data = get_all_data_from_table()
            return render_template("stored_data.html", user_data=user_data, news_data=news_data)
        else:
            flash('Incorrect password!', 'error')
            return redirect(url_for('password'))
            # To get the admin data firstly verify yourself
    return redirect(url_for('password'))

if __name__ == '__main__':
    app.run(debug=True)
