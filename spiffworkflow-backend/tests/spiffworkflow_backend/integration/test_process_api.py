"""Test Process Api Blueprint."""
import io
import json
import os
import time
from typing import Any
from typing import Dict

import pytest
from flask.app import Flask
from flask.testing import FlaskClient
from SpiffWorkflow.task import TaskState  # type: ignore
from tests.spiffworkflow_backend.helpers.base_test import BaseTest
from tests.spiffworkflow_backend.helpers.test_data import load_test_spec

from spiffworkflow_backend.exceptions.process_entity_not_found_error import (
    ProcessEntityNotFoundError,
)
from spiffworkflow_backend.models.db import db
from spiffworkflow_backend.models.group import GroupModel
from spiffworkflow_backend.models.human_task import HumanTaskModel
from spiffworkflow_backend.models.process_group import ProcessGroup
from spiffworkflow_backend.models.process_instance import ProcessInstanceModel
from spiffworkflow_backend.models.process_instance import ProcessInstanceStatus
from spiffworkflow_backend.models.process_instance_metadata import (
    ProcessInstanceMetadataModel,
)
from spiffworkflow_backend.models.process_instance_report import (
    ProcessInstanceReportModel,
)
from spiffworkflow_backend.models.process_model import NotificationType
from spiffworkflow_backend.models.process_model import ProcessModelInfoSchema
from spiffworkflow_backend.models.spec_reference import SpecReferenceCache
from spiffworkflow_backend.models.task import TaskModel  # noqa: F401
from spiffworkflow_backend.models.user import UserModel
from spiffworkflow_backend.routes.tasks_controller import _dequeued_interstitial_stream
from spiffworkflow_backend.services.authorization_service import AuthorizationService
from spiffworkflow_backend.services.file_system_service import FileSystemService
from spiffworkflow_backend.services.process_caller_service import ProcessCallerService
from spiffworkflow_backend.services.process_instance_processor import (
    ProcessInstanceProcessor,
)
from spiffworkflow_backend.services.process_instance_service import (
    ProcessInstanceService,
)
from spiffworkflow_backend.services.process_model_service import ProcessModelService

# from spiffworkflow_backend.services.git_service import GitService


