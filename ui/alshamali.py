import streamlit as st
from alShamali.main import get_all_brands

def render():
    alshamali_brands = get_all_brands()
    if not alshamali_brands:
        st.warning("No brands found.")
        return None, None

    st.write("### Select Brands")
    
    num_columns = 4
    cols = st.columns(num_columns)
    selected_brands = []
    for i, brand in enumerate(alshamali_brands):
        with cols[i % num_columns]:
            if st.checkbox(brand.get("title"), key=brand.get("link")):
                selected_brands.append(brand)

    if not selected_brands:
        st.info("Please select at least one brand to continue.")
        return [], None

    if len(selected_brands) > 1:
        st.write("---")
        st.write("### Output Options")
        output_option = st.radio(
            "How would you like the output?",
            ('Combine into a single data table', 'Save each brand to a separate file and show summary'),
            index=0,
            key='alshamali_output_option'
        )

        return selected_brands, output_option
    else:
        return selected_brands, 'Combine into a single data table'