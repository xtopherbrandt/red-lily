from flask import Flask, redirect, url_for, request
from stravalib import Client

# Next we create an instance of this class. 

app = Flask(__name__)

@app.route('/')
def hello_world():
    return render_template('helloworld.htm')

@app.route('/authorize')
def authorize():
    client = Client()
    url = client.authorization_url(client_id=16323, redirect_uri='http://127.0.0.1:8887/exchange')
    return redirect(url)

@app.route('/exchange', methods=['GET'])
def exchange():
    code = request.args.get('code')
    client = Client()
    access_token = client.exchange_code_for_token(client_id=16323, client_secret='acc979731b8be9933f46ab89f9d8094c705a3503', code=code)
    return access_token

