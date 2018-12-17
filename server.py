from flask import Flask, jsonify, make_response
from google.cloud import firestore, storage


app = Flask(__name__)
collection_name = 'tech-delivery'

# @todo: move `bucket_url` to an env variable
bucket_url = 'https://storage.googleapis.com/beautiful-soup'


@app.route("/list-days")
def list_days():
    db = firestore.Client()

    docs = db.collection(collection_name).order_by('date', direction=firestore.Query.DESCENDING).limit(5).get()
    return jsonify([doc.to_dict() for doc in docs])


@app.route("/<date_str>")
def files(date_str):
    db = firestore.Client()

    d_ref = db.collection(collection_name).document(date_str)

    if not d_ref.get().exists:
        return make_response("Not Found!!", 404)

    obj = d_ref.get().to_dict()
    obj['bucket_url'] = bucket_url

    # file_url = "{}/{}/{}".format(obj['bucket_url'], obj['folder'], obj['files'][0])
    return jsonify(obj)
