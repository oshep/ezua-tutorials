# Import necessary libraries
import streamlit as st
from PIL import Image
# import tensorflow as tf
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from tensorflow import keras
import pandas as pd
import numpy as np
import boto3
from datetime import datetime
import urllib3
import os


# turn off InsecureRequestWarning
urllib3.disable_warnings()


failover_mode = False
streamlit_title = "Ezmeral Unified Analytics Demo"

# Set up S3 credentials - primary S3 Minio endpoint
AWS_ACCESS_KEY = 'minioadmin'
AWS_SECRET_KEY = 'minioadmin'
BUCKET_NAME = 'ezaf-demo'
S3_ENDPOINT_URL = 'https://objectstore-zone1-svc.dataplatform.svc.cluster.local:9000'
S3_PATH = 'new/'
S3_DOWNLOADPATH = '/'
S3_FILE = 'ctc-model.h5'
LOCAL_FILE_PATH = 'ctc-model.h5'

# Failover S3 credentials - in case of a failure of the primary S3 endpoint
AWS_ACCESS_KEY_FAILOVER = '3saJRSVoNaj8O8A2RqeS'
AWS_SECRET_KEY_FAILOVER = 'vPIRwuOl6LWWz2gszwgl5y3VLczEmvagyUzxfDh4'
BUCKET_NAME_FAILOVER = 'ezaf-demo'
S3_ENDPOINT_URL_FAILOVER = 'https://minioapi.mydirk.de'
S3_PATH_FAILOVER = 'new/'
S3_DOWNLOADPATH_FAILOVER = '/'
S3_FILE_FAILOVER = 'ctc-model.h5'
LOCAL_FILE_PATH_FAILOVER = 'ctc-model.h5'

# Set up S3 client with ezua credentials
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    endpoint_url=S3_ENDPOINT_URL,
    verify=False  # Disable SSL certificate verification
)

if os.path.exists(LOCAL_FILE_PATH):
    print("Loading model from local file system...")
    model = keras.models.load_model(LOCAL_FILE_PATH)
else:
    try:
        print("Downloading model from S3..")
        s3.download_file(BUCKET_NAME, S3_DOWNLOADPATH+S3_FILE, LOCAL_FILE_PATH)
        model = keras.models.load_model('ctcModel.h5')
    except Exception as e:
        print(f"Error downloading file: {e}")
        print("FAILOVERMODE enabled: Downloading model from failover S3...")
        failover_mode = True
        streamlit_title = streamlit_title + " - FAILOVERMODE"
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_FAILOVER,
            aws_secret_access_key=AWS_SECRET_KEY_FAILOVER,
            endpoint_url=S3_ENDPOINT_URL_FAILOVER,
            verify=False  # Disable SSL certificate verification
        )
        s3.download_file(BUCKET_NAME_FAILOVER, S3_DOWNLOADPATH_FAILOVER+S3_FILE_FAILOVER, LOCAL_FILE_PATH_FAILOVER)
        model = keras.models.load_model('ctcModel.h5')


# Define the class labels
classes = ['ezmeral coupon', 'garden hose', 'hammer', 'ice remover spray', 'masking tape', 'meter',
           'paint', 'paintbrush', 'square board', 'steel nail']


# add logo
def add_logo(logo_path, width, height):
    """Read and return a resized logo"""
    logo = Image.open(logo_path)
    modified_logo = logo.resize((width, height))
    return modified_logo

# Define the function that predicts the class label of an input image
def predict(image):
    # Preprocess the image
    image = image.resize((224, 224))
    image = img_to_array(image)
    image = np.expand_dims(image, axis=0)
    image = image / 255


    # Make a prediction
    prediction = model.predict(image)
    prediction = np.argmax(prediction, axis=1)
    prediction = classes[prediction[0]]

    return prediction

# make any grid with a function
def make_grid(cols,rows):
    grid = [0]*cols
    for i in range(cols):
        with st.container():
            grid[i] = st.columns(rows, gap="small")
    return grid


def append_row(df, row):
    return pd.concat([
                df, 
                pd.DataFrame([row], columns=row.index)]
           ).reset_index(drop=True)

def query_presto(product):
    # to be developed this is a quick tweak
    #
    # this is a placeholder for the presto query!
    price=['0.91', '0.27', '1.67', '0.68', '3.28', '1.38',
           '0.98', '2.69', '1.58', '0.65', '0.98', '2.06', '-50%',
           '0.67', '0.90', '4.01', '0.31', '0.56', '0.68', '1.88', '0.88', 
           '0.62', '0.88', '1.32', '1.64', '1.42', '1.84', '1.32', '1.33', 
           '1.28', '2.54', '5.12', '1.33', '1.42', '0.29', '1.48', '6.23']   
    return price[classes.index(product)] 

