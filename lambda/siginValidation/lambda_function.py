import json
from signinValidation import SigninValidate
import config

def lambda_handler(event, context):
    dataModel = event
    signinValidate =  SigninValidate(dataModel, config.aws_access_key_id, config.aws_secret_access_key, config.region_name, config.collectionId,config.table)
    signinValidate.query_config()
    signinValidate.storeImage()
    signinValidate.signinValidate()
    #signinValidate.facevalidate_redshift()
    
    return signinValidate.getModel()