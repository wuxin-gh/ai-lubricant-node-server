from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProjectValidationSeverity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROJECT_VALIDATION_SEVERITY_UNSPECIFIED: _ClassVar[ProjectValidationSeverity]
    PROJECT_VALIDATION_SEVERITY_WARNING: _ClassVar[ProjectValidationSeverity]
    PROJECT_VALIDATION_SEVERITY_ERROR: _ClassVar[ProjectValidationSeverity]

class ProjectChangeAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROJECT_CHANGE_ACTION_UNSPECIFIED: _ClassVar[ProjectChangeAction]
    PROJECT_CHANGE_ACTION_CREATED: _ClassVar[ProjectChangeAction]
    PROJECT_CHANGE_ACTION_UPDATED: _ClassVar[ProjectChangeAction]
    PROJECT_CHANGE_ACTION_REMOVED: _ClassVar[ProjectChangeAction]
    PROJECT_CHANGE_ACTION_UNCHANGED: _ClassVar[ProjectChangeAction]

class ProjectWatchEventType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROJECT_WATCH_EVENT_TYPE_UNSPECIFIED: _ClassVar[ProjectWatchEventType]
    PROJECT_WATCH_EVENT_TYPE_APPLIED: _ClassVar[ProjectWatchEventType]
    PROJECT_WATCH_EVENT_TYPE_REMOVED: _ClassVar[ProjectWatchEventType]
    PROJECT_WATCH_EVENT_TYPE_CHANGED: _ClassVar[ProjectWatchEventType]

class RunStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RUN_STATUS_UNSPECIFIED: _ClassVar[RunStatus]
    RUN_STATUS_PENDING: _ClassVar[RunStatus]
    RUN_STATUS_RUNNING: _ClassVar[RunStatus]
    RUN_STATUS_SUCCEEDED: _ClassVar[RunStatus]
    RUN_STATUS_FAILED: _ClassVar[RunStatus]
    RUN_STATUS_CANCELED: _ClassVar[RunStatus]

class RunSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RUN_SOURCE_UNSPECIFIED: _ClassVar[RunSource]
    RUN_SOURCE_MANUAL: _ClassVar[RunSource]
    RUN_SOURCE_SCHEDULER: _ClassVar[RunSource]
    RUN_SOURCE_API: _ClassVar[RunSource]

class RunAgentStreamEventType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RUN_AGENT_STREAM_EVENT_TYPE_UNSPECIFIED: _ClassVar[RunAgentStreamEventType]
    RUN_AGENT_STREAM_EVENT_TYPE_STARTED: _ClassVar[RunAgentStreamEventType]
    RUN_AGENT_STREAM_EVENT_TYPE_OUTPUT: _ClassVar[RunAgentStreamEventType]
    RUN_AGENT_STREAM_EVENT_TYPE_STATUS: _ClassVar[RunAgentStreamEventType]
    RUN_AGENT_STREAM_EVENT_TYPE_COMPLETED: _ClassVar[RunAgentStreamEventType]

class RunSandboxCleanupPolicy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RUN_SANDBOX_CLEANUP_POLICY_UNSPECIFIED: _ClassVar[RunSandboxCleanupPolicy]
    RUN_SANDBOX_CLEANUP_POLICY_STOP_ON_COMPLETION: _ClassVar[RunSandboxCleanupPolicy]
    RUN_SANDBOX_CLEANUP_POLICY_KEEP_RUNNING: _ClassVar[RunSandboxCleanupPolicy]
    RUN_SANDBOX_CLEANUP_POLICY_REMOVE_ON_COMPLETION: _ClassVar[RunSandboxCleanupPolicy]

class ExecStreamEventType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXEC_STREAM_EVENT_TYPE_UNSPECIFIED: _ClassVar[ExecStreamEventType]
    EXEC_STREAM_EVENT_TYPE_STARTED: _ClassVar[ExecStreamEventType]
    EXEC_STREAM_EVENT_TYPE_OUTPUT: _ClassVar[ExecStreamEventType]
    EXEC_STREAM_EVENT_TYPE_COMPLETED: _ClassVar[ExecStreamEventType]

class AttachRunMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ATTACH_RUN_MODE_UNSPECIFIED: _ClassVar[AttachRunMode]
    ATTACH_RUN_MODE_COMMAND: _ClassVar[AttachRunMode]
    ATTACH_RUN_MODE_PROMPT: _ClassVar[AttachRunMode]

