import constants
import helpers
from google.cloud import datastore

client = datastore.Client()
data_model_attributes = {"projects": ["name", "budget", "description", "start_date", "end_date"],
                         "clients": ["name", "industry", "join_date"],
                         "team_members": ["name", "join_date", "specialty"]
                         }
# Instantiate Utilities class object with datastore client object
utilities = helpers.Utilities(client)
utilities.add_model_attributes(data_model_attributes)

def get_admins():
    # Returns any matching user entity that has admin attribute as True
    filter_vals = {"admin": True}
    admin_user = utilities.filter_entities(constants.users, filter_vals)
    return admin_user

def set_revoke_admin(user_entity, action: str):
    if action == "SET":
        user_entity["admin"] = True
        client.put(user_entity)
        patched_user = client.get(user_entity.key)
        return patched_user
    elif action == "REVOKE":
        user_entity["admin"] = False
        client.put(user_entity)
        patched_user = client.get(user_entity.key)
        return patched_user

def check_user_datastore(constants,filter_vals):
    user_entity = utilities.get_filtered_entity(constants, filter_vals)
    if user_entity == []:
        return None
    else:
        return user_entity