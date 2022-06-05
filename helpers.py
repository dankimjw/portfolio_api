# -*- coding: utf-8 -*-
import constants
from datetime import date
from six.moves.urllib.request import urlopen
from flask_cors import cross_origin
from jose import jwt

class Utilities:
    """Utilities class used to help with checking attributes of Entities
    with possibility to expand in the future with more help methods.

    Attributes:
        model_attributes: a dictionary of data models and their attributes
            e.g {"boats": [attribute1, attribute2]}
        g_client: Google datastore client object via datastore.Client().
    """
    def __init__(self, client):
        """Initializes Utilities object with data model attributes
        and datastore client object.

        Args:
            data_model_attributes: a dictionary of data models and their attributes
            saved in the model_attributes attribute.
            e.g. {"boats": ["name", "type", "length"], "loads": ["volume", "item", "creation_date"]}
            client: Google datastore client object via datastore.Client() saved in the
            g_client attribute.
            industries: List of string valued industry names that are used as attribute values for the
            entities Users and Clients
        """
        self.model_attributes = {}
        self.industries = ["Information Technology", "Information Technology", "Health Care",
                           "Financials", "Consumer Discretionary", "Communication Services",
                           "Industrials", "Consumer Staples", "Energy Utilities", "Real Estate",
                           "Materials"]
        self.g_client = client

    def add_model_attributes(self, data_model_attributes):
        """Adds the data model attributes to the object

        Args:
            data_model_attributes: A list containing attributes the data model saved in self.model_attributes.

        """
        self.model_attributes = data_model_attributes

    def compare_keys(self, model_keys: list, target_keys: list):
        """Iterates through model_keys and checks the target_keys list for
        matching values. If an attribute in model_keys is not found in
        the target_keys list, the string "invalid" will be appended to the
        results list. If the attribute is found, the string 'valid' will be
        appended to the results list.

        Args:
            model_keys: A list containing a subsection of self.model_attributes.
            e.g. model_attributes["boats"]
            target_keys: A list of strings which are the keys of the request.get_json() method.
            The JSON data must be converted to a list

        Returns:
            A list of strings containing "valid" or "invalid" respective to whether model_key
            member was found in the target_keys list.
        """
        results = []
        for m_key in model_keys:
            if m_key not in target_keys:
                results.append("invalid")
            else:
                results.append("valid")
        return list(results)

    def check_valid(self, data_model_name: str, target_content: dict):
        """Calls the method compare_keys with a list of the selected
        data model attributes and response content body keys.
        Args:
            data_model_name: A string matching one of the keys in self.model_attributes.
            e.g. model_attributes["boats"] "boats" would be the key
            target_content: A dictionary of attributes which are the keys of the request.get_json() method.
            The JSON data must be converted to a list

        Returns:
            "Invalid" or "Valid" as a string
        """
        # Convert content to a list of just the keys
        target_attributes = list(target_content.keys())
        # get the specific data model attributes
        data_model_attributes = self.model_attributes[data_model_name]
        check_list = self.compare_keys(data_model_attributes, target_attributes)
        if "invalid" in check_list:
            print("invalid check_valid")
            return "invalid"
        else:
            return "valid"

    def get_key_entity(self, constants, entity_id: int):
        """Utilizes the Google datastore client object and calls the key and get methods
        for the respective constants and entity_id
        Args:
            constants: A string matching one of the entity names such as boats or loads
            entity_id: An integer value from boat_id or load_id

        Returns:
            entity_key: google datastore entity key
            entity: google datastore entity object
        """
        entity_key = self.g_client.key(constants, entity_id)
        entity = self.g_client.get(key=entity_key)
        return entity_key, entity

    def check_duplicate(self, constants: str, content):
        """Utilizes the Google datastore client object and queries entities defined by
        the constants string. Then the "name" attribute of the queried entities are compared
        to the content["name"] sent by the client. If there is a duplicate, the string "duplicate"
        is returned. If there is no duplicate name found, then "unique" is returned.
        Args:
            constants: A string matching one of the entity names such as boats or loads
            content: Request body JSON

        Returns:
            "duplicate" or "unique" string.
        """
        query = self.g_client.query(kind=constants)
        # Check if there is an entity with that name already
        query = query.add_filter('name','=', str(content["name"]))
        results = list(query.fetch())
        # if the results list is empty
        if not results and len(results) == 0:
            return "unique"
        else:
            return "duplicate"


    def check_type_valid (self, content):
        """ Method is called in check_datatype_valid. Used to validate client sent data for
        the "type" attribute in the boats entity.
        Check List:
            1. Must be a string.
            2. Minimum of 3 to maximum of 30 characters.
            3. Must be a combination of alphanumeric characters.
            4. Cannot have leading or trailing spaces.

        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        if isinstance(content["type"], str):
            # Check for leading and trailing spaces
            if content["type"][0].isspace() or content["type"][len(content["type"]) - 1].isspace():
                return False
            # Check if any part of the name is something other than alphanumeric and space
            if not all(x.isalpha() or x.isspace() or x.isnumeric() for x in content["type"]):
                return False
            type_num_chars = len(content["type"])
            if type_num_chars < 3 or type_num_chars > 30:
                return False
            # Check if type is all integers only
            try:
                int(content["type"])
                int_only_2 = True
            except ValueError as e:
                int_only_2 = False
            if int_only_2:
                return False
        else:
            return False

    def check_length_valid(self, content):
        """ Method is called in check_datatype_valid. Used to validate client sent data
         for the "length" attribute in the boats entity.
        Check List:
            1. Must be an integer
            2. Minimum of 1 to maximum of 10 digits.
            3. Length values must be greater than or equal to 1.
        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        if isinstance(content["length"], int):
            length_num_digits = len(str(content["length"]))
            # Value of integer is equal to or less tha 0
            if content["length"] <= 0:
                return False
            # Number of digits in the length attribute is less than 1 or greater than 10
            if length_num_digits < 1 or length_num_digits > 10:
                return False
            # Check if type is all integers only
            try:
                int(content["length"])
                int_only_3 = True
            except ValueError as e:
                int_only_3 = False

            if not int_only_3:
                return False
        else:
            return False

    def check_industry_valid(self, content):
        """ Method is called in check_datatype_valid. Used to validate client sent data
         for the "industry" attribute in the Clients entity.
        Must be one of the following (Spelling and case must match exactly):
            Information Technology
            Health Care
            Financials
            Consumer Discretionary
            Communication Services
            Industrials
            Consumer Staples
            Energy
            Utilities
            Real Estate
            Materials
        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        if isinstance(content["industry"], str):
            if content["industry"] in self.industries:
                return True
            else:
                return False
        else:
            return False

    def check_budget_valid(self, content):
        """ Method is called in check_datatype_valid. Used to validate client sent data
         for the "budget" attribute in the Projects entity.
        Check List:
            1. Must be an integer
            2. Minimum of 1 to maximum of 10 digits.
            3. Budget values must be greater than or equal to 1.
        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        if isinstance(content["budget"], int):
            length_num_digits = len(str(content["budget"]))
            # Value of integer is equal to or less tha 0
            if content["budget"] <= 0:
                return False
            # Number of digits in the length attribute is less than 1 or greater than 10
            if length_num_digits < 1 or length_num_digits > 10:
                return False
            # Check if type is all integers only
            try:
                int(content["budget"])
                int_only_3 = True
            except ValueError as e:
                int_only_3 = False

            if not int_only_3:
                return False
            # Pass all tests
            return True
        else:
            return False

    def check_date_valid(self,date_value):
        """ Used to validate sent data the "start_date", "join_date", or "end_date" attribute in
            the projects, team_members, and client entities.
        Check List:
            1. Must be a string.
            2. Must be in valid date format "yyyy-mm-dd"`
            3. Cannot have leading or trailing spaces.

        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        print("date_value: ", date_value)
        valid_date = True
        if isinstance(date_value, str):
            print("date is a string")
            # Check for leading and trailing spaces
            if date_value[0].isspace() or date_value[len(date_value) - 1].isspace():
                print("spaces")
                return False

            try:
                date.fromisoformat(date_value)
            except ValueError as e:
                valid_date = False
            if not valid_date:
                print("not valid date")
                return False
            else:
                # Pass all tests
                return True
        else:
            return False

    def check_start_end_date(self, start_date, end_date):
        """ Used to validate start_date and end_date for Projects entity.
            [1] start_date and end_date should be valid dates
            [2] start_date should come before end_date
        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        try:
            # Check if dates have valid date formats and values
            date.fromisoformat(start_date)
            date.fromisoformat(end_date)
        except:
            # Not a valid date format
            return False
        # Check if the start date comes before the end_date
        if start_date < end_date:
            return True
        else:
            return False

    def check_text_valid(self, content, attribute, min: int, max: int):
        """ Method is called in check_datatype_valid. Used to validate client sent data
        the "name", "specialty" attributes in the projects, team_members, clients entities.
        Check List:
            1. Must be a string.
            2. Minimum of 3 to maximum of 30 characters.
            3. Must be a combination of alphanumeric characters.
            4. Cannot have leading or trailing spaces.

        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        print("check_text_valid: ", content[attribute])
        if isinstance(content[attribute], str):
            print("isinstance : ", True)
            # Check for leading and trailing spaces
            if content[attribute][0].isspace() or content[attribute][len(content[attribute]) - 1].isspace():
                return False
            # Check if any part of the name is something other than alphanumeric and space
            if not all(x.isalpha() or x.isspace() or x.isnumeric() for x in content[attribute]):
                print(content[attribute])
                print("not all letters")
                return False
            name_num_chars = len(content[attribute])
            if name_num_chars < min or name_num_chars > max:
                return False
            # Check if name is all integers only
            try:
                int(content[attribute])
                int_only = True
            except ValueError as e:
                int_only = False

            if int_only:
                return False
            # Pass all tests
            return True
        else:
            return False

    def check_team_members(self, content):
        """ Used to validate request body for team_members attribute
            in the projects entity's attributes.
            The team_members attribute should be contained in a list
            and each list member should have only "id" as the key with
            the corresponding value being a valid integer
            datatype.
        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        # Check if team_members attribute is in list form
        is_list = isinstance(content["team_members"], list)
        print("teammembers is list: ", is_list)
        if is_list is False:
            return False

        # Check if the list is empty
        if content["team_members"] == []:
            print("team_members is empty")
            return True

        # Check if team_members attribute has ID as an integer
        for member in content["team_members"]:
            # ID attribute value is not an integer
            try:
                int(member["id"])
                print("member id is integer?: yes")
            except ValueError as e:
                print("member id is integer?: no")
                return False
            # There are attributes other than ID
            if len(member) != 1:
                print("teammembers len: ", len(member))
                return False

        return True

    def check_client(self, content):
        """ Used to validate request body for client attribute
            in the projects entity attributes.
            The client attribute should only contain a valid "id"
            attribute with the corresponding value being a valid integer
            datatype.
        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        # Check if the attribute is null or None
        if content["client"] is None:
            print("client is null")
            return True
        # Check if Client's ID attribute is valid
        try:
            int(content["client"]["id"])
            print("client_id is integer?: yes")
        except ValueError as e:
            print("client_id is integer?: no")
            return False

        # Should only have 1 attribute which is ID
        if len(content["client"]) != 1:
            return False

        return True

    def check_projects(self,content):
        """ Used to validate request body for projects attribute
            in the clients and team_members entity attributes.
            The projects attribute should only contain a valid "id"
            attribute with the corresponding value being a valid integer
            datatype.
        Args:
            content: Request body JSON

        Returns:
            True or False
        """
        # Check if the attribute is null or None
        if content["projects"] is None:
            print("projects is null")
            return True
        # Check if project's ID attribute is valid
        try:
            int(content["projects"]["id"])
            print("projects id is integer?: yes")
        except ValueError as e:
            print("projects id is integer?: no")
            return False
        # Should only have 1 attribute which is ID
        if len(content["projects"]) != 2:
            return False

        project_content = content["projects"]
        print("project_content: ", project_content)
        is_valid_text = self.check_text_valid(project_content, "name", 3, 30)
        print("is_valid_text : ", is_valid_text)
        if is_valid_text is False:
            return False

        return True

    def check_id_datastore(self, sub_entity_name, content):
        """ Used to validate request body for entity relationship attributes.
            Primarily looks up "id" attribute of a sub entity with
            Projects entity (team_members, client) or Clients,Team_Members
            entities (projects).
            This method should be used after validating the sub-entities for datatype etc.
            If the id value is not found within DataStore, function returns False.
        Args:
            content: Request body JSON
            entity_name: Name of entity calling this method

        Returns:
            True or False
        """
        # Called by Clients or Team_Members entities
        if sub_entity_name == "projects" and content["projects"] is not None:
            project_id = content["projects"]["id"]
            project_key, project = self.get_key_entity(constants.projects, int(project_id))
            if project is None:
                return False
            else:
                return True

        # Called by Projects entity
        elif sub_entity_name == "clients" and content["client"] is not None:
            client_id = content["client"]["id"]
            print("client_id helpers: ", client_id)
            client_key, client = self.get_key_entity(constants.clients, int(client_id))
            if client is None:
                return False
            else:
                return True

        # Called by Projects entity
        elif sub_entity_name == "team_members" and content["team_members"] is not []:
            for member in content["team_members"]:
                team_member_id = member["id"]
                team_member_key, team_member = self.get_key_entity(constants.team_members, int(team_member_id))
                if team_member is None:
                    return False
            return True
        else:
            print("check id: empty value: True")
            return True

    def check_datatype_valid(self, entity_name, content, request_type: str):
        """ Calls data validation methods depending on the respective entity_name and request type
            [1] self.validate_clients_request(content, request_type)
            [2] self.validate_projects_request(content, request_type)
            [3] self.validate_team_members_request(content, request_type)
            Depending on the request_type, data validation will be performed using the
            check functions listed above.

        Args:
            content: Request body JSON
            request_type: string value of the type of method such as "PATCH" or "POST"

        Returns:
            True or False
        """
        if entity_name == "clients":
            is_valid = self.validate_clients_request(content, request_type)
            return is_valid

        elif entity_name == "projects":
            is_valid = self.validate_projects_request(content, request_type)
            return is_valid

        elif entity_name == "team_members":
            is_valid = self.validate_team_members_request(content, request_type)
            return is_valid

    def validate_projects_request(self, content, request_type: str):
        """ Called by the method self.check_datatype_valid(self, entity_name, content, request_type: str)
            Used to validate request body for projects entity route
            Data validation depends on the request_type
            POST: Requires 5 attributes
            PUT: Requires 7 attributes which includes client and team_members entity relationship attributes
            PATCH: Requires at least 1 attribute

        Args:
            content: Request body JSON
            request_type: string value of the type of method such as "PATCH" or "POST"

        Returns:
            True or False
        """
        # For Projects Entity
        if request_type == "POST":
            # Check if the number of required attributes match
            if len(content) != 5:
                print("Not 5 attributes")
                return False
            # ---- Check "name" attribute -----
            # Name requires to be alphanumeric and space values only
            name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
            if name_result is False:
                return False
            # ---- Check "budget" attribute -----
            # type requires to be alphanumeric and space values only
            budget_result = self.check_budget_valid(content)
            if budget_result is False:
                return False
            # ---- Check "description" attribute -----
            # length should be an integer only
            description_result = self.check_text_valid(content, attribute="description", min=3, max=50)
            if description_result is False:
                return False
            # ---- Check "start_date" attribute -----
            # start_date_result should be a valid date
            start_date_result = self.check_date_valid(content["start_date"])
            if start_date_result is False:
                return False
            # ---- Check "start_date" attribute -----
            # end_date_result should be a valid date
            end_date_result = self.check_date_valid(content["end_date"])
            if end_date_result is False:
                return False
        # All tests pass for all 5 attributes
            return True
        elif request_type == "PUT":
            # PUT request requires team_members and client attributes to be included in request body
            # Check if the number of required attributes match
            if len(content) != 7:
                print("Not 7 attributes")
                return False
            # ---- Check "name" attribute -----
            # Name requires to be alphanumeric and space values only
            name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
            print("name_result ", name_result)
            if name_result is False:
                return False
            # ---- Check "budget" attribute -----
            # type requires to be alphanumeric and space values only
            budget_result = self.check_budget_valid(content)
            print("budget_result ", budget_result)
            if budget_result is False:
                return False
            # ---- Check "description" attribute -----
            # length should be an integer only
            description_result = self.check_text_valid(content, attribute="description", min=3, max=50)
            print("description_result ", description_result)
            if description_result is False:
                return False
            # ---- Check "start_date" attribute -----
            # start_date_result should be a valid date
            start_date_result = self.check_date_valid(content["start_date"])
            print("start_date_result ", start_date_result)
            if start_date_result is False:
                return False
            # ---- Check "start_date" attribute -----
            # end_date_result should be a valid date
            end_date_result = self.check_date_valid(content["end_date"])
            print("end_date_result ", end_date_result)
            if end_date_result is False:
                return False
            # ---- Check "team_members" attribute -----
            # team_members should be a valid date
            team_members_result = self.check_team_members(content)
            print("team_members_result ", team_members_result)
            if team_members_result is False:
                return False
            team_member_in_datastore = self.check_id_datastore("team_members", content)
            print("team_member_in_datastore ", team_member_in_datastore)
            if team_member_in_datastore is False:
                return False
            # ---- Check "client" attribute -----
            # client should be a valid date
            client_result = self.check_client(content)
            print("client_result ", client_result)
            if client_result is False:
                return False
            client_in_datastore = self.check_id_datastore("clients", content)
            print("client_in_datastore ", client_in_datastore)
            if client_in_datastore is False:
                return False
            # All tests pass for all 5 attributes
            return True

        elif request_type == "PATCH":
            number_attributes = len(content)
            if number_attributes < 1:
                return False
            attributes = content.keys()
            for attr in attributes:
                if attr == "name":
                    # ---- Check "name" attribute -----
                    # Name requires to be alphanumeric and space values only
                    name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
                    if name_result is False:
                        return False
                elif attr == "description":
                    # ---- Check "description" attribute -----
                    # length should be an integer only
                    description_result = self.check_text_valid(content, attribute="description", min=3, max=50)
                    print("description_result: ", description_result)
                    if description_result is False:
                        return False
                elif attr == "budget":
                    # ---- Check "budget" attribute -----
                    # type requires to be alphanumeric and space values only
                    budget_result = self.check_budget_valid(content)
                    print("budget_result: ", budget_result)
                    if budget_result is False:
                        return False
                elif attr == "start_date":
                    # ---- Check "start_date" attribute -----
                    # start_date_result should be a valid date
                    start_date_result = self.check_date_valid(content["start_date"])
                    print("start_date_result: ", start_date_result)
                    if start_date_result is False:
                        return False
                elif attr == "end_date":
                    # ---- Check "start_date" attribute -----
                    # start_date_result should be a valid date
                    end_date_result = self.check_date_valid(content["end_date"])
                    if end_date_result is False:
                        return False

                elif attr == "team_members":
                    # ---- Check "team_members" attribute -----
                    # team_members should be a valid date
                    team_members_result = self.check_team_members(content)
                    print("team_members_result: ", team_members_result)
                    if team_members_result is False:
                        return False
                    team_member_in_datastore = self.check_id_datastore("team_members", content)
                    if team_member_in_datastore is False:
                        return False

                elif attr == "client":
                    # ---- Check "client" attribute -----
                    # client should be a valid date
                    client_result = self.check_client(content)
                    print("client_result: ", client_result)
                    if client_result is False:
                        return False
                    client_in_datastore = self.check_id_datastore("clients", content)
                    if client_in_datastore is False:
                        return False
                # Client provides team_members entity attribute that is not "name",
                # "description", "start_date", "end_date", "team_members", "client"
            # Pass all tests
            return True
        else:
            return False

    def validate_team_members_request(self, content, request_type: str):
        """ Called by the method self.check_datatype_valid(self, entity_name, content, request_type: str)
            Used to validate request body for team_members entity route
            Data validation depends on the request_type
            POST: Requires 3 attributes
            PUT: Requires 4 attributes which includes projects entity relationship attributes
            PATCH: Requires at least 1 attribute

        Args:
            content: Request body JSON
            request_type: string value of the type of method such as "PATCH" or "POST"

        Returns:
            True or False
        """
        # For team_members Entity
        if request_type == "POST":
            # Check if the number of required attributes match
            if len(content) != 3:
                print("Not 3 attributes")
                return False
            # ---- Check "name" attribute -----
            # Name requires to be alphanumeric and space values only
            name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
            print("name_result: ", name_result)
            if name_result is False:
                return False
            # ---- Check "join_date" attribute -----
            # join_date should be a valid date
            join_date_result = self.check_date_valid(content["join_date"])
            print("join_date_result: ", join_date_result)
            if join_date_result is False:
                return False
            # ---- Check "specialty_result" attribute -----
            # specialty_result should be a valid date
            specialty_result = self.check_text_valid(content, attribute="specialty", min=3, max=20)
            print("specialty_result: ", specialty_result)
            if specialty_result is False:
                return False
            # All tests pass for all three attributes
            return True
        elif request_type == "PUT":
            # PUT request requires team_members and client attributes to be included in request body
            # Check if the number of required attributes match
            if len(content) != 4:
                print("team_members entity Not 4 attributes")
                return False
            # ---- Check "name" attribute -----
            # Name requires to be alphanumeric and space values only
            name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
            print("name_result: ", name_result)
            if name_result is False:
                return False
            # ---- Check "join_date" attribute -----
            # join_date should be a valid date
            join_date_result = self.check_date_valid(content["join_date"])
            print("join_date_result: ", join_date_result)
            if join_date_result is False:
                return False
            # ---- Check "specialty_result" attribute -----
            # specialty_result should be a valid text
            specialty_result = self.check_text_valid(content, attribute="specialty", min=3, max=20)
            print("specialty_result: ", specialty_result)
            if specialty_result is False:
                return False
            # projects should be valid with only ID sub-attribute
            projects_result = self.check_projects(content)
            if projects_result is False:
                return False
            project_in_datastore = self.check_id_datastore("projects", content)
            if project_in_datastore is False:
                return False
            # All tests pass for all three attributes
            return True
        elif request_type == "PATCH":
            number_attributes = len(content)
            if number_attributes < 1:
                return False
            attributes = content.keys()
            for attr in attributes:
                if attr == "name":
                    # ---- Check "name" attribute -----
                    # Name requires to be alphanumeric and space values only
                    name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
                    if name_result is False:
                        return False
                elif attr == "specialty":
                    # ---- Check "specialty_result" attribute -----
                    # specialty_result should be a valid text
                    specialty_result = self.check_text_valid(content, attribute="specialty", min=3, max=20)
                    print("specialty_result: ", specialty_result)
                    if specialty_result is False:
                        return False
                elif attr == "join_date":
                    # ---- Check "start_date" attribute -----
                    # start_date_result should be a valid text
                    join_date_result = self.check_date_valid(content["join_date"])
                    if join_date_result is False:
                        return False
                    # ---- Check "projects" attribute -----
                    # projects should be valid with only ID sub-attribute
                elif attr == "projects":
                    projects_result = self.check_projects(content)
                    if projects_result is False:
                        return False
                    project_in_datastore = self.check_id_datastore("projects", content)
                    if project_in_datastore is False:
                        return False
                # Client provides client entity attribute that is not "name", "industry", "join_date", "projects"
                else:
                    return False
            return True
        else:
            return False

    def validate_clients_request(self, content, request_type: str):
        """ Called by the method self.check_datatype_valid(self, entity_name, content, request_type: str)
            Used to validate request body for clients entity route
            Data validation depends on the request_type
            POST: Requires 3 attributes
            PUT: Requires 4 attributes which includes projects entity relationship attributes
            PATCH: Requires at least 1 attribute

        Args:
            content: Request body JSON
            request_type: string value of the type of method such as "PATCH" or "POST"

        Returns:
            True or False
        """
        if request_type == "POST":
            if len(content) != 3:
                return False
            # ---- Check "name" attribute -----
            # Name requires to be alphanumeric and space values only
            name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
            if name_result is False:
                return False
            # ---- Check "industry" attribute -----
            # Should be chose from list of industries given
            industry_result = self.check_industry_valid(content)
            if industry_result is False:
                return False
            # ---- Check "join_date" attribute -----
            # join_date should be a valid date
            join_date_result = self.check_date_valid(content["join_date"])
            if join_date_result is False:
                return False

            return True
        elif request_type == "PUT":
            # Must include the projects attribute
            if len(content) != 4:
                return False
            # ---- Check "name" attribute -----
            # Name requires to be alphanumeric and space values only
            name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
            if name_result is False:
                return False
            # ---- Check "industry" attribute -----
            # Should be chose from list of industries given
            industry_result = self.check_industry_valid(content)
            if industry_result is False:
                return False
            # ---- Check "join_date" attribute -----
            # join_date should be a valid date
            join_date_result = self.check_date_valid(content["join_date"])
            if join_date_result is False:
                return False
            # ---- Check "projects" attribute -----
            # projects should be valid with only ID sub-attribute
            projects_result = self.check_projects(content)
            if projects_result is False:
                return False
            project_in_datastore = self.check_id_datastore("projects", content)
            if project_in_datastore is False:
                return False
            # Pass all tests
            return True
        elif request_type == "PATCH":
            number_attributes = len(content)
            if number_attributes < 1:
                return False
            attributes = content.keys()
            for attr in attributes:
                if attr == "name":
                    # ---- Check "name" attribute -----
                    # Name requires to be alphanumeric and space values only
                    name_result = self.check_text_valid(content, attribute="name", min=3, max=30)
                    if name_result is False:
                        return False
                elif attr == "industry":
                    # ---- Check "type" attribute -----
                    # type requires to be alphanumeric and space values only
                    industry_result = self.check_industry_valid(content)
                    if industry_result is False:
                        return False
                elif attr == "join_date":
                    # ---- Check "start_date" attribute -----
                    # start_date_result should be a valid date
                    join_date_result = self.check_date_valid(content["join_date"])
                    if join_date_result is False:
                        return False
                elif attr == "projects":
                    # ---- Check "projects" attribute -----
                    # projects should be valid with only ID sub-attribute
                    projects_result = self.check_projects(content)
                    if projects_result is False:
                        return False
                    project_in_datastore = self.check_id_datastore("projects", content)
                    if project_in_datastore is False:
                        return False
                # Client provides client entity attribute that is not "name", "industry", "join_date", "projects"
                else:
                    return False
            return True

        else:
            return False

    def get_pagination(self,limit: int, offset: int, request, constants, filters={}):
        """ Called in routes to paginate GET request results.
        Utilizes Google DataStore client and client methods

        Args:
            limit: Max count of results per page
            offest: How many results to offset by before returning results
            request: Actual request received
            constants: name of the entity found in constants file e.g. "constants.projects"
            filters: dictionary of key-value pairs that are used to filter the entities

        Returns:
            q_limit , q_offset, and l_iterator
        """
        query = self.g_client.query(kind=constants)
        if filters:
            for filter,values in filters.items():
                print("filter: ", filter)
                print("values: ", values)
                query.add_filter(filter, "=", values)
        q_limit = int(request.args.get('limit', str(limit)))
        q_offset = int(request.args.get('offset', str(offset)))
        l_iterator = query.fetch(limit=q_limit, offset=q_offset)
        return q_limit, q_offset, l_iterator

    def filter_entities(self, constants_name, filters: dict):
        """ Called in routes to filter for entities.
        Utilizes Google DataStore client and client methods

        Args:
            constants_name: name of the entity found in constants file e.g. "constants.projects"
            filters: dictionary of key-value pairs that are used to filter the entities

        Returns:
            results: a list of entity results obtained from Google DataStore
        """
        query = self.g_client.query(kind=constants_name)
        for filter,values in filters.items():
            print("filter: ", filter)
            print("values: ", values)
            query.add_filter(filter, "=", values)
        results = list(query.fetch())
        return results

    def get_filtered_entity(self, constants_name, filters: dict):
        """ Called in routes to filter for an entity.
        Utilizes Google DataStore client and client methods.
        Method mainly used in admin.py and called by the method
        def check_user_datastore(constants,filter_vals).

        Args:
            constants_name: name of the entity found in constants file e.g. "constants.projects"
            filters: dictionary of key-value pairs that are used to filter the entities

        Returns:
            entity: returns the first matching entity
        """
        query = self.g_client.query(kind=constants_name)
        for filter,values in filters.items():
            print("filter: ", filter)
            print("values: ", values)
            query.add_filter(filter, "=", values)
        results = query.fetch()
        for res in results:
            print("res: ", res)
            print("res key: ", res.key.id)
            entity_key = self.g_client.key(constants_name, res.key.id)
            entity = self.g_client.get(key=entity_key)
            return entity

    def check_team_member_project(self, project_entity, team_member_entity):
        """ Called in /<project_id>/team_members/<team_member_id> route.
        Method mainly used to check if a team_member entity is already assigned
        to a project entity

        Args:
            project_entity: project entity object
            team_member_entity: team_member entity object

        Returns:
            True if team member is found in a project
            False if a team member is not found in a project
        """
        if project_entity["team_members"] is not []:
            for member in project_entity["team_members"]:
                if member["id"] == team_member_entity.key.id:
                    return True
        return False