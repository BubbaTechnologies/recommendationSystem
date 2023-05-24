from flask import Flask, redirect, request
from models.onlineKNeighborClassifier import OnlineKNeighborClassifier
from flask_caching import Cache
import os

app = Flask(__name__)

@app.route("/")
def home():
    return redirect("https://www.peachsconemarket.com", code=302)

@app.route("/reccomendation", methods=['GET'])
def reccomendation():
    userId=request.args.get('userId', None)
    gender = request.args.get('gender', None)
    type = request.args.get('type',None)


@app.route("/like", methods=['POST'])
def like():
    pass


if __name__ == '__main__':
    oknn = OnlineKNeighborClassifier(50, 2, 1000)
    #TODO: Uploaded data to oknn

    port = int(os.environ.get('PORT', 5000))
    app.run(port=port)