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
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, render_template, session, url_for


client = datastore.Client()
data_model_attributes = {"projects": ["name", "budget", "description", "start_date", "end_date"],
                         "clients": ["name", "industry", "join_date"],
                         "team_members": ["name", "join_date", "specialty"]
                         }

# Instantiate Utilities class object with datastore client object
utilities = helpers.Utilities(client)
utilities.add_model_attributes(data_model_attributes)

bp = Blueprint('team_members', __name__, url_prefix='/team_members')


# ------------------------------------ TEAM_MEMBERS -------------------------------------------------
@bp.route('', methods=['GET', 'POST'])
def team_members_get_post():
    # ----------[Complete] ---------------------------------------------------------
    if request.method == 'POST':
        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        elif 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            # payload = verify_jwt(request, 'POST', 'default')
            # print("sub", payload["sub"])
            content = request.get_json()
            # Check that all attributes are provided in the request body
            check_result = utilities.check_valid("team_members", content)
            print("check_result: ", check_result)
            is_valid_data = utilities.check_datatype_valid("team_members", content, "POST")
            print("is_valid_data: ", is_valid_data)
            print(content)
            # Attribute is missing from the request body
            if check_result == "invalid" or not is_valid_data:
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400
            # check_duplicate = utilities.check_duplicate("boats", content)
            # if check_duplicate == "duplicate":
            #     return {"Error": "An entity with the same name already exists"}, 403
            else:
                new_team_member = datastore.entity.Entity(key=client.key(constants.team_members))
                new_team_member.update({'name': content['name'], 'join_date': content['join_date'],
                                    'specialty': content['specialty'], 'projects': None})
                client.put(new_team_member)
                post_team_member = client.get(new_team_member.key)
                post_team_member['id'] = post_team_member.key.id
                post_team_member['self'] = request.url + '/' + str(post_team_member.key.id)
                res = make_response(json.dumps(post_team_member))
                res.headers.set('Content-Type', 'application/json')
                res.status_code = 201
                return res
    # ----------[Complete] ---------------------------------------------------------
    elif request.method == 'GET':
        # payload = verify_jwt(request, 'GET', 'default')
        # Check if client has the correct accept types
        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        # If JWT is valid
        q_offset, q_limit, l_iterator = utilities.get_pagination(5, 0, request, constants.team_members)
        pages = l_iterator.pages
        results = list(next(pages))
        if l_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None
        print("results: ", results)
        for team_member_entity in results:
            team_member_entity["id"] = team_member_entity.key.id
            team_member_entity["self"] = request.url_root + 'team_member/' + str(team_member_entity.key.id)
            if team_member_entity["projects"] is not None:
                team_member_entity["projects"]["self"] = request.url_root + 'projects/' \
                                                         + str(team_member_entity["projects"]["id"])
        output = {"team_members": results}
        # If there is a next page of results
        if next_url:
            output["next"] = next_url
        return jsonify(output), 200
    else:
        return 'Method not recognized'

