# Just a duplicate of hubeau_cleitn/beam.py to not pollute original code #

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import requests
import json
from datetime import datetime, timedelta, timezone
from google.cloud import storage
from apache_beam.io.gcp.gcsio import GcsIO
from apache_beam.io.gcp.bigquery import WriteToBigQuery

client = storage.Client()

class FetchHubeauData(beam.DoFn):
    def process(self, element):
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=4)
        date_debut_obs = one_hour_ago.strftime('%Y-%m-%dT%H:%M:%SZ')

        #url = f"https://hubeau.eaufrance.fr/api/v1/observations?date_debut={start_time}&date_fin={end_time}"
        url = f"https://hubeau.eaufrance.fr/api/v1/hydrometrie/observations_tr?code_entite=O972001001&date_debut_obs={date_debut_obs}"

        response = requests.get(url)
        print(response)
        if response.status_code >= 200 & response.status_code < 300 :
            data = response.json()
            print(data)
            return [data]
        else:
            return []



def write_to_gcs(element, gcs_path):
    print(element)

    print(gcs_path)
    gcsio = GcsIO()
    file_name = f"{gcs_path}/hubeau_data_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
    with gcsio.open(file_name, 'w') as f:
        f.write(json.dumps(element).encode('utf-8'))
    breakpoint()
    return [file_name]


class ReadFromGCSAndInsertIntoBigQuery(beam.DoFn):
    def __init__(self, gcs_path, bigquery_table):
        self.gcs_path = gcs_path
        self.bigquery_table = bigquery_table

    def process(self, element):
        ingestion_timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        gcsio = GcsIO()
        with gcsio.open(element, 'r') as f:
            data = json.loads(f.read().decode('utf-8'))

        for record in data['data']:
            record['ingestion_timestamp'] = ingestion_timestamp

            print(record)
            yield record

def run():
    #datasets/raw/diary-entries
    gcs_temp = "gs://riverflood-lewagon-dev-temp/hubeau_data"
    gcs_path = 'gs://riverflood-lewagon-dev/hubeau_data'
    bigquery_table = 'riverflood-lewagon:river_observations.hubeau_observations'

    options = PipelineOptions()
    p = beam.Pipeline(options=options)

    fetched_data = (
        p
        | 'Create' >> beam.Create([None])
        | 'Fetch Hubeau Data' >> beam.ParDo(FetchHubeauData())
    )

    fetched_data = (
            fetched_data
            | 'Print' >> beam.Map(print)
            #| 'Store in bigquery'
        )


    gcs_files = (
        fetched_data
        | 'Write to GCS' >> beam.ParDo(write_to_gcs, gcs_path=gcs_path)
    )

    (
        gcs_files
        | 'Read from GCS and Insert into BigQuery' >> beam.ParDo(ReadFromGCSAndInsertIntoBigQuery(gcs_path=gcs_path, bigquery_table=bigquery_table))
        | 'Write to BigQuery' >> WriteToBigQuery(
            table=bigquery_table,
            schema=' code_site:STRING, code_station:STRING, grandeur_hydro:STRING, date_debut_serie:TIMESTAMP, date_fin_serie:TIMESTAMP, statut_serie:INTEGER, code_systeme_alti_serie:INTEGER, date_obs:TIMESTAMP, resultat_obs:FLOAT, code_methode_obs:INTEGER, libelle_methode_obs:STRING, code_qualification_obs:INTEGER, libelle_qualification_obs:STRING, continuite_obs_hydro:BOOLEAN, longitude:FLOAT, latitude:FLOAT, ingestion_timestamp:TIMESTAMP',
            custom_gcs_temp_location=gcs_temp
        )

    )

    result = p.run()
    #result.wait_until_finish()



class FetchFromAPI(beam.DoFn):
    def process(self, element):
        lasthour = datetime.now(timezone.utc) - timedelta(hours=6)
        print( lasthour.isoformat().replace("+00:00", "Z"))
        date_filter = lasthour.isoformat().replace("+00:00", "Z")
        url = f"https://hubeau.eaufrance.fr/api/v1/hydrometrie/observations_tr?code_entite=O972001001&date_debut_obs={date_filter}"
        print(url)
        #url = "https://hubeau.eaufrance.fr/api/v1/hydrometrie/observations_tr?code_entite=K*"
        response = requests.get(url)
        print(response.status_code)
        if response.status_code >= 200 & response.status_code < 300 :
            yield response.text

            #yield json.loads(response.text)
        else:
            yield None

def sendToGcp(temp_file_path):
    print(temp_file_path)

    bucket_name = "riverflood-lewagon-dev"

        # data  | 'Print in Terminal 2' >> beam.Map(print)
    today = datetime.today()
    year, month, day, hour = today.strftime("%Y"), today.strftime("%m"), today.strftime("%d"), today.strftime("%H")
    target_gcs_path = f"datasets/raw/diary-entries/{year}/{month}/{day}/observation-{hour}.json"
    bucket = client.get_bucket(bucket_name)
    breakpoint()
    blob = bucket.blob(target_gcs_path)
    blob.upload_from_filename(temp_file_path)
    return target_gcs_path

def readFromGcp(blob_path):
    print(blob_path)

    bucket_name = "riverflood-lewagon-dev"

        # data  | 'Print in Terminal 2' >> beam.Map(print)

    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_path)
    jsonfile = blob.read(temp_file_path)
    return target_gcs_path



def run_old(
    interval=15
):
    options = beam.options.pipeline_options.PipelineOptions()

    with beam.Pipeline(options=options) as pipeline:

        # data section
        ids = [1]  # Example IDs
        temp_file_path = "tempFile"
        data = (
            pipeline
            | 'Create IDs' >> beam.Create(ids)
            | 'Fetch Data from API' >> beam.ParDo(FetchFromAPI())
            #| 'Print Results' >> beam.Map(print)


        )

        out = (
            data
            | 'write output' >> beam.io.textio.WriteToText(temp_file_path, file_name_suffix='.json')
            | 'Send Results' >> beam.Map(sendToGcp)
        )

        query = (
            out
            | 'Query storage' >> beam.Map(print)
            #| 'Store in bigquery'
        )



        #            | 'Print Results' >> beam.Map(print)

        #bucket_name = "riverflood-lewagon-dev"

        # data  | 'Print in Terminal 2' >> beam.Map(print)
        #today = datetime.today()
        #year, month, day = today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
        #target_gcs_path = f"datasets/raw/diary-entries/{year}/{month}/{day}/observation.json"
        #bucket = client.get_bucket(bucket_name)
        #blob = bucket.blob(target_gcs_path)
        #blob.upload_from_filename(temp_file_path)

if __name__ == "__main__":

    run(

    )
