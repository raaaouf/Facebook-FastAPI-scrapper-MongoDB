import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure
import facebook
import json
from bson.json_util import dumps
from dotenv import load_dotenv

load_dotenv()

FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')
MONGO_URI = os.environ.get('MONGO_URI')

if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET or not MONGO_URI:
    raise ValueError('FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, and MONGO_URI environment variables must be set')

graph = facebook.GraphAPI(access_token=FACEBOOK_APP_ID + '|' + FACEBOOK_APP_SECRET, version="3.0")

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/scrape_page/{page_id}")
async def scrape_page(page_id: str):
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
        db = db_client['facebook']
        posts_collection = db['posts']
        reactions_collection = db['reactions']

        # Retrieve posts for the given page
        posts = graph.get_connections(page_id, 'posts')

        while True:
            try:
                # Attempt to retrieve more pages of results
                for post in posts['data']:
                    # Add the post to the database
                    post_id = posts_collection.insert_one(post).inserted_id

                    # Retrieve reactions for the post
                    reactions = graph.get_connections(post['id'], 'reactions')

                    # Add the reactions to the database
                    for reaction in reactions['data']:
                        reaction['post_id'] = post_id
                        reactions_collection.insert_one(reaction)

                # Attempt to make a request to the next page of results
                posts = requests.get(posts['paging']['next']).json()
            except KeyError:
                # No more pages of results
                break

        return JSONResponse(content={'message': 'Data successfully scraped and stored in the database.'})
    except (facebook.GraphAPIError, OperationFailure) as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/posts")
async def get_posts():
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
        db = db_client['facebook']
        posts_collection = db['posts']

        # Retrieve all posts from the database
        posts = await posts_collection.find().to_list(length=None)

        # Convert posts to JSON
        posts_json = json.loads(dumps(posts))

        return JSONResponse(content=posts_json)
    except OperationFailure as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profiles/{reaction_type}")
async def get_profiles(reaction_type: str):
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
        db = db_client['facebook']
        reactions_collection = db['reactions']

        # Retrieve all reactions of the given type from the database
        reactions = await reactions_collection.find({'type': reaction_type}).to_list(length=None)

        # Group reactions by profile ID
        profiles = {}
        for reaction in reactions:
            profile_id = reaction['id']
            if profile_id not in profiles:
                profiles[profile_id] = {'name': reaction['name'], 'count': 0}
@app.get("/page/{page_id}/posts")
async def get_all_posts(page_id: str, limit: int = 50, access_token: str = Depends(get_access_token)):
    graph = facebook.GraphAPI(access_token=access_token, version="11.0")
    fields = "id,message,created_time,likes.summary(true),comments.summary(true),reactions.summary(true)"
    posts = graph.get_object(id=page_id, fields=f"posts.limit({limit}){{{fields}}}")
    return posts["posts"]["data"]
@app.get("/post/{post_id}")
async def get_post_details(post_id: str, access_token: str = Depends(get_access_token)):
    graph = facebook.GraphAPI(access_token=access_token, version="11.0")
    fields = "id,message,created_time,likes.summary(true),comments.summary(true),reactions.summary(true)"
    post = graph.get_object(id=post_id, fields=fields)
    return post
@app.get("/page/{page_id}/classify")
async def classify_profiles(page_id: str, access_token: str = Depends(get_access_token)):
    graph = facebook.GraphAPI(access_token=access_token, version="11.0")
    fields = "reactions.type(LIKE).limit(0).summary(total_count).as(like)," \
             "reactions.type(LOVE).limit(0).summary(total_count).as(love)," \
             "reactions.type(HAHA).limit(0).summary(total_count).as(haha)," \
             "reactions.type(WOW).limit(0).summary(total_count).as(wow)," \
             "reactions.type(SAD).limit(0).summary(total_count).as(sad)," \
             "reactions.type(ANGRY).limit(0).summary(total_count).as(angry)," \
             "reactions.type(CARE).limit(0).summary(total_count).as(care)"
    profiles = graph.get_object(id=page_id, fields=f"fan_count,{'{'+fields+'}'}")
    profile_reactions = {
        'like': profiles['like']['summary']['total_count'],
        'love': profiles['love']['summary']['total_count'],
        'haha': profiles['haha']['summary']['total_count'],
        'wow': profiles['wow']['summary']['total_count'],
        'sad': profiles['sad']['summary']['total_count'],
        'angry': profiles['angry']['summary']['total_count'],
        'care': profiles['care']['summary']['total_count']
    }
    return profile_reactions