class StdioStream(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STDIO_STREAM_UNSPECIFIED: _ClassVar[StdioStream]
    STDIO_STREAM_STDOUT: _ClassVar[StdioStream]
    STDIO_STREAM_STDERR: _ClassVar[StdioStream]

class ImageStoreKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IMAGE_STORE_KIND_UNSPECIFIED: _ClassVar[ImageStoreKind]
    IMAGE_STORE_KIND_DOCKER_DAEMON: _ClassVar[ImageStoreKind]
    IMAGE_STORE_KIND_OCI_CACHE: _ClassVar[ImageStoreKind]

class ImageAvailabilityStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IMAGE_AVAILABILITY_STATUS_UNSPECIFIED: _ClassVar[ImageAvailabilityStatus]
    IMAGE_AVAILABILITY_STATUS_AVAILABLE: _ClassVar[ImageAvailabilityStatus]
    IMAGE_AVAILABILITY_STATUS_MISSING: _ClassVar[ImageAvailabilityStatus]
    IMAGE_AVAILABILITY_STATUS_ERROR: _ClassVar[ImageAvailabilityStatus]

class ImageOperationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IMAGE_OPERATION_STATUS_UNSPECIFIED: _ClassVar[ImageOperationStatus]
    IMAGE_OPERATION_STATUS_SUCCEEDED: _ClassVar[ImageOperationStatus]
    IMAGE_OPERATION_STATUS_FAILED: _ClassVar[ImageOperationStatus]
    IMAGE_OPERATION_STATUS_RUNNING: _ClassVar[ImageOperationStatus]

class MetricStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    METRIC_STATUS_UNSPECIFIED: _ClassVar[MetricStatus]
    METRIC_STATUS_OK: _ClassVar[MetricStatus]
    METRIC_STATUS_UNKNOWN: _ClassVar[MetricStatus]
    METRIC_STATUS_UNAVAILABLE: _ClassVar[MetricStatus]

class CacheDomain(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CACHE_DOMAIN_UNSPECIFIED: _ClassVar[CacheDomain]
    CACHE_DOMAIN_OCI_IMAGE_STORE: _ClassVar[CacheDomain]
    CACHE_DOMAIN_MATERIALIZED_IMAGE_CACHE: _ClassVar[CacheDomain]
    CACHE_DOMAIN_RUNTIME_DERIVED_CACHE: _ClassVar[CacheDomain]
    CACHE_DOMAIN_SANDBOX_EPHEMERAL_STATE: _ClassVar[CacheDomain]

class CacheStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CACHE_STATUS_UNSPECIFIED: _ClassVar[CacheStatus]
    CACHE_STATUS_ACTIVE: _ClassVar[CacheStatus]
    CACHE_STATUS_REFERENCED: _ClassVar[CacheStatus]
    CACHE_STATUS_UNUSED: _ClassVar[CacheStatus]
    CACHE_STATUS_EXPIRED: _ClassVar[CacheStatus]
    CACHE_STATUS_ORPHANED: _ClassVar[CacheStatus]
    CACHE_STATUS_UNKNOWN: _ClassVar[CacheStatus]

class NodeStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NODE_STATUS_UNSPECIFIED: _ClassVar[NodeStatus]
    NODE_STATUS_PENDING: _ClassVar[NodeStatus]
    NODE_STATUS_APPROVED: _ClassVar[NodeStatus]
    NODE_STATUS_REVOKED: _ClassVar[NodeStatus]

class NodeRole(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NODE_ROLE_UNSPECIFIED: _ClassVar[NodeRole]
    NODE_ROLE_EXECUTION: _ClassVar[NodeRole]
    NODE_ROLE_MANAGEMENT: _ClassVar[NodeRole]
    NODE_ROLE_PASSIVE_MANAGEMENT: _ClassVar[NodeRole]
    NODE_ROLE_IOS_HOST: _ClassVar[NodeRole]

class NodeStartupMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NODE_STARTUP_METHOD_UNSPECIFIED: _ClassVar[NodeStartupMethod]
    NODE_STARTUP_METHOD_STANDALONE: _ClassVar[NodeStartupMethod]
    NODE_STARTUP_METHOD_SYSTEMD: _ClassVar[NodeStartupMethod]
    NODE_STARTUP_METHOD_DOCKER: _ClassVar[NodeStartupMethod]
    NODE_STARTUP_METHOD_DOCKER_COMPOSE: _ClassVar[NodeStartupMethod]

class EnvironmentAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ENVIRONMENT_ACTION_UNSPECIFIED: _ClassVar[EnvironmentAction]
    ENVIRONMENT_ACTION_CREATE: _ClassVar[EnvironmentAction]
    ENVIRONMENT_ACTION_REMOVE: _ClassVar[EnvironmentAction]

class EditorAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EDITOR_ACTION_UNSPECIFIED: _ClassVar[EditorAction]
    EDITOR_ACTION_INSTALL: _ClassVar[EditorAction]
    EDITOR_ACTION_UPGRADE: _ClassVar[EditorAction]

class NodeToolRunKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NODE_TOOL_RUN_KIND_UNSPECIFIED: _ClassVar[NodeToolRunKind]
    NODE_TOOL_RUN_KIND_STDOUT: _ClassVar[NodeToolRunKind]
    NODE_TOOL_RUN_KIND_STDERR: _ClassVar[NodeToolRunKind]
    NODE_TOOL_RUN_KIND_EXITED: _ClassVar[NodeToolRunKind]
    NODE_TOOL_RUN_KIND_STARTED: _ClassVar[NodeToolRunKind]

class SessionStage(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SESSION_STAGE_UNSPECIFIED: _ClassVar[SessionStage]
    SESSION_STAGE_WORKSPACE_PREPARE: _ClassVar[SessionStage]
    SESSION_STAGE_GIT_CLONE: _ClassVar[SessionStage]
    SESSION_STAGE_RUNTIME_PREFLIGHT: _ClassVar[SessionStage]
    SESSION_STAGE_RUNTIME_START: _ClassVar[SessionStage]
    SESSION_STAGE_RUNNING: _ClassVar[SessionStage]
    SESSION_STAGE_RESOURCE_SYNC: _ClassVar[SessionStage]

class IosConnectionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IOS_CONNECTION_TYPE_UNSPECIFIED: _ClassVar[IosConnectionType]
    IOS_CONNECTION_TYPE_USB: _ClassVar[IosConnectionType]
    IOS_CONNECTION_TYPE_NETWORK: _ClassVar[IosConnectionType]

class IosWdaState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IOS_WDA_STATE_UNSPECIFIED: _ClassVar[IosWdaState]
    IOS_WDA_STATE_MISSING: _ClassVar[IosWdaState]
    IOS_WDA_STATE_PREPARING: _ClassVar[IosWdaState]
    IOS_WDA_STATE_READY: _ClassVar[IosWdaState]
    IOS_WDA_STATE_RENEWAL_DUE: _ClassVar[IosWdaState]
    IOS_WDA_STATE_EXPIRED: _ClassVar[IosWdaState]
    IOS_WDA_STATE_FAILED: _ClassVar[IosWdaState]

class IosWdaJobAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IOS_WDA_JOB_ACTION_UNSPECIFIED: _ClassVar[IosWdaJobAction]
    IOS_WDA_JOB_ACTION_PREPARE: _ClassVar[IosWdaJobAction]
    IOS_WDA_JOB_ACTION_RENEW: _ClassVar[IosWdaJobAction]
    IOS_WDA_JOB_ACTION_REINSTALL: _ClassVar[IosWdaJobAction]
    IOS_WDA_JOB_ACTION_INSTALL_SIGNED: _ClassVar[IosWdaJobAction]

class IosSigningMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IOS_SIGNING_MODE_UNSPECIFIED: _ClassVar[IosSigningMode]
    IOS_SIGNING_MODE_APP_STORE_CONNECT: _ClassVar[IosSigningMode]
    IOS_SIGNING_MODE_MANUAL_P12: _ClassVar[IosSigningMode]
    IOS_SIGNING_MODE_PRESIGNED: _ClassVar[IosSigningMode]

class IosJobStage(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    IOS_JOB_STAGE_UNSPECIFIED: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_QUEUED: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_DOWNLOADING: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_VERIFYING: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_ENABLING_DEVELOPER_MODE: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_ENSURING_DEVICE: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_ENSURING_BUNDLE_ID: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_PREPARING_CERTIFICATE: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_CREATING_PROFILE: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_SIGNING: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_INSTALLING: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_MOUNTING_DEVELOPER_IMAGE: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_STARTING_RUNNER: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_FORWARDING_PORT: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_WAITING_READY: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_VERIFYING_CONTROL: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_COMPLETED: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_FAILED: _ClassVar[IosJobStage]
    IOS_JOB_STAGE_CANCELLED: _ClassVar[IosJobStage]
PROJECT_VALIDATION_SEVERITY_UNSPECIFIED: ProjectValidationSeverity
PROJECT_VALIDATION_SEVERITY_WARNING: ProjectValidationSeverity
PROJECT_VALIDATION_SEVERITY_ERROR: ProjectValidationSeverity
PROJECT_CHANGE_ACTION_UNSPECIFIED: ProjectChangeAction
PROJECT_CHANGE_ACTION_CREATED: ProjectChangeAction
PROJECT_CHANGE_ACTION_UPDATED: ProjectChangeAction
PROJECT_CHANGE_ACTION_REMOVED: ProjectChangeAction
PROJECT_CHANGE_ACTION_UNCHANGED: ProjectChangeAction
PROJECT_WATCH_EVENT_TYPE_UNSPECIFIED: ProjectWatchEventType
PROJECT_WATCH_EVENT_TYPE_APPLIED: ProjectWatchEventType
PROJECT_WATCH_EVENT_TYPE_REMOVED: ProjectWatchEventType
PROJECT_WATCH_EVENT_TYPE_CHANGED: ProjectWatchEventType
RUN_STATUS_UNSPECIFIED: RunStatus
RUN_STATUS_PENDING: RunStatus
RUN_STATUS_RUNNING: RunStatus
RUN_STATUS_SUCCEEDED: RunStatus
RUN_STATUS_FAILED: RunStatus
RUN_STATUS_CANCELED: RunStatus
RUN_SOURCE_UNSPECIFIED: RunSource
RUN_SOURCE_MANUAL: RunSource
RUN_SOURCE_SCHEDULER: RunSource
RUN_SOURCE_API: RunSource
RUN_AGENT_STREAM_EVENT_TYPE_UNSPECIFIED: RunAgentStreamEventType
RUN_AGENT_STREAM_EVENT_TYPE_STARTED: RunAgentStreamEventType
RUN_AGENT_STREAM_EVENT_TYPE_OUTPUT: RunAgentStreamEventType
RUN_AGENT_STREAM_EVENT_TYPE_STATUS: RunAgentStreamEventType
RUN_AGENT_STREAM_EVENT_TYPE_COMPLETED: RunAgentStreamEventType
RUN_SANDBOX_CLEANUP_POLICY_UNSPECIFIED: RunSandboxCleanupPolicy
RUN_SANDBOX_CLEANUP_POLICY_STOP_ON_COMPLETION: RunSandboxCleanupPolicy
RUN_SANDBOX_CLEANUP_POLICY_KEEP_RUNNING: RunSandboxCleanupPolicy
RUN_SANDBOX_CLEANUP_POLICY_REMOVE_ON_COMPLETION: RunSandboxCleanupPolicy
EXEC_STREAM_EVENT_TYPE_UNSPECIFIED: ExecStreamEventType
EXEC_STREAM_EVENT_TYPE_STARTED: ExecStreamEventType
EXEC_STREAM_EVENT_TYPE_OUTPUT: ExecStreamEventType
EXEC_STREAM_EVENT_TYPE_COMPLETED: ExecStreamEventType
ATTACH_RUN_MODE_UNSPECIFIED: AttachRunMode
ATTACH_RUN_MODE_COMMAND: AttachRunMode
ATTACH_RUN_MODE_PROMPT: AttachRunMode
STDIO_STREAM_UNSPECIFIED: StdioStream
STDIO_STREAM_STDOUT: StdioStream
STDIO_STREAM_STDERR: StdioStream
IMAGE_STORE_KIND_UNSPECIFIED: ImageStoreKind
IMAGE_STORE_KIND_DOCKER_DAEMON: ImageStoreKind
IMAGE_STORE_KIND_OCI_CACHE: ImageStoreKind
IMAGE_AVAILABILITY_STATUS_UNSPECIFIED: ImageAvailabilityStatus
IMAGE_AVAILABILITY_STATUS_AVAILABLE: ImageAvailabilityStatus
IMAGE_AVAILABILITY_STATUS_MISSING: ImageAvailabilityStatus
IMAGE_AVAILABILITY_STATUS_ERROR: ImageAvailabilityStatus
IMAGE_OPERATION_STATUS_UNSPECIFIED: ImageOperationStatus
IMAGE_OPERATION_STATUS_SUCCEEDED: ImageOperationStatus
IMAGE_OPERATION_STATUS_FAILED: ImageOperationStatus
IMAGE_OPERATION_STATUS_RUNNING: ImageOperationStatus
METRIC_STATUS_UNSPECIFIED: MetricStatus
METRIC_STATUS_OK: MetricStatus
METRIC_STATUS_UNKNOWN: MetricStatus
METRIC_STATUS_UNAVAILABLE: MetricStatus
CACHE_DOMAIN_UNSPECIFIED: CacheDomain
CACHE_DOMAIN_OCI_IMAGE_STORE: CacheDomain
CACHE_DOMAIN_MATERIALIZED_IMAGE_CACHE: CacheDomain
CACHE_DOMAIN_RUNTIME_DERIVED_CACHE: CacheDomain
CACHE_DOMAIN_SANDBOX_EPHEMERAL_STATE: CacheDomain
CACHE_STATUS_UNSPECIFIED: CacheStatus
CACHE_STATUS_ACTIVE: CacheStatus
CACHE_STATUS_REFERENCED: CacheStatus
CACHE_STATUS_UNUSED: CacheStatus
CACHE_STATUS_EXPIRED: CacheStatus
CACHE_STATUS_ORPHANED: CacheStatus
CACHE_STATUS_UNKNOWN: CacheStatus
NODE_STATUS_UNSPECIFIED: NodeStatus
NODE_STATUS_PENDING: NodeStatus
NODE_STATUS_APPROVED: NodeStatus
NODE_STATUS_REVOKED: NodeStatus
NODE_ROLE_UNSPECIFIED: NodeRole
NODE_ROLE_EXECUTION: NodeRole
NODE_ROLE_MANAGEMENT: NodeRole
NODE_ROLE_PASSIVE_MANAGEMENT: NodeRole
NODE_ROLE_IOS_HOST: NodeRole
NODE_STARTUP_METHOD_UNSPECIFIED: NodeStartupMethod
NODE_STARTUP_METHOD_STANDALONE: NodeStartupMethod
NODE_STARTUP_METHOD_SYSTEMD: NodeStartupMethod
NODE_STARTUP_METHOD_DOCKER: NodeStartupMethod
NODE_STARTUP_METHOD_DOCKER_COMPOSE: NodeStartupMethod
ENVIRONMENT_ACTION_UNSPECIFIED: EnvironmentAction
ENVIRONMENT_ACTION_CREATE: EnvironmentAction
ENVIRONMENT_ACTION_REMOVE: EnvironmentAction
EDITOR_ACTION_UNSPECIFIED: EditorAction
EDITOR_ACTION_INSTALL: EditorAction
EDITOR_ACTION_UPGRADE: EditorAction
NODE_TOOL_RUN_KIND_UNSPECIFIED: NodeToolRunKind
NODE_TOOL_RUN_KIND_STDOUT: NodeToolRunKind
NODE_TOOL_RUN_KIND_STDERR: NodeToolRunKind
NODE_TOOL_RUN_KIND_EXITED: NodeToolRunKind
NODE_TOOL_RUN_KIND_STARTED: NodeToolRunKind
SESSION_STAGE_UNSPECIFIED: SessionStage
SESSION_STAGE_WORKSPACE_PREPARE: SessionStage
SESSION_STAGE_GIT_CLONE: SessionStage
SESSION_STAGE_RUNTIME_PREFLIGHT: SessionStage
SESSION_STAGE_RUNTIME_START: SessionStage
SESSION_STAGE_RUNNING: SessionStage
SESSION_STAGE_RESOURCE_SYNC: SessionStage
IOS_CONNECTION_TYPE_UNSPECIFIED: IosConnectionType
IOS_CONNECTION_TYPE_USB: IosConnectionType
IOS_CONNECTION_TYPE_NETWORK: IosConnectionType
IOS_WDA_STATE_UNSPECIFIED: IosWdaState
IOS_WDA_STATE_MISSING: IosWdaState
IOS_WDA_STATE_PREPARING: IosWdaState
IOS_WDA_STATE_READY: IosWdaState
IOS_WDA_STATE_RENEWAL_DUE: IosWdaState
IOS_WDA_STATE_EXPIRED: IosWdaState
IOS_WDA_STATE_FAILED: IosWdaState
IOS_WDA_JOB_ACTION_UNSPECIFIED: IosWdaJobAction
IOS_WDA_JOB_ACTION_PREPARE: IosWdaJobAction
IOS_WDA_JOB_ACTION_RENEW: IosWdaJobAction
IOS_WDA_JOB_ACTION_REINSTALL: IosWdaJobAction
IOS_WDA_JOB_ACTION_INSTALL_SIGNED: IosWdaJobAction
IOS_SIGNING_MODE_UNSPECIFIED: IosSigningMode
IOS_SIGNING_MODE_APP_STORE_CONNECT: IosSigningMode
IOS_SIGNING_MODE_MANUAL_P12: IosSigningMode
IOS_SIGNING_MODE_PRESIGNED: IosSigningMode
IOS_JOB_STAGE_UNSPECIFIED: IosJobStage
IOS_JOB_STAGE_QUEUED: IosJobStage
IOS_JOB_STAGE_DOWNLOADING: IosJobStage
IOS_JOB_STAGE_VERIFYING: IosJobStage
IOS_JOB_STAGE_ENABLING_DEVELOPER_MODE: IosJobStage
IOS_JOB_STAGE_ENSURING_DEVICE: IosJobStage
IOS_JOB_STAGE_ENSURING_BUNDLE_ID: IosJobStage
IOS_JOB_STAGE_PREPARING_CERTIFICATE: IosJobStage
IOS_JOB_STAGE_CREATING_PROFILE: IosJobStage
IOS_JOB_STAGE_SIGNING: IosJobStage
IOS_JOB_STAGE_INSTALLING: IosJobStage
IOS_JOB_STAGE_MOUNTING_DEVELOPER_IMAGE: IosJobStage
IOS_JOB_STAGE_STARTING_RUNNER: IosJobStage
IOS_JOB_STAGE_FORWARDING_PORT: IosJobStage
IOS_JOB_STAGE_WAITING_READY: IosJobStage
IOS_JOB_STAGE_VERIFYING_CONTROL: IosJobStage
IOS_JOB_STAGE_COMPLETED: IosJobStage
IOS_JOB_STAGE_FAILED: IosJobStage
IOS_JOB_STAGE_CANCELLED: IosJobStage

class ValidateProjectRequest(_message.Message):
    __slots__ = ("spec", "source", "expected_spec_hash")
    SPEC_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_SPEC_HASH_FIELD_NUMBER: _ClassVar[int]
    spec: ProjectSpec
    source: ProjectSource
    expected_spec_hash: str
    def __init__(self, spec: _Optional[_Union[ProjectSpec, _Mapping]] = ..., source: _Optional[_Union[ProjectSource, _Mapping]] = ..., expected_spec_hash: _Optional[str] = ...) -> None: ...

class ValidateProjectResponse(_message.Message):
    __slots__ = ("valid", "issues", "spec_hash")
    VALID_FIELD_NUMBER: _ClassVar[int]
    ISSUES_FIELD_NUMBER: _ClassVar[int]
    SPEC_HASH_FIELD_NUMBER: _ClassVar[int]
    valid: bool
    issues: _containers.RepeatedCompositeFieldContainer[ProjectValidationIssue]
    spec_hash: str
    def __init__(self, valid: _Optional[bool] = ..., issues: _Optional[_Iterable[_Union[ProjectValidationIssue, _Mapping]]] = ..., spec_hash: _Optional[str] = ...) -> None: ...

class ApplyProjectRequest(_message.Message):
    __slots__ = ("spec", "source", "expected_spec_hash", "dry_run")
    SPEC_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_SPEC_HASH_FIELD_NUMBER: _ClassVar[int]
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    spec: ProjectSpec
    source: ProjectSource
    expected_spec_hash: str
    dry_run: bool
    def __init__(self, spec: _Optional[_Union[ProjectSpec, _Mapping]] = ..., source: _Optional[_Union[ProjectSource, _Mapping]] = ..., expected_spec_hash: _Optional[str] = ..., dry_run: _Optional[bool] = ...) -> None: ...

class ApplyProjectResponse(_message.Message):
    __slots__ = ("project", "revision", "changes", "issues", "applied", "unchanged")
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    CHANGES_FIELD_NUMBER: _ClassVar[int]
    ISSUES_FIELD_NUMBER: _ClassVar[int]
    APPLIED_FIELD_NUMBER: _ClassVar[int]
    UNCHANGED_FIELD_NUMBER: _ClassVar[int]
    project: Project
    revision: ProjectRevision
    changes: _containers.RepeatedCompositeFieldContainer[ProjectChange]
    issues: _containers.RepeatedCompositeFieldContainer[ProjectValidationIssue]
    applied: bool
    unchanged: bool
    def __init__(self, project: _Optional[_Union[Project, _Mapping]] = ..., revision: _Optional[_Union[ProjectRevision, _Mapping]] = ..., changes: _Optional[_Iterable[_Union[ProjectChange, _Mapping]]] = ..., issues: _Optional[_Iterable[_Union[ProjectValidationIssue, _Mapping]]] = ..., applied: _Optional[bool] = ..., unchanged: _Optional[bool] = ...) -> None: ...

class GetProjectRequest(_message.Message):
    __slots__ = ("project", "include_spec")
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_SPEC_FIELD_NUMBER: _ClassVar[int]
    project: ProjectRef
    include_spec: bool
    def __init__(self, project: _Optional[_Union[ProjectRef, _Mapping]] = ..., include_spec: _Optional[bool] = ...) -> None: ...

class GetProjectResponse(_message.Message):
    __slots__ = ("project",)
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    project: Project
    def __init__(self, project: _Optional[_Union[Project, _Mapping]] = ...) -> None: ...

class ListProjectsRequest(_message.Message):
    __slots__ = ("query", "include_removed", "offset", "limit")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_REMOVED_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    query: str
    include_removed: bool
    offset: int
    limit: int
    def __init__(self, query: _Optional[str] = ..., include_removed: _Optional[bool] = ..., offset: _Optional[int] = ..., limit: _Optional[int] = ...) -> None: ...

class ListProjectsResponse(_message.Message):
    __slots__ = ("projects", "total_count", "has_more", "next_offset")
    PROJECTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    HAS_MORE_FIELD_NUMBER: _ClassVar[int]
    NEXT_OFFSET_FIELD_NUMBER: _ClassVar[int]
    projects: _containers.RepeatedCompositeFieldContainer[ProjectSummary]
    total_count: int
    has_more: bool
    next_offset: int
    def __init__(self, projects: _Optional[_Iterable[_Union[ProjectSummary, _Mapping]]] = ..., total_count: _Optional[int] = ..., has_more: _Optional[bool] = ..., next_offset: _Optional[int] = ...) -> None: ...

class RemoveProjectRequest(_message.Message):
    __slots__ = ("project", "remove_history", "stop_running_sandboxes")
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    REMOVE_HISTORY_FIELD_NUMBER: _ClassVar[int]
    STOP_RUNNING_SANDBOXES_FIELD_NUMBER: _ClassVar[int]
    project: ProjectRef
    remove_history: bool
    stop_running_sandboxes: bool
    def __init__(self, project: _Optional[_Union[ProjectRef, _Mapping]] = ..., remove_history: _Optional[bool] = ..., stop_running_sandboxes: _Optional[bool] = ...) -> None: ...

class RemoveProjectResponse(_message.Message):
    __slots__ = ("project", "changes")
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    CHANGES_FIELD_NUMBER: _ClassVar[int]
    project: Project
    changes: _containers.RepeatedCompositeFieldContainer[ProjectChange]
    def __init__(self, project: _Optional[_Union[Project, _Mapping]] = ..., changes: _Optional[_Iterable[_Union[ProjectChange, _Mapping]]] = ...) -> None: ...

class WatchProjectRequest(_message.Message):
    __slots__ = ("project",)
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    project: ProjectRef
    def __init__(self, project: _Optional[_Union[ProjectRef, _Mapping]] = ...) -> None: ...

class WatchProjectResponse(_message.Message):
    __slots__ = ("type", "project", "revision", "changes")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    CHANGES_FIELD_NUMBER: _ClassVar[int]
    type: ProjectWatchEventType
    project: Project
    revision: ProjectRevision
    changes: _containers.RepeatedCompositeFieldContainer[ProjectChange]
    def __init__(self, type: _Optional[_Union[ProjectWatchEventType, str]] = ..., project: _Optional[_Union[Project, _Mapping]] = ..., revision: _Optional[_Union[ProjectRevision, _Mapping]] = ..., changes: _Optional[_Iterable[_Union[ProjectChange, _Mapping]]] = ...) -> None: ...

class ProjectRef(_message.Message):
    __slots__ = ("project_id", "name", "source_path")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_PATH_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    name: str
    source_path: str
    def __init__(self, project_id: _Optional[str] = ..., name: _Optional[str] = ..., source_path: _Optional[str] = ...) -> None: ...

class ProjectSource(_message.Message):
    __slots__ = ("compose_path", "project_dir")
    COMPOSE_PATH_FIELD_NUMBER: _ClassVar[int]
    PROJECT_DIR_FIELD_NUMBER: _ClassVar[int]
    compose_path: str
    project_dir: str
    def __init__(self, compose_path: _Optional[str] = ..., project_dir: _Optional[str] = ...) -> None: ...

class Project(_message.Message):
    __slots__ = ("summary", "spec", "agents", "schedulers")
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    SPEC_FIELD_NUMBER: _ClassVar[int]
    AGENTS_FIELD_NUMBER: _ClassVar[int]
    SCHEDULERS_FIELD_NUMBER: _ClassVar[int]
    summary: ProjectSummary
    spec: ProjectSpec
    agents: _containers.RepeatedCompositeFieldContainer[ProjectAgent]
    schedulers: _containers.RepeatedCompositeFieldContainer[ProjectScheduler]
    def __init__(self, summary: _Optional[_Union[ProjectSummary, _Mapping]] = ..., spec: _Optional[_Union[ProjectSpec, _Mapping]] = ..., agents: _Optional[_Iterable[_Union[ProjectAgent, _Mapping]]] = ..., schedulers: _Optional[_Iterable[_Union[ProjectScheduler, _Mapping]]] = ...) -> None: ...

class ProjectSummary(_message.Message):
    __slots__ = ("project_id", "name", "source_path", "current_revision", "spec_hash", "agent_count", "scheduler_count", "running_run_count", "latest_run_id", "created_at", "updated_at", "removed_at")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_PATH_FIELD_NUMBER: _ClassVar[int]
    CURRENT_REVISION_FIELD_NUMBER: _ClassVar[int]
    SPEC_HASH_FIELD_NUMBER: _ClassVar[int]
    AGENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    SCHEDULER_COUNT_FIELD_NUMBER: _ClassVar[int]
    RUNNING_RUN_COUNT_FIELD_NUMBER: _ClassVar[int]
    LATEST_RUN_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    REMOVED_AT_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    name: str
    source_path: str
    current_revision: int
    spec_hash: str
    agent_count: int
    scheduler_count: int
    running_run_count: int
    latest_run_id: str
    created_at: str
    updated_at: str
    removed_at: str
    def __init__(self, project_id: _Optional[str] = ..., name: _Optional[str] = ..., source_path: _Optional[str] = ..., current_revision: _Optional[int] = ..., spec_hash: _Optional[str] = ..., agent_count: _Optional[int] = ..., scheduler_count: _Optional[int] = ..., running_run_count: _Optional[int] = ..., latest_run_id: _Optional[str] = ..., created_at: _Optional[str] = ..., updated_at: _Optional[str] = ..., removed_at: _Optional[str] = ...) -> None: ...

class ProjectRevision(_message.Message):
    __slots__ = ("project_id", "revision", "spec_hash", "spec", "created_at")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    SPEC_HASH_FIELD_NUMBER: _ClassVar[int]
    SPEC_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    revision: int
    spec_hash: str
    spec: ProjectSpec
    created_at: str
    def __init__(self, project_id: _Optional[str] = ..., revision: _Optional[int] = ..., spec_hash: _Optional[str] = ..., spec: _Optional[_Union[ProjectSpec, _Mapping]] = ..., created_at: _Optional[str] = ...) -> None: ...

class ProjectAgent(_message.Message):
    __slots__ = ("project_id", "agent_name", "managed_agent_id", "provider", "model", "image", "driver", "scheduler_enabled")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    MANAGED_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    SCHEDULER_ENABLED_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    agent_name: str
    managed_agent_id: str
    provider: str
    model: str
    image: str
    driver: str
    scheduler_enabled: bool
    def __init__(self, project_id: _Optional[str] = ..., agent_name: _Optional[str] = ..., managed_agent_id: _Optional[str] = ..., provider: _Optional[str] = ..., model: _Optional[str] = ..., image: _Optional[str] = ..., driver: _Optional[str] = ..., scheduler_enabled: _Optional[bool] = ...) -> None: ...

class ProjectScheduler(_message.Message):
    __slots__ = ("project_id", "agent_name", "scheduler_id", "managed_loader_id", "enabled", "trigger_count")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    SCHEDULER_ID_FIELD_NUMBER: _ClassVar[int]
    MANAGED_LOADER_ID_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_COUNT_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    agent_name: str
    scheduler_id: str
    managed_loader_id: str
    enabled: bool
    trigger_count: int
    def __init__(self, project_id: _Optional[str] = ..., agent_name: _Optional[str] = ..., scheduler_id: _Optional[str] = ..., managed_loader_id: _Optional[str] = ..., enabled: _Optional[bool] = ..., trigger_count: _Optional[int] = ...) -> None: ...

class ProjectValidationIssue(_message.Message):
    __slots__ = ("severity", "path", "message")
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    severity: ProjectValidationSeverity
    path: str
    message: str
    def __init__(self, severity: _Optional[_Union[ProjectValidationSeverity, str]] = ..., path: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class ProjectChange(_message.Message):
    __slots__ = ("action", "resource_type", "resource_id", "name", "message")
    ACTION_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    action: ProjectChangeAction
    resource_type: str
    resource_id: str
    name: str
    message: str
    def __init__(self, action: _Optional[_Union[ProjectChangeAction, str]] = ..., resource_type: _Optional[str] = ..., resource_id: _Optional[str] = ..., name: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class ProjectSpec(_message.Message):
    __slots__ = ("name", "variables", "agents", "network", "volumes", "workspaces", "mcps")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    AGENTS_FIELD_NUMBER: _ClassVar[int]
    NETWORK_FIELD_NUMBER: _ClassVar[int]
    VOLUMES_FIELD_NUMBER: _ClassVar[int]
    WORKSPACES_FIELD_NUMBER: _ClassVar[int]
    MCPS_FIELD_NUMBER: _ClassVar[int]
    name: str
    variables: _containers.RepeatedCompositeFieldContainer[EnvVarSpec]
    agents: _containers.RepeatedCompositeFieldContainer[AgentSpec]
    network: NetworkSpec
    volumes: _containers.RepeatedCompositeFieldContainer[ProjectVolumeSpec]
    workspaces: _containers.RepeatedCompositeFieldContainer[NamedWorkspaceSpec]
    mcps: _containers.RepeatedCompositeFieldContainer[MCPServerSpec]
    def __init__(self, name: _Optional[str] = ..., variables: _Optional[_Iterable[_Union[EnvVarSpec, _Mapping]]] = ..., agents: _Optional[_Iterable[_Union[AgentSpec, _Mapping]]] = ..., network: _Optional[_Union[NetworkSpec, _Mapping]] = ..., volumes: _Optional[_Iterable[_Union[ProjectVolumeSpec, _Mapping]]] = ..., workspaces: _Optional[_Iterable[_Union[NamedWorkspaceSpec, _Mapping]]] = ..., mcps: _Optional[_Iterable[_Union[MCPServerSpec, _Mapping]]] = ...) -> None: ...

class NamedWorkspaceSpec(_message.Message):
    __slots__ = ("name", "workspace")
    NAME_FIELD_NUMBER: _ClassVar[int]
    WORKSPACE_FIELD_NUMBER: _ClassVar[int]
    name: str
    workspace: WorkspaceSpec
    def __init__(self, name: _Optional[str] = ..., workspace: _Optional[_Union[WorkspaceSpec, _Mapping]] = ...) -> None: ...

class AgentSpec(_message.Message):
    __slots__ = ("name", "provider", "model", "system_prompt", "image", "driver", "env", "workspace", "scheduler", "capset_ids", "jupyter", "build", "volumes", "mcps", "skills")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    WORKSPACE_FIELD_NUMBER: _ClassVar[int]
    SCHEDULER_FIELD_NUMBER: _ClassVar[int]
    CAPSET_IDS_FIELD_NUMBER: _ClassVar[int]
    JUPYTER_FIELD_NUMBER: _ClassVar[int]
    BUILD_FIELD_NUMBER: _ClassVar[int]
    VOLUMES_FIELD_NUMBER: _ClassVar[int]
    MCPS_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    name: str
    provider: str
    model: str
    system_prompt: str
    image: str
    driver: DriverSpec
    env: _containers.RepeatedCompositeFieldContainer[EnvVarSpec]
    workspace: WorkspaceSpec
    scheduler: SchedulerSpec
    capset_ids: _containers.RepeatedScalarFieldContainer[str]
    jupyter: JupyterSpec
    build: BuildSpec
    volumes: _containers.RepeatedCompositeFieldContainer[VolumeMountSpec]
    mcps: _containers.RepeatedCompositeFieldContainer[MCPServerSpec]
    skills: _containers.RepeatedCompositeFieldContainer[SkillSpec]
    def __init__(self, name: _Optional[str] = ..., provider: _Optional[str] = ..., model: _Optional[str] = ..., system_prompt: _Optional[str] = ..., image: _Optional[str] = ..., driver: _Optional[_Union[DriverSpec, _Mapping]] = ..., env: _Optional[_Iterable[_Union[EnvVarSpec, _Mapping]]] = ..., workspace: _Optional[_Union[WorkspaceSpec, _Mapping]] = ..., scheduler: _Optional[_Union[SchedulerSpec, _Mapping]] = ..., capset_ids: _Optional[_Iterable[str]] = ..., jupyter: _Optional[_Union[JupyterSpec, _Mapping]] = ..., build: _Optional[_Union[BuildSpec, _Mapping]] = ..., volumes: _Optional[_Iterable[_Union[VolumeMountSpec, _Mapping]]] = ..., mcps: _Optional[_Iterable[_Union[MCPServerSpec, _Mapping]]] = ..., skills: _Optional[_Iterable[_Union[SkillSpec, _Mapping]]] = ...) -> None: ...

class MCPServerSpec(_message.Message):
    __slots__ = ("name", "type", "transport", "command", "args", "env", "url", "headers")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: str
    transport: str
    command: str
    args: _containers.RepeatedScalarFieldContainer[str]
    env: _containers.RepeatedCompositeFieldContainer[EnvVarSpec]
    url: str
    headers: _containers.RepeatedCompositeFieldContainer[EnvVarSpec]
    def __init__(self, name: _Optional[str] = ..., type: _Optional[str] = ..., transport: _Optional[str] = ..., command: _Optional[str] = ..., args: _Optional[_Iterable[str]] = ..., env: _Optional[_Iterable[_Union[EnvVarSpec, _Mapping]]] = ..., url: _Optional[str] = ..., headers: _Optional[_Iterable[_Union[EnvVarSpec, _Mapping]]] = ...) -> None: ...

class ProjectVolumeSpec(_message.Message):
    __slots__ = ("key", "name", "driver", "external", "labels", "options")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    KEY_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    key: str
    name: str
    driver: str
    external: bool
    labels: _containers.ScalarMap[str, str]
    options: _containers.ScalarMap[str, str]
    def __init__(self, key: _Optional[str] = ..., name: _Optional[str] = ..., driver: _Optional[str] = ..., external: _Optional[bool] = ..., labels: _Optional[_Mapping[str, str]] = ..., options: _Optional[_Mapping[str, str]] = ...) -> None: ...

class VolumeMountSpec(_message.Message):
    __slots__ = ("type", "source", "target", "read_only")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    READ_ONLY_FIELD_NUMBER: _ClassVar[int]
    type: str
    source: str
    target: str
    read_only: bool
    def __init__(self, type: _Optional[str] = ..., source: _Optional[str] = ..., target: _Optional[str] = ..., read_only: _Optional[bool] = ...) -> None: ...

class BuildSpec(_message.Message):
    __slots__ = ("context", "dockerfile", "target", "args", "platforms", "tags", "no_cache", "pull")
    class ArgsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    DOCKERFILE_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    PLATFORMS_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    NO_CACHE_FIELD_NUMBER: _ClassVar[int]
    PULL_FIELD_NUMBER: _ClassVar[int]
    context: str
    dockerfile: str
    target: str
    args: _containers.ScalarMap[str, str]
    platforms: _containers.RepeatedScalarFieldContainer[str]
    tags: _containers.RepeatedScalarFieldContainer[str]
    no_cache: bool
    pull: bool
    def __init__(self, context: _Optional[str] = ..., dockerfile: _Optional[str] = ..., target: _Optional[str] = ..., args: _Optional[_Mapping[str, str]] = ..., platforms: _Optional[_Iterable[str]] = ..., tags: _Optional[_Iterable[str]] = ..., no_cache: _Optional[bool] = ..., pull: _Optional[bool] = ...) -> None: ...

class EnvVarSpec(_message.Message):
    __slots__ = ("name", "value", "secret")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: str
    secret: bool
    def __init__(self, name: _Optional[str] = ..., value: _Optional[str] = ..., secret: _Optional[bool] = ...) -> None: ...

class WorkspaceSpec(_message.Message):
    __slots__ = ("provider", "url", "branch", "path", "name")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    provider: str
    url: str
    branch: str
    path: str
    name: str
    def __init__(self, provider: _Optional[str] = ..., url: _Optional[str] = ..., branch: _Optional[str] = ..., path: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class NetworkSpec(_message.Message):
    __slots__ = ("mode",)
    MODE_FIELD_NUMBER: _ClassVar[int]
    mode: str
    def __init__(self, mode: _Optional[str] = ...) -> None: ...

class SchedulerSpec(_message.Message):
    __slots__ = ("enabled", "triggers", "script", "sandbox_policy")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    TRIGGERS_FIELD_NUMBER: _ClassVar[int]
    SCRIPT_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_POLICY_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    triggers: _containers.RepeatedCompositeFieldContainer[TriggerSpec]
    script: str
    sandbox_policy: str
    def __init__(self, enabled: _Optional[bool] = ..., triggers: _Optional[_Iterable[_Union[TriggerSpec, _Mapping]]] = ..., script: _Optional[str] = ..., sandbox_policy: _Optional[str] = ...) -> None: ...

class TriggerSpec(_message.Message):
    __slots__ = ("name", "kind", "cron", "interval", "timeout", "event", "prompt", "sandbox_policy")
    NAME_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    CRON_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    EVENT_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_POLICY_FIELD_NUMBER: _ClassVar[int]
    name: str
    kind: str
    cron: str
    interval: str
    timeout: str
    event: EventTriggerSpec
    prompt: str
    sandbox_policy: str
    def __init__(self, name: _Optional[str] = ..., kind: _Optional[str] = ..., cron: _Optional[str] = ..., interval: _Optional[str] = ..., timeout: _Optional[str] = ..., event: _Optional[_Union[EventTriggerSpec, _Mapping]] = ..., prompt: _Optional[str] = ..., sandbox_policy: _Optional[str] = ...) -> None: ...

class EventTriggerSpec(_message.Message):
    __slots__ = ("topic",)
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    topic: str
    def __init__(self, topic: _Optional[str] = ...) -> None: ...

class DriverSpec(_message.Message):
    __slots__ = ("name", "boxlite", "docker", "microsandbox")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BOXLITE_FIELD_NUMBER: _ClassVar[int]
    DOCKER_FIELD_NUMBER: _ClassVar[int]
    MICROSANDBOX_FIELD_NUMBER: _ClassVar[int]
    name: str
    boxlite: BoxliteDriverSpec
    docker: DockerDriverSpec
    microsandbox: MicrosandboxDriverSpec
    def __init__(self, name: _Optional[str] = ..., boxlite: _Optional[_Union[BoxliteDriverSpec, _Mapping]] = ..., docker: _Optional[_Union[DockerDriverSpec, _Mapping]] = ..., microsandbox: _Optional[_Union[MicrosandboxDriverSpec, _Mapping]] = ...) -> None: ...

class BoxliteDriverSpec(_message.Message):
    __slots__ = ("kernel", "rootfs")
    KERNEL_FIELD_NUMBER: _ClassVar[int]
    ROOTFS_FIELD_NUMBER: _ClassVar[int]
    kernel: str
    rootfs: str
    def __init__(self, kernel: _Optional[str] = ..., rootfs: _Optional[str] = ...) -> None: ...

class DockerDriverSpec(_message.Message):
    __slots__ = ("host",)
    HOST_FIELD_NUMBER: _ClassVar[int]
    host: str
    def __init__(self, host: _Optional[str] = ...) -> None: ...

class MicrosandboxDriverSpec(_message.Message):
    __slots__ = ("profile",)
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    profile: str
    def __init__(self, profile: _Optional[str] = ...) -> None: ...

class RunAgentRequest(_message.Message):
    __slots__ = ("project_id", "agent_name", "prompt", "source", "env", "cleanup_policy", "scheduler_id", "trigger_id", "output_schema_json", "client_request_id", "command", "jupyter", "driver", "sandbox_id", "volumes", "payload_json")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    CLEANUP_POLICY_FIELD_NUMBER: _ClassVar[int]
    SCHEDULER_ID_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_ID_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_SCHEMA_JSON_FIELD_NUMBER: _ClassVar[int]
    CLIENT_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    JUPYTER_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    VOLUMES_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_JSON_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    agent_name: str
    prompt: str
    source: RunSource
    env: _containers.RepeatedCompositeFieldContainer[EnvVarSpec]
    cleanup_policy: RunSandboxCleanupPolicy
    scheduler_id: str
    trigger_id: str
    output_schema_json: str
    client_request_id: str
    command: str
    jupyter: RunJupyterSpec
    driver: str
    sandbox_id: str
    volumes: _containers.RepeatedCompositeFieldContainer[VolumeMountSpec]
    payload_json: str
    def __init__(self, project_id: _Optional[str] = ..., agent_name: _Optional[str] = ..., prompt: _Optional[str] = ..., source: _Optional[_Union[RunSource, str]] = ..., env: _Optional[_Iterable[_Union[EnvVarSpec, _Mapping]]] = ..., cleanup_policy: _Optional[_Union[RunSandboxCleanupPolicy, str]] = ..., scheduler_id: _Optional[str] = ..., trigger_id: _Optional[str] = ..., output_schema_json: _Optional[str] = ..., client_request_id: _Optional[str] = ..., command: _Optional[str] = ..., jupyter: _Optional[_Union[RunJupyterSpec, _Mapping]] = ..., driver: _Optional[str] = ..., sandbox_id: _Optional[str] = ..., volumes: _Optional[_Iterable[_Union[VolumeMountSpec, _Mapping]]] = ..., payload_json: _Optional[str] = ...) -> None: ...

class RunAgentResponse(_message.Message):
    __slots__ = ("run", "warnings")
    RUN_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    run: RunDetail
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, run: _Optional[_Union[RunDetail, _Mapping]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class RunAgentStreamResponse(_message.Message):
    __slots__ = ("event_type", "run", "run_id", "chunk", "stream", "created_at", "warnings", "transcript")
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    RUN_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    STREAM_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    TRANSCRIPT_FIELD_NUMBER: _ClassVar[int]
    event_type: RunAgentStreamEventType
    run: RunSummary
    run_id: str
    chunk: str
    stream: StdioStream
    created_at: str
    warnings: _containers.RepeatedScalarFieldContainer[str]
    transcript: TranscriptEvent
    def __init__(self, event_type: _Optional[_Union[RunAgentStreamEventType, str]] = ..., run: _Optional[_Union[RunSummary, _Mapping]] = ..., run_id: _Optional[str] = ..., chunk: _Optional[str] = ..., stream: _Optional[_Union[StdioStream, str]] = ..., created_at: _Optional[str] = ..., warnings: _Optional[_Iterable[str]] = ..., transcript: _Optional[_Union[TranscriptEvent, _Mapping]] = ...) -> None: ...

class RunAttachRequest(_message.Message):
    __slots__ = ("client_frame_id", "start", "stdin", "stdin_eof", "resize", "signal", "human_message", "cancel")
    CLIENT_FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    STDIN_FIELD_NUMBER: _ClassVar[int]
    STDIN_EOF_FIELD_NUMBER: _ClassVar[int]
    RESIZE_FIELD_NUMBER: _ClassVar[int]
    SIGNAL_FIELD_NUMBER: _ClassVar[int]
    HUMAN_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CANCEL_FIELD_NUMBER: _ClassVar[int]
    client_frame_id: str
    start: RunAttachStart
    stdin: AttachStdin
    stdin_eof: AttachStdinEOF
    resize: AttachResize
    signal: AttachSignal
    human_message: AttachHumanMessage
    cancel: AttachCancel
    def __init__(self, client_frame_id: _Optional[str] = ..., start: _Optional[_Union[RunAttachStart, _Mapping]] = ..., stdin: _Optional[_Union[AttachStdin, _Mapping]] = ..., stdin_eof: _Optional[_Union[AttachStdinEOF, _Mapping]] = ..., resize: _Optional[_Union[AttachResize, _Mapping]] = ..., signal: _Optional[_Union[AttachSignal, _Mapping]] = ..., human_message: _Optional[_Union[AttachHumanMessage, _Mapping]] = ..., cancel: _Optional[_Union[AttachCancel, _Mapping]] = ...) -> None: ...

class RunAttachResponse(_message.Message):
    __slots__ = ("server_frame_id", "created_at", "started", "output", "agent_event", "agent_turn_completed", "result", "error")
    SERVER_FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    STARTED_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    AGENT_EVENT_FIELD_NUMBER: _ClassVar[int]
    AGENT_TURN_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    server_frame_id: str
    created_at: str
    started: AttachStarted
    output: AttachOutput
    agent_event: AttachAgentEvent
    agent_turn_completed: AttachAgentTurnCompleted
    result: AttachResult
    error: AttachError
    def __init__(self, server_frame_id: _Optional[str] = ..., created_at: _Optional[str] = ..., started: _Optional[_Union[AttachStarted, _Mapping]] = ..., output: _Optional[_Union[AttachOutput, _Mapping]] = ..., agent_event: _Optional[_Union[AttachAgentEvent, _Mapping]] = ..., agent_turn_completed: _Optional[_Union[AttachAgentTurnCompleted, _Mapping]] = ..., result: _Optional[_Union[AttachResult, _Mapping]] = ..., error: _Optional[_Union[AttachError, _Mapping]] = ...) -> None: ...

class RunAttachStart(_message.Message):
    __slots__ = ("request", "mode", "attach_stdin", "tty", "terminal_size")
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    ATTACH_STDIN_FIELD_NUMBER: _ClassVar[int]
    TTY_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    request: RunAgentRequest
    mode: AttachRunMode
    attach_stdin: bool
    tty: bool
    terminal_size: AttachTerminalSize
    def __init__(self, request: _Optional[_Union[RunAgentRequest, _Mapping]] = ..., mode: _Optional[_Union[AttachRunMode, str]] = ..., attach_stdin: _Optional[bool] = ..., tty: _Optional[bool] = ..., terminal_size: _Optional[_Union[AttachTerminalSize, _Mapping]] = ...) -> None: ...

class TranscriptEvent(_message.Message):
    __slots__ = ("stream", "text", "name", "payload_json", "created_at")
    STREAM_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_JSON_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    stream: StdioStream
    text: str
    name: str
    payload_json: str
    created_at: str
    def __init__(self, stream: _Optional[_Union[StdioStream, str]] = ..., text: _Optional[str] = ..., name: _Optional[str] = ..., payload_json: _Optional[str] = ..., created_at: _Optional[str] = ...) -> None: ...

class GetRunRequest(_message.Message):
    __slots__ = ("run_id", "project_id")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    project_id: str
    def __init__(self, run_id: _Optional[str] = ..., project_id: _Optional[str] = ...) -> None: ...

class GetRunResponse(_message.Message):
    __slots__ = ("run",)
    RUN_FIELD_NUMBER: _ClassVar[int]
    run: RunDetail
    def __init__(self, run: _Optional[_Union[RunDetail, _Mapping]] = ...) -> None: ...

class ListRunsRequest(_message.Message):
    __slots__ = ("project_id", "agent_name", "scheduler_id", "status", "source", "started_from", "started_to", "offset", "limit", "sandbox_id")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    SCHEDULER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    STARTED_FROM_FIELD_NUMBER: _ClassVar[int]
    STARTED_TO_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    agent_name: str
    scheduler_id: str
    status: RunStatus
    source: RunSource
    started_from: str
    started_to: str
    offset: int
    limit: int
    sandbox_id: str
    def __init__(self, project_id: _Optional[str] = ..., agent_name: _Optional[str] = ..., scheduler_id: _Optional[str] = ..., status: _Optional[_Union[RunStatus, str]] = ..., source: _Optional[_Union[RunSource, str]] = ..., started_from: _Optional[str] = ..., started_to: _Optional[str] = ..., offset: _Optional[int] = ..., limit: _Optional[int] = ..., sandbox_id: _Optional[str] = ...) -> None: ...

class ListRunsResponse(_message.Message):
    __slots__ = ("runs",)
    RUNS_FIELD_NUMBER: _ClassVar[int]
    runs: _containers.RepeatedCompositeFieldContainer[RunSummary]
    def __init__(self, runs: _Optional[_Iterable[_Union[RunSummary, _Mapping]]] = ...) -> None: ...

class FollowRunLogsRequest(_message.Message):
    __slots__ = ("project_id", "run_id", "tail_lines", "start_offset", "follow")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    TAIL_LINES_FIELD_NUMBER: _ClassVar[int]
    START_OFFSET_FIELD_NUMBER: _ClassVar[int]
    FOLLOW_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    run_id: str
    tail_lines: int
    start_offset: int
    follow: bool
    def __init__(self, project_id: _Optional[str] = ..., run_id: _Optional[str] = ..., tail_lines: _Optional[int] = ..., start_offset: _Optional[int] = ..., follow: _Optional[bool] = ...) -> None: ...

class RunLogChunk(_message.Message):
    __slots__ = ("data", "offset", "is_final", "run_status", "created_at")
    DATA_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    IS_FINAL_FIELD_NUMBER: _ClassVar[int]
    RUN_STATUS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    data: str
    offset: int
    is_final: bool
    run_status: RunStatus
    created_at: str
    def __init__(self, data: _Optional[str] = ..., offset: _Optional[int] = ..., is_final: _Optional[bool] = ..., run_status: _Optional[_Union[RunStatus, str]] = ..., created_at: _Optional[str] = ...) -> None: ...

class StopRunRequest(_message.Message):
    __slots__ = ("run_id", "reason")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    reason: str
    def __init__(self, run_id: _Optional[str] = ..., reason: _Optional[str] = ...) -> None: ...

class StopRunResponse(_message.Message):
    __slots__ = ("run", "stop_requested")
    RUN_FIELD_NUMBER: _ClassVar[int]
    STOP_REQUESTED_FIELD_NUMBER: _ClassVar[int]
    run: RunDetail
    stop_requested: bool
    def __init__(self, run: _Optional[_Union[RunDetail, _Mapping]] = ..., stop_requested: _Optional[bool] = ...) -> None: ...

class RemoveSandboxRequest(_message.Message):
    __slots__ = ("sandbox_id", "force")
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    sandbox_id: str
    force: bool
    def __init__(self, sandbox_id: _Optional[str] = ..., force: _Optional[bool] = ...) -> None: ...

class RemoveSandboxResponse(_message.Message):
    __slots__ = ("sandbox_id", "stopped", "removed")
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    STOPPED_FIELD_NUMBER: _ClassVar[int]
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    sandbox_id: str
    stopped: bool
    removed: bool
    def __init__(self, sandbox_id: _Optional[str] = ..., stopped: _Optional[bool] = ..., removed: _Optional[bool] = ...) -> None: ...

class GetSandboxStatsRequest(_message.Message):
    __slots__ = ("sandbox_id",)
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    sandbox_id: str
    def __init__(self, sandbox_id: _Optional[str] = ...) -> None: ...

class GetSandboxStatsResponse(_message.Message):
    __slots__ = ("stats",)
    STATS_FIELD_NUMBER: _ClassVar[int]
    stats: SandboxStats
    def __init__(self, stats: _Optional[_Union[SandboxStats, _Mapping]] = ...) -> None: ...

class MetricValue(_message.Message):
    __slots__ = ("value", "unit", "status", "message")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    value: float
    unit: str
    status: MetricStatus
    message: str
    def __init__(self, value: _Optional[float] = ..., unit: _Optional[str] = ..., status: _Optional[_Union[MetricStatus, str]] = ..., message: _Optional[str] = ...) -> None: ...

class SandboxStats(_message.Message):
    __slots__ = ("sandbox_id", "driver", "sampled_at", "cpu_percent", "memory_usage_bytes", "memory_limit_bytes", "memory_percent", "network_rx_bytes", "network_tx_bytes", "block_read_bytes", "block_write_bytes", "uptime_seconds")
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    SAMPLED_AT_FIELD_NUMBER: _ClassVar[int]
    CPU_PERCENT_FIELD_NUMBER: _ClassVar[int]
    MEMORY_USAGE_BYTES_FIELD_NUMBER: _ClassVar[int]
    MEMORY_LIMIT_BYTES_FIELD_NUMBER: _ClassVar[int]
    MEMORY_PERCENT_FIELD_NUMBER: _ClassVar[int]
    NETWORK_RX_BYTES_FIELD_NUMBER: _ClassVar[int]
    NETWORK_TX_BYTES_FIELD_NUMBER: _ClassVar[int]
    BLOCK_READ_BYTES_FIELD_NUMBER: _ClassVar[int]
    BLOCK_WRITE_BYTES_FIELD_NUMBER: _ClassVar[int]
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    sandbox_id: str
    driver: str
    sampled_at: str
    cpu_percent: MetricValue
    memory_usage_bytes: MetricValue
    memory_limit_bytes: MetricValue
    memory_percent: MetricValue
    network_rx_bytes: MetricValue
    network_tx_bytes: MetricValue
    block_read_bytes: MetricValue
    block_write_bytes: MetricValue
    uptime_seconds: MetricValue
    def __init__(self, sandbox_id: _Optional[str] = ..., driver: _Optional[str] = ..., sampled_at: _Optional[str] = ..., cpu_percent: _Optional[_Union[MetricValue, _Mapping]] = ..., memory_usage_bytes: _Optional[_Union[MetricValue, _Mapping]] = ..., memory_limit_bytes: _Optional[_Union[MetricValue, _Mapping]] = ..., memory_percent: _Optional[_Union[MetricValue, _Mapping]] = ..., network_rx_bytes: _Optional[_Union[MetricValue, _Mapping]] = ..., network_tx_bytes: _Optional[_Union[MetricValue, _Mapping]] = ..., block_read_bytes: _Optional[_Union[MetricValue, _Mapping]] = ..., block_write_bytes: _Optional[_Union[MetricValue, _Mapping]] = ..., uptime_seconds: _Optional[_Union[MetricValue, _Mapping]] = ...) -> None: ...

class RunSummary(_message.Message):
    __slots__ = ("run_id", "project_id", "project_name", "project_revision", "agent_id", "agent_name", "source", "scheduler_id", "trigger_id", "status", "exit_code", "error", "started_at", "completed_at", "duration_ms", "created_at", "updated_at", "warnings", "sandbox_id", "run_short_id", "sandbox_short_id")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PROJECT_REVISION_FIELD_NUMBER: _ClassVar[int]
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    SCHEDULER_ID_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_SHORT_ID_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_SHORT_ID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    project_id: str
    project_name: str
    project_revision: int
    agent_id: str
    agent_name: str
    source: RunSource
    scheduler_id: str
    trigger_id: str
    status: RunStatus
    exit_code: int
    error: str
    started_at: str
    completed_at: str
    duration_ms: int
    created_at: str
    updated_at: str
    warnings: _containers.RepeatedScalarFieldContainer[str]
    sandbox_id: str
    run_short_id: str
    sandbox_short_id: str
    def __init__(self, run_id: _Optional[str] = ..., project_id: _Optional[str] = ..., project_name: _Optional[str] = ..., project_revision: _Optional[int] = ..., agent_id: _Optional[str] = ..., agent_name: _Optional[str] = ..., source: _Optional[_Union[RunSource, str]] = ..., scheduler_id: _Optional[str] = ..., trigger_id: _Optional[str] = ..., status: _Optional[_Union[RunStatus, str]] = ..., exit_code: _Optional[int] = ..., error: _Optional[str] = ..., started_at: _Optional[str] = ..., completed_at: _Optional[str] = ..., duration_ms: _Optional[int] = ..., created_at: _Optional[str] = ..., updated_at: _Optional[str] = ..., warnings: _Optional[_Iterable[str]] = ..., sandbox_id: _Optional[str] = ..., run_short_id: _Optional[str] = ..., sandbox_short_id: _Optional[str] = ...) -> None: ...

class RunDetail(_message.Message):
    __slots__ = ("summary", "prompt", "output", "result_json", "logs_path", "artifacts_dir", "cleanup_error", "driver", "image_ref", "warnings")
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    RESULT_JSON_FIELD_NUMBER: _ClassVar[int]
    LOGS_PATH_FIELD_NUMBER: _ClassVar[int]
    ARTIFACTS_DIR_FIELD_NUMBER: _ClassVar[int]
    CLEANUP_ERROR_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    IMAGE_REF_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    summary: RunSummary
    prompt: str
    output: str
    result_json: str
    logs_path: str
    artifacts_dir: str
    cleanup_error: str
    driver: str
    image_ref: str
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, summary: _Optional[_Union[RunSummary, _Mapping]] = ..., prompt: _Optional[str] = ..., output: _Optional[str] = ..., result_json: _Optional[str] = ..., logs_path: _Optional[str] = ..., artifacts_dir: _Optional[str] = ..., cleanup_error: _Optional[str] = ..., driver: _Optional[str] = ..., image_ref: _Optional[str] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class ExecRequest(_message.Message):
    __slots__ = ("sandbox_id", "run_id", "selector", "command", "cwd", "env", "timeout_ms", "max_output_bytes")
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    SELECTOR_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    CWD_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    MAX_OUTPUT_BYTES_FIELD_NUMBER: _ClassVar[int]
    sandbox_id: str
    run_id: str
    selector: ExecSandboxSelector
    command: ExecCommand
    cwd: str
    env: _containers.RepeatedCompositeFieldContainer[EnvVarSpec]
    timeout_ms: int
    max_output_bytes: int
    def __init__(self, sandbox_id: _Optional[str] = ..., run_id: _Optional[str] = ..., selector: _Optional[_Union[ExecSandboxSelector, _Mapping]] = ..., command: _Optional[_Union[ExecCommand, _Mapping]] = ..., cwd: _Optional[str] = ..., env: _Optional[_Iterable[_Union[EnvVarSpec, _Mapping]]] = ..., timeout_ms: _Optional[int] = ..., max_output_bytes: _Optional[int] = ...) -> None: ...

class ExecSandboxSelector(_message.Message):
    __slots__ = ("project_id", "project_name", "agent_name")
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    project_id: str
    project_name: str
    agent_name: str
    def __init__(self, project_id: _Optional[str] = ..., project_name: _Optional[str] = ..., agent_name: _Optional[str] = ...) -> None: ...

class ExecCommand(_message.Message):
    __slots__ = ("command", "args")
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    command: str
    args: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, command: _Optional[str] = ..., args: _Optional[_Iterable[str]] = ...) -> None: ...

class ExecResponse(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: ExecResult
    def __init__(self, result: _Optional[_Union[ExecResult, _Mapping]] = ...) -> None: ...

class ExecStreamResponse(_message.Message):
    __slots__ = ("event_type", "exec_id", "sandbox_id", "run_id", "chunk", "stream", "result", "transcript")
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    EXEC_ID_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    STREAM_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    TRANSCRIPT_FIELD_NUMBER: _ClassVar[int]
    event_type: ExecStreamEventType
    exec_id: str
    sandbox_id: str
    run_id: str
    chunk: str
    stream: StdioStream
    result: ExecResult
    transcript: TranscriptEvent
    def __init__(self, event_type: _Optional[_Union[ExecStreamEventType, str]] = ..., exec_id: _Optional[str] = ..., sandbox_id: _Optional[str] = ..., run_id: _Optional[str] = ..., chunk: _Optional[str] = ..., stream: _Optional[_Union[StdioStream, str]] = ..., result: _Optional[_Union[ExecResult, _Mapping]] = ..., transcript: _Optional[_Union[TranscriptEvent, _Mapping]] = ...) -> None: ...

class ExecAttachRequest(_message.Message):
    __slots__ = ("client_frame_id", "start", "stdin", "stdin_eof", "resize", "signal", "cancel", "human_message")
    CLIENT_FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    STDIN_FIELD_NUMBER: _ClassVar[int]
    STDIN_EOF_FIELD_NUMBER: _ClassVar[int]
    RESIZE_FIELD_NUMBER: _ClassVar[int]
    SIGNAL_FIELD_NUMBER: _ClassVar[int]
    CANCEL_FIELD_NUMBER: _ClassVar[int]
    HUMAN_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    client_frame_id: str
    start: ExecAttachStart
    stdin: AttachStdin
    stdin_eof: AttachStdinEOF
    resize: AttachResize
    signal: AttachSignal
    cancel: AttachCancel
    human_message: AttachHumanMessage
    def __init__(self, client_frame_id: _Optional[str] = ..., start: _Optional[_Union[ExecAttachStart, _Mapping]] = ..., stdin: _Optional[_Union[AttachStdin, _Mapping]] = ..., stdin_eof: _Optional[_Union[AttachStdinEOF, _Mapping]] = ..., resize: _Optional[_Union[AttachResize, _Mapping]] = ..., signal: _Optional[_Union[AttachSignal, _Mapping]] = ..., cancel: _Optional[_Union[AttachCancel, _Mapping]] = ..., human_message: _Optional[_Union[AttachHumanMessage, _Mapping]] = ...) -> None: ...

class ExecAttachResponse(_message.Message):
    __slots__ = ("server_frame_id", "created_at", "started", "output", "result", "error", "agent_event", "agent_turn_completed")
    SERVER_FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    STARTED_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    AGENT_EVENT_FIELD_NUMBER: _ClassVar[int]
    AGENT_TURN_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    server_frame_id: str
    created_at: str
    started: AttachStarted
    output: AttachOutput
    result: AttachResult
    error: AttachError
    agent_event: AttachAgentEvent
    agent_turn_completed: AttachAgentTurnCompleted
    def __init__(self, server_frame_id: _Optional[str] = ..., created_at: _Optional[str] = ..., started: _Optional[_Union[AttachStarted, _Mapping]] = ..., output: _Optional[_Union[AttachOutput, _Mapping]] = ..., result: _Optional[_Union[AttachResult, _Mapping]] = ..., error: _Optional[_Union[AttachError, _Mapping]] = ..., agent_event: _Optional[_Union[AttachAgentEvent, _Mapping]] = ..., agent_turn_completed: _Optional[_Union[AttachAgentTurnCompleted, _Mapping]] = ...) -> None: ...

class ExecAttachStart(_message.Message):
    __slots__ = ("request", "attach_stdin", "tty", "terminal_size", "mode", "prompt")
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    ATTACH_STDIN_FIELD_NUMBER: _ClassVar[int]
    TTY_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    request: ExecRequest
    attach_stdin: bool
    tty: bool
    terminal_size: AttachTerminalSize
    mode: AttachRunMode
    prompt: str
    def __init__(self, request: _Optional[_Union[ExecRequest, _Mapping]] = ..., attach_stdin: _Optional[bool] = ..., tty: _Optional[bool] = ..., terminal_size: _Optional[_Union[AttachTerminalSize, _Mapping]] = ..., mode: _Optional[_Union[AttachRunMode, str]] = ..., prompt: _Optional[str] = ...) -> None: ...

class AttachTerminalSize(_message.Message):
    __slots__ = ("rows", "cols")
    ROWS_FIELD_NUMBER: _ClassVar[int]
    COLS_FIELD_NUMBER: _ClassVar[int]
    rows: int
    cols: int
    def __init__(self, rows: _Optional[int] = ..., cols: _Optional[int] = ...) -> None: ...

class AttachStdin(_message.Message):
    __slots__ = ("data",)
    DATA_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    def __init__(self, data: _Optional[bytes] = ...) -> None: ...

class AttachStdinEOF(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AttachResize(_message.Message):
    __slots__ = ("terminal_size",)
    TERMINAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    terminal_size: AttachTerminalSize
    def __init__(self, terminal_size: _Optional[_Union[AttachTerminalSize, _Mapping]] = ...) -> None: ...

class AttachSignal(_message.Message):
    __slots__ = ("signal",)
    SIGNAL_FIELD_NUMBER: _ClassVar[int]
    signal: str
    def __init__(self, signal: _Optional[str] = ...) -> None: ...

class AttachHumanMessage(_message.Message):
    __slots__ = ("text", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TEXT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    text: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, text: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class AttachCancel(_message.Message):
    __slots__ = ("reason",)
    REASON_FIELD_NUMBER: _ClassVar[int]
    reason: str
    def __init__(self, reason: _Optional[str] = ...) -> None: ...

class AttachStarted(_message.Message):
    __slots__ = ("operation_id", "exec_id", "run_id", "sandbox_id", "run", "warnings")
    OPERATION_ID_FIELD_NUMBER: _ClassVar[int]
    EXEC_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    operation_id: str
    exec_id: str
    run_id: str
    sandbox_id: str
    run: RunSummary
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, operation_id: _Optional[str] = ..., exec_id: _Optional[str] = ..., run_id: _Optional[str] = ..., sandbox_id: _Optional[str] = ..., run: _Optional[_Union[RunSummary, _Mapping]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class AttachOutput(_message.Message):
    __slots__ = ("data", "stream", "tty", "transcript")
    DATA_FIELD_NUMBER: _ClassVar[int]
    STREAM_FIELD_NUMBER: _ClassVar[int]
    TTY_FIELD_NUMBER: _ClassVar[int]
    TRANSCRIPT_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    stream: StdioStream
    tty: bool
    transcript: TranscriptEvent
    def __init__(self, data: _Optional[bytes] = ..., stream: _Optional[_Union[StdioStream, str]] = ..., tty: _Optional[bool] = ..., transcript: _Optional[_Union[TranscriptEvent, _Mapping]] = ...) -> None: ...

class AttachAgentEvent(_message.Message):
    __slots__ = ("name", "text", "payload_json", "created_at")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_JSON_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    name: str
    text: str
    payload_json: str
    created_at: str
    def __init__(self, name: _Optional[str] = ..., text: _Optional[str] = ..., payload_json: _Optional[str] = ..., created_at: _Optional[str] = ...) -> None: ...

class AttachAgentTurnCompleted(_message.Message):
    __slots__ = ("run_id", "result_json", "warnings")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    RESULT_JSON_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    result_json: str
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, run_id: _Optional[str] = ..., result_json: _Optional[str] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class AttachResult(_message.Message):
    __slots__ = ("exit_code", "success", "exec_result", "run", "output", "result_json", "error")
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    EXEC_RESULT_FIELD_NUMBER: _ClassVar[int]
    RUN_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    RESULT_JSON_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    exit_code: int
    success: bool
    exec_result: ExecResult
    run: RunSummary
    output: str
    result_json: str
    error: str
    def __init__(self, exit_code: _Optional[int] = ..., success: _Optional[bool] = ..., exec_result: _Optional[_Union[ExecResult, _Mapping]] = ..., run: _Optional[_Union[RunSummary, _Mapping]] = ..., output: _Optional[str] = ..., result_json: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class AttachError(_message.Message):
    __slots__ = ("code", "message", "terminal", "details")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    terminal: bool
    details: _containers.ScalarMap[str, str]
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ..., terminal: _Optional[bool] = ..., details: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ExecResult(_message.Message):
    __slots__ = ("exec_id", "sandbox_id", "run_id", "command", "cwd", "exit_code", "success", "stdout", "stderr", "output", "stdout_truncated", "stderr_truncated", "output_truncated", "error")
    EXEC_ID_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    CWD_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    STDOUT_FIELD_NUMBER: _ClassVar[int]
    STDERR_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    STDOUT_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    STDERR_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    exec_id: str
    sandbox_id: str
    run_id: str
    command: ExecCommand
    cwd: str
    exit_code: int
    success: bool
    stdout: str
    stderr: str
    output: str
    stdout_truncated: bool
    stderr_truncated: bool
    output_truncated: bool
    error: str
    def __init__(self, exec_id: _Optional[str] = ..., sandbox_id: _Optional[str] = ..., run_id: _Optional[str] = ..., command: _Optional[_Union[ExecCommand, _Mapping]] = ..., cwd: _Optional[str] = ..., exit_code: _Optional[int] = ..., success: _Optional[bool] = ..., stdout: _Optional[str] = ..., stderr: _Optional[str] = ..., output: _Optional[str] = ..., stdout_truncated: _Optional[bool] = ..., stderr_truncated: _Optional[bool] = ..., output_truncated: _Optional[bool] = ..., error: _Optional[str] = ...) -> None: ...

class ListImagesRequest(_message.Message):
    __slots__ = ("store", "query", "all", "include_cache_status", "offset", "limit")
    STORE_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    ALL_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_CACHE_STATUS_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    store: ImageStoreKind
    query: str
    all: bool
    include_cache_status: bool
    offset: int
    limit: int
    def __init__(self, store: _Optional[_Union[ImageStoreKind, str]] = ..., query: _Optional[str] = ..., all: _Optional[bool] = ..., include_cache_status: _Optional[bool] = ..., offset: _Optional[int] = ..., limit: _Optional[int] = ...) -> None: ...

class ListImagesResponse(_message.Message):
    __slots__ = ("images", "total_count", "has_more", "next_offset", "store_status")
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    HAS_MORE_FIELD_NUMBER: _ClassVar[int]
    NEXT_OFFSET_FIELD_NUMBER: _ClassVar[int]
    STORE_STATUS_FIELD_NUMBER: _ClassVar[int]
    images: _containers.RepeatedCompositeFieldContainer[Image]
    total_count: int
    has_more: bool
    next_offset: int
    store_status: ImageStoreStatus
    def __init__(self, images: _Optional[_Iterable[_Union[Image, _Mapping]]] = ..., total_count: _Optional[int] = ..., has_more: _Optional[bool] = ..., next_offset: _Optional[int] = ..., store_status: _Optional[_Union[ImageStoreStatus, _Mapping]] = ...) -> None: ...

class PullImageRequest(_message.Message):
    __slots__ = ("image_ref", "store", "platform")
    IMAGE_REF_FIELD_NUMBER: _ClassVar[int]
    STORE_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    image_ref: str
    store: ImageStoreKind
    platform: ImagePlatform
    def __init__(self, image_ref: _Optional[str] = ..., store: _Optional[_Union[ImageStoreKind, str]] = ..., platform: _Optional[_Union[ImagePlatform, _Mapping]] = ...) -> None: ...

class PullImageResponse(_message.Message):
    __slots__ = ("image", "status", "resolved_ref", "progress", "warnings")
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_REF_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    image: Image
    status: ImageOperationStatus
    resolved_ref: str
    progress: _containers.RepeatedCompositeFieldContainer[ImagePullProgress]
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, image: _Optional[_Union[Image, _Mapping]] = ..., status: _Optional[_Union[ImageOperationStatus, str]] = ..., resolved_ref: _Optional[str] = ..., progress: _Optional[_Iterable[_Union[ImagePullProgress, _Mapping]]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class InspectImageRequest(_message.Message):
    __slots__ = ("image_ref", "store", "include_cache_status")
    IMAGE_REF_FIELD_NUMBER: _ClassVar[int]
    STORE_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_CACHE_STATUS_FIELD_NUMBER: _ClassVar[int]
    image_ref: str
    store: ImageStoreKind
    include_cache_status: bool
    def __init__(self, image_ref: _Optional[str] = ..., store: _Optional[_Union[ImageStoreKind, str]] = ..., include_cache_status: _Optional[bool] = ...) -> None: ...

class InspectImageResponse(_message.Message):
    __slots__ = ("image", "store_status")
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    STORE_STATUS_FIELD_NUMBER: _ClassVar[int]
    image: Image
    store_status: ImageStoreStatus
    def __init__(self, image: _Optional[_Union[Image, _Mapping]] = ..., store_status: _Optional[_Union[ImageStoreStatus, _Mapping]] = ...) -> None: ...

class RemoveImageRequest(_message.Message):
    __slots__ = ("image_ref", "store", "force", "prune_children")
    IMAGE_REF_FIELD_NUMBER: _ClassVar[int]
    STORE_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    PRUNE_CHILDREN_FIELD_NUMBER: _ClassVar[int]
    image_ref: str
    store: ImageStoreKind
    force: bool
    prune_children: bool
    def __init__(self, image_ref: _Optional[str] = ..., store: _Optional[_Union[ImageStoreKind, str]] = ..., force: _Optional[bool] = ..., prune_children: _Optional[bool] = ...) -> None: ...

class RemoveImageResponse(_message.Message):
    __slots__ = ("image_ref", "untagged_refs", "deleted_ids", "warnings")
    IMAGE_REF_FIELD_NUMBER: _ClassVar[int]
    UNTAGGED_REFS_FIELD_NUMBER: _ClassVar[int]
    DELETED_IDS_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    image_ref: str
    untagged_refs: _containers.RepeatedScalarFieldContainer[str]
    deleted_ids: _containers.RepeatedScalarFieldContainer[str]
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, image_ref: _Optional[str] = ..., untagged_refs: _Optional[_Iterable[str]] = ..., deleted_ids: _Optional[_Iterable[str]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class BuildImageRequest(_message.Message):
    __slots__ = ("context_dir", "dockerfile", "tags", "build_args", "target", "store", "platform", "no_cache", "pull")
    class BuildArgsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CONTEXT_DIR_FIELD_NUMBER: _ClassVar[int]
    DOCKERFILE_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    BUILD_ARGS_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    STORE_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    NO_CACHE_FIELD_NUMBER: _ClassVar[int]
    PULL_FIELD_NUMBER: _ClassVar[int]
    context_dir: str
    dockerfile: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    build_args: _containers.ScalarMap[str, str]
    target: str
    store: ImageStoreKind
    platform: ImagePlatform
    no_cache: bool
    pull: bool
    def __init__(self, context_dir: _Optional[str] = ..., dockerfile: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ..., build_args: _Optional[_Mapping[str, str]] = ..., target: _Optional[str] = ..., store: _Optional[_Union[ImageStoreKind, str]] = ..., platform: _Optional[_Union[ImagePlatform, _Mapping]] = ..., no_cache: _Optional[bool] = ..., pull: _Optional[bool] = ...) -> None: ...

class BuildImageEvent(_message.Message):
    __slots__ = ("status", "stage", "message", "image", "image_ref", "resolved_ref", "warnings")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    STAGE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    IMAGE_REF_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_REF_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    status: ImageOperationStatus
    stage: str
    message: str
    image: Image
    image_ref: str
    resolved_ref: str
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, status: _Optional[_Union[ImageOperationStatus, str]] = ..., stage: _Optional[str] = ..., message: _Optional[str] = ..., image: _Optional[_Union[Image, _Mapping]] = ..., image_ref: _Optional[str] = ..., resolved_ref: _Optional[str] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class CacheFilter(_message.Message):
    __slots__ = ("driver", "domain", "type", "status", "older_than_seconds", "cache_id")
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    OLDER_THAN_SECONDS_FIELD_NUMBER: _ClassVar[int]
    CACHE_ID_FIELD_NUMBER: _ClassVar[int]
    driver: str
    domain: CacheDomain
    type: str
    status: CacheStatus
    older_than_seconds: int
    cache_id: str
    def __init__(self, driver: _Optional[str] = ..., domain: _Optional[_Union[CacheDomain, str]] = ..., type: _Optional[str] = ..., status: _Optional[_Union[CacheStatus, str]] = ..., older_than_seconds: _Optional[int] = ..., cache_id: _Optional[str] = ...) -> None: ...

class ListCachesRequest(_message.Message):
    __slots__ = ("filter",)
    FILTER_FIELD_NUMBER: _ClassVar[int]
    filter: CacheFilter
    def __init__(self, filter: _Optional[_Union[CacheFilter, _Mapping]] = ...) -> None: ...

class ListCachesResponse(_message.Message):
    __slots__ = ("caches", "warnings")
    CACHES_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    caches: _containers.RepeatedCompositeFieldContainer[CacheItem]
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, caches: _Optional[_Iterable[_Union[CacheItem, _Mapping]]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class InspectCacheRequest(_message.Message):
    __slots__ = ("cache_id",)
    CACHE_ID_FIELD_NUMBER: _ClassVar[int]
    cache_id: str
    def __init__(self, cache_id: _Optional[str] = ...) -> None: ...

class InspectCacheResponse(_message.Message):
    __slots__ = ("cache", "warnings")
    CACHE_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    cache: CacheItem
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, cache: _Optional[_Union[CacheItem, _Mapping]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class PruneCachesRequest(_message.Message):
    __slots__ = ("filter", "include_referenced", "force")
    FILTER_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_REFERENCED_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    filter: CacheFilter
    include_referenced: bool
    force: bool
    def __init__(self, filter: _Optional[_Union[CacheFilter, _Mapping]] = ..., include_referenced: _Optional[bool] = ..., force: _Optional[bool] = ...) -> None: ...

class PruneCachesResponse(_message.Message):
    __slots__ = ("dry_run", "matched", "removed", "skipped", "warnings")
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    MATCHED_FIELD_NUMBER: _ClassVar[int]
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    SKIPPED_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    dry_run: bool
    matched: _containers.RepeatedCompositeFieldContainer[CacheItem]
    removed: _containers.RepeatedScalarFieldContainer[str]
    skipped: _containers.RepeatedCompositeFieldContainer[CacheItem]
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, dry_run: _Optional[bool] = ..., matched: _Optional[_Iterable[_Union[CacheItem, _Mapping]]] = ..., removed: _Optional[_Iterable[str]] = ..., skipped: _Optional[_Iterable[_Union[CacheItem, _Mapping]]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class RemoveCacheRequest(_message.Message):
    __slots__ = ("cache_id", "force")
    CACHE_ID_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    cache_id: str
    force: bool
    def __init__(self, cache_id: _Optional[str] = ..., force: _Optional[bool] = ...) -> None: ...

class RemoveCacheResponse(_message.Message):
    __slots__ = ("dry_run", "matched", "removed", "skipped", "warnings")
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    MATCHED_FIELD_NUMBER: _ClassVar[int]
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    SKIPPED_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    dry_run: bool
    matched: _containers.RepeatedCompositeFieldContainer[CacheItem]
    removed: _containers.RepeatedScalarFieldContainer[str]
    skipped: _containers.RepeatedCompositeFieldContainer[CacheItem]
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, dry_run: _Optional[bool] = ..., matched: _Optional[_Iterable[_Union[CacheItem, _Mapping]]] = ..., removed: _Optional[_Iterable[str]] = ..., skipped: _Optional[_Iterable[_Union[CacheItem, _Mapping]]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class CacheItem(_message.Message):
    __slots__ = ("cache_id", "domain", "driver", "kind", "path", "size_bytes", "image_id", "image_ref", "resolved_ref", "sandbox_id", "status", "removable", "blocked_reasons", "last_used_at", "last_used_source", "references", "warnings")
    CACHE_ID_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    IMAGE_ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_REF_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_REF_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    REMOVABLE_FIELD_NUMBER: _ClassVar[int]
    BLOCKED_REASONS_FIELD_NUMBER: _ClassVar[int]
    LAST_USED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_USED_SOURCE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    cache_id: str
    domain: CacheDomain
    driver: str
    kind: str
    path: str
    size_bytes: int
    image_id: str
    image_ref: str
    resolved_ref: str
    sandbox_id: str
    status: CacheStatus
    removable: bool
    blocked_reasons: _containers.RepeatedScalarFieldContainer[str]
    last_used_at: str
    last_used_source: str
    references: _containers.RepeatedCompositeFieldContainer[CacheReference]
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, cache_id: _Optional[str] = ..., domain: _Optional[_Union[CacheDomain, str]] = ..., driver: _Optional[str] = ..., kind: _Optional[str] = ..., path: _Optional[str] = ..., size_bytes: _Optional[int] = ..., image_id: _Optional[str] = ..., image_ref: _Optional[str] = ..., resolved_ref: _Optional[str] = ..., sandbox_id: _Optional[str] = ..., status: _Optional[_Union[CacheStatus, str]] = ..., removable: _Optional[bool] = ..., blocked_reasons: _Optional[_Iterable[str]] = ..., last_used_at: _Optional[str] = ..., last_used_source: _Optional[str] = ..., references: _Optional[_Iterable[_Union[CacheReference, _Mapping]]] = ..., warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class CacheReference(_message.Message):
    __slots__ = ("type", "id", "name", "path", "status", "description")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    type: str
    id: str
    name: str
    path: str
    status: str
    description: str
    def __init__(self, type: _Optional[str] = ..., id: _Optional[str] = ..., name: _Optional[str] = ..., path: _Optional[str] = ..., status: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class ListVolumesRequest(_message.Message):
    __slots__ = ("query", "driver", "project_id")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    query: str
    driver: str
    project_id: str
    def __init__(self, query: _Optional[str] = ..., driver: _Optional[str] = ..., project_id: _Optional[str] = ...) -> None: ...

class ListVolumesResponse(_message.Message):
    __slots__ = ("volumes",)
    VOLUMES_FIELD_NUMBER: _ClassVar[int]
    volumes: _containers.RepeatedCompositeFieldContainer[Volume]
    def __init__(self, volumes: _Optional[_Iterable[_Union[Volume, _Mapping]]] = ...) -> None: ...

class CreateVolumeRequest(_message.Message):
    __slots__ = ("name", "driver", "labels", "options")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    name: str
    driver: str
    labels: _containers.ScalarMap[str, str]
    options: _containers.ScalarMap[str, str]
    def __init__(self, name: _Optional[str] = ..., driver: _Optional[str] = ..., labels: _Optional[_Mapping[str, str]] = ..., options: _Optional[_Mapping[str, str]] = ...) -> None: ...

class CreateVolumeResponse(_message.Message):
    __slots__ = ("volume", "created")
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    CREATED_FIELD_NUMBER: _ClassVar[int]
    volume: Volume
    created: bool
    def __init__(self, volume: _Optional[_Union[Volume, _Mapping]] = ..., created: _Optional[bool] = ...) -> None: ...

class InspectVolumeRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class InspectVolumeResponse(_message.Message):
    __slots__ = ("volume",)
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    volume: Volume
    def __init__(self, volume: _Optional[_Union[Volume, _Mapping]] = ...) -> None: ...

class RemoveVolumeRequest(_message.Message):
    __slots__ = ("name", "force")
    NAME_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    name: str
    force: bool
    def __init__(self, name: _Optional[str] = ..., force: _Optional[bool] = ...) -> None: ...

class RemoveVolumeResponse(_message.Message):
    __slots__ = ("name", "removed")
    NAME_FIELD_NUMBER: _ClassVar[int]
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    name: str
    removed: bool
    def __init__(self, name: _Optional[str] = ..., removed: _Optional[bool] = ...) -> None: ...

class PruneVolumesRequest(_message.Message):
    __slots__ = ("query", "driver", "project_id", "force")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    query: str
    driver: str
    project_id: str
    force: bool
    def __init__(self, query: _Optional[str] = ..., driver: _Optional[str] = ..., project_id: _Optional[str] = ..., force: _Optional[bool] = ...) -> None: ...

class PruneVolumesResponse(_message.Message):
    __slots__ = ("dry_run", "matched", "removed", "skipped")
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    MATCHED_FIELD_NUMBER: _ClassVar[int]
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    SKIPPED_FIELD_NUMBER: _ClassVar[int]
    dry_run: bool
    matched: _containers.RepeatedCompositeFieldContainer[Volume]
    removed: _containers.RepeatedCompositeFieldContainer[Volume]
    skipped: _containers.RepeatedCompositeFieldContainer[Volume]
    def __init__(self, dry_run: _Optional[bool] = ..., matched: _Optional[_Iterable[_Union[Volume, _Mapping]]] = ..., removed: _Optional[_Iterable[_Union[Volume, _Mapping]]] = ..., skipped: _Optional[_Iterable[_Union[Volume, _Mapping]]] = ...) -> None: ...

class Volume(_message.Message):
    __slots__ = ("name", "driver", "path", "labels", "options", "project_id", "created_at", "updated_at")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    name: str
    driver: str
    path: str
    labels: _containers.ScalarMap[str, str]
    options: _containers.ScalarMap[str, str]
    project_id: str
    created_at: str
    updated_at: str
    def __init__(self, name: _Optional[str] = ..., driver: _Optional[str] = ..., path: _Optional[str] = ..., labels: _Optional[_Mapping[str, str]] = ..., options: _Optional[_Mapping[str, str]] = ..., project_id: _Optional[str] = ..., created_at: _Optional[str] = ..., updated_at: _Optional[str] = ...) -> None: ...

class Image(_message.Message):
    __slots__ = ("image_id", "image_ref", "resolved_ref", "repo_tags", "repo_digests", "store", "availability_status", "platform", "size_bytes", "virtual_size_bytes", "created_at", "inspected_at", "dangling", "container_count", "docker", "oci", "labels")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    IMAGE_ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_REF_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_REF_FIELD_NUMBER: _ClassVar[int]
    REPO_TAGS_FIELD_NUMBER: _ClassVar[int]
    REPO_DIGESTS_FIELD_NUMBER: _ClassVar[int]
    STORE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_STATUS_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    VIRTUAL_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    INSPECTED_AT_FIELD_NUMBER: _ClassVar[int]
    DANGLING_FIELD_NUMBER: _ClassVar[int]
    CONTAINER_COUNT_FIELD_NUMBER: _ClassVar[int]
    DOCKER_FIELD_NUMBER: _ClassVar[int]
    OCI_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    image_id: str
    image_ref: str
    resolved_ref: str
    repo_tags: _containers.RepeatedScalarFieldContainer[str]
    repo_digests: _containers.RepeatedScalarFieldContainer[str]
    store: ImageStoreKind
    availability_status: ImageAvailabilityStatus
    platform: ImagePlatform
    size_bytes: int
    virtual_size_bytes: int
    created_at: str
    inspected_at: str
    dangling: bool
    container_count: int
    docker: DockerImageStatus
    oci: OCIImageStatus
    labels: _containers.ScalarMap[str, str]
    def __init__(self, image_id: _Optional[str] = ..., image_ref: _Optional[str] = ..., resolved_ref: _Optional[str] = ..., repo_tags: _Optional[_Iterable[str]] = ..., repo_digests: _Optional[_Iterable[str]] = ..., store: _Optional[_Union[ImageStoreKind, str]] = ..., availability_status: _Optional[_Union[ImageAvailabilityStatus, str]] = ..., platform: _Optional[_Union[ImagePlatform, _Mapping]] = ..., size_bytes: _Optional[int] = ..., virtual_size_bytes: _Optional[int] = ..., created_at: _Optional[str] = ..., inspected_at: _Optional[str] = ..., dangling: _Optional[bool] = ..., container_count: _Optional[int] = ..., docker: _Optional[_Union[DockerImageStatus, _Mapping]] = ..., oci: _Optional[_Union[OCIImageStatus, _Mapping]] = ..., labels: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ImagePlatform(_message.Message):
    __slots__ = ("os", "architecture", "variant", "os_version")
    OS_FIELD_NUMBER: _ClassVar[int]
    ARCHITECTURE_FIELD_NUMBER: _ClassVar[int]
    VARIANT_FIELD_NUMBER: _ClassVar[int]
    OS_VERSION_FIELD_NUMBER: _ClassVar[int]
    os: str
    architecture: str
    variant: str
    os_version: str
    def __init__(self, os: _Optional[str] = ..., architecture: _Optional[str] = ..., variant: _Optional[str] = ..., os_version: _Optional[str] = ...) -> None: ...

class ImageStoreStatus(_message.Message):
    __slots__ = ("store", "available", "endpoint", "error")
    STORE_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    store: ImageStoreKind
    available: bool
    endpoint: str
    error: str
    def __init__(self, store: _Optional[_Union[ImageStoreKind, str]] = ..., available: _Optional[bool] = ..., endpoint: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class DockerImageStatus(_message.Message):
    __slots__ = ("local", "parent_id", "shared_size_bytes")
    LOCAL_FIELD_NUMBER: _ClassVar[int]
    PARENT_ID_FIELD_NUMBER: _ClassVar[int]
    SHARED_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    local: bool
    parent_id: str
    shared_size_bytes: int
    def __init__(self, local: _Optional[bool] = ..., parent_id: _Optional[str] = ..., shared_size_bytes: _Optional[int] = ...) -> None: ...

class OCIImageStatus(_message.Message):
    __slots__ = ("layout_cached", "rootfs_cached", "cache_key", "manifest_digest", "config_digest", "media_type")
    LAYOUT_CACHED_FIELD_NUMBER: _ClassVar[int]
    ROOTFS_CACHED_FIELD_NUMBER: _ClassVar[int]
    CACHE_KEY_FIELD_NUMBER: _ClassVar[int]
    MANIFEST_DIGEST_FIELD_NUMBER: _ClassVar[int]
    CONFIG_DIGEST_FIELD_NUMBER: _ClassVar[int]
    MEDIA_TYPE_FIELD_NUMBER: _ClassVar[int]
    layout_cached: bool
    rootfs_cached: bool
    cache_key: str
    manifest_digest: str
    config_digest: str
    media_type: str
    def __init__(self, layout_cached: _Optional[bool] = ..., rootfs_cached: _Optional[bool] = ..., cache_key: _Optional[str] = ..., manifest_digest: _Optional[str] = ..., config_digest: _Optional[str] = ..., media_type: _Optional[str] = ...) -> None: ...

class ImagePullProgress(_message.Message):
    __slots__ = ("id", "status", "progress", "current_bytes", "total_bytes")
    ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_FIELD_NUMBER: _ClassVar[int]
    CURRENT_BYTES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_BYTES_FIELD_NUMBER: _ClassVar[int]
    id: str
    status: str
    progress: str
    current_bytes: int
    total_bytes: int
    def __init__(self, id: _Optional[str] = ..., status: _Optional[str] = ..., progress: _Optional[str] = ..., current_bytes: _Optional[int] = ..., total_bytes: _Optional[int] = ...) -> None: ...

class JupyterSpec(_message.Message):
    __slots__ = ("enabled", "guest_port")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    GUEST_PORT_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    guest_port: int
    def __init__(self, enabled: _Optional[bool] = ..., guest_port: _Optional[int] = ...) -> None: ...

class RunJupyterSpec(_message.Message):
    __slots__ = ("enabled", "guest_port", "expose")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    GUEST_PORT_FIELD_NUMBER: _ClassVar[int]
    EXPOSE_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    guest_port: int
    expose: bool
    def __init__(self, enabled: _Optional[bool] = ..., guest_port: _Optional[int] = ..., expose: _Optional[bool] = ...) -> None: ...

class StartRunRequest(_message.Message):
    __slots__ = ("run",)
    RUN_FIELD_NUMBER: _ClassVar[int]
    run: RunAgentRequest
    def __init__(self, run: _Optional[_Union[RunAgentRequest, _Mapping]] = ...) -> None: ...

class StartRunResponse(_message.Message):
    __slots__ = ("run", "warnings", "started")
    RUN_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    STARTED_FIELD_NUMBER: _ClassVar[int]
    run: RunSummary
    warnings: _containers.RepeatedScalarFieldContainer[str]
    started: bool
    def __init__(self, run: _Optional[_Union[RunSummary, _Mapping]] = ..., warnings: _Optional[_Iterable[str]] = ..., started: _Optional[bool] = ...) -> None: ...

class SkillSpec(_message.Message):
    __slots__ = ("name", "source", "url", "path", "ref", "username", "password", "token")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    REF_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    name: str
    source: str
    url: str
    path: str
    ref: str
    username: str
    password: str
    token: str
    def __init__(self, name: _Optional[str] = ..., source: _Optional[str] = ..., url: _Optional[str] = ..., path: _Optional[str] = ..., ref: _Optional[str] = ..., username: _Optional[str] = ..., password: _Optional[str] = ..., token: _Optional[str] = ...) -> None: ...

class NodeUpstreamFrame(_message.Message):
    __slots__ = ("client_frame_id", "register", "heartbeat", "session_output", "session_result", "command_ack", "error", "tunnel_response", "session_event", "terminal_output", "terminal_exit", "host_exec_result", "file_upload_result", "terminal_list_result", "tool_run_event", "session_stage", "ios_devices_report", "ios_job_event", "ios_job_result", "node_build_event", "node_build_result")
    CLIENT_FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    REGISTER_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    SESSION_OUTPUT_FIELD_NUMBER: _ClassVar[int]
    SESSION_RESULT_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ACK_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    TUNNEL_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    SESSION_EVENT_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_OUTPUT_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_EXIT_FIELD_NUMBER: _ClassVar[int]
    HOST_EXEC_RESULT_FIELD_NUMBER: _ClassVar[int]
    FILE_UPLOAD_RESULT_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_LIST_RESULT_FIELD_NUMBER: _ClassVar[int]
    TOOL_RUN_EVENT_FIELD_NUMBER: _ClassVar[int]
    SESSION_STAGE_FIELD_NUMBER: _ClassVar[int]
    IOS_DEVICES_REPORT_FIELD_NUMBER: _ClassVar[int]
    IOS_JOB_EVENT_FIELD_NUMBER: _ClassVar[int]
    IOS_JOB_RESULT_FIELD_NUMBER: _ClassVar[int]
    NODE_BUILD_EVENT_FIELD_NUMBER: _ClassVar[int]
    NODE_BUILD_RESULT_FIELD_NUMBER: _ClassVar[int]
    client_frame_id: str
    register: NodeRegister
    heartbeat: NodeHeartbeat
    session_output: NodeSessionOutput
    session_result: NodeSessionResult
    command_ack: NodeCommandAck
    error: NodeError
    tunnel_response: NodeTunnelResponse
    session_event: NodeSessionEventStructured
    terminal_output: NodeTerminalOutput
    terminal_exit: NodeTerminalExit
    host_exec_result: NodeHostExecResult
    file_upload_result: NodeFileUploadResult
    terminal_list_result: NodeTerminalListResult
    tool_run_event: NodeToolRunEvent
    session_stage: NodeSessionStage
    ios_devices_report: NodeIosDevicesReport
    ios_job_event: NodeIosJobEvent
    ios_job_result: NodeIosJobResult
    node_build_event: NodeBuildEvent
    node_build_result: NodeBuildResult
    def __init__(self, client_frame_id: _Optional[str] = ..., register: _Optional[_Union[NodeRegister, _Mapping]] = ..., heartbeat: _Optional[_Union[NodeHeartbeat, _Mapping]] = ..., session_output: _Optional[_Union[NodeSessionOutput, _Mapping]] = ..., session_result: _Optional[_Union[NodeSessionResult, _Mapping]] = ..., command_ack: _Optional[_Union[NodeCommandAck, _Mapping]] = ..., error: _Optional[_Union[NodeError, _Mapping]] = ..., tunnel_response: _Optional[_Union[NodeTunnelResponse, _Mapping]] = ..., session_event: _Optional[_Union[NodeSessionEventStructured, _Mapping]] = ..., terminal_output: _Optional[_Union[NodeTerminalOutput, _Mapping]] = ..., terminal_exit: _Optional[_Union[NodeTerminalExit, _Mapping]] = ..., host_exec_result: _Optional[_Union[NodeHostExecResult, _Mapping]] = ..., file_upload_result: _Optional[_Union[NodeFileUploadResult, _Mapping]] = ..., terminal_list_result: _Optional[_Union[NodeTerminalListResult, _Mapping]] = ..., tool_run_event: _Optional[_Union[NodeToolRunEvent, _Mapping]] = ..., session_stage: _Optional[_Union[NodeSessionStage, _Mapping]] = ..., ios_devices_report: _Optional[_Union[NodeIosDevicesReport, _Mapping]] = ..., ios_job_event: _Optional[_Union[NodeIosJobEvent, _Mapping]] = ..., ios_job_result: _Optional[_Union[NodeIosJobResult, _Mapping]] = ..., node_build_event: _Optional[_Union[NodeBuildEvent, _Mapping]] = ..., node_build_result: _Optional[_Union[NodeBuildResult, _Mapping]] = ...) -> None: ...

class NodeDownstreamFrame(_message.Message):
    __slots__ = ("server_frame_id", "created_at", "registered", "create_session", "delete_session", "list_sessions", "error", "tunnel_request", "session_input", "create_execution_node", "delete_execution_node", "server_hello", "configure_session_llm", "apply_session_mcps", "apply_session_skills", "apply_session_plugins", "start_session_runtime", "restart_session_runtime", "configure_session_mode", "collect_session_artifacts", "proxy_request", "manage_editor", "self_upgrade", "runtime_upgrade", "terminal_open", "terminal_input", "terminal_resize", "terminal_close", "terminal_attach", "terminal_list", "terminal_interrupt", "host_exec", "file_upload", "public_ip_lookup_config", "node_proxy_config", "tool_run_request", "tool_run_stop", "manage_environment", "sync_environment", "inspect_environment", "ios_discover", "ios_claim_device", "ios_release_device", "ios_configure_device", "ios_wda_job", "ios_job_cancel", "inspect_system_env", "sync_system_env", "archive_system_env_resource", "node_build", "node_build_cancel", "install_host_tool")
    SERVER_FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    REGISTERED_FIELD_NUMBER: _ClassVar[int]
    CREATE_SESSION_FIELD_NUMBER: _ClassVar[int]
    DELETE_SESSION_FIELD_NUMBER: _ClassVar[int]
    LIST_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    TUNNEL_REQUEST_FIELD_NUMBER: _ClassVar[int]
    SESSION_INPUT_FIELD_NUMBER: _ClassVar[int]
    CREATE_EXECUTION_NODE_FIELD_NUMBER: _ClassVar[int]
    DELETE_EXECUTION_NODE_FIELD_NUMBER: _ClassVar[int]
    SERVER_HELLO_FIELD_NUMBER: _ClassVar[int]
    CONFIGURE_SESSION_LLM_FIELD_NUMBER: _ClassVar[int]
    APPLY_SESSION_MCPS_FIELD_NUMBER: _ClassVar[int]
    APPLY_SESSION_SKILLS_FIELD_NUMBER: _ClassVar[int]
    APPLY_SESSION_PLUGINS_FIELD_NUMBER: _ClassVar[int]
    START_SESSION_RUNTIME_FIELD_NUMBER: _ClassVar[int]
    RESTART_SESSION_RUNTIME_FIELD_NUMBER: _ClassVar[int]
    CONFIGURE_SESSION_MODE_FIELD_NUMBER: _ClassVar[int]
    COLLECT_SESSION_ARTIFACTS_FIELD_NUMBER: _ClassVar[int]
    PROXY_REQUEST_FIELD_NUMBER: _ClassVar[int]
    MANAGE_EDITOR_FIELD_NUMBER: _ClassVar[int]
    SELF_UPGRADE_FIELD_NUMBER: _ClassVar[int]
    RUNTIME_UPGRADE_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_OPEN_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_INPUT_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_RESIZE_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_CLOSE_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_ATTACH_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_LIST_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_INTERRUPT_FIELD_NUMBER: _ClassVar[int]
    HOST_EXEC_FIELD_NUMBER: _ClassVar[int]
    FILE_UPLOAD_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_IP_LOOKUP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    NODE_PROXY_CONFIG_FIELD_NUMBER: _ClassVar[int]
    TOOL_RUN_REQUEST_FIELD_NUMBER: _ClassVar[int]
    TOOL_RUN_STOP_FIELD_NUMBER: _ClassVar[int]
    MANAGE_ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    SYNC_ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    INSPECT_ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    IOS_DISCOVER_FIELD_NUMBER: _ClassVar[int]
    IOS_CLAIM_DEVICE_FIELD_NUMBER: _ClassVar[int]
    IOS_RELEASE_DEVICE_FIELD_NUMBER: _ClassVar[int]
    IOS_CONFIGURE_DEVICE_FIELD_NUMBER: _ClassVar[int]
    IOS_WDA_JOB_FIELD_NUMBER: _ClassVar[int]
    IOS_JOB_CANCEL_FIELD_NUMBER: _ClassVar[int]
    INSPECT_SYSTEM_ENV_FIELD_NUMBER: _ClassVar[int]
    SYNC_SYSTEM_ENV_FIELD_NUMBER: _ClassVar[int]
    ARCHIVE_SYSTEM_ENV_RESOURCE_FIELD_NUMBER: _ClassVar[int]
    NODE_BUILD_FIELD_NUMBER: _ClassVar[int]
    NODE_BUILD_CANCEL_FIELD_NUMBER: _ClassVar[int]
    INSTALL_HOST_TOOL_FIELD_NUMBER: _ClassVar[int]
    server_frame_id: str
    created_at: str
    registered: NodeRegistered
    create_session: NodeCreateSession
    delete_session: NodeDeleteSession
    list_sessions: NodeListSessions
    error: NodeError
    tunnel_request: NodeTunnelRequest
    session_input: NodeSessionInput
    create_execution_node: NodeCreateExecutionNode
    delete_execution_node: NodeDeleteExecutionNode
    server_hello: NodeServerHello
    configure_session_llm: ConfigureSessionLLM
    apply_session_mcps: ApplySessionMCPs
    apply_session_skills: ApplySessionSkills
    apply_session_plugins: ApplySessionPlugins
    start_session_runtime: StartSessionRuntime
    restart_session_runtime: RestartSessionRuntime
    configure_session_mode: ConfigureSessionMode
    collect_session_artifacts: CollectSessionArtifacts
    proxy_request: NodeProxyRequest
    manage_editor: NodeManageEditor
    self_upgrade: NodeSelfUpgrade
    runtime_upgrade: NodeRuntimeUpgrade
    terminal_open: NodeTerminalOpen
    terminal_input: NodeTerminalInput
    terminal_resize: NodeTerminalResize
    terminal_close: NodeTerminalClose
    terminal_attach: NodeTerminalAttach
    terminal_list: NodeTerminalListRequest
    terminal_interrupt: NodeTerminalInterrupt
    host_exec: NodeHostExecRequest
    file_upload: NodeFileUploadRequest
    public_ip_lookup_config: NodePublicIPLookupConfig
    node_proxy_config: NodeProxyConfig
    tool_run_request: NodeToolRunRequest
    tool_run_stop: NodeToolRunStop
    manage_environment: NodeManageEnvironment
    sync_environment: NodeSyncEnvironment
    inspect_environment: NodeInspectEnvironment
    ios_discover: NodeIosDiscover
    ios_claim_device: NodeIosClaimDevice
    ios_release_device: NodeIosReleaseDevice
    ios_configure_device: NodeIosConfigureDevice
    ios_wda_job: NodeIosWdaJobRequest
    ios_job_cancel: NodeIosJobCancel
    inspect_system_env: NodeInspectSystemEnv
    sync_system_env: NodeSyncSystemEnv
    archive_system_env_resource: NodeArchiveSystemEnvResource
    node_build: NodeBuildRequest
    node_build_cancel: NodeBuildCancel
    install_host_tool: NodeInstallHostTool
    def __init__(self, server_frame_id: _Optional[str] = ..., created_at: _Optional[str] = ..., registered: _Optional[_Union[NodeRegistered, _Mapping]] = ..., create_session: _Optional[_Union[NodeCreateSession, _Mapping]] = ..., delete_session: _Optional[_Union[NodeDeleteSession, _Mapping]] = ..., list_sessions: _Optional[_Union[NodeListSessions, _Mapping]] = ..., error: _Optional[_Union[NodeError, _Mapping]] = ..., tunnel_request: _Optional[_Union[NodeTunnelRequest, _Mapping]] = ..., session_input: _Optional[_Union[NodeSessionInput, _Mapping]] = ..., create_execution_node: _Optional[_Union[NodeCreateExecutionNode, _Mapping]] = ..., delete_execution_node: _Optional[_Union[NodeDeleteExecutionNode, _Mapping]] = ..., server_hello: _Optional[_Union[NodeServerHello, _Mapping]] = ..., configure_session_llm: _Optional[_Union[ConfigureSessionLLM, _Mapping]] = ..., apply_session_mcps: _Optional[_Union[ApplySessionMCPs, _Mapping]] = ..., apply_session_skills: _Optional[_Union[ApplySessionSkills, _Mapping]] = ..., apply_session_plugins: _Optional[_Union[ApplySessionPlugins, _Mapping]] = ..., start_session_runtime: _Optional[_Union[StartSessionRuntime, _Mapping]] = ..., restart_session_runtime: _Optional[_Union[RestartSessionRuntime, _Mapping]] = ..., configure_session_mode: _Optional[_Union[ConfigureSessionMode, _Mapping]] = ..., collect_session_artifacts: _Optional[_Union[CollectSessionArtifacts, _Mapping]] = ..., proxy_request: _Optional[_Union[NodeProxyRequest, _Mapping]] = ..., manage_editor: _Optional[_Union[NodeManageEditor, _Mapping]] = ..., self_upgrade: _Optional[_Union[NodeSelfUpgrade, _Mapping]] = ..., runtime_upgrade: _Optional[_Union[NodeRuntimeUpgrade, _Mapping]] = ..., terminal_open: _Optional[_Union[NodeTerminalOpen, _Mapping]] = ..., terminal_input: _Optional[_Union[NodeTerminalInput, _Mapping]] = ..., terminal_resize: _Optional[_Union[NodeTerminalResize, _Mapping]] = ..., terminal_close: _Optional[_Union[NodeTerminalClose, _Mapping]] = ..., terminal_attach: _Optional[_Union[NodeTerminalAttach, _Mapping]] = ..., terminal_list: _Optional[_Union[NodeTerminalListRequest, _Mapping]] = ..., terminal_interrupt: _Optional[_Union[NodeTerminalInterrupt, _Mapping]] = ..., host_exec: _Optional[_Union[NodeHostExecRequest, _Mapping]] = ..., file_upload: _Optional[_Union[NodeFileUploadRequest, _Mapping]] = ..., public_ip_lookup_config: _Optional[_Union[NodePublicIPLookupConfig, _Mapping]] = ..., node_proxy_config: _Optional[_Union[NodeProxyConfig, _Mapping]] = ..., tool_run_request: _Optional[_Union[NodeToolRunRequest, _Mapping]] = ..., tool_run_stop: _Optional[_Union[NodeToolRunStop, _Mapping]] = ..., manage_environment: _Optional[_Union[NodeManageEnvironment, _Mapping]] = ..., sync_environment: _Optional[_Union[NodeSyncEnvironment, _Mapping]] = ..., inspect_environment: _Optional[_Union[NodeInspectEnvironment, _Mapping]] = ..., ios_discover: _Optional[_Union[NodeIosDiscover, _Mapping]] = ..., ios_claim_device: _Optional[_Union[NodeIosClaimDevice, _Mapping]] = ..., ios_release_device: _Optional[_Union[NodeIosReleaseDevice, _Mapping]] = ..., ios_configure_device: _Optional[_Union[NodeIosConfigureDevice, _Mapping]] = ..., ios_wda_job: _Optional[_Union[NodeIosWdaJobRequest, _Mapping]] = ..., ios_job_cancel: _Optional[_Union[NodeIosJobCancel, _Mapping]] = ..., inspect_system_env: _Optional[_Union[NodeInspectSystemEnv, _Mapping]] = ..., sync_system_env: _Optional[_Union[NodeSyncSystemEnv, _Mapping]] = ..., archive_system_env_resource: _Optional[_Union[NodeArchiveSystemEnvResource, _Mapping]] = ..., node_build: _Optional[_Union[NodeBuildRequest, _Mapping]] = ..., node_build_cancel: _Optional[_Union[NodeBuildCancel, _Mapping]] = ..., install_host_tool: _Optional[_Union[NodeInstallHostTool, _Mapping]] = ...) -> None: ...

class NodeManageEnvironment(_message.Message):
    __slots__ = ("env_id", "action")
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    env_id: str
    action: EnvironmentAction
    def __init__(self, env_id: _Optional[str] = ..., action: _Optional[_Union[EnvironmentAction, str]] = ...) -> None: ...

class NodeSyncEnvironment(_message.Message):
    __slots__ = ("env_id", "skills", "plugins")
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    PLUGINS_FIELD_NUMBER: _ClassVar[int]
    env_id: str
    skills: _containers.RepeatedCompositeFieldContainer[SkillSpec]
    plugins: _containers.RepeatedCompositeFieldContainer[NodePluginSpec]
    def __init__(self, env_id: _Optional[str] = ..., skills: _Optional[_Iterable[_Union[SkillSpec, _Mapping]]] = ..., plugins: _Optional[_Iterable[_Union[NodePluginSpec, _Mapping]]] = ...) -> None: ...

class NodeInspectEnvironment(_message.Message):
    __slots__ = ("env_id",)
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    env_id: str
    def __init__(self, env_id: _Optional[str] = ...) -> None: ...

class NodeEnvironmentEntry(_message.Message):
    __slots__ = ("kind", "name", "version")
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    kind: str
    name: str
    version: str
    def __init__(self, kind: _Optional[str] = ..., name: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class NodeInspectSystemEnv(_message.Message):
    __slots__ = ("provider",)
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    provider: str
    def __init__(self, provider: _Optional[str] = ...) -> None: ...

class NodeSyncSystemEnv(_message.Message):
    __slots__ = ("skills", "plugins", "overwrite", "remove")
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    PLUGINS_FIELD_NUMBER: _ClassVar[int]
    OVERWRITE_FIELD_NUMBER: _ClassVar[int]
    REMOVE_FIELD_NUMBER: _ClassVar[int]
    skills: _containers.RepeatedCompositeFieldContainer[SkillSpec]
    plugins: _containers.RepeatedCompositeFieldContainer[NodePluginSpec]
    overwrite: bool
    remove: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, skills: _Optional[_Iterable[_Union[SkillSpec, _Mapping]]] = ..., plugins: _Optional[_Iterable[_Union[NodePluginSpec, _Mapping]]] = ..., overwrite: _Optional[bool] = ..., remove: _Optional[_Iterable[str]] = ...) -> None: ...

class NodeArchiveSystemEnvResource(_message.Message):
    __slots__ = ("kind", "name", "upload_url", "upload_token")
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_TOKEN_FIELD_NUMBER: _ClassVar[int]
    kind: str
    name: str
    upload_url: str
    upload_token: str
    def __init__(self, kind: _Optional[str] = ..., name: _Optional[str] = ..., upload_url: _Optional[str] = ..., upload_token: _Optional[str] = ...) -> None: ...

class NodeSystemEnvEntry(_message.Message):
    __slots__ = ("kind", "name", "version", "provider", "path", "platform_managed", "description", "readers")
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_MANAGED_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    READERS_FIELD_NUMBER: _ClassVar[int]
    kind: str
    name: str
    version: str
    provider: str
    path: str
    platform_managed: bool
    description: str
    readers: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, kind: _Optional[str] = ..., name: _Optional[str] = ..., version: _Optional[str] = ..., provider: _Optional[str] = ..., path: _Optional[str] = ..., platform_managed: _Optional[bool] = ..., description: _Optional[str] = ..., readers: _Optional[_Iterable[str]] = ...) -> None: ...

class NodeManageEditor(_message.Message):
    __slots__ = ("editor", "action")
    EDITOR_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    editor: str
    action: EditorAction
    def __init__(self, editor: _Optional[str] = ..., action: _Optional[_Union[EditorAction, str]] = ...) -> None: ...

class NodeSelfUpgrade(_message.Message):
    __slots__ = ("target_version", "download_url", "sha256", "proxy_mode", "proxy_url", "proxy_url_prefix")
    TARGET_VERSION_FIELD_NUMBER: _ClassVar[int]
    DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    PROXY_MODE_FIELD_NUMBER: _ClassVar[int]
    PROXY_URL_FIELD_NUMBER: _ClassVar[int]
    PROXY_URL_PREFIX_FIELD_NUMBER: _ClassVar[int]
    target_version: str
    download_url: str
    sha256: str
    proxy_mode: str
    proxy_url: str
    proxy_url_prefix: str
    def __init__(self, target_version: _Optional[str] = ..., download_url: _Optional[str] = ..., sha256: _Optional[str] = ..., proxy_mode: _Optional[str] = ..., proxy_url: _Optional[str] = ..., proxy_url_prefix: _Optional[str] = ...) -> None: ...

class NodeRuntimeUpgrade(_message.Message):
    __slots__ = ("target_version", "download_url", "sha256", "proxy_mode", "proxy_url", "proxy_url_prefix")
    TARGET_VERSION_FIELD_NUMBER: _ClassVar[int]
    DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    PROXY_MODE_FIELD_NUMBER: _ClassVar[int]
    PROXY_URL_FIELD_NUMBER: _ClassVar[int]
    PROXY_URL_PREFIX_FIELD_NUMBER: _ClassVar[int]
    target_version: str
    download_url: str
    sha256: str
    proxy_mode: str
    proxy_url: str
    proxy_url_prefix: str
    def __init__(self, target_version: _Optional[str] = ..., download_url: _Optional[str] = ..., sha256: _Optional[str] = ..., proxy_mode: _Optional[str] = ..., proxy_url: _Optional[str] = ..., proxy_url_prefix: _Optional[str] = ...) -> None: ...

class NodeInstallHostTool(_message.Message):
    __slots__ = ("tool", "target_version", "download_url", "sha256", "proxy_mode", "proxy_url", "proxy_url_prefix")
    TOOL_FIELD_NUMBER: _ClassVar[int]
    TARGET_VERSION_FIELD_NUMBER: _ClassVar[int]
    DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    PROXY_MODE_FIELD_NUMBER: _ClassVar[int]
    PROXY_URL_FIELD_NUMBER: _ClassVar[int]
    PROXY_URL_PREFIX_FIELD_NUMBER: _ClassVar[int]
    tool: str
    target_version: str
    download_url: str
    sha256: str
    proxy_mode: str
    proxy_url: str
    proxy_url_prefix: str
    def __init__(self, tool: _Optional[str] = ..., target_version: _Optional[str] = ..., download_url: _Optional[str] = ..., sha256: _Optional[str] = ..., proxy_mode: _Optional[str] = ..., proxy_url: _Optional[str] = ..., proxy_url_prefix: _Optional[str] = ...) -> None: ...

class NodeTerminalOpen(_message.Message):
    __slots__ = ("terminal_id", "shell", "cwd", "terminal_size", "session_id", "env_id")
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    SHELL_FIELD_NUMBER: _ClassVar[int]
    CWD_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    shell: str
    cwd: str
    terminal_size: AttachTerminalSize
    session_id: str
    env_id: str
    def __init__(self, terminal_id: _Optional[str] = ..., shell: _Optional[str] = ..., cwd: _Optional[str] = ..., terminal_size: _Optional[_Union[AttachTerminalSize, _Mapping]] = ..., session_id: _Optional[str] = ..., env_id: _Optional[str] = ...) -> None: ...

class NodeTerminalInput(_message.Message):
    __slots__ = ("terminal_id", "data")
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    data: bytes
    def __init__(self, terminal_id: _Optional[str] = ..., data: _Optional[bytes] = ...) -> None: ...

class NodeTerminalResize(_message.Message):
    __slots__ = ("terminal_id", "terminal_size")
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    terminal_size: AttachTerminalSize
    def __init__(self, terminal_id: _Optional[str] = ..., terminal_size: _Optional[_Union[AttachTerminalSize, _Mapping]] = ...) -> None: ...

class NodeTerminalClose(_message.Message):
    __slots__ = ("terminal_id",)
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    def __init__(self, terminal_id: _Optional[str] = ...) -> None: ...

class NodeTerminalAttach(_message.Message):
    __slots__ = ("terminal_id", "after_sequence")
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    AFTER_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    after_sequence: int
    def __init__(self, terminal_id: _Optional[str] = ..., after_sequence: _Optional[int] = ...) -> None: ...

class NodeTerminalListRequest(_message.Message):
    __slots__ = ("request_id",)
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    def __init__(self, request_id: _Optional[str] = ...) -> None: ...

class NodeTerminalStatus(_message.Message):
    __slots__ = ("terminal_id", "current_command", "running", "source", "started_at", "created_at", "attached")
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    CURRENT_COMMAND_FIELD_NUMBER: _ClassVar[int]
    RUNNING_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    ATTACHED_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    current_command: str
    running: bool
    source: str
    started_at: str
    created_at: str
    attached: bool
    def __init__(self, terminal_id: _Optional[str] = ..., current_command: _Optional[str] = ..., running: _Optional[bool] = ..., source: _Optional[str] = ..., started_at: _Optional[str] = ..., created_at: _Optional[str] = ..., attached: _Optional[bool] = ...) -> None: ...

class NodeTerminalListResult(_message.Message):
    __slots__ = ("request_id", "terminals")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TERMINALS_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    terminals: _containers.RepeatedCompositeFieldContainer[NodeTerminalStatus]
    def __init__(self, request_id: _Optional[str] = ..., terminals: _Optional[_Iterable[_Union[NodeTerminalStatus, _Mapping]]] = ...) -> None: ...

class NodeTerminalInterrupt(_message.Message):
    __slots__ = ("terminal_id",)
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    def __init__(self, terminal_id: _Optional[str] = ...) -> None: ...

class NodeTerminalOutput(_message.Message):
    __slots__ = ("terminal_id", "data", "sequence", "replay_truncated")
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    REPLAY_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    data: bytes
    sequence: int
    replay_truncated: bool
    def __init__(self, terminal_id: _Optional[str] = ..., data: _Optional[bytes] = ..., sequence: _Optional[int] = ..., replay_truncated: _Optional[bool] = ...) -> None: ...

class NodeTerminalExit(_message.Message):
    __slots__ = ("terminal_id", "exit_code", "error")
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    terminal_id: str
    exit_code: int
    error: str
    def __init__(self, terminal_id: _Optional[str] = ..., exit_code: _Optional[int] = ..., error: _Optional[str] = ...) -> None: ...

class NodeHostExecRequest(_message.Message):
    __slots__ = ("request_id", "command", "cwd", "timeout_ms", "max_output_bytes", "node_id")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    CWD_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    MAX_OUTPUT_BYTES_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    command: str
    cwd: str
    timeout_ms: int
    max_output_bytes: int
    node_id: str
    def __init__(self, request_id: _Optional[str] = ..., command: _Optional[str] = ..., cwd: _Optional[str] = ..., timeout_ms: _Optional[int] = ..., max_output_bytes: _Optional[int] = ..., node_id: _Optional[str] = ...) -> None: ...

class NodeHostExecResult(_message.Message):
    __slots__ = ("request_id", "exit_code", "success", "stdout", "stderr", "stdout_truncated", "stderr_truncated", "error")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    STDOUT_FIELD_NUMBER: _ClassVar[int]
    STDERR_FIELD_NUMBER: _ClassVar[int]
    STDOUT_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    STDERR_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    exit_code: int
    success: bool
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    error: str
    def __init__(self, request_id: _Optional[str] = ..., exit_code: _Optional[int] = ..., success: _Optional[bool] = ..., stdout: _Optional[str] = ..., stderr: _Optional[str] = ..., stdout_truncated: _Optional[bool] = ..., stderr_truncated: _Optional[bool] = ..., error: _Optional[str] = ...) -> None: ...

class NodeToolRunRequest(_message.Message):
    __slots__ = ("run_id", "binary_path", "args", "env", "cwd", "max_event_bytes", "node_id", "revision")
    class EnvEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    BINARY_PATH_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    CWD_FIELD_NUMBER: _ClassVar[int]
    MAX_EVENT_BYTES_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    binary_path: str
    args: _containers.RepeatedScalarFieldContainer[str]
    env: _containers.ScalarMap[str, str]
    cwd: str
    max_event_bytes: int
    node_id: str
    revision: int
    def __init__(self, run_id: _Optional[str] = ..., binary_path: _Optional[str] = ..., args: _Optional[_Iterable[str]] = ..., env: _Optional[_Mapping[str, str]] = ..., cwd: _Optional[str] = ..., max_event_bytes: _Optional[int] = ..., node_id: _Optional[str] = ..., revision: _Optional[int] = ...) -> None: ...

class NodeToolRunStop(_message.Message):
    __slots__ = ("run_id", "grace_ms", "node_id")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    GRACE_MS_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    grace_ms: int
    node_id: str
    def __init__(self, run_id: _Optional[str] = ..., grace_ms: _Optional[int] = ..., node_id: _Optional[str] = ...) -> None: ...

class NodeToolRunEvent(_message.Message):
    __slots__ = ("run_id", "kind", "data", "exit_code", "error", "revision", "pid")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    PID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    kind: NodeToolRunKind
    data: bytes
    exit_code: int
    error: str
    revision: int
    pid: int
    def __init__(self, run_id: _Optional[str] = ..., kind: _Optional[_Union[NodeToolRunKind, str]] = ..., data: _Optional[bytes] = ..., exit_code: _Optional[int] = ..., error: _Optional[str] = ..., revision: _Optional[int] = ..., pid: _Optional[int] = ...) -> None: ...

class NodeActiveToolRun(_message.Message):
    __slots__ = ("run_id", "revision", "pid")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    PID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    revision: int
    pid: int
    def __init__(self, run_id: _Optional[str] = ..., revision: _Optional[int] = ..., pid: _Optional[int] = ...) -> None: ...

class FollowToolRunRequest(_message.Message):
    __slots__ = ("node_id", "run_id")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    run_id: str
    def __init__(self, node_id: _Optional[str] = ..., run_id: _Optional[str] = ...) -> None: ...

class NodeFileUploadRequest(_message.Message):
    __slots__ = ("upload_id", "path", "offset", "data", "total_size", "sha256", "overwrite", "final")
    UPLOAD_ID_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    OVERWRITE_FIELD_NUMBER: _ClassVar[int]
    FINAL_FIELD_NUMBER: _ClassVar[int]
    upload_id: str
    path: str
    offset: int
    data: bytes
    total_size: int
    sha256: str
    overwrite: bool
    final: bool
    def __init__(self, upload_id: _Optional[str] = ..., path: _Optional[str] = ..., offset: _Optional[int] = ..., data: _Optional[bytes] = ..., total_size: _Optional[int] = ..., sha256: _Optional[str] = ..., overwrite: _Optional[bool] = ..., final: _Optional[bool] = ...) -> None: ...

class NodeFileUploadResult(_message.Message):
    __slots__ = ("upload_id", "ok", "bytes_written", "path", "error")
    UPLOAD_ID_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    BYTES_WRITTEN_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    upload_id: str
    ok: bool
    bytes_written: int
    path: str
    error: str
    def __init__(self, upload_id: _Optional[str] = ..., ok: _Optional[bool] = ..., bytes_written: _Optional[int] = ..., path: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class NodeRegister(_message.Message):
    __slots__ = ("node_id", "totp_code", "node_name", "capabilities", "role")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    TOTP_CODE_FIELD_NUMBER: _ClassVar[int]
    NODE_NAME_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    totp_code: str
    node_name: str
    capabilities: NodeCapabilities
    role: NodeRole
    def __init__(self, node_id: _Optional[str] = ..., totp_code: _Optional[str] = ..., node_name: _Optional[str] = ..., capabilities: _Optional[_Union[NodeCapabilities, _Mapping]] = ..., role: _Optional[_Union[NodeRole, str]] = ...) -> None: ...

class NodeServerHello(_message.Message):
    __slots__ = ("server_time",)
    SERVER_TIME_FIELD_NUMBER: _ClassVar[int]
    server_time: str
    def __init__(self, server_time: _Optional[str] = ...) -> None: ...

class EditorModeSemantics(_message.Message):
    __slots__ = ("can_read", "can_edit_workspace", "can_run_commands", "requires_approval", "network_access")
    CAN_READ_FIELD_NUMBER: _ClassVar[int]
    CAN_EDIT_WORKSPACE_FIELD_NUMBER: _ClassVar[int]
    CAN_RUN_COMMANDS_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_APPROVAL_FIELD_NUMBER: _ClassVar[int]
    NETWORK_ACCESS_FIELD_NUMBER: _ClassVar[int]
    can_read: bool
    can_edit_workspace: bool
    can_run_commands: bool
    requires_approval: bool
    network_access: bool
    def __init__(self, can_read: _Optional[bool] = ..., can_edit_workspace: _Optional[bool] = ..., can_run_commands: _Optional[bool] = ..., requires_approval: _Optional[bool] = ..., network_access: _Optional[bool] = ...) -> None: ...

class EditorModeSpec(_message.Message):
    __slots__ = ("id", "label", "native", "semantics", "source")
    class NativeEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    NATIVE_FIELD_NUMBER: _ClassVar[int]
    SEMANTICS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    id: str
    label: str
    native: _containers.ScalarMap[str, str]
    semantics: EditorModeSemantics
    source: str
    def __init__(self, id: _Optional[str] = ..., label: _Optional[str] = ..., native: _Optional[_Mapping[str, str]] = ..., semantics: _Optional[_Union[EditorModeSemantics, _Mapping]] = ..., source: _Optional[str] = ...) -> None: ...

class EditorCapability(_message.Message):
    __slots__ = ("provider", "version", "modes", "supports_interactive", "supports_model_switch", "probe_status", "probe_error", "probed_at")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    MODES_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_INTERACTIVE_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_MODEL_SWITCH_FIELD_NUMBER: _ClassVar[int]
    PROBE_STATUS_FIELD_NUMBER: _ClassVar[int]
    PROBE_ERROR_FIELD_NUMBER: _ClassVar[int]
    PROBED_AT_FIELD_NUMBER: _ClassVar[int]
    provider: str
    version: str
    modes: _containers.RepeatedCompositeFieldContainer[EditorModeSpec]
    supports_interactive: bool
    supports_model_switch: bool
    probe_status: str
    probe_error: str
    probed_at: str
    def __init__(self, provider: _Optional[str] = ..., version: _Optional[str] = ..., modes: _Optional[_Iterable[_Union[EditorModeSpec, _Mapping]]] = ..., supports_interactive: _Optional[bool] = ..., supports_model_switch: _Optional[bool] = ..., probe_status: _Optional[str] = ..., probe_error: _Optional[str] = ..., probed_at: _Optional[str] = ...) -> None: ...

class NodeCapabilities(_message.Message):
    __slots__ = ("os", "arch", "docker", "providers", "labels", "editors")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    OS_FIELD_NUMBER: _ClassVar[int]
    ARCH_FIELD_NUMBER: _ClassVar[int]
    DOCKER_FIELD_NUMBER: _ClassVar[int]
    PROVIDERS_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    EDITORS_FIELD_NUMBER: _ClassVar[int]
    os: str
    arch: str
    docker: bool
    providers: _containers.RepeatedScalarFieldContainer[str]
    labels: _containers.ScalarMap[str, str]
    editors: _containers.RepeatedCompositeFieldContainer[EditorCapability]
    def __init__(self, os: _Optional[str] = ..., arch: _Optional[str] = ..., docker: _Optional[bool] = ..., providers: _Optional[_Iterable[str]] = ..., labels: _Optional[_Mapping[str, str]] = ..., editors: _Optional[_Iterable[_Union[EditorCapability, _Mapping]]] = ...) -> None: ...

class NodePublicIPReport(_message.Message):
    __slots__ = ("config_revision", "ipv4", "ipv6", "ipv4_resolved_at", "ipv6_resolved_at", "ipv4_disabled", "ipv6_disabled")
    CONFIG_REVISION_FIELD_NUMBER: _ClassVar[int]
    IPV4_FIELD_NUMBER: _ClassVar[int]
    IPV6_FIELD_NUMBER: _ClassVar[int]
    IPV4_RESOLVED_AT_FIELD_NUMBER: _ClassVar[int]
    IPV6_RESOLVED_AT_FIELD_NUMBER: _ClassVar[int]
    IPV4_DISABLED_FIELD_NUMBER: _ClassVar[int]
    IPV6_DISABLED_FIELD_NUMBER: _ClassVar[int]
    config_revision: int
    ipv4: str
    ipv6: str
    ipv4_resolved_at: str
    ipv6_resolved_at: str
    ipv4_disabled: bool
    ipv6_disabled: bool
    def __init__(self, config_revision: _Optional[int] = ..., ipv4: _Optional[str] = ..., ipv6: _Optional[str] = ..., ipv4_resolved_at: _Optional[str] = ..., ipv6_resolved_at: _Optional[str] = ..., ipv4_disabled: _Optional[bool] = ..., ipv6_disabled: _Optional[bool] = ...) -> None: ...

class NodeHeartbeat(_message.Message):
    __slots__ = ("node_id", "active_session_ids", "public_ip_report", "active_terminal_ids", "active_tool_runs")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_SESSION_IDS_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_IP_REPORT_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_TERMINAL_IDS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_TOOL_RUNS_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    active_session_ids: _containers.RepeatedScalarFieldContainer[str]
    public_ip_report: NodePublicIPReport
    active_terminal_ids: _containers.RepeatedScalarFieldContainer[str]
    active_tool_runs: _containers.RepeatedCompositeFieldContainer[NodeActiveToolRun]
    def __init__(self, node_id: _Optional[str] = ..., active_session_ids: _Optional[_Iterable[str]] = ..., public_ip_report: _Optional[_Union[NodePublicIPReport, _Mapping]] = ..., active_terminal_ids: _Optional[_Iterable[str]] = ..., active_tool_runs: _Optional[_Iterable[_Union[NodeActiveToolRun, _Mapping]]] = ...) -> None: ...

class NodePublicIPLookupConfig(_message.Message):
    __slots__ = ("revision", "ipv4_urls", "ipv6_urls")
    REVISION_FIELD_NUMBER: _ClassVar[int]
    IPV4_URLS_FIELD_NUMBER: _ClassVar[int]
    IPV6_URLS_FIELD_NUMBER: _ClassVar[int]
    revision: int
    ipv4_urls: _containers.RepeatedScalarFieldContainer[str]
    ipv6_urls: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, revision: _Optional[int] = ..., ipv4_urls: _Optional[_Iterable[str]] = ..., ipv6_urls: _Optional[_Iterable[str]] = ...) -> None: ...

class NodeProxyConfig(_message.Message):
    __slots__ = ("revision", "proxy_mode", "proxy_url", "proxy_url_prefix", "proxy_config_id")
    REVISION_FIELD_NUMBER: _ClassVar[int]
    PROXY_MODE_FIELD_NUMBER: _ClassVar[int]
    PROXY_URL_FIELD_NUMBER: _ClassVar[int]
    PROXY_URL_PREFIX_FIELD_NUMBER: _ClassVar[int]
    PROXY_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    revision: int
    proxy_mode: str
    proxy_url: str
    proxy_url_prefix: str
    proxy_config_id: str
    def __init__(self, revision: _Optional[int] = ..., proxy_mode: _Optional[str] = ..., proxy_url: _Optional[str] = ..., proxy_url_prefix: _Optional[str] = ..., proxy_config_id: _Optional[str] = ...) -> None: ...

class GetPublicIPLookupConfigRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class UpdatePublicIPLookupConfigRequest(_message.Message):
    __slots__ = ("ipv4_urls", "ipv6_urls")
    IPV4_URLS_FIELD_NUMBER: _ClassVar[int]
    IPV6_URLS_FIELD_NUMBER: _ClassVar[int]
    ipv4_urls: _containers.RepeatedScalarFieldContainer[str]
    ipv6_urls: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, ipv4_urls: _Optional[_Iterable[str]] = ..., ipv6_urls: _Optional[_Iterable[str]] = ...) -> None: ...

class GetNodeProxyConfigRequest(_message.Message):
    __slots__ = ("node_id",)
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    def __init__(self, node_id: _Optional[str] = ...) -> None: ...

class UpdateNodeProxyConfigRequest(_message.Message):
    __slots__ = ("proxy_config_id", "node_id")
    PROXY_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    proxy_config_id: str
    node_id: str
    def __init__(self, proxy_config_id: _Optional[str] = ..., node_id: _Optional[str] = ...) -> None: ...

class SetNodeLastProxyRequest(_message.Message):
    __slots__ = ("node_id", "proxy_config_id")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    PROXY_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    proxy_config_id: str
    def __init__(self, node_id: _Optional[str] = ..., proxy_config_id: _Optional[str] = ...) -> None: ...

class SetNodeLastProxyResponse(_message.Message):
    __slots__ = ("node_id", "last_proxy_config_id")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_PROXY_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    last_proxy_config_id: str
    def __init__(self, node_id: _Optional[str] = ..., last_proxy_config_id: _Optional[str] = ...) -> None: ...

class NodeRegistered(_message.Message):
    __slots__ = ("node_id", "status", "server_time", "online")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIME_FIELD_NUMBER: _ClassVar[int]
    ONLINE_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    status: NodeStatus
    server_time: str
    online: bool
    def __init__(self, node_id: _Optional[str] = ..., status: _Optional[_Union[NodeStatus, str]] = ..., server_time: _Optional[str] = ..., online: _Optional[bool] = ...) -> None: ...

class NodeCreateSession(_message.Message):
    __slots__ = ("session_id", "project_id", "provider", "model", "git", "llm", "mcps", "skills", "plugins", "env", "volumes", "tags", "driver", "guest_image", "interactive", "mode", "defer_start", "editor_id", "editor_session_id", "task_id", "env_mode", "env_id", "active_skills", "active_plugins")
    class TagsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    GIT_FIELD_NUMBER: _ClassVar[int]
    LLM_FIELD_NUMBER: _ClassVar[int]
    MCPS_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    PLUGINS_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    VOLUMES_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    DRIVER_FIELD_NUMBER: _ClassVar[int]
    GUEST_IMAGE_FIELD_NUMBER: _ClassVar[int]
    INTERACTIVE_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    DEFER_START_FIELD_NUMBER: _ClassVar[int]
    EDITOR_ID_FIELD_NUMBER: _ClassVar[int]
    EDITOR_SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    ENV_MODE_FIELD_NUMBER: _ClassVar[int]
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_SKILLS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_PLUGINS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    project_id: str
    provider: str
    model: str
    git: NodeGitSpec
    llm: NodeLLMConfig
    mcps: _containers.RepeatedCompositeFieldContainer[MCPServerSpec]
    skills: _containers.RepeatedCompositeFieldContainer[SkillSpec]
    plugins: _containers.RepeatedCompositeFieldContainer[NodePluginSpec]
    env: _containers.RepeatedCompositeFieldContainer[EnvVarSpec]
    volumes: _containers.RepeatedCompositeFieldContainer[VolumeMountSpec]
    tags: _containers.ScalarMap[str, str]
    driver: str
    guest_image: str
    interactive: bool
    mode: str
    defer_start: bool
    editor_id: str
    editor_session_id: str
    task_id: str
    env_mode: str
    env_id: str
    active_skills: _containers.RepeatedScalarFieldContainer[str]
    active_plugins: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, session_id: _Optional[str] = ..., project_id: _Optional[str] = ..., provider: _Optional[str] = ..., model: _Optional[str] = ..., git: _Optional[_Union[NodeGitSpec, _Mapping]] = ..., llm: _Optional[_Union[NodeLLMConfig, _Mapping]] = ..., mcps: _Optional[_Iterable[_Union[MCPServerSpec, _Mapping]]] = ..., skills: _Optional[_Iterable[_Union[SkillSpec, _Mapping]]] = ..., plugins: _Optional[_Iterable[_Union[NodePluginSpec, _Mapping]]] = ..., env: _Optional[_Iterable[_Union[EnvVarSpec, _Mapping]]] = ..., volumes: _Optional[_Iterable[_Union[VolumeMountSpec, _Mapping]]] = ..., tags: _Optional[_Mapping[str, str]] = ..., driver: _Optional[str] = ..., guest_image: _Optional[str] = ..., interactive: _Optional[bool] = ..., mode: _Optional[str] = ..., defer_start: _Optional[bool] = ..., editor_id: _Optional[str] = ..., editor_session_id: _Optional[str] = ..., task_id: _Optional[str] = ..., env_mode: _Optional[str] = ..., env_id: _Optional[str] = ..., active_skills: _Optional[_Iterable[str]] = ..., active_plugins: _Optional[_Iterable[str]] = ...) -> None: ...

class NodeGitSpec(_message.Message):
    __slots__ = ("url", "branch", "commit", "create_branch", "new_branch", "username", "password", "token")
    URL_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    COMMIT_FIELD_NUMBER: _ClassVar[int]
    CREATE_BRANCH_FIELD_NUMBER: _ClassVar[int]
    NEW_BRANCH_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    url: str
    branch: str
    commit: str
    create_branch: bool
    new_branch: str
    username: str
    password: str
    token: str
    def __init__(self, url: _Optional[str] = ..., branch: _Optional[str] = ..., commit: _Optional[str] = ..., create_branch: _Optional[bool] = ..., new_branch: _Optional[str] = ..., username: _Optional[str] = ..., password: _Optional[str] = ..., token: _Optional[str] = ...) -> None: ...

class NodeLLMConfig(_message.Message):
    __slots__ = ("endpoint", "api_key", "model", "protocol", "headers", "extra")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class ExtraEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    API_KEY_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    endpoint: str
    api_key: str
    model: str
    protocol: str
    headers: _containers.ScalarMap[str, str]
    extra: _containers.ScalarMap[str, str]
    def __init__(self, endpoint: _Optional[str] = ..., api_key: _Optional[str] = ..., model: _Optional[str] = ..., protocol: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ..., extra: _Optional[_Mapping[str, str]] = ...) -> None: ...

class NodePluginSpec(_message.Message):
    __slots__ = ("name", "url", "version")
    NAME_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    name: str
    url: str
    version: str
    def __init__(self, name: _Optional[str] = ..., url: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class ConfigureSessionLLM(_message.Message):
    __slots__ = ("session_id", "revision", "llm")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    LLM_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    revision: int
    llm: NodeLLMConfig
    def __init__(self, session_id: _Optional[str] = ..., revision: _Optional[int] = ..., llm: _Optional[_Union[NodeLLMConfig, _Mapping]] = ...) -> None: ...

class ApplySessionMCPs(_message.Message):
    __slots__ = ("session_id", "revision", "mcps")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    MCPS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    revision: int
    mcps: _containers.RepeatedCompositeFieldContainer[MCPServerSpec]
    def __init__(self, session_id: _Optional[str] = ..., revision: _Optional[int] = ..., mcps: _Optional[_Iterable[_Union[MCPServerSpec, _Mapping]]] = ...) -> None: ...

class ApplySessionSkills(_message.Message):
    __slots__ = ("session_id", "revision", "skills")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    revision: int
    skills: _containers.RepeatedCompositeFieldContainer[SkillSpec]
    def __init__(self, session_id: _Optional[str] = ..., revision: _Optional[int] = ..., skills: _Optional[_Iterable[_Union[SkillSpec, _Mapping]]] = ...) -> None: ...

class ApplySessionPlugins(_message.Message):
    __slots__ = ("session_id", "revision", "plugins")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    PLUGINS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    revision: int
    plugins: _containers.RepeatedCompositeFieldContainer[NodePluginSpec]
    def __init__(self, session_id: _Optional[str] = ..., revision: _Optional[int] = ..., plugins: _Optional[_Iterable[_Union[NodePluginSpec, _Mapping]]] = ...) -> None: ...

class ConfigureSessionMode(_message.Message):
    __slots__ = ("session_id", "revision", "mode")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    revision: int
    mode: str
    def __init__(self, session_id: _Optional[str] = ..., revision: _Optional[int] = ..., mode: _Optional[str] = ...) -> None: ...

class StartSessionRuntime(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class RestartSessionRuntime(_message.Message):
    __slots__ = ("session_id", "fresh")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    FRESH_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    fresh: bool
    def __init__(self, session_id: _Optional[str] = ..., fresh: _Optional[bool] = ...) -> None: ...

class CollectSessionArtifacts(_message.Message):
    __slots__ = ("session_id", "path")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    path: str
    def __init__(self, session_id: _Optional[str] = ..., path: _Optional[str] = ...) -> None: ...

class NodeDeleteSession(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class NodeListSessions(_message.Message):
    __slots__ = ("request_id",)
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    def __init__(self, request_id: _Optional[str] = ...) -> None: ...

class NodeSessionInput(_message.Message):
    __slots__ = ("session_id", "kind", "text", "model", "mode", "llm", "client_message_id", "delivery_attempt")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    LLM_FIELD_NUMBER: _ClassVar[int]
    CLIENT_MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    DELIVERY_ATTEMPT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    kind: str
    text: str
    model: str
    mode: str
    llm: NodeLLMConfig
    client_message_id: str
    delivery_attempt: int
    def __init__(self, session_id: _Optional[str] = ..., kind: _Optional[str] = ..., text: _Optional[str] = ..., model: _Optional[str] = ..., mode: _Optional[str] = ..., llm: _Optional[_Union[NodeLLMConfig, _Mapping]] = ..., client_message_id: _Optional[str] = ..., delivery_attempt: _Optional[int] = ...) -> None: ...

class NodeCreateExecutionNode(_message.Message):
    __slots__ = ("launch_id", "server_url", "node_id", "secret", "startup_method", "node_name", "guest_image", "env", "labels")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    LAUNCH_ID_FIELD_NUMBER: _ClassVar[int]
    SERVER_URL_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    STARTUP_METHOD_FIELD_NUMBER: _ClassVar[int]
    NODE_NAME_FIELD_NUMBER: _ClassVar[int]
    GUEST_IMAGE_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    launch_id: str
    server_url: str
    node_id: str
    secret: str
    startup_method: NodeStartupMethod
    node_name: str
    guest_image: str
    env: _containers.RepeatedCompositeFieldContainer[EnvVarSpec]
    labels: _containers.ScalarMap[str, str]
    def __init__(self, launch_id: _Optional[str] = ..., server_url: _Optional[str] = ..., node_id: _Optional[str] = ..., secret: _Optional[str] = ..., startup_method: _Optional[_Union[NodeStartupMethod, str]] = ..., node_name: _Optional[str] = ..., guest_image: _Optional[str] = ..., env: _Optional[_Iterable[_Union[EnvVarSpec, _Mapping]]] = ..., labels: _Optional[_Mapping[str, str]] = ...) -> None: ...

class NodeDeleteExecutionNode(_message.Message):
    __slots__ = ("launch_id",)
    LAUNCH_ID_FIELD_NUMBER: _ClassVar[int]
    launch_id: str
    def __init__(self, launch_id: _Optional[str] = ...) -> None: ...

class SendSessionInputRequest(_message.Message):
    __slots__ = ("session_id", "kind", "text", "model", "mode", "llm", "client_message_id", "delivery_attempt")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    LLM_FIELD_NUMBER: _ClassVar[int]
    CLIENT_MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    DELIVERY_ATTEMPT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    kind: str
    text: str
    model: str
    mode: str
    llm: NodeLLMConfig
    client_message_id: str
    delivery_attempt: int
    def __init__(self, session_id: _Optional[str] = ..., kind: _Optional[str] = ..., text: _Optional[str] = ..., model: _Optional[str] = ..., mode: _Optional[str] = ..., llm: _Optional[_Union[NodeLLMConfig, _Mapping]] = ..., client_message_id: _Optional[str] = ..., delivery_attempt: _Optional[int] = ...) -> None: ...

class SendSessionInputResponse(_message.Message):
    __slots__ = ("accepted", "error")
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    accepted: bool
    error: str
    def __init__(self, accepted: _Optional[bool] = ..., error: _Optional[str] = ...) -> None: ...

class NodeTunnelRequest(_message.Message):
    __slots__ = ("tunnel_id", "session_id", "service", "method", "path", "headers", "body", "body_complete")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TUNNEL_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    BODY_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    tunnel_id: str
    session_id: str
    service: str
    method: str
    path: str
    headers: _containers.ScalarMap[str, str]
    body: bytes
    body_complete: bool
    def __init__(self, tunnel_id: _Optional[str] = ..., session_id: _Optional[str] = ..., service: _Optional[str] = ..., method: _Optional[str] = ..., path: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ..., body: _Optional[bytes] = ..., body_complete: _Optional[bool] = ...) -> None: ...

class NodeTunnelResponse(_message.Message):
    __slots__ = ("tunnel_id", "status", "headers", "body", "done", "error")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TUNNEL_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    tunnel_id: str
    status: int
    headers: _containers.ScalarMap[str, str]
    body: bytes
    done: bool
    error: str
    def __init__(self, tunnel_id: _Optional[str] = ..., status: _Optional[int] = ..., headers: _Optional[_Mapping[str, str]] = ..., body: _Optional[bytes] = ..., done: _Optional[bool] = ..., error: _Optional[str] = ...) -> None: ...

class NodeSessionOutput(_message.Message):
    __slots__ = ("session_id", "data", "stream", "offset", "created_at")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    STREAM_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    data: bytes
    stream: StdioStream
    offset: int
    created_at: str
    def __init__(self, session_id: _Optional[str] = ..., data: _Optional[bytes] = ..., stream: _Optional[_Union[StdioStream, str]] = ..., offset: _Optional[int] = ..., created_at: _Optional[str] = ...) -> None: ...

class NodeSessionResult(_message.Message):
    __slots__ = ("session_id", "exit_code", "success", "error", "result_json")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    RESULT_JSON_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    exit_code: int
    success: bool
    error: str
    result_json: str
    def __init__(self, session_id: _Optional[str] = ..., exit_code: _Optional[int] = ..., success: _Optional[bool] = ..., error: _Optional[str] = ..., result_json: _Optional[str] = ...) -> None: ...

class NodeSessionStage(_message.Message):
    __slots__ = ("session_id", "stage", "ok", "detail", "error", "created_at")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    STAGE_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    stage: SessionStage
    ok: bool
    detail: str
    error: str
    created_at: str
    def __init__(self, session_id: _Optional[str] = ..., stage: _Optional[_Union[SessionStage, str]] = ..., ok: _Optional[bool] = ..., detail: _Optional[str] = ..., error: _Optional[str] = ..., created_at: _Optional[str] = ...) -> None: ...

class NodeCommandAck(_message.Message):
    __slots__ = ("server_frame_id", "ok", "error", "sessions", "applied_revision", "effective_revision", "restart_required", "editor_version", "environment_inventory", "system_env_inventory", "node_version", "npm_version", "xcodebuild_version")
    SERVER_FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    SESSIONS_FIELD_NUMBER: _ClassVar[int]
    APPLIED_REVISION_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_REVISION_FIELD_NUMBER: _ClassVar[int]
    RESTART_REQUIRED_FIELD_NUMBER: _ClassVar[int]
    EDITOR_VERSION_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_INVENTORY_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ENV_INVENTORY_FIELD_NUMBER: _ClassVar[int]
    NODE_VERSION_FIELD_NUMBER: _ClassVar[int]
    NPM_VERSION_FIELD_NUMBER: _ClassVar[int]
    XCODEBUILD_VERSION_FIELD_NUMBER: _ClassVar[int]
    server_frame_id: str
    ok: bool
    error: str
    sessions: _containers.RepeatedCompositeFieldContainer[NodeSessionSummary]
    applied_revision: int
    effective_revision: int
    restart_required: bool
    editor_version: str
    environment_inventory: _containers.RepeatedCompositeFieldContainer[NodeEnvironmentEntry]
    system_env_inventory: _containers.RepeatedCompositeFieldContainer[NodeSystemEnvEntry]
    node_version: str
    npm_version: str
    xcodebuild_version: str
    def __init__(self, server_frame_id: _Optional[str] = ..., ok: _Optional[bool] = ..., error: _Optional[str] = ..., sessions: _Optional[_Iterable[_Union[NodeSessionSummary, _Mapping]]] = ..., applied_revision: _Optional[int] = ..., effective_revision: _Optional[int] = ..., restart_required: _Optional[bool] = ..., editor_version: _Optional[str] = ..., environment_inventory: _Optional[_Iterable[_Union[NodeEnvironmentEntry, _Mapping]]] = ..., system_env_inventory: _Optional[_Iterable[_Union[NodeSystemEnvEntry, _Mapping]]] = ..., node_version: _Optional[str] = ..., npm_version: _Optional[str] = ..., xcodebuild_version: _Optional[str] = ...) -> None: ...

class NodeSessionSummary(_message.Message):
    __slots__ = ("session_id", "project_id", "provider")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    project_id: str
    provider: str
    def __init__(self, session_id: _Optional[str] = ..., project_id: _Optional[str] = ..., provider: _Optional[str] = ...) -> None: ...

class NodeError(_message.Message):
    __slots__ = ("code", "message", "terminal")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    terminal: bool
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ..., terminal: _Optional[bool] = ...) -> None: ...

class ListNodesRequest(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: NodeStatus
    def __init__(self, status: _Optional[_Union[NodeStatus, str]] = ...) -> None: ...

class ListNodesResponse(_message.Message):
    __slots__ = ("nodes",)
    NODES_FIELD_NUMBER: _ClassVar[int]
    nodes: _containers.RepeatedCompositeFieldContainer[NodeInfo]
    def __init__(self, nodes: _Optional[_Iterable[_Union[NodeInfo, _Mapping]]] = ...) -> None: ...

class NodeInfo(_message.Message):
    __slots__ = ("node_id", "node_name", "status", "capabilities", "connected_at", "last_heartbeat_at", "connected", "active_session_ids", "role", "startup_method", "manager_node_id", "online", "capacity", "proxy_config_id", "last_proxy_config_id")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_NAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    CONNECTED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_HEARTBEAT_AT_FIELD_NUMBER: _ClassVar[int]
    CONNECTED_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_SESSION_IDS_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    STARTUP_METHOD_FIELD_NUMBER: _ClassVar[int]
    MANAGER_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ONLINE_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    PROXY_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_PROXY_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    node_name: str
    status: NodeStatus
    capabilities: NodeCapabilities
    connected_at: str
    last_heartbeat_at: str
    connected: bool
    active_session_ids: _containers.RepeatedScalarFieldContainer[str]
    role: NodeRole
    startup_method: NodeStartupMethod
    manager_node_id: str
    online: bool
    capacity: NodeCapacity
    proxy_config_id: str
    last_proxy_config_id: str
    def __init__(self, node_id: _Optional[str] = ..., node_name: _Optional[str] = ..., status: _Optional[_Union[NodeStatus, str]] = ..., capabilities: _Optional[_Union[NodeCapabilities, _Mapping]] = ..., connected_at: _Optional[str] = ..., last_heartbeat_at: _Optional[str] = ..., connected: _Optional[bool] = ..., active_session_ids: _Optional[_Iterable[str]] = ..., role: _Optional[_Union[NodeRole, str]] = ..., startup_method: _Optional[_Union[NodeStartupMethod, str]] = ..., manager_node_id: _Optional[str] = ..., online: _Optional[bool] = ..., capacity: _Optional[_Union[NodeCapacity, _Mapping]] = ..., proxy_config_id: _Optional[str] = ..., last_proxy_config_id: _Optional[str] = ...) -> None: ...

class NodeCapacity(_message.Message):
    __slots__ = ("max_sessions", "cpu_total", "memory_total")
    MAX_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    CPU_TOTAL_FIELD_NUMBER: _ClassVar[int]
    MEMORY_TOTAL_FIELD_NUMBER: _ClassVar[int]
    max_sessions: int
    cpu_total: float
    memory_total: int
    def __init__(self, max_sessions: _Optional[int] = ..., cpu_total: _Optional[float] = ..., memory_total: _Optional[int] = ...) -> None: ...

class SetNodeCapacityRequest(_message.Message):
    __slots__ = ("node_id", "capacity")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    capacity: NodeCapacity
    def __init__(self, node_id: _Optional[str] = ..., capacity: _Optional[_Union[NodeCapacity, _Mapping]] = ...) -> None: ...

class SetNodeCapacityResponse(_message.Message):
    __slots__ = ("node_id", "capacity")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    capacity: NodeCapacity
    def __init__(self, node_id: _Optional[str] = ..., capacity: _Optional[_Union[NodeCapacity, _Mapping]] = ...) -> None: ...

class MoveNodeRequest(_message.Message):
    __slots__ = ("node_id", "manager_node_id")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    MANAGER_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    manager_node_id: str
    def __init__(self, node_id: _Optional[str] = ..., manager_node_id: _Optional[str] = ...) -> None: ...

class MoveNodeResponse(_message.Message):
    __slots__ = ("node",)
    NODE_FIELD_NUMBER: _ClassVar[int]
    node: NodeInfo
    def __init__(self, node: _Optional[_Union[NodeInfo, _Mapping]] = ...) -> None: ...

class ManageEditorRequest(_message.Message):
    __slots__ = ("node_id", "editor", "action")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    EDITOR_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    editor: str
    action: EditorAction
    def __init__(self, node_id: _Optional[str] = ..., editor: _Optional[str] = ..., action: _Optional[_Union[EditorAction, str]] = ...) -> None: ...

class ManageEditorResponse(_message.Message):
    __slots__ = ("node_id", "editor", "action", "version")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    EDITOR_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    editor: str
    action: str
    version: str
    def __init__(self, node_id: _Optional[str] = ..., editor: _Optional[str] = ..., action: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class ManageNodeEnvironmentRequest(_message.Message):
    __slots__ = ("node_id", "env_id", "action")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    env_id: str
    action: EnvironmentAction
    def __init__(self, node_id: _Optional[str] = ..., env_id: _Optional[str] = ..., action: _Optional[_Union[EnvironmentAction, str]] = ...) -> None: ...

class ManageNodeEnvironmentResponse(_message.Message):
    __slots__ = ("node_id", "env_id", "action", "exists")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    EXISTS_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    env_id: str
    action: str
    exists: bool
    def __init__(self, node_id: _Optional[str] = ..., env_id: _Optional[str] = ..., action: _Optional[str] = ..., exists: _Optional[bool] = ...) -> None: ...

class SyncNodeEnvironmentRequest(_message.Message):
    __slots__ = ("node_id", "env_id", "skills", "plugins")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    PLUGINS_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    env_id: str
    skills: _containers.RepeatedCompositeFieldContainer[SkillSpec]
    plugins: _containers.RepeatedCompositeFieldContainer[NodePluginSpec]
    def __init__(self, node_id: _Optional[str] = ..., env_id: _Optional[str] = ..., skills: _Optional[_Iterable[_Union[SkillSpec, _Mapping]]] = ..., plugins: _Optional[_Iterable[_Union[NodePluginSpec, _Mapping]]] = ...) -> None: ...

class SyncNodeEnvironmentResponse(_message.Message):
    __slots__ = ("node_id", "env_id", "ok")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    env_id: str
    ok: bool
    def __init__(self, node_id: _Optional[str] = ..., env_id: _Optional[str] = ..., ok: _Optional[bool] = ...) -> None: ...

class InspectNodeEnvironmentRequest(_message.Message):
    __slots__ = ("node_id", "env_id")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    env_id: str
    def __init__(self, node_id: _Optional[str] = ..., env_id: _Optional[str] = ...) -> None: ...

class InspectNodeEnvironmentResponse(_message.Message):
    __slots__ = ("node_id", "env_id", "installed")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ENV_ID_FIELD_NUMBER: _ClassVar[int]
    INSTALLED_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    env_id: str
    installed: _containers.RepeatedCompositeFieldContainer[NodeEnvironmentEntry]
    def __init__(self, node_id: _Optional[str] = ..., env_id: _Optional[str] = ..., installed: _Optional[_Iterable[_Union[NodeEnvironmentEntry, _Mapping]]] = ...) -> None: ...

class InspectNodeSystemEnvRequest(_message.Message):
    __slots__ = ("node_id", "provider")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    provider: str
    def __init__(self, node_id: _Optional[str] = ..., provider: _Optional[str] = ...) -> None: ...

class InspectNodeSystemEnvResponse(_message.Message):
    __slots__ = ("node_id", "installed")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    INSTALLED_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    installed: _containers.RepeatedCompositeFieldContainer[NodeSystemEnvEntry]
    def __init__(self, node_id: _Optional[str] = ..., installed: _Optional[_Iterable[_Union[NodeSystemEnvEntry, _Mapping]]] = ...) -> None: ...

class SyncNodeSystemEnvRequest(_message.Message):
    __slots__ = ("node_id", "skills", "plugins", "overwrite", "remove")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    PLUGINS_FIELD_NUMBER: _ClassVar[int]
    OVERWRITE_FIELD_NUMBER: _ClassVar[int]
    REMOVE_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    skills: _containers.RepeatedCompositeFieldContainer[SkillSpec]
    plugins: _containers.RepeatedCompositeFieldContainer[NodePluginSpec]
    overwrite: bool
    remove: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, node_id: _Optional[str] = ..., skills: _Optional[_Iterable[_Union[SkillSpec, _Mapping]]] = ..., plugins: _Optional[_Iterable[_Union[NodePluginSpec, _Mapping]]] = ..., overwrite: _Optional[bool] = ..., remove: _Optional[_Iterable[str]] = ...) -> None: ...

class SyncNodeSystemEnvResponse(_message.Message):
    __slots__ = ("node_id", "ok", "touched")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    TOUCHED_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    ok: bool
    touched: _containers.RepeatedCompositeFieldContainer[NodeSystemEnvEntry]
    def __init__(self, node_id: _Optional[str] = ..., ok: _Optional[bool] = ..., touched: _Optional[_Iterable[_Union[NodeSystemEnvEntry, _Mapping]]] = ...) -> None: ...

class ArchiveNodeSystemEnvResourceRequest(_message.Message):
    __slots__ = ("node_id", "kind", "name")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    kind: str
    name: str
    def __init__(self, node_id: _Optional[str] = ..., kind: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class ArchiveNodeSystemEnvResourceResponse(_message.Message):
    __slots__ = ("node_id", "kind", "name", "ok")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    kind: str
    name: str
    ok: bool
    def __init__(self, node_id: _Optional[str] = ..., kind: _Optional[str] = ..., name: _Optional[str] = ..., ok: _Optional[bool] = ...) -> None: ...

class SelfUpgradeNodeRequest(_message.Message):
    __slots__ = ("node_id",)
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    def __init__(self, node_id: _Optional[str] = ...) -> None: ...

class SelfUpgradeNodeResponse(_message.Message):
    __slots__ = ("node_id", "target_version", "download_url", "sha256")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    TARGET_VERSION_FIELD_NUMBER: _ClassVar[int]
    DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    target_version: str
    download_url: str
    sha256: str
    def __init__(self, node_id: _Optional[str] = ..., target_version: _Optional[str] = ..., download_url: _Optional[str] = ..., sha256: _Optional[str] = ...) -> None: ...

class RuntimeUpgradeNodeRequest(_message.Message):
    __slots__ = ("node_id",)
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    def __init__(self, node_id: _Optional[str] = ...) -> None: ...

class RuntimeUpgradeNodeResponse(_message.Message):
    __slots__ = ("node_id", "target_version", "download_url", "sha256")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    TARGET_VERSION_FIELD_NUMBER: _ClassVar[int]
    DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    target_version: str
    download_url: str
    sha256: str
    def __init__(self, node_id: _Optional[str] = ..., target_version: _Optional[str] = ..., download_url: _Optional[str] = ..., sha256: _Optional[str] = ...) -> None: ...

class HostExecRequest(_message.Message):
    __slots__ = ("node_id", "command", "cwd", "timeout_ms", "max_output_bytes")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    CWD_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    MAX_OUTPUT_BYTES_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    command: str
    cwd: str
    timeout_ms: int
    max_output_bytes: int
    def __init__(self, node_id: _Optional[str] = ..., command: _Optional[str] = ..., cwd: _Optional[str] = ..., timeout_ms: _Optional[int] = ..., max_output_bytes: _Optional[int] = ...) -> None: ...

class HostExecResponse(_message.Message):
    __slots__ = ("request_id", "exit_code", "success", "stdout", "stderr", "stdout_truncated", "stderr_truncated", "error")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    STDOUT_FIELD_NUMBER: _ClassVar[int]
    STDERR_FIELD_NUMBER: _ClassVar[int]
    STDOUT_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    STDERR_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    exit_code: int
    success: bool
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    error: str
    def __init__(self, request_id: _Optional[str] = ..., exit_code: _Optional[int] = ..., success: _Optional[bool] = ..., stdout: _Optional[str] = ..., stderr: _Optional[str] = ..., stdout_truncated: _Optional[bool] = ..., stderr_truncated: _Optional[bool] = ..., error: _Optional[str] = ...) -> None: ...

class HostFileUploadRequest(_message.Message):
    __slots__ = ("node_id", "upload_id", "path", "offset", "data", "total_size", "sha256", "overwrite", "final")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_ID_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    OVERWRITE_FIELD_NUMBER: _ClassVar[int]
    FINAL_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    upload_id: str
    path: str
    offset: int
    data: bytes
    total_size: int
    sha256: str
    overwrite: bool
    final: bool
    def __init__(self, node_id: _Optional[str] = ..., upload_id: _Optional[str] = ..., path: _Optional[str] = ..., offset: _Optional[int] = ..., data: _Optional[bytes] = ..., total_size: _Optional[int] = ..., sha256: _Optional[str] = ..., overwrite: _Optional[bool] = ..., final: _Optional[bool] = ...) -> None: ...

class HostFileUploadResponse(_message.Message):
    __slots__ = ("upload_id", "ok", "bytes_written", "path", "error")
    UPLOAD_ID_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    BYTES_WRITTEN_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    upload_id: str
    ok: bool
    bytes_written: int
    path: str
    error: str
    def __init__(self, upload_id: _Optional[str] = ..., ok: _Optional[bool] = ..., bytes_written: _Optional[int] = ..., path: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class ApproveNodeRequest(_message.Message):
    __slots__ = ("node_id",)
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    def __init__(self, node_id: _Optional[str] = ...) -> None: ...

class ApproveNodeResponse(_message.Message):
    __slots__ = ("node",)
    NODE_FIELD_NUMBER: _ClassVar[int]
    node: NodeInfo
    def __init__(self, node: _Optional[_Union[NodeInfo, _Mapping]] = ...) -> None: ...

class RevokeNodeRequest(_message.Message):
    __slots__ = ("node_id",)
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    def __init__(self, node_id: _Optional[str] = ...) -> None: ...

class RevokeNodeResponse(_message.Message):
    __slots__ = ("node",)
    NODE_FIELD_NUMBER: _ClassVar[int]
    node: NodeInfo
    def __init__(self, node: _Optional[_Union[NodeInfo, _Mapping]] = ...) -> None: ...

class DeleteNodeRequest(_message.Message):
    __slots__ = ("node_id", "force")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    force: bool
    def __init__(self, node_id: _Optional[str] = ..., force: _Optional[bool] = ...) -> None: ...

class DeleteNodeResponse(_message.Message):
    __slots__ = ("deleted",)
    DELETED_FIELD_NUMBER: _ClassVar[int]
    deleted: bool
    def __init__(self, deleted: _Optional[bool] = ...) -> None: ...

class OnboardNodeRequest(_message.Message):
    __slots__ = ("role", "startup_method", "node_name", "labels", "manager_node_id", "proxy_config_id")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ROLE_FIELD_NUMBER: _ClassVar[int]
    STARTUP_METHOD_FIELD_NUMBER: _ClassVar[int]
    NODE_NAME_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    MANAGER_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    PROXY_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    role: NodeRole
    startup_method: NodeStartupMethod
    node_name: str
    labels: _containers.ScalarMap[str, str]
    manager_node_id: str
    proxy_config_id: str
    def __init__(self, role: _Optional[_Union[NodeRole, str]] = ..., startup_method: _Optional[_Union[NodeStartupMethod, str]] = ..., node_name: _Optional[str] = ..., labels: _Optional[_Mapping[str, str]] = ..., manager_node_id: _Optional[str] = ..., proxy_config_id: _Optional[str] = ...) -> None: ...

class OnboardNodeResponse(_message.Message):
    __slots__ = ("node_id", "secret", "install_command", "script_url", "node", "otpauth_uri", "launched")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    INSTALL_COMMAND_FIELD_NUMBER: _ClassVar[int]
    SCRIPT_URL_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    OTPAUTH_URI_FIELD_NUMBER: _ClassVar[int]
    LAUNCHED_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    secret: str
    install_command: str
    script_url: str
    node: NodeInfo
    otpauth_uri: str
    launched: bool
    def __init__(self, node_id: _Optional[str] = ..., secret: _Optional[str] = ..., install_command: _Optional[str] = ..., script_url: _Optional[str] = ..., node: _Optional[_Union[NodeInfo, _Mapping]] = ..., otpauth_uri: _Optional[str] = ..., launched: _Optional[bool] = ...) -> None: ...

class RevokeOnboardNodeRequest(_message.Message):
    __slots__ = ("node_id",)
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    def __init__(self, node_id: _Optional[str] = ...) -> None: ...

class RevokeOnboardNodeResponse(_message.Message):
    __slots__ = ("deleted", "revoked", "node")
    DELETED_FIELD_NUMBER: _ClassVar[int]
    REVOKED_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    deleted: bool
    revoked: bool
    node: NodeInfo
    def __init__(self, deleted: _Optional[bool] = ..., revoked: _Optional[bool] = ..., node: _Optional[_Union[NodeInfo, _Mapping]] = ...) -> None: ...

class DispatchSessionRequest(_message.Message):
    __slots__ = ("node_id", "session")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    session: NodeCreateSession
    def __init__(self, node_id: _Optional[str] = ..., session: _Optional[_Union[NodeCreateSession, _Mapping]] = ...) -> None: ...

class DispatchSessionResponse(_message.Message):
    __slots__ = ("session_id", "node_id", "accepted", "error")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    node_id: str
    accepted: bool
    error: str
    def __init__(self, session_id: _Optional[str] = ..., node_id: _Optional[str] = ..., accepted: _Optional[bool] = ..., error: _Optional[str] = ...) -> None: ...

class ConfigureNodeSessionLLMRequest(_message.Message):
    __slots__ = ("session_id", "llm")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    LLM_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    llm: NodeLLMConfig
    def __init__(self, session_id: _Optional[str] = ..., llm: _Optional[_Union[NodeLLMConfig, _Mapping]] = ...) -> None: ...

class ApplyNodeSessionMCPsRequest(_message.Message):
    __slots__ = ("session_id", "mcps")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    MCPS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    mcps: _containers.RepeatedCompositeFieldContainer[MCPServerSpec]
    def __init__(self, session_id: _Optional[str] = ..., mcps: _Optional[_Iterable[_Union[MCPServerSpec, _Mapping]]] = ...) -> None: ...

class ApplyNodeSessionSkillsRequest(_message.Message):
    __slots__ = ("session_id", "skills")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    skills: _containers.RepeatedCompositeFieldContainer[SkillSpec]
    def __init__(self, session_id: _Optional[str] = ..., skills: _Optional[_Iterable[_Union[SkillSpec, _Mapping]]] = ...) -> None: ...

class ApplyNodeSessionPluginsRequest(_message.Message):
    __slots__ = ("session_id", "plugins")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PLUGINS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    plugins: _containers.RepeatedCompositeFieldContainer[NodePluginSpec]
    def __init__(self, session_id: _Optional[str] = ..., plugins: _Optional[_Iterable[_Union[NodePluginSpec, _Mapping]]] = ...) -> None: ...

class ConfigureNodeSessionModeRequest(_message.Message):
    __slots__ = ("session_id", "mode")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    mode: str
    def __init__(self, session_id: _Optional[str] = ..., mode: _Optional[str] = ...) -> None: ...

class StartNodeSessionRuntimeRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class RestartNodeSessionRuntimeRequest(_message.Message):
    __slots__ = ("session_id", "fresh")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    FRESH_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    fresh: bool
    def __init__(self, session_id: _Optional[str] = ..., fresh: _Optional[bool] = ...) -> None: ...

class CollectNodeSessionArtifactsRequest(_message.Message):
    __slots__ = ("session_id", "path")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    path: str
    def __init__(self, session_id: _Optional[str] = ..., path: _Optional[str] = ...) -> None: ...

class NodeSessionConfigAck(_message.Message):
    __slots__ = ("ok", "error", "applied_revision", "effective_revision", "restart_required")
    OK_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    APPLIED_REVISION_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_REVISION_FIELD_NUMBER: _ClassVar[int]
    RESTART_REQUIRED_FIELD_NUMBER: _ClassVar[int]
    ok: bool
    error: str
    applied_revision: int
    effective_revision: int
    restart_required: bool
    def __init__(self, ok: _Optional[bool] = ..., error: _Optional[str] = ..., applied_revision: _Optional[int] = ..., effective_revision: _Optional[int] = ..., restart_required: _Optional[bool] = ...) -> None: ...

class DeleteNodeSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class DeleteNodeSessionResponse(_message.Message):
    __slots__ = ("deleted", "error")
    DELETED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    deleted: bool
    error: str
    def __init__(self, deleted: _Optional[bool] = ..., error: _Optional[str] = ...) -> None: ...

class FollowNodeSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class NodeSessionEvent(_message.Message):
    __slots__ = ("output", "result", "structured")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    STRUCTURED_FIELD_NUMBER: _ClassVar[int]
    output: NodeSessionOutput
    result: NodeSessionResult
    structured: NodeSessionEventStructured
    def __init__(self, output: _Optional[_Union[NodeSessionOutput, _Mapping]] = ..., result: _Optional[_Union[NodeSessionResult, _Mapping]] = ..., structured: _Optional[_Union[NodeSessionEventStructured, _Mapping]] = ...) -> None: ...

class NodeSessionEventStructured(_message.Message):
    __slots__ = ("session_id", "seq", "event_type", "item_type", "agent_id", "payload_json", "created_at", "logical_event_id", "event_name", "event_kind", "tool_name", "subagent_id", "phase", "status")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ITEM_TYPE_FIELD_NUMBER: _ClassVar[int]
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_JSON_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    LOGICAL_EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_NAME_FIELD_NUMBER: _ClassVar[int]
    EVENT_KIND_FIELD_NUMBER: _ClassVar[int]
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    SUBAGENT_ID_FIELD_NUMBER: _ClassVar[int]
    PHASE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    seq: int
    event_type: str
    item_type: str
    agent_id: str
    payload_json: str
    created_at: str
    logical_event_id: str
    event_name: str
    event_kind: str
    tool_name: str
    subagent_id: str
    phase: str
    status: str
    def __init__(self, session_id: _Optional[str] = ..., seq: _Optional[int] = ..., event_type: _Optional[str] = ..., item_type: _Optional[str] = ..., agent_id: _Optional[str] = ..., payload_json: _Optional[str] = ..., created_at: _Optional[str] = ..., logical_event_id: _Optional[str] = ..., event_name: _Optional[str] = ..., event_kind: _Optional[str] = ..., tool_name: _Optional[str] = ..., subagent_id: _Optional[str] = ..., phase: _Optional[str] = ..., status: _Optional[str] = ...) -> None: ...

class NodeProxyRequest(_message.Message):
    __slots__ = ("tunnel_id", "method", "url", "headers", "body", "body_complete")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TUNNEL_ID_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    BODY_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    tunnel_id: str
    method: str
    url: str
    headers: _containers.ScalarMap[str, str]
    body: bytes
    body_complete: bool
    def __init__(self, tunnel_id: _Optional[str] = ..., method: _Optional[str] = ..., url: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ..., body: _Optional[bytes] = ..., body_complete: _Optional[bool] = ...) -> None: ...

class NodeIosDiscover(_message.Message):
    __slots__ = ("request_id",)
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    def __init__(self, request_id: _Optional[str] = ...) -> None: ...

class NodeIosDevice(_message.Message):
    __slots__ = ("udid", "name", "model", "product_version", "connection_type", "present", "claimed", "device_id", "device_control_online", "wda_state", "wda_bundle_id", "profile_expires_at", "last_error", "config_revision_applied", "developer_mode_enabled")
    UDID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    PRODUCT_VERSION_FIELD_NUMBER: _ClassVar[int]
    CONNECTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    PRESENT_FIELD_NUMBER: _ClassVar[int]
    CLAIMED_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    DEVICE_CONTROL_ONLINE_FIELD_NUMBER: _ClassVar[int]
    WDA_STATE_FIELD_NUMBER: _ClassVar[int]
    WDA_BUNDLE_ID_FIELD_NUMBER: _ClassVar[int]
    PROFILE_EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_ERROR_FIELD_NUMBER: _ClassVar[int]
    CONFIG_REVISION_APPLIED_FIELD_NUMBER: _ClassVar[int]
    DEVELOPER_MODE_ENABLED_FIELD_NUMBER: _ClassVar[int]
    udid: str
    name: str
    model: str
    product_version: str
    connection_type: IosConnectionType
    present: bool
    claimed: bool
    device_id: str
    device_control_online: bool
    wda_state: IosWdaState
    wda_bundle_id: str
    profile_expires_at: str
    last_error: str
    config_revision_applied: int
    developer_mode_enabled: bool
    def __init__(self, udid: _Optional[str] = ..., name: _Optional[str] = ..., model: _Optional[str] = ..., product_version: _Optional[str] = ..., connection_type: _Optional[_Union[IosConnectionType, str]] = ..., present: _Optional[bool] = ..., claimed: _Optional[bool] = ..., device_id: _Optional[str] = ..., device_control_online: _Optional[bool] = ..., wda_state: _Optional[_Union[IosWdaState, str]] = ..., wda_bundle_id: _Optional[str] = ..., profile_expires_at: _Optional[str] = ..., last_error: _Optional[str] = ..., config_revision_applied: _Optional[int] = ..., developer_mode_enabled: _Optional[bool] = ...) -> None: ...

class NodeIosDevicesReport(_message.Message):
    __slots__ = ("request_id", "snapshot_revision", "reported_at", "devices", "enumerate_error")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_REVISION_FIELD_NUMBER: _ClassVar[int]
    REPORTED_AT_FIELD_NUMBER: _ClassVar[int]
    DEVICES_FIELD_NUMBER: _ClassVar[int]
    ENUMERATE_ERROR_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    snapshot_revision: int
    reported_at: str
    devices: _containers.RepeatedCompositeFieldContainer[NodeIosDevice]
    enumerate_error: str
    def __init__(self, request_id: _Optional[str] = ..., snapshot_revision: _Optional[int] = ..., reported_at: _Optional[str] = ..., devices: _Optional[_Iterable[_Union[NodeIosDevice, _Mapping]]] = ..., enumerate_error: _Optional[str] = ...) -> None: ...

class NodeIosClaimDevice(_message.Message):
    __slots__ = ("request_id", "udid", "device_label", "pairing_code", "server_url", "transport", "wda_bundle_id", "xctest_config_name", "config_revision")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    UDID_FIELD_NUMBER: _ClassVar[int]
    DEVICE_LABEL_FIELD_NUMBER: _ClassVar[int]
    PAIRING_CODE_FIELD_NUMBER: _ClassVar[int]
    SERVER_URL_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_FIELD_NUMBER: _ClassVar[int]
    WDA_BUNDLE_ID_FIELD_NUMBER: _ClassVar[int]
    XCTEST_CONFIG_NAME_FIELD_NUMBER: _ClassVar[int]
    CONFIG_REVISION_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    udid: str
    device_label: str
    pairing_code: str
    server_url: str
    transport: str
    wda_bundle_id: str
    xctest_config_name: str
    config_revision: int
    def __init__(self, request_id: _Optional[str] = ..., udid: _Optional[str] = ..., device_label: _Optional[str] = ..., pairing_code: _Optional[str] = ..., server_url: _Optional[str] = ..., transport: _Optional[str] = ..., wda_bundle_id: _Optional[str] = ..., xctest_config_name: _Optional[str] = ..., config_revision: _Optional[int] = ...) -> None: ...

class NodeIosReleaseDevice(_message.Message):
    __slots__ = ("request_id", "device_id", "udid", "delete_credential", "uninstall_wda")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    UDID_FIELD_NUMBER: _ClassVar[int]
    DELETE_CREDENTIAL_FIELD_NUMBER: _ClassVar[int]
    UNINSTALL_WDA_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    device_id: str
    udid: str
    delete_credential: bool
    uninstall_wda: bool
    def __init__(self, request_id: _Optional[str] = ..., device_id: _Optional[str] = ..., udid: _Optional[str] = ..., delete_credential: _Optional[bool] = ..., uninstall_wda: _Optional[bool] = ...) -> None: ...

class NodeIosConfigureDevice(_message.Message):
    __slots__ = ("request_id", "device_id", "udid", "config_revision", "transport", "wda_bundle_id", "xctest_config_name", "host_wda_port", "auto_prepare", "renew_before_days")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    UDID_FIELD_NUMBER: _ClassVar[int]
    CONFIG_REVISION_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_FIELD_NUMBER: _ClassVar[int]
    WDA_BUNDLE_ID_FIELD_NUMBER: _ClassVar[int]
    XCTEST_CONFIG_NAME_FIELD_NUMBER: _ClassVar[int]
    HOST_WDA_PORT_FIELD_NUMBER: _ClassVar[int]
    AUTO_PREPARE_FIELD_NUMBER: _ClassVar[int]
    RENEW_BEFORE_DAYS_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    device_id: str
    udid: str
    config_revision: int
    transport: str
    wda_bundle_id: str
    xctest_config_name: str
    host_wda_port: int
    auto_prepare: bool
    renew_before_days: int
    def __init__(self, request_id: _Optional[str] = ..., device_id: _Optional[str] = ..., udid: _Optional[str] = ..., config_revision: _Optional[int] = ..., transport: _Optional[str] = ..., wda_bundle_id: _Optional[str] = ..., xctest_config_name: _Optional[str] = ..., host_wda_port: _Optional[int] = ..., auto_prepare: _Optional[bool] = ..., renew_before_days: _Optional[int] = ...) -> None: ...

class NodeIosSigningMaterial(_message.Message):
    __slots__ = ("mode", "asc_key_id", "asc_issuer_id", "asc_private_key", "certificate_id", "certificate_p12", "p12_password", "provisioning_profile")
    MODE_FIELD_NUMBER: _ClassVar[int]
    ASC_KEY_ID_FIELD_NUMBER: _ClassVar[int]
    ASC_ISSUER_ID_FIELD_NUMBER: _ClassVar[int]
    ASC_PRIVATE_KEY_FIELD_NUMBER: _ClassVar[int]
    CERTIFICATE_ID_FIELD_NUMBER: _ClassVar[int]
    CERTIFICATE_P12_FIELD_NUMBER: _ClassVar[int]
    P12_PASSWORD_FIELD_NUMBER: _ClassVar[int]
    PROVISIONING_PROFILE_FIELD_NUMBER: _ClassVar[int]
    mode: IosSigningMode
    asc_key_id: str
    asc_issuer_id: str
    asc_private_key: bytes
    certificate_id: str
    certificate_p12: bytes
    p12_password: str
    provisioning_profile: bytes
    def __init__(self, mode: _Optional[_Union[IosSigningMode, str]] = ..., asc_key_id: _Optional[str] = ..., asc_issuer_id: _Optional[str] = ..., asc_private_key: _Optional[bytes] = ..., certificate_id: _Optional[str] = ..., certificate_p12: _Optional[bytes] = ..., p12_password: _Optional[str] = ..., provisioning_profile: _Optional[bytes] = ...) -> None: ...

class NodeIosWdaArtifact(_message.Message):
    __slots__ = ("artifact_id", "url", "sha256", "size_bytes", "version", "target_bundle_id", "xctest_config_name")
    ARTIFACT_ID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TARGET_BUNDLE_ID_FIELD_NUMBER: _ClassVar[int]
    XCTEST_CONFIG_NAME_FIELD_NUMBER: _ClassVar[int]
    artifact_id: str
    url: str
    sha256: str
    size_bytes: int
    version: str
    target_bundle_id: str
    xctest_config_name: str
    def __init__(self, artifact_id: _Optional[str] = ..., url: _Optional[str] = ..., sha256: _Optional[str] = ..., size_bytes: _Optional[int] = ..., version: _Optional[str] = ..., target_bundle_id: _Optional[str] = ..., xctest_config_name: _Optional[str] = ...) -> None: ...

class NodeIosWdaJobRequest(_message.Message):
    __slots__ = ("job_id", "request_id", "device_id", "udid", "action", "artifact", "signing", "config_revision", "force", "enable_developer_mode")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    UDID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_FIELD_NUMBER: _ClassVar[int]
    SIGNING_FIELD_NUMBER: _ClassVar[int]
    CONFIG_REVISION_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    ENABLE_DEVELOPER_MODE_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    request_id: str
    device_id: str
    udid: str
    action: IosWdaJobAction
    artifact: NodeIosWdaArtifact
    signing: NodeIosSigningMaterial
    config_revision: int
    force: bool
    enable_developer_mode: bool
    def __init__(self, job_id: _Optional[str] = ..., request_id: _Optional[str] = ..., device_id: _Optional[str] = ..., udid: _Optional[str] = ..., action: _Optional[_Union[IosWdaJobAction, str]] = ..., artifact: _Optional[_Union[NodeIosWdaArtifact, _Mapping]] = ..., signing: _Optional[_Union[NodeIosSigningMaterial, _Mapping]] = ..., config_revision: _Optional[int] = ..., force: _Optional[bool] = ..., enable_developer_mode: _Optional[bool] = ...) -> None: ...

class NodeIosJobCancel(_message.Message):
    __slots__ = ("request_id", "job_id")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    job_id: str
    def __init__(self, request_id: _Optional[str] = ..., job_id: _Optional[str] = ...) -> None: ...

class NodeIosJobEvent(_message.Message):
    __slots__ = ("job_id", "seq", "stage", "message", "percent", "reported_at", "log_tail")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    STAGE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PERCENT_FIELD_NUMBER: _ClassVar[int]
    REPORTED_AT_FIELD_NUMBER: _ClassVar[int]
    LOG_TAIL_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    seq: int
    stage: IosJobStage
    message: str
    percent: int
    reported_at: str
    log_tail: str
    def __init__(self, job_id: _Optional[str] = ..., seq: _Optional[int] = ..., stage: _Optional[_Union[IosJobStage, str]] = ..., message: _Optional[str] = ..., percent: _Optional[int] = ..., reported_at: _Optional[str] = ..., log_tail: _Optional[str] = ...) -> None: ...

class NodeIosJobResult(_message.Message):
    __slots__ = ("job_id", "ok", "error_code", "error_message", "retryable", "stage_reached", "wda_bundle_id", "profile_expires_at", "artifact_sha256", "artifact_version", "certificate_id", "config_revision")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRYABLE_FIELD_NUMBER: _ClassVar[int]
    STAGE_REACHED_FIELD_NUMBER: _ClassVar[int]
    WDA_BUNDLE_ID_FIELD_NUMBER: _ClassVar[int]
    PROFILE_EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_SHA256_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    CERTIFICATE_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIG_REVISION_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    ok: bool
    error_code: str
    error_message: str
    retryable: bool
    stage_reached: IosJobStage
    wda_bundle_id: str
    profile_expires_at: str
    artifact_sha256: str
    artifact_version: str
    certificate_id: str
    config_revision: int
    def __init__(self, job_id: _Optional[str] = ..., ok: _Optional[bool] = ..., error_code: _Optional[str] = ..., error_message: _Optional[str] = ..., retryable: _Optional[bool] = ..., stage_reached: _Optional[_Union[IosJobStage, str]] = ..., wda_bundle_id: _Optional[str] = ..., profile_expires_at: _Optional[str] = ..., artifact_sha256: _Optional[str] = ..., artifact_version: _Optional[str] = ..., certificate_id: _Optional[str] = ..., config_revision: _Optional[int] = ...) -> None: ...

class NodeBuildRequest(_message.Message):
    __slots__ = ("build_id", "recipe_kind", "source_url", "source_ref", "steps", "artifact_glob", "upload_url", "upload_token", "timeout_seconds", "artifact_name", "artifact_version")
    BUILD_ID_FIELD_NUMBER: _ClassVar[int]
    RECIPE_KIND_FIELD_NUMBER: _ClassVar[int]
    SOURCE_URL_FIELD_NUMBER: _ClassVar[int]
    SOURCE_REF_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_GLOB_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_SECONDS_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_NAME_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    build_id: str
    recipe_kind: str
    source_url: str
    source_ref: str
    steps: _containers.RepeatedScalarFieldContainer[str]
    artifact_glob: str
    upload_url: str
    upload_token: str
    timeout_seconds: int
    artifact_name: str
    artifact_version: str
    def __init__(self, build_id: _Optional[str] = ..., recipe_kind: _Optional[str] = ..., source_url: _Optional[str] = ..., source_ref: _Optional[str] = ..., steps: _Optional[_Iterable[str]] = ..., artifact_glob: _Optional[str] = ..., upload_url: _Optional[str] = ..., upload_token: _Optional[str] = ..., timeout_seconds: _Optional[int] = ..., artifact_name: _Optional[str] = ..., artifact_version: _Optional[str] = ...) -> None: ...

class NodeBuildCancel(_message.Message):
    __slots__ = ("build_id",)
    BUILD_ID_FIELD_NUMBER: _ClassVar[int]
    build_id: str
    def __init__(self, build_id: _Optional[str] = ...) -> None: ...

class NodeBuildEvent(_message.Message):
    __slots__ = ("build_id", "seq", "stage", "message", "percent", "reported_at", "log_tail")
    BUILD_ID_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    STAGE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PERCENT_FIELD_NUMBER: _ClassVar[int]
    REPORTED_AT_FIELD_NUMBER: _ClassVar[int]
    LOG_TAIL_FIELD_NUMBER: _ClassVar[int]
    build_id: str
    seq: int
    stage: str
    message: str
    percent: int
    reported_at: str
    log_tail: str
    def __init__(self, build_id: _Optional[str] = ..., seq: _Optional[int] = ..., stage: _Optional[str] = ..., message: _Optional[str] = ..., percent: _Optional[int] = ..., reported_at: _Optional[str] = ..., log_tail: _Optional[str] = ...) -> None: ...

class NodeBuildResult(_message.Message):
    __slots__ = ("build_id", "ok", "error_code", "error_message", "retryable", "stage_reached", "artifact_sha256", "artifact_size_bytes")
    BUILD_ID_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRYABLE_FIELD_NUMBER: _ClassVar[int]
    STAGE_REACHED_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_SHA256_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    build_id: str
    ok: bool
    error_code: str
    error_message: str
    retryable: bool
    stage_reached: str
    artifact_sha256: str
    artifact_size_bytes: int
    def __init__(self, build_id: _Optional[str] = ..., ok: _Optional[bool] = ..., error_code: _Optional[str] = ..., error_message: _Optional[str] = ..., retryable: _Optional[bool] = ..., stage_reached: _Optional[str] = ..., artifact_sha256: _Optional[str] = ..., artifact_size_bytes: _Optional[int] = ...) -> None: ...
