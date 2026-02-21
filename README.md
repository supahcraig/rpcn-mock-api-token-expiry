# Mock Token API + Redpanda Connect Example

## Run Flask API

```bash
cd flask-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py


icd connect
redpanda-connect run pipeline.yaml


