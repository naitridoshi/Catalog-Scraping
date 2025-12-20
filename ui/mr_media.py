import streamlit as st
import asyncio
from MrMedia.main import get_all_categories

def render():
    all_categories = asyncio.run(get_all_categories())
    if not all_categories:
        st.warning("No categories found for Mr. Media.")
        return [], None

    st.write("### Select Categories")
    
    num_columns = 4
    cols = st.columns(num_columns)
    selected_categories = []
    
    for i, category in enumerate(all_categories):
        with cols[i % num_columns]:
            name = category.get("name")
            link = category.get("link")
            if st.checkbox(name, key=link):
                selected_categories.append(category)

    if not selected_categories:
        st.info("Please select at least one category to continue.")
        return [], None

    if len(selected_categories) > 1:
        st.write("---")
        st.write("### Output Options")
        output_option = st.radio(
            "How would you like the output?",
            ('Combine into a single data table', 'Save each category to a separate file and show summary'),
            index=0,
            key='mr_media_output_option'
        )
        return selected_categories, output_option
    else:
        return selected_categories, 'Combine into a single data table'
