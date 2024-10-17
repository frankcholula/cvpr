import cv2
import numpy as np
import os
from extractors import Extractors
from matplotlib import pyplot as plt
from typing import Dict, List, Tuple
import random
import streamlit as st
from data_sources import FirebaseConnection
import time

class DescriptorExtractor:
    def __init__(self, dataset_folder: str, descriptor_folder: str, extract_method: str, **kwargs):
        self.DATASET_FOLDER = dataset_folder
        self.DESCRIPTOR_FOLDER = descriptor_folder
        self.extract_method = extract_method
        self.AVAILABLE_EXTRACTORS = {
            'rgb': {
                'path': os.path.join(self.DESCRIPTOR_FOLDER, 'rgb'),
                'method': Extractors.extract_rgb
            },
            'random': {
                'path': os.path.join(self.DESCRIPTOR_FOLDER, 'random'),
                'method': Extractors.extract_random
            },
            'globalRGBhisto': {
                'path': os.path.join(self.DESCRIPTOR_FOLDER, 'globalRGBhisto'),
                'method': lambda img: Extractors.extract_globalRGBhisto(img, bins = kwargs.get('bins'))
            }
        }

    def extract(self, recompute=False):
        if self.extract_method not in self.AVAILABLE_EXTRACTORS:
            raise ValueError(f"Invalid extract_method: {self.extract_method}")

        descriptor_path = self.AVAILABLE_EXTRACTORS[self.extract_method]['path']
        if not os.path.exists(descriptor_path) or recompute:
            # compute the descriptors if they don't exist, otherwise load them
            os.makedirs(descriptor_path, exist_ok=True)
            for filename in os.listdir(os.path.join(self.DATASET_FOLDER, 'Images')):
                if filename.endswith(".bmp"):
                    img_path = os.path.join(self.DATASET_FOLDER, 'Images', filename)
                    img = cv2.imread(img_path).astype(np.float64) / 255.0  # Normalize the image
                    fout = os.path.join(descriptor_path, filename).replace('.bmp', '.npy')
                    F = self.AVAILABLE_EXTRACTORS[self.extract_method]['method'](img)
                    np.save(fout, F)


    def get_image_descriptor_mapping(self) -> Dict[str, np.ndarray]:
        descriptor_path = os.path.join(self.DESCRIPTOR_FOLDER, self.extract_method)
        img_to_descriptor = {}
        for filename in os.listdir(descriptor_path):
            if filename.endswith('.npy'):
                img_path = os.path.join(self.DATASET_FOLDER, 'Images', filename.replace('.npy', '.bmp'))
                descriptor_data = np.load(os.path.join(descriptor_path, filename))
                img_to_descriptor[img_path] = descriptor_data
        return img_to_descriptor
    
