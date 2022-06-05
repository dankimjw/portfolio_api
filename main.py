from google.cloud import datastore
from flask import Flask, request, make_response, jsonify, _request_ctx_stack
import requests

import json
from flask import jsonify
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, render_template, session, url_for

import string
import secrets
import constants
import helpers
from  verifyJWT import AuthError, verify_jwt
import projects
import team_members
import clients
from admin import get_admins, set_revoke_admin, check_user_datastore

app = Flask(__name__)
app.register_blueprint(projects.bp)
app.register_blueprint(team_members.bp)
app.register_blueprint(clients.bp)

# Set secret_key in order to use session objects
# if secret_key is set dynamically and randomly within the app , there will be an error
# when redirects occur at the authentication / login webpage.
# i.e State values will be different on redirects and throw and error.
# Thus, "secret_key" should be static.
with open('app-keys.json') as data_file:
    data = json.load(data_file)

app.secret_key = data['SECRET_KEY']
# app.secret_key = secret_key

client = datastore.Client()
data_model_attributes = {"projects": ["name", "budget", "description", "start_date", "end_date"],
                         "clients": ["name", "industry", "join_date"],
                         "team_members": ["name", "join_date", "specialty"]
                         }
# Instantiate Utilities class object with datastore client object
utilities = helpers.Utilities(client)
utilities.add_model_attributes(data_model_attributes)

# Update the values of the following 3 variables
CLIENT_ID = data['CLIENT_ID']
CLIENT_SECRET = data['CLIENT_SECRET']
DOMAIN = data['DOMAIN']
ALGORITHMS = ["RS256"]

# For example
# DOMAIN = 'fall21.us.auth0.com'
LOGIN_URL_TEST = "http://127.0.0.1:8080"
LOGIN_URL_LIVE = "https://portfolio-kimd3.ue.r.appspot.com"

REDIRECT_URI_TEST = "https://127.0.0.1:8080/authO"
REDIRECT_URI_LIVE = "https://portfolio-kimd3.ue.r.appspot.com/authO"
# --------------[** CHANGE **] ------------- when testing and using live -----------------
REDIRECT_CALLBACK_URL = REDIRECT_URI_TEST
# --------------[** CHANGE **] ------------- when testing and using live -----------------

oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    api_base_url="https://" + DOMAIN,
    access_token_url="https://" + DOMAIN + "/oauth/token",
    authorize_url="https://" + DOMAIN + "/authorize",
    client_kwargs={
        'scope': 'openid profile email',
    },
server_metadata_url=f'https://{DOMAIN}/.well-known/openid-configuration'
)

# This code is adapted from https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga=2.46956069.349333901.1589042886-466012638.1589042885#create-the-jwt-validation-decorator

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response
#
# Decode the JWT supplied in the Authorization header
@app.route('/decode', methods=['GET'])
def decode_jwt():
    payload = verify_jwt(request, 'default')
    return payload

# Generate a JWT from the Auth0 domain and return it
# Request: JSON body with 2 properties with "username" and "password"
#       of a user registered with this Auth0 domain
# Response: JSON with the JWT as the value of the property id_token
@app.route('/login', methods=['POST'])
def login_user():
    content = request.get_json()
    print('content: ', content)
    username = content["username"]
    password = content["password"]
    body = {'grant_type': 'password',
            'username': username,
            'password': password,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
            }
    headers = {'content-type': 'application/json'}
    url = 'https://' + DOMAIN + '/oauth/token'
    r = requests.post(url, json=body, headers=headers)
    return r.text, 200, {'Content-Type': 'application/json'}

# Login route
@app.route("/user_login")
def user_login():
    session.clear()
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for('authO_route', _external=True)
    )

# Callback route
@app.route('/authO', methods=["GET", "POST"])
def authO_route():
    # if request.method == "GET":
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    # print(token)
    print("token[email]: ", token["userinfo"]["email"])
    print("token[name]: ", token["userinfo"]["name"])

    return redirect("/")

