import os
from dataclasses import dataclass
import datetime

import streamlit as st
import psycopg2
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Prompt:
    title: str
    prompt: str
    is_favorite: bool
    created_at: datetime.datetime = None
    updated_at: datetime.datetime = None

def setup_database():
    con = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS prompts (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            prompt TEXT NOT NULL,
            is_favorite BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.commit()
    return con, cur

def prompt_form(prompt=None):
    default = Prompt("", "", False) if prompt is None else prompt
    with st.form(key="prompt_form", clear_on_submit=True):
        title = st.text_input("Title", value=default.title)
        prompt_content = st.text_area("Prompt", height=200, value=default.prompt)
        is_favorite = st.checkbox("Favorite", value=default.is_favorite)

        submitted = st.form_submit_button("Submit")
        if submitted:
            if not title or not prompt_content:
                st.error('Please fill in both the title and prompt fields.')
                return
            return Prompt(title, prompt_content, is_favorite)

def toggle_favorite(cur, con, prompt_id, current_status):
    new_status = not current_status
    cur.execute(
        "UPDATE prompts SET is_favorite = %s WHERE id = %s",
        (new_status, prompt_id)
    )
    con.commit()

def search_prompts(cur, search_term=None, sort_order="created_at DESC", filter_favorites=False):
    base_query = "SELECT * FROM prompts"
    where_clauses = []
    query_params = []

    if search_term:
        where_clauses.append("(title ILIKE %s OR prompt ILIKE %s)")
        query_params.extend(['%' + search_term + '%', '%' + search_term + '%'])

    if filter_favorites:
        where_clauses.append("is_favorite = TRUE")

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " ORDER BY " + sort_order

    cur.execute(base_query, query_params)
    return cur.fetchall()



def display_prompts(cur, con):
    sort_options = {
        "Newest first": "created_at DESC",
        "Oldest first": "created_at ASC",
        "Title (A-Z)": "title ASC",
        "Title (Z-A)": "title DESC"
    }
    search_term = st.text_input('Search Prompts')
    sort_order = st.selectbox("Sort by", list(sort_options.keys()), index=0)
    filter_favorites = st.checkbox("Show only favorites")

    prompts = search_prompts(cur, search_term, sort_options[sort_order], filter_favorites)
    for p in prompts:
        title = p[1] + " 💜" if p[3] else p[1]
        with st.expander(title):
            st.code(p[2])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Toggle Favorite", key=f"fav-{p[0]}"):
                    toggle_favorite(cur, con, p[0], p[3])
                    st.experimental_rerun()
            with col2:
                if st.button("Delete", key=f"del-{p[0]}"):
                    cur.execute("DELETE FROM prompts WHERE id = %s", (p[0],))
                    con.commit()
                    st.experimental_rerun()



if __name__ == "__main__":
    st.title("PromptBase")
    st.subheader("A webapp for your favorite ChatGPT prompts 💌")

    con, cur = setup_database()

    new_prompt = prompt_form()
    if new_prompt:
        try: 
            cur.execute(
                "INSERT INTO prompts (title, prompt, is_favorite) VALUES (%s, %s, %s)",
                (new_prompt.title, new_prompt.prompt, new_prompt.is_favorite)
            )
            con.commit()
            st.success("Prompt added successfully!")
        except psycopg2.Error as e:
            st.error(f"Database error: {e}")

    display_prompts(cur, con)
    con.close()