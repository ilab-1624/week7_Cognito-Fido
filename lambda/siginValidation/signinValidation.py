import boto3
import base64
import copy
import psycopg2
from datetime import datetime
import json
import config
from cutImage import image_splite

class SigninValidate:
    def __init__(self, dataModel, aws_access_key_id, aws_secret_access_key, region_name, collectionId,table):
        self.__aws_access_key_id = aws_access_key_id
        self.__aws_secret_access_key = aws_secret_access_key
        self.__region_name = region_name
        self.__collectionId = collectionId
        self.__dataModel = dataModel
        self.__rekognitionS3Model = None
        self.__dynamoDbResource = boto3.resource(
            'dynamodb', 
            aws_access_key_id=self.__aws_access_key_id, 
            aws_secret_access_key=self.__aws_secret_access_key,
            region_name = self.__region_name
        )
        
        self.__table = self.__dynamoDbResource.Table(table)

    def signinValidate(self):
        image = self.__dataModel["frame"]["openCV"]["imageBase64"]
        self.__client = boto3.client('rekognition',aws_access_key_id=self.__aws_access_key_id, aws_secret_access_key=self.__aws_secret_access_key,region_name=self.__region_name)
        s3Client = boto3.client('s3', aws_access_key_id=self.__aws_access_key_id, aws_secret_access_key=self.__aws_secret_access_key,region_name=self.__region_name)
    
        body = s3Client.get_object(Bucket = config.sourceBucketName,Key = "rekognition.json")['Body']
        jsonString = body.read().decode('utf-8')
        self.__rekognitionS3Model = json.loads(jsonString) #{"imageData":[]}
        body.close()
        
        binaryImage = base64.b64decode(self.__dataModel["frame"]["openCV"]["imageBase64"])
        faceDetectResponse = self.__client.detect_faces(Image={'Bytes': binaryImage})
        print("faceDetectResponse")
        print(faceDetectResponse)
        try:
            threshold = self.__dataModel["config"]["memberRecognitionSimilarityThreshold"]
        except Exception as e:
            print(e)
            threshold = 80
        #self.__outputModel["signinValidation"]["personCount"] = len(faceDetectResponse["FaceDetails"])
        memberList = []
        personList = []
        faceImageUrlList = []
        faceIdList = []
        faceImageIdList = []
        similarityList = []
        registrationImageCount = 0
        registrationImageList = []
        matchedImageCounter = 0
        personIdCounter = len(faceDetectResponse["FaceDetails"])
        matchedImageCount = 0
        sumSimilarity = 0
        averageSimilarity = 0
        sourceBucketName = 'secomv3-source-images' #來自config
        #self.__dataModel["personList"] = []
        self.__dataModel["signInResult"] = {}
        self.__dataModel["signInResult"]["personList"] = []
        self.__dataModel["frame"]["personList"] = []
        self.__dataModel["frame"]["sourceImage"]["personCount"] = len(faceDetectResponse["FaceDetails"])
        if len(faceDetectResponse["FaceDetails"]) == 0:
            pass
        elif len(faceDetectResponse["FaceDetails"]) < 0:
            searchFaceResponse=self.__client.search_faces_by_image(CollectionId=self.__collectionId,
                                Image={'Bytes':binaryImage},
                                FaceMatchThreshold=threshold,
                                MaxFaces=3)
            print("----------------")
            #print(searchFaceResponse)
            print("----------------")
            if len(searchFaceResponse["FaceMatches"]) > 1:
                s3Response = s3Client.list_objects_v2(Bucket=config.faceBucketName,StartAfter="registration-faces/" + searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"])
                for face in s3Response["Contents"]:
                    try:
                        uid,faceImageId = face["Key"].split('_')[0],face["Key"].split('_')[1]
                        uid = uid.split('/')[1]
                        if uid == searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"]:
                            faceImageIdList.append(faceImageId)
                    except Exception as e:
                        print(e)
                print(faceImageIdList)
                
                registrationImageCount = len(faceImageIdList)
                for face in searchFaceResponse["FaceMatches"]:
                    print("faceup")
                    print(face)
                    print("facedown")
                    if face["Similarity"] > 70 and face["Face"]["FaceId"] in faceImageIdList:
                        registrationModel = {}
                        faceImageUrl = 'https://'+ config.faceBucketName +'.s3-' + self.__region_name + '.amazonaws.com/registration-faces/' + searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"] + '_' + face["Face"]["FaceId"]
                        faceImageUrlList.append(faceImageUrl)
                        faceIdList.append(face["Face"]["FaceId"])
                        similarityList.append(face["Similarity"])
                        sumSimilarity += face["Similarity"]
                        timestamp = 0
                        try:
                            timestamp = next(item for item in self.__rekognitionS3Model["imageData"] if item["faceId"] == face["Face"]["FaceId"])["timestamp"]
                        except StopIteration:
                                print("StopIteration stop")
                        registrationModel["imageUrl"] = faceImageUrl
                        registrationModel["faceId"] = face["Face"]["FaceId"]
                        registrationModel["similarity"] = face["Similarity"]
                        registrationModel["timestamp"] = timestamp
                        print(registrationModel)
                        print("M>L")
                        registrationImageList.append(registrationModel)
                        print(registrationImageList)
                    if searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"] not in memberList:
                        memberList.append(searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"])
                matchedImageCounter = len(memberList)
                fileName = self.__dataModel["frame"]["captureResult"]["id"]
                averageSimilarity = sumSimilarity / len(registrationImageList)
                personList={
                    "sourceFaceImage":{"imageUrl":self.__dataModel["frame"]["sourceImage"]["imageUrl"],
                    "averageSimilarity": averageSimilarity},
                    "registrationImageList":registrationImageList,

                }
                print("personlist")
                self.__dataModel["frame"]["personList"].append(personList)
                self.__dataModel["signInResult"]["personList"] = []
                self.__dataModel["signInResult"]["personList"].append({
                                                                        "isMember":True,
                                                                        "memberId":searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"],
                                                                        "registrationImageCount":len(faceImageIdList),
                                                                        "matchedImageCount":matchedImageCounter,
                                                                        "averageSimilarity":averageSimilarity
                                                                    })
            else:
                self.__dataModel["signInResult"]["personList"].append({
                                                                        "isMember":False
                                                                    })
            self.__dataModel["signInResult"]["personCount"] = personIdCounter
            self.__dataModel["signInResult"]["memberCount"] = matchedImageCounter
            self.__dataModel["signInResult"]["notMemberCount"] = personIdCounter - matchedImageCounter
            self.__dataModel["signInResult"]["timestamp"] = self.__dataModel["frame"]["captureResult"]["timestamp"]
                
        elif len(faceDetectResponse["FaceDetails"]) >= 1:
            faceBoundingBox = []
            for face in faceDetectResponse["FaceDetails"]:
                faceBoundingBox.append(face["BoundingBox"])
            binaryImage = base64.b64decode(image)
            faceImageList = image_splite(binaryImage,faceBoundingBox)
            faceImageUrlList = self.storeFaceImage(faceImageList)
            personIdCounter = len(faceDetectResponse["FaceDetails"])
            faceBoundingBoxIndex = 0
            serialNo = 0
            memberNo = 0
            for faceImage in faceImageList:
                searchFaceResponse=self.__client.search_faces_by_image(CollectionId=self.__collectionId,
                                    Image={'Bytes':faceImage},
                                    FaceMatchThreshold=threshold,
                                    MaxFaces=10)
                ###############################
                print(searchFaceResponse)
                ####################################
                personIdCounter = personIdCounter+1
                faceImageIdList = []
                personList = {}
                #fileName = ""
                matchedImageCounter = 0
                registrationImageList = []
                if len(searchFaceResponse["FaceMatches"]) !=0:
                    
                    personIdCounter = personIdCounter + 1
                    s3Response = s3Client.list_objects_v2(Bucket=config.faceBucketName,StartAfter="registration-faces/" + searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"])
                    print(s3Response)
                    print("print(s3Response)")
                    for face in s3Response["Contents"]:
                        try:
                            print(face)
                            uid,faceImageId = face["Key"].split('_')[0],face["Key"].split('_')[1]
                            uid = uid.split('/')[1]
                            print(uid)
                            print(searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"])
                            if uid == searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"]:
                                faceImageIdList.append(faceImageId)
                        except Exception as e:
                            print(e)
                    print(faceImageIdList)
                    
                    registrationImageCount = len(faceImageIdList)
                    registrationImageList = []
                    sumSimilarity = 0
                    for face in searchFaceResponse["FaceMatches"]:
                        print(face["Face"]["FaceId"])
                        if face["Similarity"] > 70 and face["Face"]["FaceId"] in faceImageIdList:
                            registrationModel = {}
                            #self.__outputModel["signinValidation"]["memberCount"] = 1
                            faceImageUrl = 'https://'+ config.faceBucketName +'.s3-' + self.__region_name + '.amazonaws.com/registration-faces/' + searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"] + '_' + face["Face"]["FaceId"]
                            faceImageUrlList.append(faceImageUrl)
                            faceIdList.append(face["Face"]["FaceId"])
                            similarityList.append(face["Similarity"])
                            sumSimilarity += face["Similarity"]
                            timestamp = 0
                            try:
                                timestamp = next(item for item in self.__rekognitionS3Model["imageData"] if item["faceId"] == face["Face"]["FaceId"])["timestamp"]
                            except StopIteration:
                                print("StopIteration stop")
                            
                            registrationModel["imageUrl"] = faceImageUrl #faceImageUrlList[serialNo]
                            registrationModel["faceId"] = face["Face"]["FaceId"]
                            registrationModel["confidence"] = searchFaceResponse["SearchedFaceConfidence"]
                            registrationModel["similarity"] = face["Similarity"]
                            registrationModel["timestamp"] = timestamp
                            registrationImageList.append(registrationModel)
                        if searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"] not in memberList:
                            memberList.append(searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"])
                        matchedImageCounter = len(searchFaceResponse["FaceMatches"])
                        
                        self.__dataModel["personCount"] = personIdCounter
                        
                        self.__dataModel["memberCount"] = matchedImageCounter
                        
                        self.__dataModel["notMemberCount"] = personIdCounter - matchedImageCounter
                        self.__dataModel["timestamp"] = self.__dataModel["frame"]["captureResult"]["timestamp"]
                    averageSimilarity = sumSimilarity / len(registrationImageList)    
                    self.__dataModel["signInResult"]["personList"].append({
                                                                            "isMember":True,
                                                                            "memberId":searchFaceResponse["FaceMatches"][0]["Face"]["ExternalImageId"],
                                                                            "registrationImageCount":len(faceImageIdList),
                                                                            "matchedImageCount":matchedImageCounter,
                                                                            "averageSimilarity":averageSimilarity
                                                                        })
                    
                    fileName = 'registration-faces/face' + str(self.__dataModel["frame"]["captureResult"]["timestamp"]) + str(serialNo)
                    serialNo += 1
                    memberNo += 1
                    personList={
                        "sourceFaceImage":{"imageUrl":'https://'+ config.faceBucketName +'.s3-' + self.__region_name + '.amazonaws.com/' + fileName,
                        "averageSimilarity": averageSimilarity},
                        "registrationImageList":registrationImageList,
                        }
                        
                    self.__dataModel["frame"]["personList"].append(personList)
                elif len(searchFaceResponse["FaceMatches"]) ==0:
                    
                    self.__dataModel["signInResult"]["personList"].append({
                                                                            "isMember":False
                                                                                })
                    serialNo += 1
                
                faceBoundingBoxIndex = faceBoundingBoxIndex + 1
                #serialNo += 1
            self.__dataModel["signInResult"]["personCount"] = len(faceDetectResponse["FaceDetails"])
            self.__dataModel["signInResult"]["memberCount"] = memberNo
            self.__dataModel["signInResult"]["notMemberCount"] = self.__dataModel["signInResult"]["personCount"] - self.__dataModel["signInResult"]["memberCount"]
            self.__dataModel["signInResult"]["timestamp"] = self.__dataModel["frame"]["captureResult"]["timestamp"]
            self.__dataModel["frame"]["sourceImage"]["personCount"] = len(faceDetectResponse["FaceDetails"])

    def storeFaceImage(self,imageList):
        s3Client = boto3.client('s3', aws_access_key_id=self.__aws_access_key_id, aws_secret_access_key=self.__aws_secret_access_key,region_name=self.__region_name)
        faceImageUrlList = []
        faceBucketName = config.faceBucketName
        serialNo = 0
        for image in imageList:
            #fileName = 'all-face-images/' + uid + '_' + faceId + '.jpg'
            fileName = 'registration-faces/face' + str(self.__dataModel["frame"]["captureResult"]["timestamp"]) + str(serialNo)
            response=s3Client.put_object(ACL='public-read',
                                    Body=image,
                                    Bucket=faceBucketName,
                                    Key=fileName,
                                    ContentEncoding='base64',
                                    ContentType='image/jpeg',)
            serialNo += 1
            faceImageUrlList.append('https://' + faceBucketName + '.s3-' + self.__region_name + '.amazonaws.com/' + fileName)
        return faceImageUrlList
    def storeImage(self):
        client = boto3.client('s3', aws_access_key_id=self.__aws_access_key_id, aws_secret_access_key=self.__aws_secret_access_key,region_name=self.__region_name)
        image = self.__dataModel['frame']["openCV"]["imageBase64"]
        image = base64.b64decode(image)
        fileName = self.__dataModel["frame"]["captureResult"]["id"]
        bucketName = ""
        sourceBucketName = "webapp-registeration-image"
        self.__dataModel["frame"]["sourceImage"] = {}
        self.__dataModel["frame"]["sourceImage"]["imageUrl"] = 'https://' + sourceBucketName + '.s3-' + self.__region_name + '.amazonaws.com/' + fileName
        self.__dataModel["frame"]["sourceImage"]["timestamp"] = self.__dataModel["frame"]["captureResult"]["timestamp"]
        client.put_object(ACL='public-read',Body=image, Bucket=sourceBucketName, Key=fileName ,ContentEncoding='base64',ContentType='image/jpeg')
        
    def query_config(self):
        response = self.__table.get_item(
            Key={
                'agent': self.__dataModel["agent"],
            }
        )

        item = response['Item']
        #print(item)
        aiConfig = item['aiApps']['faceRecognition']
        self.__dataModel["config"] = aiConfig
        #print(aiConfig)
        
    def getModel(self):
        print("getModel")
        self.__dataModel["frame"]["openCV"]["imageBase64"] = ""
        #try:
        print(self.__dataModel)
        """except Exception as e:
            print("line311")
            print(e)"""
        return self.__dataModel
        
