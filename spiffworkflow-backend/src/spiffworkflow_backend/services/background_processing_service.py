"""Background_processing_service."""
import flask

from spiffworkflow_backend.models.process_instance import ProcessInstanceStatus
from spiffworkflow_backend.services.message_service import MessageService
from spiffworkflow_backend.services.process_instance_lock_service import (
    ProcessInstanceLockService,
)
from spiffworkflow_backend.services.process_instance_service import (
    ProcessInstanceService,
)


class BackgroundProcessingService:
    """Used to facilitate doing work outside of an HTTP request/response."""

    def __init__(self, app: flask.app.Flask):
        """__init__."""
        self.app = app

    def process_waiting_process_instances(self) -> None:
        """Since this runs in a scheduler, we need to specify the app context as well."""
        with self.app.app_context():
            ProcessInstanceLockService.set_thread_local_locking_context("bg:waiting")
            ProcessInstanceService.do_waiting()

    def process_user_input_required_process_instances(self) -> None:
        """Since this runs in a scheduler, we need to specify the app context as well."""
        with self.app.app_context():
            ProcessInstanceLockService.set_thread_local_locking_context("bg:userinput")
            ProcessInstanceService.do_waiting(ProcessInstanceStatus.user_input_required.value)

    def process_message_instances_with_app_context(self) -> None:
        """Since this runs in a scheduler, we need to specify the app context as well."""
        with self.app.app_context():
            ProcessInstanceLockService.set_thread_local_locking_context("bg:messages")
            MessageService.correlate_all_message_instances()