# Get the team_member_id
@bp.route('/<team_member_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def team_members_get_edit_delete(team_member_id):
    # View a team_members with team_member_id
    # ----------[To DO] ---------------------------------------------------------
    if request.method == 'GET':
        # if the client requests accepts only a mimetype that is not json then error
        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406

        team_member_key, team_member_entity = utilities.get_key_entity(constants.team_members, int(team_member_id))
        # Ownership Validation: Check if JWT sub value matches project's sub value
        if team_member_entity is None:
            return jsonify({"Error": "No team_member with this team_member_id exists"}), 404
        else:
            team_member_entity["id"] = team_member_entity.key.id
            team_member_entity["self"] = request.url
            if team_member_entity["projects"] is not None:
                team_member_entity["projects"]["self"] = request.root_url + 'projects/' + str(team_member_entity["projects"]["id"])
            # Check for mimetypes that the client accepts
            res = make_response(jsonify(team_member_entity))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 200
            return res
    # ----------[To DO] ---------------------------------------------------------
    # Delete a project with project_id
    elif request.method == 'DELETE':
        # ----- Check if user has valid JWT -----
        payload = verify_jwt(request, 'default')
        user_sub = payload["sub"]
        # Get current user with matching sub value
        filter_vals = {"sub": user_sub}
        user_entity = check_user_datastore(constants.users, filter_vals)
        # ---- Check if user had admin access ----
        if user_entity is not None:
            # Check if there is already an admin
            current_admin = get_admins()
            print("Current_admin: ", current_admin)
            # If the user is not the current admins
            if user_entity["admin"] is False:
                return jsonify({"Error": "User is not the current admin."}), 403
        else:
            return jsonify({"Error": "User is not registered, logged in via log-in page"}), 401

        if user_entity is not None and user_entity["admin"] == True:
            team_member_key, team_member_entity = utilities.get_key_entity(constants.team_members, int(team_member_id))

        if team_member_entity is None:
            return jsonify({"Error": "No team_member with this team_member_id exists"}), 404
        else:
            # --- [Requires Admin  access] -----  Delete the projects relationship
            if team_member_entity["projects"] is not None:
                project_key, project_entity = utilities.get_key_entity(constants.projects, int(team_member_entity["projects"]["id"]))
                if project_entity is not None:
                    # Remove the load id from the loads attribute in the respective boat entity
                    project_entity["client"] = None
                    client.put(project_entity)
            # Delete the respective client
            client.delete(team_member_key)
            res = make_response('')
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 204
            return res

    # ----------[To DO] ---------------------------------------------------------
    # PATCH method: only edit some attributes of a projects with projects_id
    elif request.method == 'PATCH':
        # ----- Check if user has valid JWT -----
        payload = verify_jwt(request, 'default')
        user_sub = payload["sub"]
        # Get current user with matching sub value
        filter_vals = {"sub": user_sub}
        user_entity = check_user_datastore(constants.users, filter_vals)
        # ---- Check if user had admin access ----
        if user_entity is not None:
            # Check if there is already an admin
            current_admin = get_admins()
            print("Current_admin: ", current_admin)
            # If the user is not the current admins
            if user_entity["admin"] is False:
                return jsonify({"Error": "User is not the current admin."}), 403
        else:
            return jsonify({"Error": "User is not registered, logged in via log-in page"}), 401

        team_member_key, team_member_entity = utilities.get_key_entity(constants.team_members, int(team_member_id))
        # Boat or load with id is not found
        if team_member_entity is None:
            return {"Error": "No team_member with this team_member_id exists"}, 404
        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        elif 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            content = request.get_json()
            is_valid_data = utilities.check_datatype_valid("team_members", content, "PATCH")
            # Attribute is missing from the request body
            if not is_valid_data:
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400
            # Check that attributes are of the correct type and not duplicates
            for key in content.keys():
                # Delete the current client-projects relationship if it exists
                if key == "projects" and team_member_entity["projects"] is not None:
                    print("team_member_entity not None")
                    old_project_entity = client.get(key=client.key(constants.projects,
                                                                     team_member_entity["projects"]["id"]))
                    if old_project_entity is not None:
                        # Set the old project's client attribute to None or Null
                        old_project_entity['team_members'].remove({"id": int(team_member_id)})
                        # Update the Entity in datastore
                        client.put(old_project_entity)
                        team_member_entity["projects"] = None
                # Add the new client-projects relationship if it exists
                if key == "projects" and content["projects"] is not None:
                    new_project_entity = client.get(key=client.key(constants.projects, content["projects"]["id"]))
                    if new_project_entity is not None:
                        # Set the client attribute to the id of the current client entity
                        new_project_entity['team_members'].append({"id": int(team_member_entity.key.id)})
                        # Set the project's name to what was provided in the request body
                        new_project_entity['name'] = content["projects"]["name"]
                        # Update the project entity in datastore
                        client.put(new_project_entity)
                # Update the client entity
                team_member_entity[key] = content[key]
            # Save the updated Clients entity in DataStore and generate a self link
            client.put(team_member_entity)
            patched_team_member = client.get(team_member_key)
            patched_team_member['id'] = patched_team_member.key.id
            patched_team_member['self'] = request.url
            res = make_response(json.dumps(patched_team_member))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 204
            return res
    # ----------[To DO] ---------------------------------------------------------
    # PUT method: required to edit/provide all attributes of a project with project_id
    elif request.method == 'PUT':
        # ----- Check if user has valid JWT -----
        payload = verify_jwt(request, 'default')
        user_sub = payload["sub"]
        # Get current user with matching sub value
        filter_vals = {"sub": user_sub}
        user_entity = check_user_datastore(constants.users, filter_vals)
        # ---- Check if user had admin access ----
        if user_entity is not None:
            # Check if there is already an admin
            current_admin = get_admins()
            print("Current_admin: ", current_admin)
            # If the user is not the current admins
            if user_entity["admin"] is False:
                return jsonify({"Error": "User is not the current admin."}), 403
        else:
            return jsonify({"Error": "User is not registered, logged in via log-in page"}), 401

        team_member_key, team_member_entity = utilities.get_key_entity(constants.team_members, int(team_member_id))
        # Boat or load with id is not found
        if team_member_entity is None:
            return jsonify({"Error": "No team_members with this team_member_id exists"}), 404
        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        elif 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            content = request.get_json()
            # Check that all attributes are provided in the request body
            check_result = utilities.check_valid("team_members", content)
            is_valid_data = utilities.check_datatype_valid("team_members", content, "PUT")

            # Attribute is missing from the request body
            if check_result == "invalid" or not is_valid_data:
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400

            # Delete the current team_member relationship
            else:
                # Delete the current client-projects relationship
                if team_member_entity["projects"] is not None:
                    old_project_entity = client.get(key=client.key(constants.projects, team_member_entity["projects"]["id"]))
                    if old_project_entity is not None:
                        # Remove team_member's id from the old project's team_members attribute
                        old_project_entity['team_members'].remove({"id": int(team_member_id)})
                        # Update the Entity in datastore
                        client.put(old_project_entity)
                        # Delete that project from the team_member's projects attribute
                        team_member_entity["projects"] = None
                # Check for projects attribute in request body
                for key in content.keys():
                    if key == "projects" and content["projects"] is not None:
                        new_project_entity = client.get(key=client.key(constants.projects, content["projects"]["id"]))
                        if new_project_entity is not None:
                            # Set the client attribute to the id of the current client entity
                            new_project_entity['team_members'].append({"id": int(team_member_entity.key.id)})
                            # Set the project's name to what was provided in the request body
                            new_project_entity['name'] = content["projects"]["name"]
                            # Update the project entity in datastore
                            client.put(new_project_entity)
                    # Update the client entity
                    team_member_entity[key] = content[key]
                # Update all the boat attributes and generate a self link
                client.put(team_member_entity)
                put_team_member = client.get(team_member_key)
                put_team_member['id'] = put_team_member.key.id
                put_team_member['self'] = request.url
                # Generate a Location header with a link to the edited boat
                res = make_response(put_team_member)
                res.headers.set('Location', str(put_team_member['self']))
                res.status_code = 201
                return res
    else:
        return 'Method not recognized'


# ---------------------------------------------------------------------------------------------------