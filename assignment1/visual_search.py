import os
import random
import time
import streamlit as st
from data_sources import FirebaseConnection
from descriptor import Descriptor
from retriever import Retriever

@st.cache_resource(show_spinner=False)
def load_data():
    firebase_conn = FirebaseConnection()
    bucket = firebase_conn.get_bucket()    
    # Directory in Firebase storage
    image_directory = "MSRC_ObjCategImageDatabase_v2/Images"
    # Create a local directory to store images
    local_image_dir = "MSRC_ObjCategImageDatabase_v2_local/Images"
    required_file_count = 591
    sleep_time = 1.5
    message, success = firebase_conn.check_local_dir(local_image_dir, required_file_count)
    if success:
        time.sleep(sleep_time)
        message.empty()
        return
    else:
        os.makedirs(local_image_dir, exist_ok=True)
        blobs = list(bucket.list_blobs(prefix=image_directory))
        status = firebase_conn.download_images(blobs, local_image_dir, max_download=required_file_count)
        time.sleep(sleep_time)
        status.empty()
    time.sleep(sleep_time)
    message.empty()

def init_session_state(image_files):
    if 'bins' not in st.session_state:
        st.session_state['bins'] = 32
    if 'selected_image' not in st.session_state:
        st.session_state['selected_image'] = image_files[0]
    if 'base' not in st.session_state:
        st.session_state['base'] = 256
    if 'metric' not in st.session_state:
        st.session_state['metric'] = "l2"
    if 'recompute' not in st.session_state:
        st.session_state['recompute'] = True

def update_metric():
    st.session_state['metric'] = st.session_state['metric_radio']

def update_bins():
    if st.session_state['bins'] != st.session_state['bins_slider']:
        st.session_state['bins'] = st.session_state['bins_slider']
        st.session_state['recompute'] = True
    else:
        st.session_state['recompute'] = False

def update_base():
    if st.session_state['base'] != st.session_state['base_slider']:
        st.session_state['base'] = st.session_state['base_slider']
        st.session_state['recompute'] = True
    else:
        st.session_state['recompute'] = False

def main():
    load_data()
    DATASET_FOLDER = "MSRC_ObjCategImageDatabase_v2_local"
    DESCRIPTOR_FOLDER = "descriptors"
    image_files = [f for f in os.listdir(os.path.join(DATASET_FOLDER, 'Images')) if f.endswith('.bmp')]
    init_session_state(image_files)
    
    # Section to choose the image and the descriptor
    st.title("Visual Search Engine 👀")
    cols = st.columns([1.75,1.75,1])
    selected_image = cols[0].selectbox(
        "Choose an Image...",
        image_files,
        index=image_files.index(st.session_state['selected_image']))
    
    metric = cols[0].radio(
        "Select Comparison Metric...",
        options=["l2", "l1"],
        index=["l2", "l1"].index(st.session_state['metric']),
        key="metric_radio",
        on_change=update_metric
    )

    # Choose the descriptor method
    descriptor_method = cols[1].selectbox(
        "Choose your Descriptor...",
        options=['rgb', 'random', 'globalRGBhisto'])
    
    if descriptor_method == "globalRGBhisto":
        cols[1].select_slider(
            "Select the number of bins...",
            options = [8, 16, 32, 64, 128, 256],
            value=32,
            key="bins_slider",
            on_change=update_bins)
    # TODO: fix globalRGencoding later
    # if descriptor_method == "globalRGBencoding":
    #     cols[1].select_slider(
    #         "Select the base for encoding...",
    #         options = [64, 128, 256],
    #         value=256,
    #         key="base_slider",
    #         on_change=update_base)
    
    if st.session_state['recompute']:
        # generate a new descriptor and set recompute back to false
        descriptor = Descriptor(
            DATASET_FOLDER,
            DESCRIPTOR_FOLDER,
            descriptor_method,
            bins=st.session_state['bins'],
            base=st.session_state['base'])
        st.session_state['recompute'] = False

    descriptor = Descriptor(
        DATASET_FOLDER,
        DESCRIPTOR_FOLDER,
        descriptor_method,
        bins=st.session_state['bins'],
        base=st.session_state['base'])
    descriptor.extract()
    img2descriptors = descriptor.get_image_descriptor_mapping()

    # Button to select a random image
    cols[2].markdown("<div style='width: 1px; height: 28px'></div>", unsafe_allow_html=True)
    if cols[2].button("I'm Feeling Lucky"):
        st.session_state['selected_image']  =  random.choice(image_files)
        selected_image = st.session_state['selected_image']
        st.rerun()
    
    # Section to display the query image and the top similar images

    st.write("Query Image:")
    st.image(os.path.join(DATASET_FOLDER, 'Images', selected_image), use_column_width=True)
    result_num = 10
    retriever = Retriever(img2descriptors, metric)
    similiar_images = retriever.retrieve(os.path.join(DATASET_FOLDER, 'Images', selected_image), number=result_num)
    st.write(f"Top {result_num} similar images:")
    cols = st.columns(result_num)
    for col, img_path in zip(cols, similiar_images):
        col.image(img_path, use_column_width=True)


if __name__ == "__main__":
    main()