class ImageRetriever:
    def __init__(self, img_desc_dict: Dict[str, np.ndarray]):
        self.img_desc_dict = img_desc_dict

    def cvpr_compare(self, F1, F2, metric) -> float:
        # This function should compare F1 to F2 - i.e. compute the distance
        # between the two descriptors
        match metric:
            case "l2":
                dst = np.linalg.norm(F1 - F2)
            case "l1":
                dst = np.linalg.norm(F1 - F2, ord=1)
        return dst

    def compute_distance(self, query_img: str, metric="l2") -> List[Tuple[float, str]]:
        # Compute the distance between the query and all other descriptors
        dst = []
        query_img_desc = self.img_desc_dict[query_img]
        
        for img_path, candidate_desc in self.img_desc_dict.items():
            if img_path != query_img:  # Skip the query image itself
                distance = self.cvpr_compare(query_img_desc, candidate_desc, metric)
                dst.append((distance, img_path))
        
        dst.sort(key=lambda x: x[0])
        return dst

    def retrieve(self, query_img: str, number: int = 10) -> list:
        # Compute distances
        distances = self.compute_distance(query_img)
        top_similar_images = distances[:number]
        ImageRetriever.display_images(query_img, top_similar_images, number)
        return [img_path for _, img_path in top_similar_images]

    @staticmethod
    def display_images(query_img: str, top_similar_images: list, number: int):
        fig, axes = plt.subplots(1, number + 1, figsize=(20, 5))
        distances = []
        # Display the query image
        query_img_data = cv2.imread(query_img)
        query_img_data = cv2.cvtColor(query_img_data, cv2.COLOR_BGR2RGB)
        axes[0].imshow(query_img_data)
        axes[0].set_title('Query Image')
        axes[0].axis('off')
        
        # Display the top similar images
        for ax, (distance, img_path) in zip(axes[1:], top_similar_images):
            img = cv2.imread(img_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            ax.imshow(img)
            ax.axis('off')
            distances.append(distance)
        plt.show()
        print("Distances: \n", distances)



@st.cache_resource(show_spinner=False)
def load_data():
    firebase_conn = FirebaseConnection()
    bucket = firebase_conn.get_bucket()    
    # Directory in Firebase storage
    image_directory = "MSRC_ObjCategImageDatabase_v2/Images"
    # Create a local directory to store images
    local_image_dir = "MSRC_ObjCategImageDatabase_v2_local/Images"
    required_file_count = 591
    message, success = firebase_conn.check_local_dir(local_image_dir, required_file_count)
    if success:
        time.sleep(2)
        message.empty()
        return
    else:
        os.makedirs(local_image_dir, exist_ok=True)
        blobs = list(bucket.list_blobs(prefix=image_directory))
        status = firebase_conn.download_images(blobs, local_image_dir, max_download=required_file_count)
        time.sleep(2)
        status.empty()
    time.sleep(2)
    message.empty()


def main():
    load_data()
    DATASET_FOLDER = "MSRC_ObjCategImageDatabase_v2_local"
    DESCRIPTOR_FOLDER = "descriptors"
    st.title("Visual Search Engine 👀")
    image_files = [f for f in os.listdir(os.path.join(DATASET_FOLDER, 'Images')) if f.endswith('.bmp')]
    
    # Section to select the image and descriptor method
    RECOMPUTE = False
    if 'bins' not in st.session_state:
        st.session_state['bins'] = 32
    cols = st.columns([1.75,1.75,1])
    selected_image = cols[0].selectbox("Choose an Image...", image_files)
    # TODO: add more descriptors here
    descriptor_method = cols[1].selectbox("Choose your Descriptor...", options=['rgb', 'globalRGBhisto', 'random'])
    if descriptor_method == "globalRGBhisto":
        bins = cols[1].select_slider("Select the number of bins...", options = [16, 32, 64, 128, 256], value=32)
        if bins != st.session_state['bins']:
            st.session_state['bins'] = bins
            RECOMPUTE = True
    
    extractor = DescriptorExtractor(DATASET_FOLDER, DESCRIPTOR_FOLDER, descriptor_method, bins=bins)
    extractor.extract(RECOMPUTE)
    img2descriptors = extractor.get_image_descriptor_mapping()

    cols[2].markdown("<div style='width: 1px; height: 28px'></div>", unsafe_allow_html=True)
    if cols[2].button("I'm Feeling Lucky"):
        selected_image = random.choice(image_files)
    

    # Section to display the query image and the top similar images
    st.write("Query Image:")
    st.image(os.path.join(DATASET_FOLDER, 'Images', selected_image), use_column_width=True)
    result_num = 10
    retriever = ImageRetriever(img2descriptors)
    similiar_images = retriever.retrieve(os.path.join(DATASET_FOLDER, 'Images', selected_image), number=result_num)
    st.write("Top {} similar images:".format(result_num))
    cols = st.columns(result_num)
    for col, img_path in zip(cols, similiar_images):
        col.image(img_path, use_column_width=True)

if __name__ == "__main__":
    main()