import streamlit as st

st.set_page_config(page_title="Employee Score Portal")

st.title("Employee Score Portal")

search = st.text_input("Search Employee")

if search:
    st.write(f"You searched for: {search}")
