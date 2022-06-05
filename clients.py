from flask import Blueprint, request
from google.cloud import datastore
from flask import Flask, request, make_response, jsonify, _request_ctx_stack
import requests
from flask import jsonify
import json
import constants
import helpers
from  verifyJWT import AuthError, verify_jwt
from admin import get_admins, set_revoke_admin, check_user_datastore

from  verifyJWT import AuthError, verify_jwt
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, render_template, session, url_for



gclient = datastore.Client()
data_model_attributes = {"projects": ["name", "budget", "description", "start_date", "end_date"],
                         "clients": ["name", "industry", "join_date"],
                         "team_members": ["name", "join_date", "specialty"]
                         }

# Instantiate Utilities class object with datastore client object
utilities = helpers.Utilities(gclient)
utilities.add_model_attributes(data_model_attributes)

bp = Blueprint('clients', __name__, url_prefix='/clients')

# ------------------------------------ [ /clients ] -----------------------------------------------------
@bp.route('', methods=['GET', 'POST'])
def client_get_post():
    # ---------- Create a Client ----------
    if request.method == 'POST':
        content = request.get_json()
        # Check that all attributes are provided in the request body
        check_result = utilities.check_valid("clients", content)
        print("check_result: ", check_result)
        is_valid_data = utilities.check_datatype_valid("clients", content, "POST")
        print("is_valid_data: ", is_valid_data)
        print(content)
        # Attribute is missing from the request body
        if check_result == "invalid" or not is_valid_data:
            return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400

        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        elif 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            new_client = datastore.entity.Entity(key=gclient.key(constants.clients))
            new_client.update({'name': content['name'], 'industry': content['industry'],
                             'join_date': content['join_date'], "projects": None })
            gclient.put(new_client)
            posted_client = gclient.get(new_client.key)
            posted_client['id'] = posted_client.key.id
            posted_client['self'] = request.url + '/' + str(posted_client.key.id)
            res = make_response(json.dumps(posted_client))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 201
            return res
    # ---------- Get All Clients ----------
    elif request.method == 'GET':
        # Check if client has the correct accept types
        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        # If JWT is valid
        q_offset, q_limit, l_iterator = utilities.get_pagination(5, 0, request, constants.clients)
        pages = l_iterator.pages
        results = list(next(pages))
        if l_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None
        print("results: ", results)
        for client_entity in results:
            client_entity["id"] = client_entity.key.id
            client_entity["self"] = request.url_root + 'clients/' + str(client_entity.key.id)
            if client_entity["projects"] is not None:
                client_entity["projects"]["self"] = request.url_root + 'projects/' \
                                                         + str(client_entity["projects"]["id"])
        output = {"clients": results}
        # If there is a next page of results
        if next_url:
            output["next"] = next_url
        return jsonify(output), 200
    else:
        return 'Method not recognized'