class TestProcessApi(BaseTest):
    """TestProcessAPi."""

    def test_returns_403_if_user_does_not_have_permission(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
    ) -> None:
        """Test_returns_403_if_user_does_not_have_permission."""
        user = self.find_or_create_user()
        response = client.get(
            "/v1.0/process-groups",
            headers=self.logged_in_headers(user),
        )
        assert response.status_code == 403

        self.add_permissions_to_user(user, target_uri="/v1.0/process-groups", permission_names=["read"])
        response = client.get(
            "/v1.0/process-groups",
            headers=self.logged_in_headers(user),
        )
        assert response.status_code == 200

        response = client.post(
            "/v1.0/process-groups",
            headers=self.logged_in_headers(user),
        )
        assert response.status_code == 403

    def test_permissions_check(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
    ) -> None:
        """Test_permissions_check."""
        user = self.find_or_create_user()
        self.add_permissions_to_user(user, target_uri="/v1.0/process-groups", permission_names=["read"])
        request_body = {
            "requests_to_check": {
                "/v1.0/process-groups": ["GET", "POST"],
                "/v1.0/process-models": ["GET"],
            }
        }
        expected_response_body = {
            "results": {
                "/v1.0/process-groups": {"GET": True, "POST": False},
                "/v1.0/process-models": {"GET": False},
            }
        }
        response = client.post(
            "/v1.0/permissions-check",
            headers=self.logged_in_headers(user),
            content_type="application/json",
            data=json.dumps(request_body),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json == expected_response_body

    def test_process_model_create(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_create."""
        process_group_id = "test_process_group"
        process_group_display_name = "Test Process Group"
        # creates the group directory, and the json file
        self.create_process_group_with_api(client, with_super_admin_user, process_group_id, process_group_display_name)

        process_model_id = "sample"
        model_display_name = "Sample"
        model_description = "The Sample"
        process_model_identifier = f"{process_group_id}/{process_model_id}"

        # creates the model directory, and adds the json file
        self.create_process_model_with_api(
            client,
            process_model_id=process_model_identifier,
            process_model_display_name=model_display_name,
            process_model_description=model_description,
            user=with_super_admin_user,
        )
        process_model = ProcessModelService.get_process_model(
            process_model_identifier,
        )
        assert model_display_name == process_model.display_name
        assert 0 == process_model.display_order
        assert 1 == len(ProcessModelService.get_process_groups())

        # add bpmn file to the model
        bpmn_file_name = "sample.bpmn"
        bpmn_file_data_bytes = self.get_test_data_file_contents(bpmn_file_name, "sample")
        self.create_spec_file(
            client,
            process_model_id=process_model.id,
            process_model_location="sample",
            process_model=process_model,
            file_name=bpmn_file_name,
            file_data=bpmn_file_data_bytes,
            user=with_super_admin_user,
        )
        # get the model, assert that primary is set
        process_model = ProcessModelService.get_process_model(process_model_identifier)
        assert process_model.primary_file_name == bpmn_file_name
        assert process_model.primary_process_id == "sample"

    def test_process_model_create_with_natural_language(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_create_with_natural_language."""
        process_group_id = "test_process_group"
        process_group_description = "Test Process Group"
        process_model_id = "sample"
        process_model_identifier = f"{process_group_id}/{process_model_id}"
        self.create_process_group_with_api(client, with_super_admin_user, process_group_id, process_group_description)

        text = "Create a Bug Tracker process model "
        text += "with a Bug Details form that collects summary, description, and priority"
        body = {"natural_language_text": text}
        self.create_process_model_with_api(
            client,
            process_model_id=process_model_identifier,
            user=with_super_admin_user,
        )
        response = client.post(
            f"/v1.0/process-models-natural-language/{process_group_id}",
            content_type="application/json",
            data=json.dumps(body),
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 201
        assert response.json is not None
        assert response.json["id"] == f"{process_group_id}/bug-tracker"
        assert response.json["display_name"] == "Bug Tracker"
        assert response.json["metadata_extraction_paths"] == [
            {"key": "summary", "path": "summary"},
            {"key": "description", "path": "description"},
            {"key": "priority", "path": "priority"},
        ]

        process_model = ProcessModelService.get_process_model(response.json["id"])
        process_model_path = os.path.join(
            FileSystemService.root_path(),
            FileSystemService.id_string_to_relative_path(process_model.id),
        )

        process_model_diagram = os.path.join(process_model_path, "bug-tracker.bpmn")
        assert os.path.exists(process_model_diagram)
        form_schema_json = os.path.join(process_model_path, "bug-details-schema.json")
        assert os.path.exists(form_schema_json)
        form_uischema_json = os.path.join(process_model_path, "bug-details-uischema.json")
        assert os.path.exists(form_uischema_json)

        process_instance_report = ProcessInstanceReportModel.query.filter_by(identifier="bug-tracker").first()
        assert process_instance_report is not None
        report_column_accessors = [i["accessor"] for i in process_instance_report.report_metadata["columns"]]
        expected_column_accessors = [
            "id",
            "process_model_display_name",
            "start_in_seconds",
            "end_in_seconds",
            "process_initiator_username",
            "status",
            "summary",
            "description",
            "priority",
        ]
        assert report_column_accessors == expected_column_accessors

    def test_primary_process_id_updates_via_xml(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_primary_process_id_updates_via_xml."""
        process_group_id = "test_group"
        process_model_id = "sample"
        process_model_identifier = f"{process_group_id}/{process_model_id}"
        initial_primary_process_id = "sample"
        terminal_primary_process_id = "new_process_id"
        self.create_process_group_with_api(
            client=client, user=with_super_admin_user, process_group_id=process_group_id
        )

        bpmn_file_name = f"{process_model_id}.bpmn"
        bpmn_file_source_directory = process_model_id
        process_model = load_test_spec(
            process_model_id=process_model_identifier,
            bpmn_file_name=bpmn_file_name,
            process_model_source_directory=process_model_id,
        )
        assert process_model.primary_process_id == initial_primary_process_id

        bpmn_file_data_bytes = self.get_test_data_file_contents(bpmn_file_name, bpmn_file_source_directory)
        bpmn_file_data_string = bpmn_file_data_bytes.decode("utf-8")
        old_string = f'bpmn:process id="{initial_primary_process_id}"'
        new_string = f'bpmn:process id="{terminal_primary_process_id}"'
        updated_bpmn_file_data_string = bpmn_file_data_string.replace(old_string, new_string)
        updated_bpmn_file_data_bytes = bytearray(updated_bpmn_file_data_string, "utf-8")
        data = {"file": (io.BytesIO(updated_bpmn_file_data_bytes), bpmn_file_name)}

        modified_process_model_id = process_model_identifier.replace("/", ":")
        response = client.put(
            f"/v1.0/process-models/{modified_process_model_id}/files/{bpmn_file_name}",
            data=data,
            follow_redirects=True,
            content_type="multipart/form-data",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        process_model = ProcessModelService.get_process_model(process_model_identifier)
        assert process_model.primary_file_name == bpmn_file_name
        assert process_model.primary_process_id == terminal_primary_process_id

    def test_process_model_delete(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_delete."""
        process_group_id = "test_process_group"
        process_group_description = "Test Process Group"
        process_model_id = "sample"
        process_model_identifier = f"{process_group_id}/{process_model_id}"
        self.create_process_group_with_api(client, with_super_admin_user, process_group_id, process_group_description)
        self.create_process_model_with_api(
            client,
            process_model_id=process_model_identifier,
            user=with_super_admin_user,
        )

        # assert we have a model
        process_model = ProcessModelService.get_process_model(process_model_identifier)
        assert process_model is not None
        assert process_model.id == process_model_identifier

        # delete the model
        modified_process_model_identifier = process_model_identifier.replace("/", ":")
        response = client.delete(
            f"/v1.0/process-models/{modified_process_model_identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["ok"] is True

    def test_process_model_delete_with_instances(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_delete_with_instances."""
        test_process_group_id = "runs_without_input"
        test_process_model_id = "sample"
        bpmn_file_name = "sample.bpmn"
        bpmn_file_location = "sample"
        process_model_identifier = f"{test_process_group_id}/{test_process_model_id}"
        modified_process_model_identifier = process_model_identifier.replace("/", ":")
        self.create_process_group_with_api(client, with_super_admin_user, test_process_group_id)
        self.create_process_model_with_api(client, process_model_identifier, user=with_super_admin_user)
        bpmn_file_data_bytes = self.get_test_data_file_contents(bpmn_file_name, bpmn_file_location)
        self.create_spec_file(
            client=client,
            process_model_id=process_model_identifier,
            process_model_location=test_process_model_id,
            file_name=bpmn_file_name,
            file_data=bpmn_file_data_bytes,
            user=with_super_admin_user,
        )
        headers = self.logged_in_headers(with_super_admin_user)
        # create an instance from a model
        response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )

        data = json.loads(response.get_data(as_text=True))
        # make sure the instance has the correct model
        assert data["process_model_identifier"] == process_model_identifier

        # try to delete the model
        response = client.delete(
            f"/v1.0/process-models/{modified_process_model_identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        # make sure we get an error in the response
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert data["error_code"] == "existing_instances"
        assert (
            data["message"]
            == f"We cannot delete the model `{process_model_identifier}`, there are"
            " existing instances that depend on it."
        )

    def test_process_model_update(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_update."""
        self.create_process_group_with_api(client, with_super_admin_user, "test_process_group", "Test Process Group")
        process_model_identifier = "test_process_group/make_cookies"
        self.create_process_model_with_api(
            client,
            process_model_id=process_model_identifier,
            user=with_super_admin_user,
        )
        process_model = ProcessModelService.get_process_model(process_model_identifier)
        assert process_model.id == process_model_identifier
        assert process_model.display_name == "Cooooookies"
        assert process_model.primary_file_name is None
        assert process_model.primary_process_id is None

        process_model.display_name = "Updated Display Name"
        process_model.primary_file_name = "superduper.bpmn"
        process_model.primary_process_id = "superduper"
        process_model.metadata_extraction_paths = [{"key": "extraction1", "path": "path1"}]

        modified_process_model_identifier = process_model_identifier.replace("/", ":")
        response = client.put(
            f"/v1.0/process-models/{modified_process_model_identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
            content_type="application/json",
            data=json.dumps(ProcessModelInfoSchema().dump(process_model)),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["display_name"] == "Updated Display Name"
        assert response.json["primary_file_name"] == "superduper.bpmn"
        assert response.json["primary_process_id"] == "superduper"
        assert response.json["metadata_extraction_paths"] == [{"key": "extraction1", "path": "path1"}]

    def test_process_model_list_all(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_list_all."""
        group_id = "test_group/test_sub_group"
        self.create_process_group_with_api(client, with_super_admin_user, group_id)

        # add 5 models to the group
        for i in range(5):
            process_model_identifier = f"{group_id}/test_model_{i}"
            model_display_name = f"Test Model {i}"
            model_description = f"Test Model {i} Description"
            self.create_process_model_with_api(
                client,
                process_model_id=process_model_identifier,
                process_model_display_name=model_display_name,
                process_model_description=model_description,
                user=with_super_admin_user,
            )

        # get all models
        response = client.get(
            "/v1.0/process-models?per_page=1000&recursive=true",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 5
        assert response.json["pagination"]["count"] == 5
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 1

    def test_process_model_list(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_list."""
        # create a group
        group_id = "test_group"
        self.create_process_group_with_api(client, with_super_admin_user, group_id)

        # add 5 models to the group
        for i in range(5):
            process_model_identifier = f"{group_id}/test_model_{i}"
            model_display_name = f"Test Model {i}"
            model_description = f"Test Model {i} Description"
            self.create_process_model_with_api(
                client,
                process_model_id=process_model_identifier,
                process_model_display_name=model_display_name,
                process_model_description=model_description,
                user=with_super_admin_user,
            )

        # get all models
        response = client.get(
            f"/v1.0/process-models?process_group_identifier={group_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 5
        assert response.json["pagination"]["count"] == 5
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 1

        # get first page, 1 per page
        response = client.get(
            f"/v1.0/process-models?page=1&per_page=1&process_group_identifier={group_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 1
        assert response.json["results"][0]["id"] == "test_group/test_model_0"
        assert response.json["pagination"]["count"] == 1
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 5

        # get second page, 1 per page
        response = client.get(
            f"/v1.0/process-models?page=2&per_page=1&process_group_identifier={group_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 1
        assert response.json["results"][0]["id"] == "test_group/test_model_1"
        assert response.json["pagination"]["count"] == 1
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 5

        # get first page, 3 per page
        response = client.get(
            f"/v1.0/process-models?page=1&per_page=3&process_group_identifier={group_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 3
        assert response.json["results"][0]["id"] == "test_group/test_model_0"
        assert response.json["pagination"]["count"] == 3
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 2

        # get second page, 3 per page
        response = client.get(
            f"/v1.0/process-models?page=2&per_page=3&process_group_identifier={group_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        # there should only be 2 left
        assert response.json is not None
        assert len(response.json["results"]) == 2
        assert response.json["results"][0]["id"] == "test_group/test_model_3"
        assert response.json["pagination"]["count"] == 2
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 2

    def test_process_list(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """It should be possible to get a list of all processes known to the system."""
        load_test_spec(
            "test_group_one/simple_form",
            process_model_source_directory="simple_form",
            bpmn_file_name="simple_form",
        )
        # When adding a process model with one Process, no decisions, and some json files, only one process is recorded.
        assert len(SpecReferenceCache.query.all()) == 1

        self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id="test_group_two",
            process_model_id="call_activity_nested",
            bpmn_file_location="call_activity_nested",
        )
        # When adding a process model with 4 processes and a decision, 5 new records will be in the Cache
        assert len(SpecReferenceCache.query.all()) == 6

        # get the results
        response = client.get(
            "/v1.0/processes",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        # We should get 5 back, as one of the items in the cache is a decision.
        assert len(response.json) == 5
        simple_form = next(p for p in response.json if p["identifier"] == "Process_WithForm")
        assert simple_form["display_name"] == "Process With Form"
        assert simple_form["process_model_id"] == "test_group_one/simple_form"
        assert simple_form["has_lanes"] is False
        assert simple_form["is_executable"] is True
        assert simple_form["is_primary"] is True

    def test_process_callers(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """It should be possible to get a list of all processes that call another process."""
        load_test_spec(
            "test_group_one/simple_form",
            process_model_source_directory="simple_form",
            bpmn_file_name="simple_form",
        )
        # When adding a process model with one Process, no decisions, and some json files, only one process is recorded.
        assert len(SpecReferenceCache.query.all()) == 1
        # but no callers are recorded
        assert ProcessCallerService.count() == 0

        self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id="test_group_two",
            process_model_id="call_activity_nested",
            bpmn_file_location="call_activity_nested",
        )
        # When adding a process model with 4 processes and a decision, 5 new records will be in the Cache
        assert len(SpecReferenceCache.query.all()) == 6
        # and 4 callers recorded
        assert ProcessCallerService.count() == 4

        # get the results
        response = client.get(
            "/v1.0/processes/callers?bpmn_process_identifier=Level2",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        # We should get 1 back, Level1 calls Level2
        assert len(response.json) == 1
        caller = response.json[0]
        assert caller["identifier"] == "Level1"

    def test_process_group_add(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_add_process_group."""
        process_group = ProcessGroup(
            id="test",
            display_name="Another Test Category",
            display_order=0,
            admin=False,
            description="Test Description",
        )
        response = client.post(
            "/v1.0/process-groups",
            headers=self.logged_in_headers(with_super_admin_user),
            content_type="application/json",
            data=json.dumps(process_group.serialized),
        )
        assert response.status_code == 201
        assert response.json

        # Check what is returned
        result = ProcessGroup(**response.json)
        assert result is not None
        assert result.display_name == "Another Test Category"
        assert result.id == "test"
        assert result.description == "Test Description"

        # Check what is persisted
        persisted = ProcessModelService.get_process_group("test")
        assert persisted.display_name == "Another Test Category"
        assert persisted.id == "test"
        assert persisted.description == "Test Description"

    def test_process_group_delete(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_group_delete."""
        process_group_id = "test"
        process_group_display_name = "My Process Group"

        self.create_process_group_with_api(
            client,
            with_super_admin_user,
            process_group_id,
            display_name=process_group_display_name,
        )
        persisted = ProcessModelService.get_process_group(process_group_id)
        assert persisted is not None
        assert persisted.id == process_group_id

        client.delete(
            f"/v1.0/process-groups/{process_group_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        with pytest.raises(ProcessEntityNotFoundError):
            ProcessModelService.get_process_group(process_group_id)

    def test_process_group_update(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test Process Group Update."""
        group_id = "test_process_group"
        group_display_name = "Test Group"

        self.create_process_group_with_api(client, with_super_admin_user, group_id, display_name=group_display_name)
        process_group = ProcessModelService.get_process_group(group_id)

        assert process_group.display_name == group_display_name

        process_group.display_name = "Modified Display Name"

        response = client.put(
            f"/v1.0/process-groups/{group_id}",
            headers=self.logged_in_headers(with_super_admin_user),
            content_type="application/json",
            data=json.dumps(process_group.serialized),
        )
        assert response.status_code == 200

        process_group = ProcessModelService.get_process_group(group_id)
        assert process_group.display_name == "Modified Display Name"

    def test_process_group_list(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_group_list."""
        # add 5 groups
        for i in range(5):
            group_id = f"test_process_group_{i}"
            group_display_name = f"Test Group {i}"
            self.create_process_group_with_api(
                client, with_super_admin_user, group_id, display_name=group_display_name
            )

        # get all groups
        response = client.get(
            "/v1.0/process-groups",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 5
        assert response.json["pagination"]["count"] == 5
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 1

        # get first page, one per page
        response = client.get(
            "/v1.0/process-groups?page=1&per_page=1",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 1
        assert response.json["results"][0]["id"] == "test_process_group_0"
        assert response.json["pagination"]["count"] == 1
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 5

        # get second page, one per page
        response = client.get(
            "/v1.0/process-groups?page=2&per_page=1",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 1
        assert response.json["results"][0]["id"] == "test_process_group_1"
        assert response.json["pagination"]["count"] == 1
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 5

        # get first page, 3 per page
        response = client.get(
            "/v1.0/process-groups?page=1&per_page=3",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert len(response.json["results"]) == 3
        assert response.json["results"][0]["id"] == "test_process_group_0"
        assert response.json["results"][1]["id"] == "test_process_group_1"
        assert response.json["results"][2]["id"] == "test_process_group_2"
        assert response.json["pagination"]["count"] == 3
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 2

        # get second page, 3 per page
        response = client.get(
            "/v1.0/process-groups?page=2&per_page=3",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        # there should only be 2 left
        assert response.json is not None
        assert len(response.json["results"]) == 2
        assert response.json["results"][0]["id"] == "test_process_group_3"
        assert response.json["results"][1]["id"] == "test_process_group_4"
        assert response.json["pagination"]["count"] == 2
        assert response.json["pagination"]["total"] == 5
        assert response.json["pagination"]["pages"] == 2

    def test_process_model_file_update_fails_if_no_file_given(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_file_update."""
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        modified_process_model_id = process_model_identifier.replace("/", ":")

        data = {"key1": "THIS DATA"}
        response = client.put(
            f"/v1.0/process-models/{modified_process_model_id}/files/random_fact.svg",
            data=data,
            follow_redirects=True,
            content_type="multipart/form-data",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 400
        assert response.json is not None
        assert response.json["error_code"] == "no_file_given"

    def test_process_model_file_update_fails_if_contents_is_empty(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_file_update."""
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        modified_process_model_id = process_model_identifier.replace("/", ":")

        data = {"file": (io.BytesIO(b""), "random_fact.svg")}
        response = client.put(
            f"/v1.0/process-models/{modified_process_model_id}/files/random_fact.svg",
            data=data,
            follow_redirects=True,
            content_type="multipart/form-data",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 400
        assert response.json is not None
        assert response.json["error_code"] == "file_contents_empty"

    def test_process_model_file_update(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_file_update."""
        process_group_id = "test_group"
        process_group_description = "Test Group"
        process_model_id = "random_fact"
        process_model_identifier = f"{process_group_id}/{process_model_id}"
        self.create_process_group_with_api(client, with_super_admin_user, process_group_id, process_group_description)
        self.create_process_model_with_api(
            client,
            process_model_id=process_model_identifier,
            user=with_super_admin_user,
        )

        bpmn_file_name = "random_fact.bpmn"
        original_file = load_test_spec(
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            process_model_source_directory="random_fact",
        )

        modified_process_model_id = process_model_identifier.replace("/", ":")
        new_file_contents = b"THIS_IS_NEW_DATA"
        data = {"file": (io.BytesIO(new_file_contents), "random_fact.svg")}
        response = client.put(
            f"/v1.0/process-models/{modified_process_model_id}/files/random_fact.svg",
            data=data,
            follow_redirects=True,
            content_type="multipart/form-data",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 200
        assert response.json is not None
        assert response.json["file_contents"] is not None

        response = client.get(
            f"/v1.0/process-models/{modified_process_model_id}/files/random_fact.svg",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        updated_file = json.loads(response.get_data(as_text=True))
        assert original_file != updated_file
        assert updated_file["file_contents"] == new_file_contents.decode()

    def test_process_model_file_delete_when_bad_process_model(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_file_update."""
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        # self.create_spec_file(client, user=with_super_admin_user)

        # process_model = load_test_spec("random_fact")
        bad_process_model_identifier = f"x{process_model_identifier}"
        modified_bad_process_model_identifier = bad_process_model_identifier.replace("/", ":")
        response = client.delete(
            f"/v1.0/process-models/{modified_bad_process_model_identifier}/files/random_fact.svg",
            follow_redirects=True,
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 400
        assert response.json is not None
        assert response.json["error_code"] == "process_model_cannot_be_found"

    def test_process_model_file_delete_when_bad_file(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_file_update."""
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        modified_process_model_identifier = process_model_identifier.replace("/", ":")

        response = client.delete(
            f"/v1.0/process-models/{modified_process_model_identifier}/files/random_fact_DOES_NOT_EXIST.svg",
            follow_redirects=True,
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 400
        assert response.json is not None
        assert response.json["error_code"] == "process_model_file_cannot_be_found"

    def test_process_model_file_delete_when_primary_file(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        process_model = ProcessModelService.get_process_model(process_model_id=process_model_identifier)
        modified_process_model_identifier = process_model_identifier.replace("/", ":")

        response = client.delete(
            f"/v1.0/process-models/{modified_process_model_identifier}/files/{process_model.primary_file_name}",
            follow_redirects=True,
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 400
        assert response.json is not None
        assert response.json["error_code"] == "process_model_file_cannot_be_deleted"

    def test_process_model_file_delete(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_file_update."""
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        modified_process_model_identifier = process_model_identifier.replace("/", ":")

        self.create_spec_file(
            client,
            process_model_id=process_model_identifier,
            file_name="second_file.json",
            file_data=b"<h1>HEY</h1>",
            user=with_super_admin_user,
        )

        response = client.delete(
            f"/v1.0/process-models/{modified_process_model_identifier}/files/second_file.json",
            follow_redirects=True,
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 200
        assert response.json is not None
        assert response.json["ok"]

        response = client.get(
            f"/v1.0/process-models/{modified_process_model_identifier}/files/second_file.json",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 404

    def test_get_file(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_get_file."""
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        modified_process_model_identifier = process_model_identifier.replace("/", ":")

        response = client.get(
            f"/v1.0/process-models/{modified_process_model_identifier}/files/random_fact.bpmn",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["name"] == "random_fact.bpmn"
        assert response.json["process_model_id"] == "test_group/random_fact"

    def test_get_workflow_from_workflow_spec(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_get_workflow_from_workflow_spec."""
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        modified_process_model_identifier = process_model_identifier.replace("/", ":")

        response = client.post(
            f"/v1.0/process-instances/{modified_process_model_identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 201
        assert response.json is not None
        assert "test_group/random_fact" == response.json["process_model_identifier"]

    def test_get_process_groups_when_none(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_get_process_groups_when_none."""
        response = client.get(
            "/v1.0/process-groups",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["results"] == []

    def test_get_process_groups_when_there_are_some(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_get_process_groups_when_there_are_some."""
        self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        response = client.get(
            "/v1.0/process-groups",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 1
        assert response.json["pagination"]["count"] == 1
        assert response.json["pagination"]["total"] == 1
        assert response.json["pagination"]["pages"] == 1

    def test_get_process_group_when_found(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_get_process_group_when_found."""
        process_model_identifier = self.create_group_and_model_with_bpmn(client, with_super_admin_user)
        process_group_id, process_model_id = os.path.split(process_model_identifier)

        response = client.get(
            f"/v1.0/process-groups/{process_group_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 200
        assert response.json is not None
        assert response.json["id"] == process_group_id
        assert response.json["process_models"][0]["id"] == process_model_identifier
        assert response.json["parent_groups"] == []

    def test_get_process_group_show_when_nested(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_get_process_group_show_when_nested."""
        self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id="test_group_one",
            process_model_id="simple_form",
            bpmn_file_location="simple_form",
        )

        self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id="test_group_one/test_group_two",
            process_model_id="call_activity_nested",
            bpmn_file_location="call_activity_nested",
        )

        response = client.get(
            "/v1.0/process-groups/test_group_one:test_group_two",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 200
        assert response.json is not None
        assert response.json["id"] == "test_group_one/test_group_two"
        assert response.json["parent_groups"] == [{"display_name": "test_group_one", "id": "test_group_one"}]

    def test_get_process_model_when_found(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_get_process_model_when_found."""
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client, with_super_admin_user, bpmn_file_name="random_fact.bpmn"
        )
        modified_process_model_identifier = process_model_identifier.replace("/", ":")

        response = client.get(
            f"/v1.0/process-models/{modified_process_model_identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 200
        assert response.json is not None
        assert response.json["id"] == process_model_identifier
        assert len(response.json["files"]) == 1
        assert response.json["files"][0]["name"] == "random_fact.bpmn"
        assert response.json["parent_groups"] == [{"display_name": "test_group", "id": "test_group"}]

    def test_get_process_model_when_not_found(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_get_process_model_when_not_found."""
        process_model_dir_name = "THIS_NO_EXISTS"
        group_id = self.create_process_group_with_api(client, with_super_admin_user, "my_group")
        bad_process_model_id = f"{group_id}/{process_model_dir_name}"
        modified_bad_process_model_id = bad_process_model_id.replace("/", ":")
        response = client.get(
            f"/v1.0/process-models/{modified_bad_process_model_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 400
        assert response.json is not None
        assert response.json["error_code"] == "process_model_cannot_be_found"

    def test_process_instance_create(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_create."""
        test_process_model_id = "runs_without_input/sample"
        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(client, test_process_model_id, headers)
        assert response.json is not None
        assert response.json["updated_at_in_seconds"] is not None
        assert response.json["status"] == "not_started"
        assert response.json["process_model_identifier"] == test_process_model_id
        # TODO: mock out the responses for the git service so we can do something like this
        # current_revision = GitService.get_current_revision()
        # assert response.json["bpmn_version_control_identifier"] == current_revision

    def test_process_instance_run(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_run."""
        # process_model_id = "runs_without_input/sample"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id="runs_without_input",
            process_model_id="sample",
            bpmn_file_name=None,
            bpmn_file_location="sample",
        )

        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        assert response.json is not None
        process_instance_id = response.json["id"]
        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.json is not None
        assert type(response.json["updated_at_in_seconds"]) is int
        assert response.json["updated_at_in_seconds"] > 0
        assert response.json["status"] == "complete"
        assert response.json["process_model_identifier"] == process_model_identifier
        assert response.json["data"]["Mike"] == "Awesome"
        assert response.json["data"]["person"] == "Kevin"

    def test_process_instance_show(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_show."""
        process_group_id = "simple_script"
        process_model_id = "simple_script"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
        )
        modified_process_model_identifier = self.modify_process_identifier_for_path_param(process_model_identifier)
        headers = self.logged_in_headers(with_super_admin_user)
        create_response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        assert create_response.json is not None
        process_instance_id = create_response.json["id"]
        client.post(
            f"/v1.0/process-instances/{modified_process_model_identifier}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        show_response = client.get(
            f"/v1.0/process-instances/{modified_process_model_identifier}/{process_instance_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert show_response.json is not None
        assert show_response.status_code == 200
        file_system_root = FileSystemService.root_path()
        file_path = f"{file_system_root}/{process_model_identifier}/{process_model_id}.bpmn"
        with open(file_path) as f_open:
            xml_file_contents = f_open.read()
            assert show_response.json["bpmn_xml_file_contents"] == xml_file_contents

    def test_process_instance_show_with_specified_process_identifier(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_show_with_specified_process_identifier."""
        process_model_id = "call_activity_nested"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id="test_group_two",
            process_model_id=process_model_id,
            bpmn_file_location="call_activity_nested",
        )
        spec_reference = SpecReferenceCache.query.filter_by(identifier="Level2b").first()
        assert spec_reference
        modified_process_model_identifier = self.modify_process_identifier_for_path_param(process_model_identifier)
        headers = self.logged_in_headers(with_super_admin_user)
        create_response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        assert create_response.json is not None
        assert create_response.status_code == 201
        process_instance_id = create_response.json["id"]
        run_response = client.post(
            f"/v1.0/process-instances/{modified_process_model_identifier}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert run_response.status_code == 200
        show_response = client.get(
            f"/v1.0/process-instances/{modified_process_model_identifier}/{process_instance_id}?process_identifier={spec_reference.identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert show_response.json is not None
        assert show_response.status_code == 200
        file_system_root = FileSystemService.root_path()
        process_instance_file_path = f"{file_system_root}/{process_model_identifier}/{process_model_id}.bpmn"
        with open(process_instance_file_path) as f_open:
            xml_file_contents = f_open.read()
            assert show_response.json["bpmn_xml_file_contents"] != xml_file_contents
        spec_reference_file_path = os.path.join(file_system_root, spec_reference.relative_path)
        with open(spec_reference_file_path) as f_open:
            xml_file_contents = f_open.read()
            assert show_response.json["bpmn_xml_file_contents"] == xml_file_contents

    def test_message_send_when_starting_process_instance(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_message_send_when_starting_process_instance."""
        # ensure process model is loaded
        process_group_id = "test_message_send"
        process_model_id = "message_receiver"
        bpmn_file_name = "message_receiver.bpmn"
        bpmn_file_location = "message_send_one_conversation"
        self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        message_model_identifier = "Request Approval"
        payload = {
            "customer_id": "sartography",
            "po_number": "1001",
            "amount": "One Billion Dollars! Mwhahahahahaha",
            "description": "But seriously.",
        }
        response = client.post(
            f"/v1.0/messages/{message_model_identifier}",
            content_type="application/json",
            headers=self.logged_in_headers(with_super_admin_user),
            data=json.dumps({"payload": payload}),
        )
        assert response.status_code == 200
        json_data = response.json
        assert json_data
        assert json_data["status"] == "complete"
        process_instance_id = json_data["id"]
        process_instance = ProcessInstanceModel.query.filter_by(id=process_instance_id).first()
        assert process_instance

        processor = ProcessInstanceProcessor(process_instance)
        process_instance_data = processor.get_data()
        assert process_instance_data
        assert process_instance_data["invoice"] == payload

    def test_message_send_when_providing_message_to_running_process_instance(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_message_send_when_providing_message_to_running_process_instance."""
        process_group_id = "test_message_send"
        process_model_id = "message_sender"
        bpmn_file_name = "message_sender.bpmn"
        bpmn_file_location = "message_send_one_conversation"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        message_model_identifier = "Approval Result"
        payload = {
            "customer_id": "sartography",
            "po_number": "1001",
            "amount": "One Billion Dollars! Mwhahahahahaha",
            "description": "Ya!, a-ok bud!",
        }
        response = self.create_process_instance_from_process_model_id_with_api(
            client,
            process_model_identifier,
            self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        process_instance_id = response.json["id"]

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None

        process_instance = ProcessInstanceModel.query.filter_by(id=process_instance_id).first()
        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        task = processor.get_all_user_tasks()[0]
        human_task = process_instance.active_human_tasks[0]

        ProcessInstanceService.complete_form_task(
            processor,
            task,
            payload,
            with_super_admin_user,
            human_task,
        )
        processor.save()

        response = client.post(
            f"/v1.0/messages/{message_model_identifier}",
            content_type="application/json",
            headers=self.logged_in_headers(with_super_admin_user),
            data=json.dumps({"payload": payload, "process_instance_id": process_instance_id}),
        )
        assert response.status_code == 200
        json_data = response.json
        assert json_data
        assert json_data["status"] == "complete"
        process_instance_id = json_data["id"]
        process_instance = ProcessInstanceModel.query.filter_by(id=process_instance_id).first()
        assert process_instance

        processor = ProcessInstanceProcessor(process_instance)
        process_instance_data = processor.get_data()
        assert process_instance_data
        assert process_instance_data["the_payload"] == payload

    def test_message_send_errors_when_providing_message_to_suspended_process_instance(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_message_send_when_providing_message_to_running_process_instance."""
        process_group_id = "test_message_send"
        process_model_id = "message_sender"
        bpmn_file_name = "message_sender.bpmn"
        bpmn_file_location = "message_send_one_conversation"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        message_model_identifier = "Approval Result"
        payload = {
            "customer_id": "sartography",
            "po_number": "1001",
            "amount": "One Billion Dollars! Mwhahahahahaha",
            "description": "But seriously.",
        }

        response = self.create_process_instance_from_process_model_id_with_api(
            client,
            process_model_identifier,
            self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        process_instance_id = response.json["id"]

        process_instance = ProcessInstanceModel.query.filter_by(id=process_instance_id).first()
        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        task = processor.get_all_user_tasks()[0]
        human_task = process_instance.active_human_tasks[0]

        ProcessInstanceService.complete_form_task(
            processor,
            task,
            payload,
            with_super_admin_user,
            human_task,
        )
        processor.save()

        processor.suspend()
        payload["description"] = "Message To Suspended"
        response = client.post(
            f"/v1.0/messages/{message_model_identifier}",
            content_type="application/json",
            headers=self.logged_in_headers(with_super_admin_user),
            data=json.dumps({"payload": payload, "process_instance_id": process_instance_id}),
        )
        assert response.status_code == 400
        assert response.json
        assert response.json["error_code"] == "message_not_accepted"

        processor.resume()
        payload["description"] = "Message To Resumed"
        response = client.post(
            f"/v1.0/messages/{message_model_identifier}",
            content_type="application/json",
            headers=self.logged_in_headers(with_super_admin_user),
            data=json.dumps({"payload": payload}),
        )
        assert response.status_code == 200
        json_data = response.json
        assert json_data
        assert json_data["status"] == "complete"
        process_instance_id = json_data["id"]
        process_instance = ProcessInstanceModel.query.filter_by(id=process_instance_id).first()
        assert process_instance
        processor = ProcessInstanceProcessor(process_instance)
        process_instance_data = processor.get_data()
        assert process_instance_data
        assert process_instance_data["the_payload"] == payload

        processor.terminate()
        response = client.post(
            f"/v1.0/messages/{message_model_identifier}",
            content_type="application/json",
            headers=self.logged_in_headers(with_super_admin_user),
            data=json.dumps({"payload": payload, "process_instance_id": process_instance_id}),
        )
        assert response.status_code == 400
        assert response.json
        assert response.json["error_code"] == "message_not_accepted"

    def test_process_instance_can_be_terminated(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_message_send_when_providing_message_to_running_process_instance."""
        # this task will wait on a catch event
        process_group_id = "test_message_send"
        process_model_id = "message_sender"
        bpmn_file_name = "message_sender.bpmn"
        bpmn_file_location = "message_send_one_conversation"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        response = self.create_process_instance_from_process_model_id_with_api(
            client,
            process_model_identifier,
            self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        process_instance_id = response.json["id"]

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None

        response = client.post(
            f"/v1.0/process-instance-terminate/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None

        process_instance = ProcessInstanceModel.query.filter_by(id=process_instance_id).first()
        assert process_instance
        assert process_instance.status == "terminated"

    def test_process_instance_delete(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_delete."""
        process_group_id = "my_process_group"
        process_model_id = "sample"
        bpmn_file_location = "sample"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_location=bpmn_file_location,
        )

        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        assert response.json is not None
        process_instance_id = response.json["id"]

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert response.status_code == 200

        delete_response = client.delete(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert delete_response.json["ok"] is True
        assert delete_response.status_code == 200

    def test_task_show(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_run_user_task."""
        process_group_id = "my_process_group"
        process_model_id = "dynamic_enum_select_fields"
        bpmn_file_location = "dynamic_enum_select_fields"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            # bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        assert response.json is not None
        process_instance_id = response.json["id"]

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        # Call this to assure all engine-steps are fully processed.
        _dequeued_interstitial_stream(process_instance_id)
        assert response.json is not None
        assert response.json["next_task"] is not None

        human_tasks = (
            db.session.query(HumanTaskModel).filter(HumanTaskModel.process_instance_id == process_instance_id).all()
        )
        assert len(human_tasks) == 1
        human_task = human_tasks[0]
        response = client.get(
            f"/v1.0/tasks/{process_instance_id}/{human_task.task_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["form_schema"]["definitions"]["Color"]["anyOf"][1]["title"] == "Green"

        # if you set this in task data:
        #   form_ui_hidden_fields = ["veryImportantFieldButOnlySometimes", "building.floor"]
        # you will get this ui schema:
        assert response.json["form_ui_schema"] == {
            "building": {"floor": {"ui:widget": "hidden"}},
            "veryImportantFieldButOnlySometimes": {"ui:widget": "hidden"},
        }

    def test_interstitial_page(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        process_group_id = "my_process_group"
        process_model_id = "interstitial"
        bpmn_file_location = "interstitial"
        # Assure we have someone in the finance team
        finance_user = self.find_or_create_user("testuser2")
        AuthorizationService.import_permissions_from_yaml_file()
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_location=bpmn_file_location,
        )
        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        assert response.json is not None
        process_instance_id = response.json["id"]

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=headers,
        )

        assert response.json is not None
        assert response.json["next_task"] is not None
        assert response.json["next_task"]["state"] == "READY"
        assert response.json["next_task"]["title"] == "Script Task #2"

        # Rather that call the API and deal with the Server Side Events, call the loop directly and covert it to
        # a list.  It tests all of our code.  No reason to test Flasks SSE support.
        stream_results = _dequeued_interstitial_stream(process_instance_id)
        results = list(stream_results)
        # strip the "data:" prefix and convert remaining string to dict.
        json_results = list(map(lambda x: json.loads(x[5:]), results))  # type: ignore
        # There should be 2 results back -
        # the first script task should not be returned (it contains no end user instructions)
        # The second script task should produce rendered jinja text
        # The Manual Task should then return a message as well.
        assert len(results) == 2
        assert json_results[0]["state"] == "READY"
        assert json_results[0]["title"] == "Script Task #2"
        assert json_results[0]["properties"]["instructionsForEndUser"] == "I am Script Task 2"
        assert json_results[1]["state"] == "READY"
        assert json_results[1]["title"] == "Manual Task"

        response = client.put(
            f"/v1.0/tasks/{process_instance_id}/{json_results[1]['id']}",
            headers=headers,
        )

        assert response.json is not None

        # we should now be on a task that does not belong to the original user, and the interstitial page should know this.
        results = list(_dequeued_interstitial_stream(process_instance_id))
        json_results = list(map(lambda x: json.loads(x[5:]), results))  # type: ignore
        assert len(results) == 1
        assert json_results[0]["state"] == "READY"
        assert json_results[0]["can_complete"] is False
        assert json_results[0]["title"] == "Please Approve"
        assert json_results[0]["properties"]["instructionsForEndUser"] == "I am a manual task in another lane"

        # Complete task as the finance user.
        response = client.put(
            f"/v1.0/tasks/{process_instance_id}/{json_results[0]['id']}",
            headers=self.logged_in_headers(finance_user),
        )

        # We should now be on the end task with a valid message, even after loading it many times.
        list(_dequeued_interstitial_stream(process_instance_id))
        list(_dequeued_interstitial_stream(process_instance_id))
        results = list(_dequeued_interstitial_stream(process_instance_id))
        json_results = list(map(lambda x: json.loads(x[5:]), results))  # type: ignore
        assert len(json_results) == 1
        assert json_results[0]["state"] == "COMPLETED"
        assert json_results[0]["properties"]["instructionsForEndUser"] == "I am the end task"

    def test_process_instance_list_with_default_list(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_list_with_default_list."""
        process_group_id = "runs_without_input"
        process_model_id = "sample"
        bpmn_file_location = "sample"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_location=bpmn_file_location,
        )

        headers = self.logged_in_headers(with_super_admin_user)
        self.create_process_instance_from_process_model_id_with_api(client, process_model_identifier, headers)

        response = client.get(
            "/v1.0/process-instances",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 1
        assert response.json["pagination"]["count"] == 1
        assert response.json["pagination"]["pages"] == 1
        assert response.json["pagination"]["total"] == 1

        process_instance_dict = response.json["results"][0]
        assert type(process_instance_dict["id"]) is int
        assert process_instance_dict["process_model_identifier"] == process_model_identifier
        assert type(process_instance_dict["start_in_seconds"]) is int
        assert process_instance_dict["start_in_seconds"] > 0
        assert process_instance_dict["end_in_seconds"] is None
        assert process_instance_dict["status"] == "not_started"

    def test_process_instance_list_with_paginated_items(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_list_with_paginated_items."""
        process_group_id = "runs_without_input"
        process_model_id = "sample"
        bpmn_file_name = "sample.bpmn"
        bpmn_file_location = "sample"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )
        headers = self.logged_in_headers(with_super_admin_user)
        self.create_process_instance_from_process_model_id_with_api(client, process_model_identifier, headers)
        self.create_process_instance_from_process_model_id_with_api(client, process_model_identifier, headers)
        self.create_process_instance_from_process_model_id_with_api(client, process_model_identifier, headers)
        self.create_process_instance_from_process_model_id_with_api(client, process_model_identifier, headers)
        self.create_process_instance_from_process_model_id_with_api(client, process_model_identifier, headers)

        response = client.get(
            "/v1.0/process-instances?per_page=2&page=3",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 1
        assert response.json["pagination"]["count"] == 1
        assert response.json["pagination"]["pages"] == 3
        assert response.json["pagination"]["total"] == 5

        response = client.get(
            "/v1.0/process-instances?per_page=2&page=1",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 2
        assert response.json["pagination"]["count"] == 2
        assert response.json["pagination"]["pages"] == 3
        assert response.json["pagination"]["total"] == 5

    def test_process_instance_list_filter(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_list_filter."""
        process_group_id = "runs_without_input"
        process_model_id = "sample"
        bpmn_file_name = "sample.bpmn"
        bpmn_file_location = "sample"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        statuses = [status.value for status in ProcessInstanceStatus]
        # create 5 instances with different status, and different start_in_seconds/end_in_seconds
        for i in range(5):
            process_instance = ProcessInstanceModel(
                status=ProcessInstanceStatus[statuses[i]].value,
                process_initiator=with_super_admin_user,
                process_model_identifier=process_model_identifier,
                process_model_display_name=process_model_identifier,
                updated_at_in_seconds=round(time.time()),
                start_in_seconds=(1000 * i) + 1000,
                end_in_seconds=(1000 * i) + 2000,
                bpmn_version_control_identifier=i,
            )
            db.session.add(process_instance)
        db.session.commit()

        # Without filtering we should get all 5 instances
        response = client.get(
            f"/v1.0/process-instances?process_model_identifier={process_model_identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        results = response.json["results"]
        assert len(results) == 5

        # filter for each of the status
        # we should get 1 instance each time
        for i in range(5):
            response = client.get(
                f"/v1.0/process-instances?process_status={ProcessInstanceStatus[statuses[i]].value}&process_model_identifier={process_model_identifier}",
                headers=self.logged_in_headers(with_super_admin_user),
            )
            assert response.json is not None
            results = response.json["results"]
            assert len(results) == 1
            assert results[0]["status"] == ProcessInstanceStatus[statuses[i]].value

        response = client.get(
            f"/v1.0/process-instances?process_status=not_started,complete&process_model_identifier={process_model_identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        results = response.json["results"]
        assert len(results) == 2
        assert results[0]["status"] in ["complete", "not_started"]
        assert results[1]["status"] in ["complete", "not_started"]

        # filter by start/end seconds
        # start > 1000 - this should eliminate the first
        response = client.get(
            "/v1.0/process-instances?start_from=1001",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        results = response.json["results"]
        assert len(results) == 4
        for i in range(4):
            assert json.loads(results[i]["bpmn_version_control_identifier"]) in (
                1,
                2,
                3,
                4,
            )

        # start > 2000, end < 5000 - this should eliminate the first 2 and the last
        response = client.get(
            "/v1.0/process-instances?start_from=2001&end_to=5999",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        results = response.json["results"]
        assert len(results) == 2
        assert json.loads(results[0]["bpmn_version_control_identifier"]) in (2, 3)
        assert json.loads(results[1]["bpmn_version_control_identifier"]) in (2, 3)

        # start > 1000, start < 4000 - this should eliminate the first and the last 2
        response = client.get(
            "/v1.0/process-instances?start_from=1001&start_to=3999",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        results = response.json["results"]
        assert len(results) == 2
        assert json.loads(results[0]["bpmn_version_control_identifier"]) in (1, 2)
        assert json.loads(results[1]["bpmn_version_control_identifier"]) in (1, 2)

        # end > 2000, end < 6000 - this should eliminate the first and the last
        response = client.get(
            "/v1.0/process-instances?end_from=2001&end_to=5999",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        results = response.json["results"]
        assert len(results) == 3
        for i in range(3):
            assert json.loads(results[i]["bpmn_version_control_identifier"]) in (
                1,
                2,
                3,
            )

    def test_process_instance_report_list(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_report_list."""
        process_group_id = "runs_without_input"
        process_model_id = "sample"
        bpmn_file_name = "sample.bpmn"
        bpmn_file_location = "sample"
        process_model_identifier = self.create_group_and_model_with_bpmn(  # noqa: F841
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )
        self.logged_in_headers(with_super_admin_user)

        report_identifier = "testreport"
        report_metadata = {"order_by": ["month"]}
        ProcessInstanceReportModel.create_with_attributes(
            identifier=report_identifier,
            report_metadata=report_metadata,
            user=with_super_admin_user,
        )
        response = client.get(
            "/v1.0/process-instances/reports",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json) == 1
        assert response.json[0]["identifier"] == report_identifier
        assert response.json[0]["report_metadata"]["order_by"] == ["month"]

    # def test_process_instance_report_show_with_default_list(
    #     self,
    #     app: Flask,
    #     client: FlaskClient,
    #     with_db_and_bpmn_file_cleanup: None,
    #     with_super_admin_user: UserModel,
    #     setup_process_instances_for_reports: list[ProcessInstanceModel],
    # ) -> None:
    #     """Test_process_instance_report_show_with_default_list."""
    #     process_group_id = "runs_without_input"
    #     process_model_id = "sample"
    #     process_model_identifier = f"{process_group_id}/{process_model_id}"
    #
    #     report_metadata = {
    #         "columns": [
    #             {"Header": "id", "accessor": "id"},
    #             {
    #                 "Header": "process_model_identifier",
    #                 "accessor": "process_model_identifier",
    #             },
    #             {"Header": "process_group_id", "accessor": "process_group_identifier"},
    #             {"Header": "start_in_seconds", "accessor": "start_in_seconds"},
    #             {"Header": "status", "accessor": "status"},
    #             {"Header": "Name", "accessor": "name"},
    #             {"Header": "Status", "accessor": "status"},
    #         ],
    #         "order_by": ["test_score"],
    #         "filter_by": [
    #             {"field_name": "grade_level", "operator": "equals", "field_value": 2}
    #         ],
    #     }
    #
    #     report = ProcessInstanceReportModel.create_with_attributes(
    #         identifier="sure",
    #         report_metadata=report_metadata,
    #         user=with_super_admin_user,
    #     )
    #
    #     response = client.get(
    #         f"/v1.0/process-instances/reports/{report.id}",
    #         headers=self.logged_in_headers(with_super_admin_user),
    #     )
    #     assert response.status_code == 200
    #     assert response.json is not None
    #     assert len(response.json["results"]) == 2
    #     assert response.json["pagination"]["count"] == 2
    #     assert response.json["pagination"]["pages"] == 1
    #     assert response.json["pagination"]["total"] == 2
    #
    #     process_instance_dict = response.json["results"][0]
    #     assert type(process_instance_dict["id"]) is int
    #     assert (
    #         process_instance_dict["process_model_identifier"]
    #         == process_model_identifier
    #     )
    #     assert type(process_instance_dict["start_in_seconds"]) is int
    #     assert process_instance_dict["start_in_seconds"] > 0
    #     assert process_instance_dict["status"] == "complete"
    #
    # def test_process_instance_report_show_with_dynamic_filter_and_query_param(
    #     self,
    #     app: Flask,
    #     client: FlaskClient,
    #     with_db_and_bpmn_file_cleanup: None,
    #     with_super_admin_user: UserModel,
    #     setup_process_instances_for_reports: list[ProcessInstanceModel],
    # ) -> None:
    #     """Test_process_instance_report_show_with_default_list."""
    #     report_metadata = {
    #         "filter_by": [
    #             {
    #                 "field_name": "grade_level",
    #                 "operator": "equals",
    #                 "field_value": "{{grade_level}}",
    #             }
    #         ],
    #     }
    #
    #     report = ProcessInstanceReportModel.create_with_attributes(
    #         identifier="sure",
    #         report_metadata=report_metadata,
    #         user=with_super_admin_user,
    #     )
    #
    #     response = client.get(
    #         f"/v1.0/process-instances/reports/{report.id}?grade_level=1",
    #         headers=self.logged_in_headers(with_super_admin_user),
    #     )
    #     assert response.status_code == 200
    #     assert response.json is not None
    #     assert len(response.json["results"]) == 1

    def test_process_instance_report_show_with_bad_identifier(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
        setup_process_instances_for_reports: list[ProcessInstanceModel],
    ) -> None:
        """Test_process_instance_report_show_with_bad_identifier."""
        response = client.get(
            "/v1.0/process-instances/reports/13000000?grade_level=1",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 404
        data = json.loads(response.get_data(as_text=True))
        assert data["error_code"] == "unknown_process_instance_report"

    def setup_testing_instance(
        self,
        client: FlaskClient,
        process_model_id: str,
        with_super_admin_user: UserModel,
    ) -> Any:
        """Setup_testing_instance."""
        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(client, process_model_id, headers)
        process_instance = response.json
        assert isinstance(process_instance, dict)
        process_instance_id = process_instance["id"]
        return process_instance_id

    def test_error_handler(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_error_handler."""
        process_group_id = "data"
        process_model_id = "error"
        bpmn_file_name = "error.bpmn"
        bpmn_file_location = "error"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        process_instance_id = self.setup_testing_instance(client, process_model_identifier, with_super_admin_user)

        process = db.session.query(ProcessInstanceModel).filter(ProcessInstanceModel.id == process_instance_id).first()
        assert process is not None
        assert process.status == "not_started"

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 400

        api_error = json.loads(response.get_data(as_text=True))
        assert api_error["error_code"] == "unexpected_workflow_exception"
        assert 'TypeError:can only concatenate str (not "int") to str' in api_error["message"]

        process = db.session.query(ProcessInstanceModel).filter(ProcessInstanceModel.id == process_instance_id).first()
        assert process is not None
        assert process.status == "error"

    def test_error_handler_suspend(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_error_handler_suspend."""
        process_group_id = "data"
        process_model_id = "error"
        bpmn_file_name = "error.bpmn"
        bpmn_file_location = "error"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        process_instance_id = self.setup_testing_instance(client, process_model_identifier, with_super_admin_user)
        process_model = ProcessModelService.get_process_model(process_model_identifier)
        ProcessModelService.update_process_model(
            process_model,
            {"fault_or_suspend_on_exception": NotificationType.suspend.value},
        )

        process = db.session.query(ProcessInstanceModel).filter(ProcessInstanceModel.id == process_instance_id).first()
        assert process is not None
        assert process.status == "not_started"

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 400

        process = db.session.query(ProcessInstanceModel).filter(ProcessInstanceModel.id == process_instance_id).first()
        assert process is not None
        assert process.status == "suspended"

    def test_error_handler_system_notification(self) -> None:
        """Test_error_handler_system_notification."""
        # TODO: make sure the system notification process is run on exceptions
        ...

    def test_task_data_is_set_even_if_process_instance_errors_through_the_api(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_task_data_is_set_even_if_process_instance_errors."""
        process_model = load_test_spec(
            process_model_id="group/error_with_task_data",
            bpmn_file_name="script_error_with_task_data.bpmn",
            process_model_source_directory="error",
        )
        process_instance = self.create_process_instance_from_process_model(
            process_model=process_model, user=with_super_admin_user
        )

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model.id)}/{process_instance.id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 400
        assert process_instance.status == "error"
        processor = ProcessInstanceProcessor(process_instance)
        spiff_task = processor.get_task_by_bpmn_identifier("script_task_two", processor.bpmn_process_instance)
        assert spiff_task is not None
        assert spiff_task.state == TaskState.ERROR
        assert spiff_task.data == {"my_var": "THE VAR"}

    def test_process_model_file_create(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_model_file_create."""
        process_group_id = "hello_world"
        process_model_id = "hello_world"
        file_name = "hello_world.svg"
        file_data = b"abc123"
        bpmn_file_name = "hello_world.bpmn"
        bpmn_file_location = "hello_world"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        result = self.create_spec_file(
            client,
            process_model_id=process_model_identifier,
            file_name=file_name,
            file_data=file_data,
            user=with_super_admin_user,
        )

        assert result["process_model_id"] == process_model_identifier
        assert result["name"] == file_name
        assert bytes(str(result["file_contents"]), "utf-8") == file_data

    def test_can_get_message_instances_by_process_instance_id_and_without(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_can_get_message_instances_by_process_instance_id."""
        process_group_id = "test_message_send"
        process_model_id = "message_receiver"
        bpmn_file_name = "message_receiver.bpmn"
        bpmn_file_location = "message_send_one_conversation"
        self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )
        # load_test_spec(
        #     "message_receiver",
        #     process_model_source_directory="message_send_one_conversation",
        #     bpmn_file_name="message_receiver",
        # )
        message_model_identifier = "Request Approval"
        payload = {
            "customer_id": "sartography",
            "po_number": "1001",
            "amount": "One Billion Dollars! Mwhahahahahaha",
            "description": "But seriously.",
        }
        response = client.post(
            f"/v1.0/messages/{message_model_identifier}",
            content_type="application/json",
            headers=self.logged_in_headers(with_super_admin_user),
            data=json.dumps({"payload": payload}),
        )
        assert response.status_code == 200
        assert response.json is not None
        process_instance_id_one = response.json["id"]

        payload["po_number"] = "1002"
        response = client.post(
            f"/v1.0/messages/{message_model_identifier}",
            content_type="application/json",
            headers=self.logged_in_headers(with_super_admin_user),
            data=json.dumps({"payload": payload}),
        )
        assert response.status_code == 200
        assert response.json is not None
        process_instance_id_two = response.json["id"]

        response = client.get(
            f"/v1.0/messages?process_instance_id={process_instance_id_one}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 2  # Two messages, one is the completed receive, the other is new send
        assert response.json["results"][0]["process_instance_id"] == process_instance_id_one

        response = client.get(
            f"/v1.0/messages?process_instance_id={process_instance_id_two}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 2
        assert response.json["results"][0]["process_instance_id"] == process_instance_id_two

        response = client.get(
            "/v1.0/messages",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        #   4 -Two messages for each process (a record of the completed receive, and then a send created)
        # + 2 -Two messages logged for the API Calls used to create the processes.
        assert len(response.json["results"]) == 6

    # @pytest.mark.skipif(
    #     os.environ.get("SPIFFWORKFLOW_BACKEND_DATABASE_TYPE") == "postgres",
    #     reason="look at comment in tasks_controller method task_list_my_tasks",
    # )
    def test_correct_user_can_get_and_update_a_task(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_correct_user_can_get_and_update_a_task."""
        initiator_user = self.find_or_create_user("testuser4")
        finance_user = self.find_or_create_user("testuser2")
        assert initiator_user.principal is not None
        assert finance_user.principal is not None
        AuthorizationService.import_permissions_from_yaml_file()

        finance_group = GroupModel.query.filter_by(identifier="Finance Team").first()
        assert finance_group is not None

        process_group_id = "finance"
        process_model_id = "model_with_lanes"
        bpmn_file_name = "lanes.bpmn"
        bpmn_file_location = "model_with_lanes"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client,
            with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        # process_model = load_test_spec(
        #     process_model_id="model_with_lanes",
        #     bpmn_file_name="lanes.bpmn",
        #     process_group_id="finance",
        # )

        response = self.create_process_instance_from_process_model_id_with_api(
            client,
            # process_model.process_group_id,
            process_model_identifier,
            headers=self.logged_in_headers(initiator_user),
        )
        assert response.status_code == 201

        assert response.json is not None
        process_instance_id = response.json["id"]
        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(initiator_user),
        )
        assert response.status_code == 200

        response = client.get(
            "/v1.0/tasks",
            headers=self.logged_in_headers(finance_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 0

        response = client.get(
            "/v1.0/tasks",
            headers=self.logged_in_headers(initiator_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 1

        task_id = response.json["results"][0]["id"]
        assert task_id is not None

        response = client.put(
            f"/v1.0/tasks/{process_instance_id}/{task_id}",
            headers=self.logged_in_headers(finance_user),
        )
        assert response.status_code == 500
        assert response.json
        assert "UserDoesNotHaveAccessToTaskError" in response.json["message"]

        response = client.put(
            f"/v1.0/tasks/{process_instance_id}/{task_id}",
            headers=self.logged_in_headers(initiator_user),
        )
        assert response.status_code == 200

        response = client.get(
            "/v1.0/tasks",
            headers=self.logged_in_headers(initiator_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 0

        response = client.get(
            "/v1.0/tasks",
            headers=self.logged_in_headers(finance_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 1

    # TODO: test the auth callback endpoint
    # def test_can_store_authentication_secret(
    #     self, app: Flask, client: FlaskClient, with_db_and_bpmn_file_cleanup: None
    # ) -> None:
    #     """Test_can_store_authentication_secret."""
    #     response = client.get(
    #         "/v1.0/authentication_callback",
    #         headers=self.logged_in_headers(user),
    #     )

    # def test_get_process_model(self):
    #
    #     load_test_spec('random_fact')
    #     response = client.get('/v1.0/workflow-specification/random_fact', headers=self.logged_in_headers())
    #     assert_success(response)
    #     json_data = json.loads(response.get_data(as_text=True))
    #     api_spec = WorkflowSpecInfoSchema().load(json_data)
    #
    #     fs_spec = process_model_service.get_spec('random_fact')
    #     assert(WorkflowSpecInfoSchema().dump(fs_spec) == json_data)
    #

    # def test_waku_debug_info(self) -> None:
    #     """Test_waku_debug_info."""
    #     debug_info_method = "get_waku_v2_debug_v1_info"
    #
    #     headers = {"Content-Type": "application/json"}
    #
    #     rpc_json = {
    #         "jsonrpc": "2.0",
    #         "method": debug_info_method,
    #         "params": [],
    #         "id": "id",
    #     }
    #
    #     request_url = "http://localhost:8545"
    #     rpc_response = requests.post(request_url, headers=headers, json=rpc_json)
    #
    #     rpc_json_text: dict = json.loads(rpc_response.text)
    #     assert isinstance(rpc_json_text, dict)
    #     # assert 'jsonrpc' in rpc_json_text
    #     # assert rpc_json_text['jsonrpc'] == '2.0'
    #     assert "result" in rpc_json_text
    #     result = rpc_json_text["result"]
    #     assert isinstance(result, dict)
    #     assert "listenAddresses" in result
    #     assert "enrUri" in result
    #
    #     print("test_call_waku")
    #
    # def test_send_message(self) -> None:
    #     """Test_send_message."""
    #     relay_message_method = "post_waku_v2_relay_v1_message"
    #
    #     headers = {"Content-Type": "application/json"}
    #
    #     # class WakuMessage:
    #     #     payload: str
    #     #     contentTopic: str  # Optional
    #     #     # version: int  # Optional
    #     #     timestamp: int  # Optional
    #     payload = "This is my message"
    #     contentTopic = "myTestTopic"  # noqa: N806
    #     timestamp = time.time()
    #
    #     waku_relay_message = {
    #         "payload": payload,
    #         "contentTopic": contentTopic,
    #         "timestamp": timestamp,
    #     }
    #
    #     # ["", [{"contentTopic":"/waku/2/default-content/proto"}]]
    #     params = ["/waku/2/default-waku/proto", {"message": waku_relay_message}]
    #     rpc_json = {
    #         "jsonrpc": "2.0",
    #         "method": relay_message_method,
    #         "params": params,
    #         "id": 1,
    #     }
    #
    #     request_url = "http://localhost:8545"
    #     rpc_response = requests.post(request_url, headers=headers, json=rpc_json)
    #     assert rpc_response.status_code == 200
    #
    #     rpc_json_data: dict = json.loads(rpc_response.text)
    #     assert "error" in rpc_json_data
    #     assert "result" in rpc_json_data
    #     assert rpc_json_data["error"] is None
    #     assert rpc_json_data["result"] is True
    #
    #     print("test_send_message")
    #
    # def test_get_waku_messages(self) -> None:
    #     """Test_get_waku_messages."""
    #     method = "get_waku_v2_store_v1_messages"
    #     headers = {"Content-Type": "application/json"}
    #     params = [{"contentTopic": "/waku/2/default-content/proto"}]
    #
    #     rpc_json = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    #     request_url = "http://localhost:8545"
    #     rpc_response = requests.post(request_url, headers=headers, json=rpc_json)
    #     assert rpc_response.status_code == 200
    #
    #     rpc_json_data: dict = json.loads(rpc_response.text)
    #     assert "error" in rpc_json_data
    #     assert rpc_json_data["error"] is None
    #     assert "result" in rpc_json_data
    #     assert isinstance(rpc_json_data["result"], dict)
    #     assert "messages" in rpc_json_data["result"]
    #     assert "pagingInfo" in rpc_json_data["result"]
    #
    #     print("get_waku_messages")

    def test_process_instance_suspend(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_suspend."""
        bpmn_file_name = "manual_task.bpmn"
        bpmn_file_location = "manual_task"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_model_id="manual_task",
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        bpmn_file_data_bytes = self.get_test_data_file_contents(bpmn_file_name, bpmn_file_location)
        self.create_spec_file(
            client=client,
            process_model_id=process_model_identifier,
            process_model_location=process_model_identifier,
            file_name=bpmn_file_name,
            file_data=bpmn_file_data_bytes,
            user=with_super_admin_user,
        )

        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        assert response.json is not None
        process_instance_id = response.json["id"]

        client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        process_instance = ProcessInstanceService().get_process_instance(process_instance_id)
        assert process_instance.status == "user_input_required"

        client.post(
            f"/v1.0/process-instance-suspend/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        process_instance = ProcessInstanceService().get_process_instance(process_instance_id)
        assert process_instance.status == "suspended"

        response = client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        process_instance = ProcessInstanceService().get_process_instance(process_instance_id)
        assert process_instance.status == "suspended"
        assert response.status_code == 400

        response = client.post(
            f"/v1.0/process-instance-resume/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        process_instance = ProcessInstanceService().get_process_instance(process_instance_id)
        assert process_instance.status == "waiting"

    def test_script_unit_test_run(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_script_unit_test_run."""
        process_group_id = "test_group"
        process_model_id = "simple_script"
        bpmn_file_name = "simple_script.bpmn"
        bpmn_file_location = "simple_script"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        bpmn_file_data_bytes = self.get_test_data_file_contents(bpmn_file_name, bpmn_file_location)
        self.create_spec_file(
            client=client,
            process_model_id=process_model_identifier,
            process_model_location=process_model_identifier,
            file_name=bpmn_file_name,
            file_data=bpmn_file_data_bytes,
            user=with_super_admin_user,
        )

        # python_script = _get_required_parameter_or_raise("python_script", body)
        # input_json = _get_required_parameter_or_raise("input_json", body)
        # expected_output_json = _get_required_parameter_or_raise(
        #     "expected_output_json", body
        # )
        python_script = "c = a + b"
        input_json = {"a": 1, "b": 2}
        expected_output_json = {"a": 1, "b": 2, "c": 3}
        # bpmn_task_identifier = "Activity_CalculateNewData"

        data = {
            "python_script": python_script,
            "input_json": input_json,
            "expected_output_json": expected_output_json,
        }

        response = client.post(  # noqa: F841
            f"/v1.0/process-models/{process_group_id}/{process_model_id}/script-unit-tests/run",
            headers=self.logged_in_headers(with_super_admin_user),
            content_type="application/json",
            data=json.dumps(data),
        )

        print("test_script_unit_test_run")

    def test_send_event(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_script_unit_test_run."""
        process_group_id = "test_group"
        process_model_id = "process_navigation"
        bpmn_file_name = "process_navigation.bpmn"
        bpmn_file_location = "process_navigation"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        bpmn_file_data_bytes = self.get_test_data_file_contents(bpmn_file_name, bpmn_file_location)
        self.create_spec_file(
            client=client,
            process_model_id=process_model_identifier,
            process_model_location=process_model_identifier,
            file_name=bpmn_file_name,
            file_data=bpmn_file_data_bytes,
            user=with_super_admin_user,
        )

        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        process_instance_id = response.json["id"]

        client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        # This is exactly the same the test above, but some reason I to a totally irrelevant type.
        data: Dict = {
            "correlation_properties": [],
            "expression": None,
            "external": True,
            "internal": False,
            "payload": {"message": "message 1"},
            "name": "Message 1",
            "typename": "MessageEventDefinition",
        }
        response = client.post(
            f"/v1.0/send-event/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}",
            headers=self.logged_in_headers(with_super_admin_user),
            content_type="application/json",
            data=json.dumps(data),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["status"] == "complete"

        response = client.get(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/task-info?all_tasks=true",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        end_task = next(task for task in response.json if task["bpmn_identifier"] == "Event_174a838")
        response = client.get(
            f"/v1.0/task-data/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/{end_task['guid']}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        task = response.json
        assert task["data"]["result"] == {"message": "message 1"}

    def test_manual_complete_task(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_script_unit_test_run."""
        process_group_id = "test_group"
        process_model_id = "manual_task"
        bpmn_file_name = "manual_task.bpmn"
        bpmn_file_location = "manual_task"
        process_model_identifier = self.create_group_and_model_with_bpmn(
            client=client,
            user=with_super_admin_user,
            process_group_id=process_group_id,
            process_model_id=process_model_id,
            bpmn_file_name=bpmn_file_name,
            bpmn_file_location=bpmn_file_location,
        )

        bpmn_file_data_bytes = self.get_test_data_file_contents(bpmn_file_name, bpmn_file_location)
        self.create_spec_file(
            client=client,
            process_model_id=process_model_identifier,
            process_model_location=process_model_identifier,
            file_name=bpmn_file_name,
            file_data=bpmn_file_data_bytes,
            user=with_super_admin_user,
        )

        headers = self.logged_in_headers(with_super_admin_user)
        response = self.create_process_instance_from_process_model_id_with_api(
            client, process_model_identifier, headers
        )
        process_instance_id = response.json["id"]

        client.post(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/run",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        response = client.get(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/task-info",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert len(response.json) == 7
        human_task = next(task for task in response.json if task["bpmn_identifier"] == "manual_task_one")

        response = client.post(
            f"/v1.0/task-complete/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/{human_task['guid']}",
            headers=self.logged_in_headers(with_super_admin_user),
            content_type="application/json",
            data=json.dumps({"execute": False}),
        )
        assert response.json["status"] == "suspended"
        task_model = TaskModel.query.filter_by(guid=human_task["guid"]).first()
        assert task_model is not None
        assert task_model.state == "COMPLETED"

        response = client.get(
            f"/v1.0/process-instances/{self.modify_process_identifier_for_path_param(process_model_identifier)}/{process_instance_id}/task-info",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert len(response.json) == 7

    def setup_initial_groups_for_move_tests(self, client: FlaskClient, with_super_admin_user: UserModel) -> None:
        """Setup_initial_groups_for_move_tests."""
        groups = ["group_a", "group_b", "group_b/group_bb"]
        # setup initial groups
        for group in groups:
            self.create_process_group_with_api(client, with_super_admin_user, group, display_name=group)
        # make sure initial groups exist
        for group in groups:
            persisted = ProcessModelService.get_process_group(group)
            assert persisted is not None
            assert persisted.id == group

    def test_move_model(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_move_model."""
        self.setup_initial_groups_for_move_tests(client, with_super_admin_user)

        process_model_id = "test_model"
        original_location = "group_a"
        original_process_model_path = f"{original_location}/{process_model_id}"

        # add model to `group_a`
        self.create_process_model_with_api(
            client,
            original_process_model_path,
            user=with_super_admin_user,
            process_model_display_name=process_model_id,
            process_model_description=process_model_id,
        )
        persisted = ProcessModelService.get_process_model(original_process_model_path)
        assert persisted is not None
        assert persisted.id == original_process_model_path

        # move model to `group_b/group_bb`
        new_location = "group_b/group_bb"
        new_process_model_path = f"{new_location}/{process_model_id}"
        modified_original_process_model_id = original_process_model_path.replace("/", ":")

        response = client.put(
            f"/v1.0/process-models/{modified_original_process_model_id}/move?new_location={new_location}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json["id"] == new_process_model_path

        # make sure the original model does not exist
        with pytest.raises(ProcessEntityNotFoundError) as e:
            ProcessModelService.get_process_model(original_process_model_path)
        assert e.value.args[0] == "process_model_not_found"

        # make sure the new model does exist
        new_process_model = ProcessModelService.get_process_model(new_process_model_path)
        assert new_process_model is not None
        assert new_process_model.id == new_process_model_path

    def test_move_group(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_move_group."""
        self.setup_initial_groups_for_move_tests(client, with_super_admin_user)

        # add sub group to `group_a`
        sub_group_id = "sub_group"
        original_location = "group_a"
        original_sub_path = f"{original_location}/{sub_group_id}"
        self.create_process_group_with_api(client, with_super_admin_user, original_sub_path, display_name=sub_group_id)
        # make sure original subgroup exists
        persisted = ProcessModelService.get_process_group(original_sub_path)
        assert persisted is not None
        assert persisted.id == original_sub_path

        # move sub_group to `group_b/group_bb`
        new_location = "group_b/group_bb"
        new_sub_path = f"{new_location}/{sub_group_id}"
        modified_original_process_group_id = original_sub_path.replace("/", ":")
        response = client.put(
            f"/v1.0/process-groups/{modified_original_process_group_id}/move?new_location={new_location}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json["id"] == new_sub_path

        # make sure the original subgroup does not exist
        with pytest.raises(ProcessEntityNotFoundError) as e:
            ProcessModelService.get_process_group(original_sub_path)

        assert e.value.args[0] == "process_group_not_found"
        assert e.value.args[1] == f"Process Group Id: {original_sub_path}"

        # make sure the new subgroup does exist
        new_process_group = ProcessModelService.get_process_group(new_sub_path)
        assert new_process_group.id == new_sub_path

    # this doesn't work in CI
    # assert "Initial Commit" in output
    # def test_process_model_publish(
    #     self,
    #     app: Flask,
    #     client: FlaskClient,
    #     with_db_and_bpmn_file_cleanup: None,
    #     with_super_admin_user: UserModel,
    # ) -> None:
    #     """Test_process_model_publish."""
    #     bpmn_root = FileSystemService.root_path()
    #     shell_command = ["git", "init", "--initial-branch=main", bpmn_root]
    #     output = GitService.run_shell_command_to_get_stdout(shell_command)
    #     assert output == f"Initialized empty Git repository in {bpmn_root}/.git/\n"
    #     with FileSystemService.cd(bpmn_root):
    #         output = GitService.run_shell_command_to_get_stdout(["git", "status"])
    #         assert "On branch main" in output
    #         assert "No commits yet" in output
    #         assert (
    #             'nothing to commit (create/copy files and use "git add" to track)'
    #             in output
    #         )
    #
    #         process_group_id = "test_group"
    #         self.create_process_group_with_api(
    #             client, with_super_admin_user, process_group_id, process_group_id
    #         )
    #
    #         sub_process_group_id = "test_group/test_sub_group"
    #         process_model_id = "hello_world"
    #         bpmn_file_name = "hello_world.bpmn"
    #         bpmn_file_location = "hello_world"
    #         process_model_identifier = self.create_group_and_model_with_bpmn(
    #             client=client,
    #             user=with_super_admin_user,
    #             process_group_id=sub_process_group_id,
    #             process_model_id=process_model_id,
    #             bpmn_file_name=bpmn_file_name,
    #             bpmn_file_location=bpmn_file_location,
    #         )
    #         process_model_absolute_dir = os.path.join(
    #             bpmn_root, process_model_identifier
    #         )
    #
    #         output = GitService.run_shell_command_to_get_stdout(["git", "status"])
    #         test_string = 'Untracked files:\n  (use "git add <file>..." to include in what will be committed)\n\ttest_group'
    #         assert test_string in output
    #
    #         os.system("git add .")
    #         output = os.popen("git commit -m 'Initial Commit'").read()
    #         assert "Initial Commit" in output
    #         assert "4 files changed" in output
    #         assert "test_group/process_group.json" in output
    #         assert "test_group/test_sub_group/hello_world/hello_world.bpmn" in output
    #         assert "test_group/test_sub_group/hello_world/process_model.json" in output
    #         assert "test_group/test_sub_group/process_group.json" in output
    #
    #         output = GitService.run_shell_command_to_get_stdout(["git", "status"])
    #         assert "On branch main" in output
    #         assert "nothing to commit" in output
    #         assert "working tree clean" in output
    #
    #         output = os.popen("git branch --list").read()  # noqa: S605
    #         assert output == "* main\n"
    #         os.system("git branch staging")
    #         output = os.popen("git branch --list").read()  # noqa: S605
    #         assert output == "* main\n  staging\n"
    #
    #         os.system("git checkout staging")
    #
    #         output = GitService.run_shell_command_to_get_stdout(["git", "status"])
    #         assert "On branch staging" in output
    #         assert "nothing to commit" in output
    #         assert "working tree clean" in output
    #
    #         # process_model = ProcessModelService.get_process_model(process_model_identifier)
    #
    #         listing = os.listdir(process_model_absolute_dir)
    #         assert len(listing) == 2
    #         assert "hello_world.bpmn" in listing
    #         assert "process_model.json" in listing
    #
    #         os.system("git checkout main")
    #
    #         output = GitService.run_shell_command_to_get_stdout(["git", "status"])
    #         assert "On branch main" in output
    #         assert "nothing to commit" in output
    #         assert "working tree clean" in output
    #
    #         file_data = b"abc123"
    #         new_file_path = os.path.join(process_model_absolute_dir, "new_file.txt")
    #         with open(new_file_path, "wb") as f_open:
    #             f_open.write(file_data)
    #
    #         output = GitService.run_shell_command_to_get_stdout(["git", "status"])
    #         assert "On branch main" in output
    #         assert "Untracked files:" in output
    #         assert "test_group/test_sub_group/hello_world/new_file.txt" in output
    #
    #         os.system(
    #             "git add test_group/test_sub_group/hello_world/new_file.txt"
    #         )  # noqa: S605
    #         output = os.popen("git commit -m 'add new_file.txt'").read()  # noqa: S605
    #
    #         assert "add new_file.txt" in output
    #         assert "1 file changed, 1 insertion(+)" in output
    #         assert "test_group/test_sub_group/hello_world/new_file.txt" in output
    #
    #         listing = os.listdir(process_model_absolute_dir)
    #         assert len(listing) == 3
    #         assert "hello_world.bpmn" in listing
    #         assert "process_model.json" in listing
    #         assert "new_file.txt" in listing
    #
    #         # modified_process_model_id = process_model_identifier.replace("/", ":")
    #         # response = client.post(
    #         #     f"/v1.0/process-models/{modified_process_model_id}/publish?branch_to_update=staging",
    #         #     headers=self.logged_in_headers(with_super_admin_user),
    #         # )
    #
    #     print("test_process_model_publish")

    def test_can_get_process_instance_list_with_report_metadata(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_can_get_process_instance_list_with_report_metadata."""
        process_model = load_test_spec(
            process_model_id="save_process_instance_metadata/save_process_instance_metadata",
            bpmn_file_name="save_process_instance_metadata.bpmn",
            process_model_source_directory="save_process_instance_metadata",
        )
        process_instance = self.create_process_instance_from_process_model(
            process_model=process_model, user=with_super_admin_user
        )

        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        process_instance_metadata = ProcessInstanceMetadataModel.query.filter_by(
            process_instance_id=process_instance.id
        ).all()
        assert len(process_instance_metadata) == 3

        report_metadata = {
            "columns": [
                {"Header": "ID", "accessor": "id"},
                {"Header": "Status", "accessor": "status"},
                {"Header": "Key One", "accessor": "key1"},
                {"Header": "Key Two", "accessor": "key2"},
            ],
            "order_by": ["status"],
            "filter_by": [],
        }
        process_instance_report = ProcessInstanceReportModel.create_with_attributes(
            identifier="sure",
            report_metadata=report_metadata,
            user=with_super_admin_user,
        )

        response = client.get(
            f"/v1.0/process-instances?report_identifier={process_instance_report.identifier}",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.json is not None
        assert response.status_code == 200

        assert len(response.json["results"]) == 1
        assert response.json["results"][0]["status"] == "complete"
        assert response.json["results"][0]["id"] == process_instance.id
        assert response.json["results"][0]["key1"] == "value1"
        assert response.json["results"][0]["key2"] == "value2"
        assert response.json["pagination"]["count"] == 1
        assert response.json["pagination"]["pages"] == 1
        assert response.json["pagination"]["total"] == 1

    def test_can_get_process_instance_list_with_report_metadata_and_process_initiator(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_can_get_process_instance_list_with_report_metadata_and_process_initator."""
        user_one = self.create_user_with_permission(username="user_one")

        process_model = load_test_spec(
            process_model_id="save_process_instance_metadata/save_process_instance_metadata",
            bpmn_file_name="save_process_instance_metadata.bpmn",
            process_model_source_directory="save_process_instance_metadata",
        )
        self.create_process_instance_from_process_model(process_model=process_model, user=user_one)
        self.create_process_instance_from_process_model(process_model=process_model, user=user_one)
        self.create_process_instance_from_process_model(process_model=process_model, user=with_super_admin_user)

        dne_report_metadata = {
            "columns": [
                {"Header": "ID", "accessor": "id"},
                {"Header": "Status", "accessor": "status"},
                {"Header": "Process Initiator", "accessor": "username"},
            ],
            "order_by": ["status"],
            "filter_by": [
                {
                    "field_name": "process_initiator_username",
                    "field_value": "DNE",
                    "operator": "equals",
                }
            ],
        }

        user_one_report_metadata = {
            "columns": [
                {"Header": "ID", "accessor": "id"},
                {"Header": "Status", "accessor": "status"},
                {"Header": "Process Initiator", "accessor": "username"},
            ],
            "order_by": ["status"],
            "filter_by": [
                {
                    "field_name": "process_initiator_username",
                    "field_value": user_one.username,
                    "operator": "equals",
                }
            ],
        }
        process_instance_report_dne = ProcessInstanceReportModel.create_with_attributes(
            identifier="dne_report",
            report_metadata=dne_report_metadata,
            user=user_one,
        )
        process_instance_report_user_one = ProcessInstanceReportModel.create_with_attributes(
            identifier="user_one_report",
            report_metadata=user_one_report_metadata,
            user=user_one,
        )

        response = client.get(
            f"/v1.0/process-instances?report_identifier={process_instance_report_user_one.identifier}",
            headers=self.logged_in_headers(user_one),
        )
        assert response.json is not None
        assert response.status_code == 200
        assert len(response.json["results"]) == 2
        assert response.json["results"][0]["process_initiator_username"] == user_one.username
        assert response.json["results"][1]["process_initiator_username"] == user_one.username

        response = client.get(
            f"/v1.0/process-instances?report_identifier={process_instance_report_dne.identifier}",
            headers=self.logged_in_headers(user_one),
        )
        assert response.json is not None
        assert response.status_code == 200
        assert len(response.json["results"]) == 0

    def test_can_get_process_instance_report_column_list(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_can_get_process_instance_list_with_report_metadata."""
        process_model = self.create_process_model_with_metadata()
        process_instance = self.create_process_instance_from_process_model(
            process_model=process_model, user=with_super_admin_user
        )

        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        process_instance_metadata = ProcessInstanceMetadataModel.query.filter_by(
            process_instance_id=process_instance.id
        ).all()
        assert len(process_instance_metadata) == 2

        process_model = load_test_spec(
            process_model_id="save_process_instance_metadata/save_process_instance_metadata",
            bpmn_file_name="save_process_instance_metadata.bpmn",
            process_model_source_directory="save_process_instance_metadata",
        )
        process_instance = self.create_process_instance_from_process_model(
            process_model=process_model, user=with_super_admin_user
        )

        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        process_instance_metadata = ProcessInstanceMetadataModel.query.filter_by(
            process_instance_id=process_instance.id
        ).all()
        assert len(process_instance_metadata) == 3

        response = client.get(
            "/v1.0/process-instances/reports/columns",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.json is not None
        assert response.status_code == 200
        assert response.json == [
            {"Header": "Id", "accessor": "id", "filterable": False},
            {
                "Header": "Process",
                "accessor": "process_model_display_name",
                "filterable": False,
            },
            {"Header": "Start", "accessor": "start_in_seconds", "filterable": False},
            {"Header": "End", "accessor": "end_in_seconds", "filterable": False},
            {
                "Header": "Started By",
                "accessor": "process_initiator_username",
                "filterable": False,
            },
            {"Header": "Status", "accessor": "status", "filterable": False},
            {"Header": "awesome_var", "accessor": "awesome_var", "filterable": True},
            {"Header": "invoice_number", "accessor": "invoice_number", "filterable": True},
            {"Header": "key1", "accessor": "key1", "filterable": True},
            {"Header": "key2", "accessor": "key2", "filterable": True},
            {"Header": "key3", "accessor": "key3", "filterable": True},
        ]

        # pluck accessor from each dict in list
        accessors = [column["accessor"] for column in response.json]
        stock_columns = [
            "id",
            "process_model_display_name",
            "start_in_seconds",
            "end_in_seconds",
            "process_initiator_username",
            "status",
        ]
        assert accessors == stock_columns + ["awesome_var", "invoice_number", "key1", "key2", "key3"]

        # expected columns are fewer if we filter by process_model_identifier
        response = client.get(
            "/v1.0/process-instances/reports/columns?process_model_identifier=save_process_instance_metadata/save_process_instance_metadata",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.json is not None
        assert response.status_code == 200
        accessors = [column["accessor"] for column in response.json]
        assert accessors == stock_columns + ["key1", "key2", "key3"]

    def test_process_instance_list_can_order_by_metadata(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_instance_list_can_order_by_metadata."""
        self.create_process_group_with_api(client, with_super_admin_user, "test_group", "test_group")
        process_model = load_test_spec(
            "test_group/hello_world",
            process_model_source_directory="nested-task-data-structure",
        )
        ProcessModelService.update_process_model(
            process_model,
            {
                "metadata_extraction_paths": [
                    {"key": "time_ns", "path": "outer.time"},
                ]
            },
        )

        process_instance_one = self.create_process_instance_from_process_model(process_model)
        processor = ProcessInstanceProcessor(process_instance_one)
        processor.do_engine_steps(save=True)
        assert process_instance_one.status == "complete"
        process_instance_two = self.create_process_instance_from_process_model(process_model)
        processor = ProcessInstanceProcessor(process_instance_two)
        processor.do_engine_steps(save=True)
        assert process_instance_two.status == "complete"

        report_metadata = {
            "columns": [
                {"Header": "id", "accessor": "id"},
                {"Header": "Time", "accessor": "time_ns"},
            ],
            "order_by": ["time_ns"],
        }
        report_one = ProcessInstanceReportModel.create_with_attributes(
            identifier="report_one",
            report_metadata=report_metadata,
            user=with_super_admin_user,
        )

        response = client.get(
            f"/v1.0/process-instances?report_id={report_one.id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 2
        assert response.json["results"][0]["id"] == process_instance_one.id
        assert response.json["results"][1]["id"] == process_instance_two.id

        report_metadata = {
            "columns": [
                {"Header": "id", "accessor": "id"},
                {"Header": "Time", "accessor": "time_ns"},
            ],
            "order_by": ["-time_ns"],
        }
        report_two = ProcessInstanceReportModel.create_with_attributes(
            identifier="report_two",
            report_metadata=report_metadata,
            user=with_super_admin_user,
        )

        response = client.get(
            f"/v1.0/process-instances?report_id={report_two.id}",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json["results"]) == 2
        assert response.json["results"][1]["id"] == process_instance_one.id
        assert response.json["results"][0]["id"] == process_instance_two.id

    def test_process_data_show(
        self,
        app: Flask,
        client: FlaskClient,
        with_db_and_bpmn_file_cleanup: None,
        with_super_admin_user: UserModel,
    ) -> None:
        """Test_process_data_show."""
        process_model = load_test_spec(
            "test_group/data_object_test",
            process_model_source_directory="data_object_test",
        )
        process_instance_one = self.create_process_instance_from_process_model(process_model)
        processor = ProcessInstanceProcessor(process_instance_one)
        processor.do_engine_steps(save=True)
        assert process_instance_one.status == "user_input_required"

        response = client.get(
            f"/v1.0/process-data/{self.modify_process_identifier_for_path_param(process_model.id)}/{process_instance_one.id}/the_data_object_var",
            headers=self.logged_in_headers(with_super_admin_user),
        )

        assert response.status_code == 200
        assert response.json is not None
        assert response.json["process_data_value"] == "hey"
