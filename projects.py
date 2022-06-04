from flask import Blueprint, request
from google.cloud import datastore
from flask import Flask, request, make_response, jsonify, _request_ctx_stack
import requests
from flask import jsonify
import json
import constants
import helpers
from  verifyJWT import AuthError, verify_jwt
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

bp = Blueprint('projects', __name__, url_prefix='/projects')

# /projects
# ------------------------------------ PROJECTS -----------------------------------------------------
@bp.route('', methods=['GET', 'POST'])
def project_get_post():
    # ----------[Complete] ---------------------------------------------------------
    if request.method == 'POST':
        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        elif 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            payload = verify_jwt(request, 'default')
            print("sub", payload["sub"])
            content = request.get_json()
            if content is None:
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400
            # Check that all attributes are provided in the request body
            check_result = utilities.check_valid("projects", content)
            print("check_result: ", check_result)
            is_valid_data = utilities.check_datatype_valid("projects", content, "POST")
            print("is_valid_data: ", is_valid_data)
            print(content)
            # Attribute is missing from the request body
            if check_result == "invalid" or not is_valid_data:
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400
            # check_duplicate = utilities.check_duplicate("boats", content)
            # if check_duplicate == "duplicate":
            #     return {"Error": "An entity with the same name already exists"}, 403
            else:
                new_project = datastore.entity.Entity(key=client.key(constants.projects))
                new_project.update({'name': content['name'], 'budget': int(content['budget']),
                                 'description': content['description'], 'start_date': content['start_date'],
                                    'end_date': content['end_date'], 'client': None,
                                    'team_members': [], "project_owner": payload["sub"]})
                client.put(new_project)
                posted_project = client.get(new_project.key)
                posted_project['id'] = posted_project.key.id
                posted_project['self'] = request.url + '/' + str(posted_project.key.id)
                res = make_response(json.dumps(posted_project))
                res.headers.set('Content-Type', 'application/json')
                res.status_code = 201
                return res
    # ----------[Complete] ---------------------------------------------------------
    elif request.method == 'GET':
        payload = verify_jwt(request, 'default')
        # Check if client has the correct accept types
        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        # If JWT is valid
        if payload != False:
            jwt_sub_value = payload["sub"]
            print('jwt_sub_value: ', jwt_sub_value)
            filter_vals = {"project_owner": jwt_sub_value}
            q_offset, q_limit, l_iterator = utilities.get_pagination(5, 0, request,
                                                                     constants.projects, filter_vals)
            pages = l_iterator.pages
            results = list(next(pages))
            if l_iterator.next_page_token:
                next_offset = q_offset + q_limit
                next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
            else:
                next_url = None
            print("results: ", results)
            for project_entity in results:
                project_entity["id"] = project_entity.key.id
                project_entity["self"] = request.url_root + 'projects/' + str(project_entity.key.id)
                if project_entity["team_members"] is not []:
                    for team_members in project_entity["team_members"]:
                        # if load is not None:`
                        team_members["self"] = request.url_root + 'team_members/' + str(team_members["id"])
            output = {"projects": results}
            # If there is a next page of results
            if next_url:
                output["next"] = next_url
            return jsonify(output), 200
    else:
        return 'Method not recognized'
# ---------------------------------------------------------------------------------------------------

