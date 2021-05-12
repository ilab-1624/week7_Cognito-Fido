import os
import copy
import time
import importlib
import mainConfig
import awsconfig
import boto3
import cv2
import threading
import json
from API.captureAPI import Capture


client = boto3.client('stepfunctions', aws_access_key_id=awsconfig.access_key, aws_secret_access_key=awsconfig.secret_access_key,region_name= awsconfig.region_name)


# global variable(s)...

frame = None

stremingtype= True


def stream():

    global frame
    while True:
        streamPort = 0
        videoSource = cv2.VideoCapture(streamPort)

        print("Streaming........")

        while stremingtype:
            try:
                if videoSource.isOpened():
                    ret, frame = videoSource.read()

                    if frame is not None:
                        Height , Width = frame.shape[:2]
                        scale = None
                        if Height/640 > Width/960:
                            scale = Height/640
                        else:
                            scale = Width/960

                        if mainConfig.local_config["system"] == 4:
                            image = cv2.line(frame.copy(), (640, 0), (640, 720), (0, 0, 255), 5)
                            image = cv2.resize(image, (int(Width/scale), int(Height/scale)), interpolation=cv2.INTER_CUBIC)
                        else:
                            image = cv2.resize(frame.copy(), (int(Width/scale), int(Height/scale)), interpolation=cv2.INTER_CUBIC)
                        cv2.imshow("CSI", image)
                    else:
                        print('frame is not ready')
                        cv2.waitKey(1000)
                        continue

                    cv2.waitKey(10)
                    if ret == False:
                        videoSource = cv2.VideoCapture(streamPort)
            except:
                print('Source video is unavailable! reconnecting ....')
                cv2.destroyAllWindows()

        cv2.destroyAllWindows()
        videoSource.release()
        print("Changing RTSP source!!")
        time.sleep(1)

streamingThread = threading.Thread(target = stream,daemon=True)
streamingThread.start()


def main():
    global stremingtype
    while True:

        agent = 'MaxAgent'

        while mainConfig.local_config["activation"]:

            print(mainConfig.local_config)

            if frame is not None:
                model = {}
                if mainConfig.local_config['system'] == 1:
                    awsARN = awsconfig.ARN_Object
                    model["frame"] = Capture().Frame(frame)
                    model["agent"] = agent
                elif mainConfig.local_config['system'] == 2:
                    awsARN = awsconfig.ARN_Signin
                    model["frame"] = Capture().Frame(frame)
                    model["agent"] = agent
                elif mainConfig.local_config['system'] == 3:
                    awsARN = awsconfig.ARN_PPE
                    model["frame"] = Capture().Frame(frame)
                    model["agent"] = agent        
                elif mainConfig.local_config['system'] == 4:
                    awsARN = awsconfig.ARN_Fraud
                    model = Capture().FrameFraud(frame)
                    model["agent"] = agent
                    model["site"]["s3Bucket"] = "ilab-entry01"
                    model["site"]["site"]= "IN"
                    model["site"]["stepFunctionActivateFreqency"] = mainConfig.local_config["stepFunctionActivateFreqency"]

                #print(model)
                response = client.start_execution(
                   stateMachineArn = awsARN,
                   input = json.dumps(model)
                )

                time.sleep(mainConfig.local_config['stepFunctionActivateFreqency'])

            else:
                print("No frame")

                time.sleep(1)

        print("system set to False")
        time.sleep(1)

if __name__ == '__main__':

    main()
 