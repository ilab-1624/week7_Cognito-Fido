import boto3
import cv2
import base64
import copy

aws_access_key_id = ''                          # please fill your aws_access_key_id
aws_secret_access_key = ''                      # please fill your aws_secret_access_key
collection_id = 'ai-bigdata-system-collection'    # please fill your aws_secret_access_key

client = boto3.client(
    'rekognition',
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key,
    region_name = 'us-west-2'
)

def create_collection(collection_id):

    #Create a collection
    print('Creating collection:' + collection_id)
    response=client.create_collection(CollectionId=collection_id)
    print('Collection ARN: ' + response['CollectionArn'])
    print('Status code: ' + str(response['StatusCode']))
    print('Done...')

def delete_face_data(faceId):
    faceIdList = [faceId]
    response=client.delete_faces(CollectionId=collection_id,
                              FaceIds=faceIdList)
    successfully=""
    if len(response['DeletedFaces'])==0:
        successfully = 'fail'
    else:
        successfully = 'success'
   
    return print(successfully)

def list_face_data():
    maxResults=10
    faces_count=0
    emptyDict = {}
    faceDataList = []
    tokens=True
    response=client.list_faces(CollectionId=collection_id,
                                MaxResults=maxResults)
    while tokens:
        faces=response['Faces']
        for face in faces:
            # print (face)
            faceData = copy.deepcopy(emptyDict)
            faceData["faceId"] = face["FaceId"]
            #faceData["name"] = face["ExternalImageId"]
            faceDataList.append(faceData)
            faces_count+=1
        if 'NextToken' in response:
            nextToken=response['NextToken']
            response=client.list_faces(CollectionId=collection_id,
                                        NextToken=nextToken,MaxResults=maxResults)
        else:
            tokens=False

    print(faceDataList)
    return faceDataList

def main():
    create_collection(collection_id)
    #delete_collection(collection_id)
    list_face_data()
    
if __name__ == "__main__":
    main()
