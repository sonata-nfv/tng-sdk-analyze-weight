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

import pandas as pd
import requests
import os
import json
import database.db_connect as mongo_db
import methods.main_methods as meth
import logmatic
import logging
from classes.JsonEncoder import JSONEncoder as json_enc
from flask import Flask,request,render_template,Response
from fileinput import filename

app = Flask(__name__)

UPLOAD_DADA_FOLDER = 'data'

logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(logmatic.JsonFormatter(extra={"hostname":"tng-sdk-analysis-weight"}))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Create a URL route in our application for "/"
@app.route('/tng-sdk-analysis-weight/api/weight/v1')
def home():
    logger.info("Logging home end point")
    return render_template('home.html')

@app.route('/tng-sdk-analysis-weight/api/weight/v1/train', methods=['GET'])
def train():
    logger.warning("Logging training end point")
    mongo_db.drop_collection("tng-sdk-analysis-weight", "dictionaries")
    logger.info("Call in mongo container")
    for root, dirs, files in os.walk(UPLOAD_DADA_FOLDER):
        for filename in files:        
            d = pd.read_csv(UPLOAD_DADA_FOLDER+"/"+filename, index_col=0)
            df = pd.DataFrame(data = d)
            result = meth.get_top_abs_correlations(df, 5) 
            json_result = json.loads(result)            
            vnf_name = {"vnf_id":filename[:-4]}            
            json_result['schema'] = vnf_name
            json_result['vnf'] = json_result.pop('schema')
            json_result['correlations'] = json_result.pop('data')                      
            mongo_db.insert_docs("tng-sdk-analysis-weight", "dictionaries", json_result)
    logger.info("Training Finished succesfully")
    response = "{'response':'Training was successful. Correlation dictionaries were updated'}"
    return Response(json.dumps(response),  mimetype='application/json')
     
@app.route('/tng-sdk-analysis-weight/api/weight/v1/<ns_uuid>', methods=['GET'])
def correlation(ns_uuid):
    logger.warning("Logging get weights for a NS")
    dictionaries = list()
    unknown_vnfs_list = list()
    http_code = meth.get_http_code(ns_uuid)
    if http_code == 200:
        logger.info("Call to the Catalogue", extra={"http_code": http_code})
        nsd = meth.get_ns(ns_uuid)
        vnfs = meth.extract_vnfs(nsd)
        logger.info("Extract VNFs from the NS")
        dictionaries = mongo_db.get_documents("tng-sdk-analysis-weight", "dictionaries",vnfs)
        known_vnfs = mongo_db.get_known_vnfs("tng-sdk-analysis-weight", "dictionaries",vnfs)
        if len(dictionaries) == 0:
            response = "{'response':'The provided VNFs are currently unknown. Try again later'}"   
            mongo_db.add_to_unknown("tng-sdk-analysis-weight", "unknown_vnfs", vnfs)
            logger.info("Unknown VNFs added to collection")            
            return Response(json.dumps(response),  mimetype='application/json')
        if len(dictionaries) > 0 and len(dictionaries) < len(vnfs):
            for vnf in vnfs:
                if vnf not in known_vnfs:
                    unknown_vnfs_list.append(vnf)
            mongo_db.add_to_unknown("tng-sdk-analysis-weight", "unknown_vnfs", unknown_vnfs_list) 
        logger.info("Return weigth for provided NS")                                    
        return Response(json_enc().encode(dictionaries),  mimetype='application/json')        
    else:
        logger.error("error", extra={"http_code": http_code})
    return ""
         
@app.route('/tng-sdk-analysis-weight/api/weight/v1/train/new/vnf/<vnf_type>', methods=['GET','POST'])
def consume_train_data(vnf_type):
    logger.warning("Logging upload dataset for train a VNF")
    file = request.files['file']
    file_name = file.filename
    file_validity = meth.file_validator(file_name)
    file_exist = meth.get_file(file_name)
    if (file_validity == True and file_exist == False and mongo_db.not_in_db("tng-sdk-analysis-weight", "dictionaries", vnf_type) == True):
        file.save(os.path.join(UPLOAD_DADA_FOLDER, file_name))
        logger.info("File validated and uploaded")
        meth.train_vnf(vnf_type, file_name)
        logger.info("Training for provided VNF started")
        response = "{'response':'File was successfully uploaded. Train started '}"
        return Response(json.dumps(response),  mimetype='application/json')
    if (file_validity == False ):
        response = "{'response':'There was an error with the file.','error': 'File not .csv'}"  
        return Response(json.dumps(response),  mimetype='application/json')  
    if (file_exist == True ):
        response = "{'response':'There was an error with the file.','error': 'File already exists'}"  
        return Response(json.dumps(response),  mimetype='application/json')  
    if (mongo_db.not_in_db("tng-sdk-analysis-weight", "dictionaries", vnf_type) == False ):
        response = "{'response':'There was an error with the vnf type.','error': 'Vnf type already exists'}"  
        return Response(json.dumps(response),  mimetype='application/json')
    logger.error("")
    return 

@app.route('/tng-sdk-analysis-weight/api/weight/v1/vnftype', methods=['GET'])
def correlated_vnf():
    logger.warning("Logging get weights for a VNF type")
    unknown_vnfs_list = list()
    logger.info("Retrieve unknown VNFs")
    provided_vnfs = request.args.get('vnf_type')
    vnfs_list = provided_vnfs.split(',')
    dictionaries = mongo_db.get_documents("tng-sdk-analysis-weight", "dictionaries",vnfs_list)
    known_vnfs = mongo_db.get_known_vnfs("tng-sdk-analysis-weight", "dictionaries",vnfs_list)
    if len(dictionaries) == 0:
        response = "{'response':'The provided VNFs are currently unknown. Try again later'}"   
        mongo_db.add_to_unknown("tng-sdk-analysis-weight", "unknown_vnfs", vnfs_list)            
        return Response(json.dumps(response),  mimetype='application/json')
    if len(dictionaries) > 0 and len(dictionaries) < len(vnfs_list):        
        for vnf in vnfs_list:
            if vnf not in known_vnfs:
                unknown_vnfs_list.append(vnf)
        mongo_db.add_to_unknown("tng-sdk-analysis-weight", "unknown_vnfs", unknown_vnfs_list)
    logger.info("Weights for provided VNFs retrieved")
    return Response(json_enc().encode(dictionaries),  mimetype='application/json')

@app.route('/tng-sdk-analysis-weight/api/weight/v1/mgmt/knownvnfs', methods=['GET'])
def vnf_dictionaries():
    logger.warning("Logging get supported VNF types")
    response = mongo_db.get_supported_vnfs("tng-sdk-analysis-weight", "dictionaries")
    logger.info("Supported VNFs retrieved")
    return Response(json.dumps(response),  mimetype='application/json')  
 
app.run(host='0.0.0.0', port=8082, debug=True)