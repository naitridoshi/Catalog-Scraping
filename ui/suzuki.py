import streamlit as st
from suzuki.main import get_all_models

def render():
    all_models = get_all_models()
    if not all_models:
        st.warning("No models found for Suzuki.")
        return [], None

    st.write("### Select Models")
    
    num_columns = 4
    cols = st.columns(num_columns)
    selected_models = []
    
    for i, (model_name, model_value) in enumerate(sorted(all_models.items())):
        with cols[i % num_columns]:
            if st.checkbox(model_name, key=model_value):
                selected_models.append({"model_name": model_name, "model_id": model_value})

    if not selected_models:
        st.info("Please select at least one model to continue.")
        return [], None

    if len(selected_models) > 1:
        st.write("---")
        st.write("### Output Options")
        output_option = st.radio(
            "How would you like the output?",
            ('Combine into a single data table', 'Save each model to a separate file and show summary'),
            index=0,
            key='suzuki_output_option'
        )
        return selected_models, output_option
    else:
        return selected_models, 'Combine into a single data table'