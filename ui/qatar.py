import streamlit as st

def render():
    return st.number_input("Enter Page Number:", min_value=1, value=1)
