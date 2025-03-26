import streamlit as st
import requests

st.title("🧑‍💻 Legacy Code Expert Chatbot")

user_query = st.text_input("Ask a question about the code:")

if user_query:
    response = requests.get("http://localhost:8000/query/", params={"user_question": user_query})
    
    if response.status_code == 200:
        st.write("### Answer:")
        st.write(response.json()["answer"])
    else:
        st.error(f"Error fetching response. Status code: {response.status_code}, Content: {response.text}")
