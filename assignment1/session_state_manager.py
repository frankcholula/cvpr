import streamlit as st
import logging
import os

logging.basicConfig(level=logging.INFO)


class SessionStateManager:
    def __init__(self, image_files):
        self.image_files = image_files
        self.init_session_state()

    def init_session_state(self):
        if "bins" not in st.session_state:
            st.session_state["bins"] = 32
        if "selected_image" not in st.session_state:
            st.session_state["selected_image"] = self.image_files[0]
        if "quant_lvl" not in st.session_state:
            st.session_state["quant_lvl"] = 8
        if "metric" not in st.session_state:
            st.session_state["metric"] = "l2"
        if "recompute" not in st.session_state:
            st.session_state["recompute"] = True
        if "descriptor" not in st.session_state:
            st.session_state["descriptor"] = "globalRGBhisto_quant"
        if "result_num" not in st.session_state:
            st.session_state["result_num"] = 5
        if "grid_size" not in st.session_state:
            st.session_state["grid_size"] = 4
        if "sobel_filter_size" not in st.session_state:
            st.session_state["sobel_filter_size"] = 3

    def update_metric(self):
        st.session_state["metric"] = st.session_state["metric_radio"]

    def update_bins(self):
        if st.session_state["bins"] != st.session_state["bins_slider"]:
            st.session_state["bins"] = st.session_state["bins_slider"]
            st.session_state["recompute"] = True
        else:
            self.update_recompute(False)

    def update_quant(self):
        if st.session_state["quant_lvl"] != st.session_state["quant_slider"]:
            st.session_state["quant_lvl"] = st.session_state["quant_slider"]
            st.session_state["recompute"] = True
        else:
            self.update_recompute(False)

    def update_descriptor(self):
        if st.session_state["descriptor"] != st.session_state["descriptor_selectbox"]:
            logging.info(
                f"Updating descriptor to {st.session_state['descriptor_selectbox']}"
            )
            st.session_state["descriptor"] = st.session_state["descriptor_selectbox"]
            # TODO: fix the path here
            if os.path.exists(f"descriptors/{st.session_state['descriptor']}"):
                self.update_recompute(False)
            else:
                self.update_recompute(True)
        else:
            self.update_recompute(False)

    def update_result_num(self):
        st.session_state["result_num"] = st.session_state["result_num_slider"]

    def update_grid_size(self):
        st.session_state["grid_size"] = st.session_state["grid_slider"]
        self.update_recompute(True)

    def update_sobel_filter_size(self):
        st.session_state["sobel_filter_size"] = st.session_state["sobel_filter_slider"]
        self.update_recompute(True)

    def update_recompute(self, recompute: bool):
        st.session_state["recompute"] = recompute