"""Example_data."""
import glob
import os
from typing import Optional

from flask import current_app

from spiffworkflow_backend.models.process_model import ProcessModelInfo
from spiffworkflow_backend.services.process_model_service import ProcessModelService
from spiffworkflow_backend.services.spec_file_service import SpecFileService


class ExampleDataLoader:
    """ExampleDataLoader."""

    @staticmethod
    def create_spec(
        process_model_id: str,
        display_name: str = "",
        description: str = "",
        display_order: int = 0,
        bpmn_file_name: Optional[str] = None,
        process_model_source_directory: Optional[str] = None,
    ) -> ProcessModelInfo:
        """Assumes that process_model_source_directory exists in static/bpmn and contains bpmn_file_name.

        further assumes that bpmn_file_name is the primary file for the process model.
        if bpmn_file_name is None we load all files in process_model_source_directory,
        otherwise, we only load bpmn_file_name
        """
        if process_model_source_directory is None:
            raise Exception("You must include `process_model_source_directory`.")

        spec = ProcessModelInfo(
            id=process_model_id,
            display_name=display_name,
            description=description,
            display_order=display_order,
        )
        ProcessModelService.add_process_model(spec)

        bpmn_file_name_with_extension = bpmn_file_name
        if not bpmn_file_name_with_extension:
            bpmn_file_name_with_extension = os.path.basename(process_model_id)

        if not bpmn_file_name_with_extension.endswith(".bpmn"):
            bpmn_file_name_with_extension += ".bpmn"

        process_model_source_directory_to_use = process_model_source_directory
        if not process_model_source_directory_to_use:
            process_model_source_directory_to_use = process_model_id

        file_name_matcher = "*.*"
        if bpmn_file_name:
            file_name_matcher = bpmn_file_name_with_extension

        # we need instance_path here for nox tests
        file_glob = os.path.join(
            current_app.instance_path,
            "..",
            "..",
            "tests",
            "data",
            process_model_source_directory_to_use,
            file_name_matcher,
        )

        files = sorted(glob.glob(file_glob))
        for file_path in files:
            if os.path.isdir(file_path):
                continue  # Don't try to process sub directories

            filename = os.path.basename(file_path)
            # since there are multiple bpmn files in a test data directory, ensure we set the correct one as the primary
            is_primary = filename.lower() == bpmn_file_name_with_extension
            file = None
            try:
                file = open(file_path, "rb")
                data = file.read()
                file_info = SpecFileService.add_file(process_model_info=spec, file_name=filename, binary_data=data)
                if is_primary:
                    references = SpecFileService.get_references_for_file(file_info, spec)
                    spec.primary_process_id = references[0].identifier
                    spec.primary_file_name = filename
                    ProcessModelService.save_process_model(spec)
            finally:
                if file:
                    file.close()
        return spec