def upload_file_to_s3(bucket_name, file_path):

    # s3 = boto3.client('s3')
    
    # Get the current date and time
    current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # Extract the filename from the file path
    file_name = file_path.split('/')[-1]
    
    # Append the date and time suffix to the filename
    new_file_name = f"{current_datetime}_{file_name}"
    
    try:
        # Upload the file to the S3 bucket
        s3.upload_file(file_path, bucket_name, S3_PATH+ new_file_name)
        print("File uploaded successfully!")
    except Exception as e:
        print(f"Error uploading file: {e}")
        try:
            print("FAILOVERMODE enabled: Uploading model to failover S3...")
            s3 = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_FAILOVER,
                aws_secret_access_key=AWS_SECRET_KEY_FAILOVER,
                endpoint_url=S3_ENDPOINT_URL_FAILOVER,
                verify=False  # Disable SSL certificate verification
            )
            s3.upload_file(file_path, BUCKET_NAME_FAILOVER, S3_PATH_FAILOVER+ new_file_name)
            print("File uploaded successfully!")
        except Exception as e:
            print(f"Error uploading file: {e}")
        

def app():
    file_name='/root/data.csv' 
    price = 0

    if "load_state" not in st.session_state:

        # Download the file once
        st.session_state.load_state = False
        st.session_state['price'] = 0
        df = pd.DataFrame(columns=('Amount', 'Product', 'price'))
        df.to_csv(file_name, encoding='utf-8', index=False)
    else:
        df=pd.read_csv('data.csv')
        price=st.session_state['price']  
 

    st.set_page_config(           
        page_title=streamlit_title,
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={
            'Get Help': 'https://help.mydirk.de',
            'Report a bug': "https://bug.mydirk.de",
            'About': "Ezmeral Unfied Analytics Demo. Do not hesitate to contact me: dirk.derichsweiler@hpe.com"
        }
    )

    # Hide mainmenu and footer
     #               #MainMenu {visibility: hidden;}
    hide_streamlit_style = """
                <style>
                footer {visibility: hidden;}
                </style>
                """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)


    image=Image.open('hpelogo.png')
    headline = make_grid(1,4)       
    with headline[0][3]:
        st.image(image, width=300)
    with headline[0][0]:
        st.title(streamlit_title)
    st.write('This app is to demonstrate the use of HPE Ezmeral Unified Analytics Software for image classification and is using EzPresto to get the required data fields from the privous created datasets.')
    st.divider()
    grid = make_grid(3,3)
    with grid[0][2]:
        placeholder = st.empty()
        placeholder.data_editor(df,use_container_width=True)
    with grid[2][2]:             
        placeholder_price = st.empty()        
        total = df['price'].sum()
        total = "{:.2f}".format(total)
        placeholder_price.title(str("Total: " + str(total) + " USD"))

    st.divider()

    #take_photo = grid[0][0].back_camera_input("live camera feed", label_visibility="collapsed", key="camera-1")
    take_photo = grid[0][0].camera_input("Take a picture")

    if take_photo is not None:
        image = Image.open(take_photo)
        grid[0][1].image(image, caption='Uploaded image', use_column_width=True)

        image.convert('RGB')
        image.save('image.jpg', format='JPEG', quality=90)

        prediction = predict(image)

        # st.divider()
        if prediction != 'ezmeral coupon':

            st.metric(label="EZSQL Query (Presto)", value='SELECT price FROM tools WHERE tool = "' + prediction + '"')
            
            price = query_presto(prediction)
            #st.session_state['price']  = st.session_state['price']  + price
            st.metric(label="SQL Return (Value in USD)", value=price)


            new_row = pd.Series({'Amount':'1', 'Product':prediction, 'price': float(price)})  
            df = append_row(df, new_row) 
            df.to_csv(file_name, encoding='utf-8', index=False)

            with grid[0][2]:
                placeholder.data_editor(df,use_container_width=True)

            with grid[2][2]: 
                total = df['price'].sum()
                total = "{:.2f}".format(total)
                placeholder_price.title(str("Total: " + str(total) + " USD"))

            upload_file_to_s3(BUCKET_NAME,'image.jpg')

        else:
            st.title("You found the coupon!!!   You get 50% discount!!!!")
            with grid[2][2]: 
                total_new = float(total) * 0.5
                total_new = "{:.2f}".format(total_new)
                placeholder_price.title(str("reduced price: " + str(total_new) + " USD"))
            upload_file_to_s3(BUCKET_NAME,'image.jpg')

           

# Run the app
if __name__ == '__main__':
    app()
