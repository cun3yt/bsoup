* create a python3 virtual environment with python 3.6.4
* activate the virtual env.
* create a google cloud account, create a project and activate these services on google cloud console (https://console.cloud.google.com/home/dashboard):
  * firestore,
  * google storage,
  * google text-to-speech
* download and copy the google application credentials service as `gc.json` to the root project folder.
* set environment variable `GOOGLE_APPLICATION_CREDENTIALS` to `gc.json`: `export GOOGLE_APPLICATION_CREDENTIALS='gc.json'`
* install python dependencies: `pip install -r requirements.txt`
* create `output_files/` folder at the project's root folder.
* run parse script to create the audio files, e.g. `python parse.py 2018-11-08`
* change `bucket_url` in `server.py` to the relevant public domain
* run flask server: `FLASK_APP=server.py flask run`
* hit `localhost:5000/<date>` to see what is served, e.g. `localhost:5000/2018-11-08`