# ------------------------------------ PROJECTS by Project_ID-----------------------------------------------------
@bp.route('/<project_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def projects_get_edit_delete(project_id):
    # View a boat with boat_id
    payload = verify_jwt(request, 'default')
    print("sub", payload["sub"])
    jwt_sub_value = payload["sub"]
    print('jwt_sub_value: ', jwt_sub_value)
    filter_vals = {"project_owner": jwt_sub_value}
    # ----------[Complete] ---------------------------------------------------------
    if request.method == 'GET':
        # if the client requests accepts only a mimetype that is not json then error
        if 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406

        project_key, project = utilities.get_key_entity(constants.projects, int(project_id))
        # Ownership Validation: Check if JWT sub value matches project's sub value
        if project is None:
            return jsonify({"Error": "No project with this project_id exists"}), 404
        elif project['project_owner'] != jwt_sub_value:
            return jsonify({"Error": "Invalid project_owner for this project_id"}), 403
        else:
            project["id"] = project.key.id
            project["self"] = request.url
            if project["team_members"] is not []:
                for team_member in project["team_members"]:
                    # if load is not None:`
                    team_member["self"] = request.url_root + 'team_members/' + str(team_member["id"])
            if project["client"] is not None:
                project["client"]["self"] = request.root_url + 'clients/' + str(project["client"]["id"])
            # Check for mimetypes that the client accepts
            res = make_response(jsonify(project))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 200
            return res
    # ----------[To DO] ---------------------------------------------------------
    # Delete a project with project_id
    elif request.method == 'DELETE':
        project_key, project = utilities.get_key_entity(constants.projects, int(project_id))
        if project is None:
            return jsonify({"Error": "No project with this project_id exists"}), 404
        # Ownership Validation: Check if JWT sub value matches project's sub value
        elif project['project_owner'] != jwt_sub_value:
            return jsonify({"Error": "Invalid project_owner for this project_id"}), 403
        else:
            # Delete the project for the team_member entity
            if project["team_members"] is not []:
                for team_member in project["team_members"]:
                    team_member_entity = client.get(key=client.key(constants.team_members, team_member["id"]))
                    if team_member_entity is not None:
                        # Set the project of that team_member to None or Null
                        team_member_entity['projects'] = None
                        # Update the Entity in datastore
                        client.put(team_member_entity)
                # Delete project for the client entity
            if project["client"] is not None:
                client_key, client_entity = utilities.get_key_entity(constants.clients, int(project["client"]["id"]))
                if client_entity is not None:
                    # Remove the load id from the loads attribute in the respective boat entity
                    client_entity["projects"] = None
                    client.put(client_entity)
            # Delete the project
            client.delete(project)
            res = make_response(jsonify(''))
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 204
            return res
    # ----------[Complete] ---------------------------------------------------------
    # PATCH method: only edit some attributes of a projects with projects_id
    elif request.method == 'PATCH':
        project_key, project = utilities.get_key_entity(constants.projects, int(project_id))
        # Boat or load with id is not found
        if project is None:
            return {"Error": "No project with this project_id exists"}, 404
        # Ownership Validation: Check if JWT sub value matches project's sub value
        if project['project_owner'] != jwt_sub_value:
            return jsonify({"Error": "Invalid project_owner for this project_id"}), 403

        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        else:
            content = request.get_json()
            # No data provided in request body
            if content is None:
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400
            is_valid_data = utilities.check_datatype_valid("projects", content, "PATCH")
            # Attribute is missing from the request body
            if not is_valid_data:
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400
            # Check that team_members or client attributes are correct formats
            for key in content.keys():
                # ----- Reset each team_member entity's projects attribute -----
                if key == "team_members":
                    if project["team_members"] is not []:
                        for old_member in project["team_members"]:
                            old_member_entity = client.get(key=client.key(constants.team_members, old_member["id"]))
                            if old_member_entity is not None:
                                # Set the team_member entity to have the project attribute to this projects id
                                old_member_entity['projects'] = None
                                # Update the Entity in datastore
                                client.put(old_member_entity)
                    # ---- if the team_members attribute is not empty ----
                    if content["team_members"] is not []:
                        # ---- Add projects id to each new team_member in the updated project
                        for new_member in content["team_members"]:
                            new_member_entity = client.get(key=client.key(constants.team_members, new_member["id"]))
                            if new_member_entity is not None:
                                # if the patch request includes a new project name
                                if "name" in content.keys():
                                    # Set the team_member entity to have the project attribute to this project's id and name
                                    # If there is a new project name in the patch request, assign that name as well
                                    new_member_entity['projects'] = {"id": int(project.key.id), "name": content["name"]}
                                else:
                                    # If there is no new project name in the patch request, assign the old project name
                                    new_member_entity['projects'] = {"id": int(project.key.id), "name": project["name"]}
                                # Update the Entity in datastore
                                client.put(new_member_entity)
                # ----- Reset each client entity's projects attribute -----
                if key == "client":
                    if project["client"] is not None:
                        print("client not None")
                        old_client_entity = client.get(key=client.key(constants.clients, project["client"]["id"]))
                        if old_client_entity is not None:
                            # Set the carrier of that load to None or Null
                            old_client_entity['projects'] = None
                            # Update the Entity in datastore
                            client.put(old_client_entity)
                    # ---- Update the new client relationship if a new client exists in the content ----
                    if content["client"] is not None:
                        new_client_entity = client.get(key=client.key(constants.clients, content["client"]["id"]))
                        if new_client_entity is not None:
                            # Set the client entity to have the project attribute to this project's id and name
                            # If there is a new project name in the patch request, assign that name as well
                            if "name" in content.keys():
                                new_client_entity['projects'] = {"id": int(project.key.id), "name": content["name"]}
                            else:
                                # If there is no new project name in the patch request, assign the old project name
                                new_client_entity['projects'] = {"id": int(project.key.id), "name": project["name"]}
                            # Update the Entity in datastore
                            client.put(new_client_entity)
                # ----- Finally update the project with the new content -----
                print("key and content[key] ", key, content[key])
                project[key] = content[key]
            # Update an attribute of the boat and generate a self link
            client.put(project)
            # patched_project = client.get(project_key)
            # patched_project['id'] = patched_project.key.id
            # patched_project['self'] = request.url
            res = make_response('')
            res.headers.set('Content-Type', 'application/json')
            res.status_code = 204
            return res

    # ----------[Complete] ---------------------------------------------------------
    # PUT method: required to edit/provide all attributes of a project with project_id
    elif request.method == 'PUT':
        project_key, project = utilities.get_key_entity(constants.projects, int(project_id))
        # Boat or load with id is not found
        if project is None:
            return jsonify({"Error": "No project with this project_id exists"}), 404
        # Ownership Validation: Check if JWT sub value matches project's sub value
        if project['project_owner'] != jwt_sub_value:
            return jsonify({"Error": "Invalid project_owner for this project_id"}), 403
        # Check if client has the correct accept types and content_type
        if 'application/json' not in request.content_type:
            return jsonify(''), 415
        elif 'application/json' not in request.accept_mimetypes:
            return jsonify(''), 406
        else:
            content = request.get_json()
            # No data provided in the request body
            if content is None:
                print("empty content")
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400
            # Check that all attributes are provided in the request body
            is_valid_data = utilities.check_datatype_valid("projects", content, "PUT")
            # Attribute is missing from the request body
            if is_valid_data == False:
                return jsonify({"Error": "The request object is missing at least one of the required attributes"}), 400
            # Delete the current team_member relationship
            if project["team_members"] is not []:
                print("team_members not []")
                for old_member in project["team_members"]:
                    old_member_entity = client.get(key=client.key(constants.team_members, old_member["id"]))
                    if old_member_entity is not None:
                        # Set the team_member entity to have the project attribute to this projects id
                        old_member_entity['projects'] = None
                        # Update the Entity in datastore
                        client.put(old_member_entity)
            # Delete the current client relationship
            if project["client"] is not None:
                print("client not None")
                old_client_entity = client.get(key=client.key(constants.clients, project["client"]["id"]))
                if old_client_entity is not None:
                    # Set the carrier of that load to None or Null
                    old_client_entity['projects'] = None
                    # Update the Entity in datastore
                    client.put(old_client_entity)
                    project["client"] = None
            # Set the team_member entity to have the project attribute to this projects id
            for key in content.keys():
                # only update team_member entities if there are team_members included in the content
                if key == "team_members" and content["team_members"] is not []:
                    for new_member in content["team_members"]:
                        new_member_entity = client.get(key=client.key(constants.team_members, new_member["id"]))
                        if new_member_entity is not None:
                            # Set the team_member entity to have the project attribute to this projects id
                            new_member_entity['projects'] = {"id": int(project.key.id), "name": content["name"]}
                            # Update the Entity in datastore
                            client.put(new_member_entity)
                # only update client entities if there is a client included in the content
                elif key == "client" and content["client"] is not None:
                    print("client id: ", content["client"]["id"])
                    new_client_entity = client.get(key=client.key(constants.clients, content["client"]["id"]))
                    if new_client_entity is not None:
                        # Set the projects attribute of the new client to the project's id
                        new_client_entity['projects'] = {"id": int(project.key.id), "name": content["name"]}
                        # Update the Entity in datastore
                        client.put(new_client_entity)
                # Update the attribute
                project[key] = content[key]
            # Update all the boat attributes and generate a self link
            client.put(project)
            put_project = client.get(project_key)
            put_project['id'] = put_project.key.id
            put_project['self'] = request.url
            # Generate a Location header with a link to the edited boat
            res = make_response(jsonify(put_project))
            res.headers.set('Location', str(put_project['self']))
            res.status_code = 201
            return res
    else:
        return 'Method not recognized'

# ------------------------------------ PROJECTS and Team_Members-----------------------------------------------------
@bp.route('/<project_id>/team_members/<team_member_id>', methods=['PUT', 'DELETE'])
def add_delete_team_members(project_id, team_member_id):
    payload = verify_jwt(request, 'default')
    print("sub", payload["sub"])
    jwt_sub_value = payload["sub"]
    print('jwt_sub_value: ', jwt_sub_value)
    filter_vals = {"project_owner": jwt_sub_value}
    # Assign a team_member to the project
    if request.method == 'PUT':
        # ------------------- Put in a separate function -------------------
        project_key, project = utilities.get_key_entity(constants.projects, int(project_id))
        team_member_key, team_member = utilities.get_key_entity(constants.team_members, int(team_member_id))
        # Project or team_members with id is not found
        if (project is None) or (team_member is None):
            return jsonify({"Error": "The specified project and/or team_member does not exist"}), 404
        # Ownership Validation: Check if JWT sub value matches project's sub value
        elif project['project_owner'] != jwt_sub_value:
            return jsonify({"Error": "Invalid project_owner for this project_id"}), 403
        elif team_member["projects"] is not None:
            return {"Error": "The team_member is already assigned to another project"}, 403
        else:
            # if team_members attribute is not empty
            if project["team_members"] is not []:
                # Update the project's team_members attribute
                project["team_members"].append({"id": int(team_member.key.id)})
            # Update the team_members entity with this project's id and name
            team_member["projects"] = {"id": int(project.key.id), "name": project["name"]}
            client.put(project)
            client.put(team_member)
            # ------------------- Put in a separate function -------------------
            return jsonify(''), 204
    # Remove a load from a boat
    elif request.method == 'DELETE':
        project_key, project = utilities.get_key_entity(constants.projects, int(project_id))
        team_member_key, team_member = utilities.get_key_entity(constants.team_members, int(team_member_id))
        # Project or team_members with id is not found
        if (project is None) or (team_member is None):
            return jsonify({"Error": "No project with project_id has a team_member with team_member_id"}), 404
        elif project['project_owner'] != jwt_sub_value:
            return jsonify({"Error": "Invalid project_owner for this project_id"}), 403
        # Team_members is not on this project
        elif (team_member["projects"] is None) or (team_member["projects"]["id"] != project.key.id):
            return jsonify({"Error": "No boat with this boat_id is loaded with the load with this load_id"}), 404
        else:
            if 'team_members' in project.keys():
                # Remove team_members id from the team_members attribute of the project
                project['team_members'].remove({"id": int(team_member_id)})
                # Set projects attribute of the team_member to None or Null
                team_member['projects'] = None
            client.put(project)
            client.put(team_member)
            return jsonify(''), 204
    else:
        return 'Method not recognized'

# ------------------------------------ PROJECTS and Clients -----------------------------------------------------
@bp.route('/<project_id>/clients/<client_id>', methods=['PUT', 'DELETE'])
def add_delete_clients(project_id, client_id):
    payload = verify_jwt(request, 'default')
    print("sub", payload["sub"])
    jwt_sub_value = payload["sub"]
    print('jwt_sub_value: ', jwt_sub_value)
    # Assign a client to a project
    if request.method == 'PUT':
        project_key, project = utilities.get_key_entity(constants.projects, int(project_id))
        client_key, client_entity = utilities.get_key_entity(constants.clients, int(client_id))
        # Project or clients with id is not found
        if (project is None) or (client_entity is None):
            return jsonify({"Error": "The specified project and/or client does not exist"}), 404
        elif project['project_owner'] != jwt_sub_value:
            return jsonify({"Error": "Invalid project_owner for this project_id"}), 403
        elif client_entity["projects"] is not None:
            return jsonify({"Error": "The client is already assigned to another project"}), 403
        elif project["client"] is not None:
            return jsonify({"Error": "There is already another client that is assigned to this project"}), 403
        else:
            # if client for the project is not empty
            project["client"] = {"id": int(client_entity.key.id)}
            # Update the projects attribute for the respective client
            client_entity["projects"] = {"id": int(project.key.id), "name": project["name"]}
            client.put(project)
            client.put(client_entity)
            return jsonify(''), 204
    # Remove a client from project
    elif request.method == 'DELETE':
        project_key, project = utilities.get_key_entity(constants.projects, int(project_id))
        client_key, client_entity = utilities.get_key_entity(constants.clients, int(client_id))
        # Project or Client with id is not found
        if (project is None) or (client_entity is None):
            return jsonify({"Error": "No project with project_id has a client with client_id"}), 404
        elif project['project_owner'] != jwt_sub_value:
            return jsonify({"Error": "Invalid project_owner for this project_id"}), 403
        # client is not assigned to this project
        elif (client_entity["projects"] is None) or (client_entity["projects"]["id"] != project.key.id):
            return jsonify({"Error": "No project with this project_id has a client with this client_id"}), 404
        else:
            if 'client' in project.keys():
                # Remove client id from the client attribute of the project
                project['client'] = None
                # Set projects attribute of the load to None or Null
                client_entity['projects'] = None
            client.put(project)
            client.put(client_entity)
            return jsonify(''), 204
    else:
        return 'Method not recognized'


# ------------------------------------ PROJECTS and Clients -----------------------------------------------------
@bp.route('/tests', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'])
def test_route():
    # ----------[Complete] ---------------------------------------------------------
    if request.method == 'POST' or  request.method == 'PUT' or request.method == 'PATCH':
        content = request.get_json()
        try:
            print("Content: ", content)
            print("Content: ", content["team_members"])
            # print("Content: ", content["team_members"]["id"])
            print("1 instance? : ", isinstance(content["team_members"], list))
            print("For loop: ")
            for member in content["team_members"]:
                print(int(member['id']))
                # int(content["team_members"]["id"])
            print("2 instance? : ", content["team_members"][0]["id"])
            # Must be True
            print("2 instance? : ", isinstance(content["team_members"][0]["id"], int))

            print("2 len? : ", len(content["team_members"][0]))
            print("3 len? : ", len(content["team_members"][1]))
            # print("4 client len? : ", len(content["client"]))

            print("3 team_members  : ", content["team_members"][1]["id"])
            # Must be True
            print("3 instance? : ", isinstance(content["team_members"][1]["id"], int))

            # Must be True
            print("Client instance? : ", isinstance(content["client"]["id"], int))
        except ValueError as e:
            print(e)

        finally:
            result = utilities.check_team_members(content)
            print("result1: ", result)
            result2 = utilities.check_client(content)
            print("result2: ", result2)
            result3 = utilities.check_datatype_valid("projects",content,request.method)
            print("result 3: ", result3)
            # result4 = utilities.check_projects(content)
            # print("result4: ", result4)
            return jsonify(result), 201