@app.route("/user_logout")
def logout():
    session.clear()
    return redirect(
        "https://" + DOMAIN
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for('index', _external=True),
                "client_id": CLIENT_ID,
            },
            quote_via=quote_plus,
        )
    )

# Home route where user chooses to log in and log out
@app.route('/')
def index():
    id_val = None
    user = session.get('user')
    print("user: ", user)
    if user:
            # Check if the user is already in the database via sub attribute
            user_sub = user['userinfo']['sub']
            filter_vals = {"sub": user_sub}
            results = utilities.filter_entities(constants.users, filter_vals)
            print("results: ", results)
            # if the user is not already saved in datastore, create a new user entity
            if results == []:
                print("User not in database")
                new_user = datastore.entity.Entity(key=client.key(constants.users))
                new_user.update({'name': user['userinfo']['name'],'email': user['userinfo']['email'],
                                 'sub': user['userinfo']['sub'], 'admin': False})
                client.put(new_user)
                posted_user = client.get(new_user.key)
                id_val = posted_user.key.id

            else:
                print("user in database")
                print("results: ", results[0].key.id )
                if results[0].key.id is not None:
                    id_val = results[0].key.id
                else:
                    id_val = results

    return render_template("index.html", session=session.get('user'),
                       pretty = json.dumps(session.get('user')), posted_user_id=id_val, user_sub=session.get('user'),indent=4)

# ------------------------------------ USERS ------------------------------------------------------
@app.route('/users', methods=['GET'])
def users_get():
    if request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        query = client.query(kind=constants.users)
        results = list(query.fetch())
        for user_entity in results:
            user_entity["id"] = user_entity.key.id
        output = {"users": results}
        return jsonify(output), 200
    else:
        return 'Method not recognized'

# ------------------------------------ ADMIN ------------------------------------------------------

@app.route('/admin', methods=['GET', 'POST', 'DELETE'])
def admin_post():
    if request.method == "GET":
        payload = verify_jwt(request, 'default')
        print("sub", payload["sub"])
        user_sub = payload["sub"]

        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            filter_vals = {"admin": True}
            results = utilities.filter_entities(constants.users, filter_vals)
            for user_entity in results:
                user_entity["id"] = user_entity.key.id

            output = {"admins": results}
            res = make_response(json.dumps(output))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 200
            return res

    # This route requires a valid JWT with user already registered/logged-in
    elif request.method == "POST":
        payload = verify_jwt(request, 'default')
        print("sub", payload["sub"])
        user_sub = payload["sub"]
        filter_vals = {"sub": user_sub}
        user_entity = check_user_datastore(constants.users, filter_vals)
        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        # User is not already admin
        if user_entity["admin"] is False:
            patched_user_entity = set_revoke_admin(user_entity, "SET")
            patched_user_entity["id"] = patched_user_entity.key.id
            res = make_response(json.dumps(patched_user_entity))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 201
            return res

        else:
            # User is already the current admin
            return jsonify({"Error": "User is already an admin."}), 400

    elif request.method == "DELETE":
        payload = verify_jwt(request, 'default')
        print("sub", payload["sub"])
        user_sub = payload["sub"]
        filter_vals = {"sub": user_sub}
        user_entity = check_user_datastore(constants.users, filter_vals)
        print("User_entity admin: ", user_entity['admin'])
        # Check if there is already an admin
        current_admin = get_admins()
        print("Current_admin: ", current_admin)
        # There are no current admins
        if current_admin == [] or user_entity['admin'] is False:
            return jsonify({"Error": "User is not an admin."}), 403
        else:
            # User is the current admin
            set_revoke_admin(user_entity, "REVOKE")
            res = make_response('')
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 204
            return res

    else:
        return 'Method not recognized'

@app.route('/test', methods=['GET', 'POST', 'DELETE'])
def test_url():
    if request.method=='GET':
        content = request.get_json()
        return '',200


if __name__ == '__main__':
    # app.run(host='127.0.0.1', port=8080, debug=True)
    app.run(host='127.0.0.1', port=8000, debug=True, ssl_context='adhoc')
