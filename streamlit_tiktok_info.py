import requests
import re
from common import *
import pandas as pd
from utils import *
from Parallelizer import make_parallel
import streamlit as st
import streamlit as st
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
import yaml
import os
from dotenv import load_dotenv
load_dotenv()

with open('./config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)
print(config)
config['credentials']['usernames']["admin"]["password"] = os.getenv("ADMIN-PASSWORD")
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)


st.title("Tiktok Info")

@st.cache_data
def get_info(username):
    url = f"https://tokapi-mobile-version.p.rapidapi.com/v1/user/@{username}"

    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "tokapi-mobile-version.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers)

    return response.json()

@st.cache_data
def get_posts(user_id):
    url = f"https://tokapi-mobile-version.p.rapidapi.com/v1/post/user/{user_id}/posts"

    querystring = {"offset":"0","count":"10","region":"VN","with_pinned_posts":"1"}

    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "tokapi-mobile-version.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    return response.json()

def url2username(url):
    return re.search(r"tiktok.com/@(\w+)", url).group(1)

MAPPING_POST = {
    "share_url": ["share_url"],
    "create_time": ["create_time"],
}


@make_parallel
def post_transform(post):
    return Common.mapping_data(post, MAPPING_POST)


MAPPING = {
    "username": ["user","unique_id"],
    "follower": ["user","follower_count"],
    "bio_url": ["user","bio_url"],
    "bio": ["user","signature"],
    "sec_uid": ["user","sec_uid"],
    "has_shop": ["user","tab_settings","shop_tab","show_shop_tab"],
    "uid": ["user","uid"],
}


authenticator.login()
if st.session_state["authentication_status"]:

    links = st.text_area("Enter Tiktok links", "https://www.tiktok.com/@tiktok")
    if links and st.button("Get Info"):
        with st.spinner("Getting info..."):
            info_placeholder = st.empty()
            df_placeholder = st.empty()
            links = links.split("\n")
            results = []
            for link in links:
                username = url2username(link)
                info_placeholder.markdown(f"Getting info for **{username}**...")
                try:
                    info = get_info(username)
                    transformed = Common.mapping_data(info, MAPPING)
                    post_list = get_posts(transformed["uid"])
                    try:
                        post_list = post_list["aweme_list"]
                        post_list_transformed = post_transform(post_list)
                        latest_post = max(post_list_transformed, key=lambda x: x["create_time"])
                        if latest_post:
                            minimal_url = latest_post["share_url"].split("?")[0]
                            transformed["latest_post"] = minimal_url
                        results.append(transformed)
                    except Exception as e:
                        print(f"Error getting posts for {username}: {e}")
                        results.append(transformed | {"error": str(e)})
                except Exception as e:
                    print(f"Error getting info for {username}: {e}")
                    results.append({"username": username, "error": str(e)})
                df = pd.DataFrame(results)
                df["follower"] = df["follower"].apply(lambda x: big_number_to_string_number(x))
                df["other_url"] = df["bio"].apply(lambda x: extract_url(x) if x else None)
                df["url"] = df["username"].apply(lambda x: f"https://www.tiktok.com/@{x}")
                df["bio_url"] = df["bio_url"].apply(lambda x: x or "")
                df["bio"] = df["bio"] + df["bio_url"]
                cols = ["url","sec_uid","latest_post","follower","has_shop","bio"]
                df = df[cols]
                # df.to_csv("tiktok.csv", index=False)
                df_placeholder.write(df)
      
elif st.session_state["authentication_status"] is False:
    st.error('username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')