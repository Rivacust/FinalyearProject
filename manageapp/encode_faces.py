import cv2
import face_recognition
import pickle
import zipfile
import os
import numpy as np
from bson.binary import Binary
from .mongo_connect import client

def encode_and_store_images(zip_file_path, username):
    db_name = username
    if db_name not in client.list_database_names():
        raise Exception(f"Database '{db_name}' does not exist. Aborting.")

    db = client[db_name]
    collection = db['Image_info']

    # Load and process images from zip
    imgList = []
    Ids = []

    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                with zip_ref.open(file_name) as file:
                    file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
                    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    if img is not None:
                        imgList.append(img)
                        Ids.append(os.path.splitext(os.path.basename(file_name))[0])

    # Encode faces
    encodeList = []
    for img in imgList:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(img)
        if encodings:
            encodeList.append(encodings[0])

    encodeListKnownWithIds = [encodeList, Ids]

    # Convert to binary using pickle
    pickle_data = Binary(pickle.dumps(encodeListKnownWithIds))

    # Replace previous data if any
    collection.delete_many({})
    collection.insert_one({
        "pickle_data": pickle_data
    })

    print(f"Encodings saved to existing DB '{db_name}' in collection 'Image_info'.")
