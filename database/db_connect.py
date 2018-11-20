## Copyright (c) 2015 SONATA-NFV, 2017 5GTANGO [, ANY ADDITIONAL AFFILIATION]
## ALL RIGHTS RESERVED.
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##
## Neither the name of the SONATA-NFV, 5GTANGO [, ANY ADDITIONAL AFFILIATION]
## nor the names of its contributors may be used to endorse or promote
## products derived from this software without specific prior written
## permission.
##
## This work has been performed in the framework of the SONATA project,
## funded by the European Commission under Grant number 671517 through
## the Horizon 2020 and 5G-PPP programmes. The authors would like to
## acknowledge the contributions of their colleagues of the SONATA
## partner consortium (www.sonata-nfv.eu).
##
## This work has been performed in the framework of the 5GTANGO project,
## funded by the European Commission under Grant number 761493 through
## the Horizon 2020 and 5G-PPP programmes. The authors would like to
## acknowledge the contributions of their colleagues of the 5GTANGO
## partner consortium (www.5gtango.eu).

from pymongo import MongoClient
import json


def mongo_connect():
    client = MongoClient()
    client = MongoClient('mongo', 27017)
    return client

def create_db(db_name):
    client = mongo_connect()
    my_db = client[db_name]
    client.close()

def insert_docs(db, collection, doc):
    client = mongo_connect()
    db = client[db]
    collection_doc = db[collection]
    
    collection_doc.insert(doc)
    client.close()

def add_to_unknown(db, collection, vnfs):
    client = mongo_connect()
    db = client[db]
    collection = db[collection]
    
    for vnf in vnfs:
        collection.insert_one({'vnf_id': vnf})
    client.close()
      
def del_doc(db, collection, doc):
    client = mongo_connect()
    mydb = client[db]
    mycol = mydb[collection]

    with open(doc) as f:
        file_data = json.load(f)

    mycol.delete_one(file_data)
    client.close()
    

def get_documents(db, collection,vnf_names):
    documents_list = list()
    client = mongo_connect()

    mydb = client[db]
    mycol = mydb[collection]
       
    for vnf_name in vnf_names:
        myquery = { 'vnf': {
                    'vnf_id':vnf_name
                    } 
                  }
        cursor = mycol.find(myquery)
  
        for document in cursor:
            documents_list.append(document)
                     
    client.close()
    return documents_list

def get_known_vnfs(db, collection,vnf_names):
    client = mongo_connect()
    known_vnfs = list()
    mydb = client[db]
    mycol = mydb[collection]
       
    for vnf_name in vnf_names:
        myquery = { 'vnf': {
                    'vnf_id':vnf_name
                    } 
                  }
        cursor = mycol.count(myquery)
        if cursor > 0:
            known_vnfs.append(vnf_name)
                              
    client.close()
    return known_vnfs

def not_in_db(db, collection, vnf):
    client = mongo_connect()
    mydb = client[db]
    mycol = mydb[collection]
    
    myquery = { 'vnf': {
                    'vnf_id':vnf
                    } 
                  }
    cursor = mycol.count(myquery)
    
    if cursor == 0:
        return True
    else:
        return False
    
    
def get_supported_vnfs(db, collection):
    documents_list = list()
    vnfs_list = list()
    client = mongo_connect()
    mydb = client[db]
    mycol = mydb[collection]
       
    cursor = mycol.find({})
    for document in cursor:
        documents_list.append(document)
    
    for field in documents_list:
        vnfs_list.append(field['vnf']['vnf_id'])   
    client.close()    
    return vnfs_list

def drop_collection(db, collection):
    client = mongo_connect()
    mydb = client[db]
    collection_doc = mydb[collection].drop()
    client.close()