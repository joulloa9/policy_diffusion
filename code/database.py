# This module handles the creation and management of the elasticsearch backend
import os
import argparse
from elasticsearch import Elasticsearch
import json

#Constants
STATE_BILL_INDEX = "state_bills"
MODEL_LEGISLATION_INDEX = "model_legistlation"
#ES_CONNECTION = Elasticsearch(timeout=300)
ES_CONNECTION = Elasticsearch([{'host': '54.212.36.132', 'port': 9200}],timeout = 300)


class SunlightElasticConnection():

    def __init__(host = "localhost",port = 9200):
        self.es_connection = Elasticsearch([{'host': host, 'port': port}],timeout = 300)

    # bulk loads all json files in subdirectory
    def load_bulk_bills(bill_directory):
        ES_CONNECTION.bulk(index=STATE_BILL_INDEX, body=bulk_data,timeout = 100)
        bulk_data = []
        ES_CONNECTION.bulk(index=STATE_BILL_INDEX, body=bulk_data,timeout=100)
        return


    # creates index for bills and model legislation stored in
    # data_path, overwriting index if it is already created
    def create_index(data_path):
        if ES_CONNECTION.indices.exists(STATE_BILL_INDEX):
            print("deleting '%s' index..." % (STATE_BILL_INDEX))
            ES_CONNECTION.indices.delete(index=STATE_BILL_INDEX)


        mapping_doc = json.loads(open(os.environ['POLICY_DIFFUSION'] + "/db/state_bill_mapping.json").read())
        settings_doc = json.loads(open(os.environ['POLICY_DIFFUSION'] + "/db/state_bill_index.json").read())

        print("creating '%s' index..." % (STATE_BILL_INDEX))
        res = ES_CONNECTION.indices.create(index=STATE_BILL_INDEX, body=settings_doc,timeout=30)

        print("adding mapping for bill_documents")
        res = ES_CONNECTION.indices.put_mapping(index=STATE_BILL_INDEX, doc_type="bill_document",
                                                body=mapping_doc)

        bulk_data = []
        for i, line in enumerate(open(data_path)):
            json_obj = json.loads(line.strip())
            if json_obj is None:
                continue


            op_dict = {
                "index": {
                    "_index": STATE_BILL_INDEX,
                    "_type": "bill_document",
                    "_id": json_obj["unique_id"]
                }
            }

            bulk_data.append(op_dict)
            bulk_data.append(json_obj)
            if len(bulk_data) == 1000:
                print i
                ES_CONNECTION.bulk(index=STATE_BILL_INDEX, body=bulk_data, timeout=300)

                del bulk_data
                bulk_data = []



    def query_state_bills(query,index_name = STATE_BILL_INDEX):

        json_query = {
                "query": {
                    "bool": {
                            "should": {
                        "match": {
                          "bill_document_last.shingles": query
                        }
                      }
                    }
                  },
                  "highlight": {
                    "pre_tags": [
                      "<mark>"
                    ],
                    "post_tags": [
                      "</mark>"
                    ],
                    "fields": {
                      "bill_document_last.shingles": {
                        "number_of_fragments": 0
                      }
                    }
                  }
                }
        
        
        results = ES_CONNECTION.search(index = STATE_BILL_INDEX,body = json_query)
        results = results['hits']['hits']
        result_docs = []
        for res in results:
            doc = {}
            doc['doc_text_with_highlights'] = res['highlight']['bill_document_last.shingles']
            doc['doc_text'] = res['_source']['bill_document_last']
            doc['score'] = res['_score']
            doc['bill_id'] = res['_source']['unique_id']
            doc['state'] = res['_source']['state']
            doc['title'] = res['_source']['bill_title']
            result_docs.append(doc)

        return result_docs





## main function that manages unix interface
def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('command', help='command to run, options are: build_index')
    parser.add_argument('--data_path', dest='data_path', help="file path of data to be indexed ")

    args = parser.parse_args()

    if args.command == "build_index":
        create_index(args.data_path)
    else:
        print args


if __name__ == "__main__":
    main()