# ------------------------------------[/clients/client_id] -----------------------------------------------------
@bp.route('/<client_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def clients_get_edit_delete(client_id):
    if request.method == 'GET':
        # if the client requests accepts only a mimetype that is not json then error
        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406

        client_key, client_entity = utilities.get_key_entity(constants.clients, int(client_id))
        # Ownership Validation: Check if JWT sub value matches project's sub value
        if client_entity is None:
            return jsonify({"Error": "No client with this client_id exists"}), 404
        else:
            client_entity["id"] = client_entity.key.id
            client_entity["self"] = request.url
            if client_entity["projects"] is not None:
                client_entity["projects"]["self"] = request.root_url + 'projects/' + str(client_entity["projects"]["id"])
            # Check for mimetypes that the client accepts
            res = make_response(jsonify(client_entity))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 200
            return res
    # ---------- Delete a Client with client_id ----------
    elif request.method == 'DELETE':
        # ----- Check if user has valid JWT -----
        payload = verify_jwt(request, 'default')
        user_sub = payload["sub"]
        # Get current user with matching sub value
        filter_vals = {"sub": user_sub}
        user_entity = check_user_datastore(constants.users, filter_vals)
        # ---- Check if user had admin access ----
        if user_entity is not None:
            # If the user is not the current admins
            if user_entity["admin"] is False:
                return jsonify({"Error": "User is not an admin."}), 403
        else:
            return jsonify({"Error": "User is not registered, logged in via log-in page"}), 401
        # User is registered and has admin access
        if user_entity is not None and user_entity["admin"] == True:
            # Proceed to find the Client entity
            client_key, client_entity = utilities.get_key_entity(constants.clients, int(client_id))

        if client_entity is None:
            return jsonify({"Error": "No client with this client_id exists"}), 404
        else:
            # --- [Requires Admin  access] -----  Delete the projects relationship
            if client_entity["projects"] is not None:
                project_key, project_entity = utilities.get_key_entity(constants.projects,
                                                                       int(client_entity["projects"]["id"]))
                if project_entity is not None:
                    # Remove the load id from the loads attribute in the respective boat entity
                    project_entity["client"] = None
                    gclient.put(project_entity)
            # Delete the respective client
            gclient.delete(client_key)
            res = make_response('')
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 204
            return res
    # ---------- PATCH method: only edit some attributes of a Client with client_id ----------
    elif request.method == 'PATCH':
        # Check if there is a request body and that the request body data is valid
        content = request.get_json()
        is_valid_data = utilities.check_datatype_valid("clients", content, "PATCH")
        # Attribute is missing from the request body
        if not is_valid_data:
            return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400

        # ----- Check if user has valid JWT -----
        payload = verify_jwt(request, 'default')
        user_sub = payload["sub"]
        # Get current user with matching sub value
        filter_vals = {"sub": user_sub}
        user_entity = check_user_datastore(constants.users, filter_vals)
        # ---- Check if user had admin access ----
        if user_entity is not None:
            # If the user is not the current admins
            if user_entity["admin"] is False:
                return jsonify({"Error": "User is not an admin."}), 403
        else:
            return jsonify({"Error": "User is not registered, logged in via log-in page"}), 401

        client_key, client_entity = utilities.get_key_entity(constants.clients, int(client_id))
        # Boat or load with id is not found
        if client_entity is None:
            return {"Error": "No client with this client_id exists"}, 404
        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        elif 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            # Check that attributes are of the correct type and not duplicates
            for key in content.keys():
                # Delete the current client-projects relationship if it exists
                if key == "projects" and client_entity["projects"] is not None:
                    print("client not None")
                    old_project_entity = gclient.get(key=gclient.key(constants.projects,
                                                                     client_entity["projects"]["id"]))
                    if old_project_entity is not None:
                        # Set the old project's client attribute to None or Null
                        old_project_entity['client'] = None
                        # Update the Entity in datastore
                        gclient.put(old_project_entity)
                        client_entity["projects"] = None
                # Add the new client-projects relationship if it exists
                if key == "projects" and content["projects"] is not None:
                    print("projects id: ", content["projects"]["id"])
                    new_project_entity = gclient.get(key=gclient.key(constants.projects, content["projects"]["id"]))
                    if new_project_entity is not None:
                        print("new_project_entity not none")
                        # Set the client attribute to the id of the current client entity
                        new_project_entity['client'] = {"id": int(client_entity.key.id)}
                        new_project_entity['name'] =  content["projects"]["name"]
                        # Update the project entity in datastore
                        gclient.put(new_project_entity)

                # Update the client entity
                client_entity[key] = content[key]
            # Save the updated Clients entity in DataStore and generate a self link
            gclient.put(client_entity)
            patched_client = gclient.get(client_key)
            patched_client['id'] = patched_client.key.id
            patched_client['self'] = request.url
            res = make_response(json.dumps(patched_client))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 204
            return res

    # ---------- PUT method: required to edit/provide all attributes of a Client with client_id ----------
    elif request.method == 'PUT':
        # Check if there is a request body and that the request body data is valid
        content = request.get_json()
        # Check that all attributes are provided in the request body
        check_result = utilities.check_valid("clients", content)
        is_valid_data = utilities.check_datatype_valid("clients", content, "PUT")

        # Attribute is missing from the request body
        if check_result == "invalid" or not is_valid_data:
            return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400

        # ----- Check if user has valid JWT -----
        payload = verify_jwt(request, 'default')
        user_sub = payload["sub"]
        # Get current user with matching sub value
        filter_vals = {"sub": user_sub}
        user_entity = check_user_datastore(constants.users, filter_vals)
        # ---- Check if user had admin access ----
        if user_entity is not None:
            # If the user is not the current admins
            if user_entity["admin"] is False:
                return jsonify({"Error": "User is not an admin."}), 403
        else:
            return jsonify({"Error": "User is not registered, logged in via log-in page"}), 401

        client_key, client_entity = utilities.get_key_entity(constants.clients, int(client_id))
        # Boat or load with id is not found
        if client_entity is None:
            return jsonify({"Error": "No client with this client_id exists"}), 404
        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        elif 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            # Delete the current client-projects relationship
            if client_entity["projects"] is not None:
                print("client not None")
                old_project_entity = gclient.get(key=gclient.key(constants.projects, client_entity["projects"]["id"]))
                if old_project_entity is not None:
                    # Set the old project's client attribute to None or Null
                    old_project_entity['client'] = None
                    # Update the Entity in datastore
                    gclient.put(old_project_entity)
                    client_entity["projects"] = None
            # Check for projects attribute in request body
            for key in content.keys():
                if key == "projects" and content["projects"] is not None:
                    print("projects id: ", content["projects"]["id"])
                    new_project_entity = gclient.get(key=gclient.key(constants.projects, content["projects"]["id"]))
                    if new_project_entity is not None:
                        print("new_project_entity not none")
                        # Set the client attribute to the id of the current client entity
                        new_project_entity['client'] = {"id": int(client_entity.key.id)}
                        # Set the project's name to what was provided in the request body
                        new_project_entity['name'] = content["projects"]["name"]
                        # Update the project entity in datastore
                        gclient.put(new_project_entity)
                # Update the client entity
                client_entity[key] = content[key]
            # Update all the projects attributes and generate a self link
            gclient.put(client_entity)
            put_client = gclient.get(client_key)
            put_client['id'] = put_client.key.id
            put_client['self'] = request.url
            # Generate a Location header with a link to the edited boat
            res = make_response(put_client)
            res.headers.set('Location', str(put_client['self']))
            res.status_code = 201
            return res
    else:
        return 'Method not recognized'
