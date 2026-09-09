"""Unary Connect-RPC surface for NodeService (JSON-over-HTTP).

The data-side ``monkeycode_compat.node_client`` speaks Connect *unary* over HTTP:

    POST {base}/agentcompose.v2.NodeService/{Method}
    Content-Type: application/json
    <request message as JSON: camelCase fields, proto enum names>
    → <response message as JSON>

We mount exactly that surface as FastAPI POST routes. Request/response bodies are
converted JSON↔protobuf with :mod:`google.protobuf.json_format`, so the wire
shape (camelCase, ``NODE_STATUS_*`` enum names) is byte-for-byte what connect-go
emitted and what the client already parses via ``_normalize_node_info``.

The streaming RPCs (``NodeConnect`` / ``FollowNodeSession``) are *not* here —
``NodeConnect`` is the raw-ASGI bidi handler in :mod:`.connect_stream`;
``FollowNodeSession`` is a Connect server-stream also handled there. This router
is only the unary management + dispatch + config plane.

Auth: an optional static Bearer token (``node_control_token``). Empty =
open (matching the Go daemon's default when ``AGENT_COMPOSE_API_TOKEN`` is
unset). When set, every unary call must carry ``Authorization: Bearer <token>``.
"""
from __future__ import annotations

import hmac
import json
from typing import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.protobuf import json_format
from loguru import logger

from . import agentcompose_v2_pb2 as pb
from .service import Code, NodeService, RPCError

# Connect error code → HTTP status (Connect's canonical mapping).
_CODE_HTTP = {
    Code.CANCELED: 499,
    Code.UNKNOWN: 500,
    Code.INVALID_ARGUMENT: 400,
    Code.DEADLINE_EXCEEDED: 504,
    Code.NOT_FOUND: 404,
    Code.PERMISSION_DENIED: 403,
    Code.FAILED_PRECONDITION: 412,
    Code.UNAVAILABLE: 503,
    Code.INTERNAL: 500,
}

# The Connect service path segment (matches NodeServiceName in the proto).
_SERVICE = "agentcompose.v2.NodeService"


def _parse_request(body: bytes, msg):
    """Parse a JSON request body into ``msg`` (camelCase, enum names). Empty body
    is treated as an empty message. Raises RPCError(invalid_argument) on bad JSON."""
    text = (body or b"").decode("utf-8").strip()
    if not text:
        return msg
    try:
        payload = json.loads(text)
        payload = _normalize_repeated_nulls(payload)
        json_format.ParseDict(payload, msg, ignore_unknown_fields=True)
    except (json.JSONDecodeError, TypeError, json_format.ParseError) as exc:
        raise RPCError(Code.INVALID_ARGUMENT, f"invalid request body: {exc}")
    return msg


_REPEATED_FIELDS = {
    # NodeCreateSession repeated fields. Some web/API callers send `null` for
    # empty lists; protobuf JSON requires [] for repeated fields and rejects null
    # before the request reaches NodeService.dispatch_session. Normalize at the
    # unary boundary so every caller gets the same tolerant behaviour.
    "mcps",
    "skills",
    "plugins",
    "env",
    "additional_mounts",
    "additionalMounts",
    "models",
}


def _normalize_repeated_nulls(value):
    if isinstance(value, list):
        return [_normalize_repeated_nulls(item) for item in value]
    if not isinstance(value, dict):
        return value
    normalized = {}
    for key, item in value.items():
        if key in _REPEATED_FIELDS:
            if item is None:
                normalized[key] = []
                continue
            if isinstance(item, str):
                try:
                    decoded = json.loads(item)
                except json.JSONDecodeError:
                    decoded = []
                normalized[key] = (
                    [_normalize_repeated_nulls(entry) for entry in decoded]
                    if isinstance(decoded, list)
                    else []
                )
                continue
        normalized[key] = _normalize_repeated_nulls(item)
    return normalized


def _json_response(msg) -> JSONResponse:
    """Serialize a proto message as the Connect JSON response (camelCase)."""
    data = json_format.MessageToDict(
        msg,
        preserving_proto_field_name=False,  # camelCase, matches connect-go
        use_integers_for_enums=False,        # emit enum *names* (NODE_STATUS_*)
    )
    return JSONResponse(content=data)


def _connect_error(err: RPCError) -> JSONResponse:
    """Build a Connect unary error envelope + HTTP status.

    Connect encodes a unary error as an HTTP error status with a JSON body
    ``{"code": "<code>", "message": "<msg>"}``; the data-side client reads
    ``body["code"]``/``body["message"]`` and raises ``RPCError``.
    """
    status = _CODE_HTTP.get(err.code, 500)
    return JSONResponse(status_code=status, content={"code": err.code, "message": err.message})


def build_unary_router(service: NodeService, *, api_token: str = "") -> APIRouter:
    """Build the NodeService unary router bound to a live :class:`NodeService`.

    ``api_token`` gates every call with a static Bearer token when non-empty.
    """
    router = APIRouter()
    token = (api_token or "").strip()

    def _authorized(request: Request) -> bool:
        if not token:
            return True  # open, matching the Go daemon default
        header = request.headers.get("authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        # constant-time compare, mirroring the Go middleware
        return hmac.compare_digest(header[len(prefix):].strip(), token)

    # Each entry: RPC method name → (request message class, service coroutine).
    handlers: dict[str, tuple[type | None, Callable[[object], Awaitable]]] = {
        "ListNodes": (pb.ListNodesRequest, service.list_nodes),
        "GetPublicIPLookupConfig": (
            pb.GetPublicIPLookupConfigRequest,
            service.get_public_ip_lookup_config,
        ),
        "UpdatePublicIPLookupConfig": (
            pb.UpdatePublicIPLookupConfigRequest,
            service.update_public_ip_lookup_config,
        ),
        "GetNodeProxyConfig": (
            pb.GetNodeProxyConfigRequest,
            service.get_node_proxy_config,
        ),
        "UpdateNodeProxyConfig": (
            pb.UpdateNodeProxyConfigRequest,
            service.update_node_proxy_config,
        ),
        "SetNodeLastProxy": (
            pb.SetNodeLastProxyRequest,
            service.set_node_last_proxy,
        ),
        "ApproveNode": (pb.ApproveNodeRequest, service.approve_node),
        "RevokeNode": (pb.RevokeNodeRequest, service.revoke_node),
        "DeleteNode": (pb.DeleteNodeRequest, service.delete_node),
        "OnboardNode": (pb.OnboardNodeRequest, service.onboard_node),
        "RevokeOnboardNode": (pb.RevokeOnboardNodeRequest, service.revoke_onboard_node),
        "DispatchSession": (pb.DispatchSessionRequest, service.dispatch_session),
        "DeleteNodeSession": (pb.DeleteNodeSessionRequest, service.delete_node_session),
        "SendSessionInput": (pb.SendSessionInputRequest, service.send_session_input),
        "ConfigureNodeSessionLLM": (pb.ConfigureNodeSessionLLMRequest, service.configure_session_llm),
        "ApplyNodeSessionMCPs": (pb.ApplyNodeSessionMCPsRequest, service.apply_session_mcps),
        "ApplyNodeSessionSkills": (pb.ApplyNodeSessionSkillsRequest, service.apply_session_skills),
        "ApplyNodeSessionPlugins": (pb.ApplyNodeSessionPluginsRequest, service.apply_session_plugins),
        "ConfigureNodeSessionMode": (pb.ConfigureNodeSessionModeRequest, service.configure_session_mode),
        "StartNodeSessionRuntime": (pb.StartNodeSessionRuntimeRequest, service.start_session_runtime),
        "RestartNodeSessionRuntime": (pb.RestartNodeSessionRuntimeRequest, service.restart_session_runtime),
        "CollectNodeSessionArtifacts": (pb.CollectNodeSessionArtifactsRequest, service.collect_session_artifacts),
    }

    async def _dispatch(method: str, request: Request) -> JSONResponse:
        if not _authorized(request):
            return _connect_error(RPCError(Code.PERMISSION_DENIED, "invalid or missing bearer token"))
        entry = handlers.get(method)
        body = await request.body()
        try:
            # These command-oriented methods already have protobuf payloads for
            # the node stream, but no standalone unary request messages. Keep
            # their Connect JSON shape explicit until the proto service surface
            # is regenerated with dedicated request/response messages.
            if method in {"MoveNode", "ManageEditor", "SelfUpgradeNode", "RuntimeUpgradeNode", "InstallHostTool", "UpgradeNode", "HostExec", "StartToolRun", "StopToolRun", "ListActiveToolRuns", "ManageNodeEnvironment", "SyncNodeEnvironment", "InspectNodeEnvironment", "InspectNodeSystemEnv", "SyncNodeSystemEnv", "ArchiveNodeSystemEnvResource", "IosDiscover", "IosClaimDevice", "IosReleaseDevice", "IosConfigureDevice", "GetIosDevices", "IosStartWdaJob", "IosCancelWdaJob", "GetIosWdaJobStatus", "StartNodeBuild", "GetNodeBuildStatus", "CancelNodeBuild"}:
                import json

                payload = json.loads((body or b"{}").decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise RPCError(Code.INVALID_ARGUMENT, "request body must be an object")
                if method == "MoveNode":
                    record = await service.move_node(payload.get("nodeId", ""), payload.get("managerNodeId", ""))
                    data = {"node": json_format.MessageToDict(service.node_info(record), preserving_proto_field_name=False)}
                elif method == "ManageEditor":
                    data = await service.manage_editor(payload.get("nodeId", ""), payload.get("editor", ""), payload.get("action", ""))
                elif method == "SelfUpgradeNode":
                    data = await service.self_upgrade_node(
                        payload.get("nodeId", ""), target=payload.get("target") or None
                    )
                elif method == "InstallHostTool":
                    data = await service.install_host_tool(
                        payload.get("nodeId", ""), payload.get("tool", ""), target=payload.get("target") or None
                    )
                elif method == "RuntimeUpgradeNode":
                    data = await service.runtime_upgrade_node(
                        payload.get("nodeId", ""), target=payload.get("target") or None
                    )
                elif method == "UpgradeNode":
                    data = await service.upgrade_node(
                        payload.get("nodeId", ""),
                        runtime_target=payload.get("runtimeTarget") or None,
                        node_target=payload.get("nodeTarget") or None,
                    )
                elif method == "StartToolRun":
                    await service.start_tool_run(
                        payload.get("nodeId", ""),
                        payload.get("runId", ""),
                        payload.get("binaryPath", ""),
                        list(payload.get("args", []) or []),
                        env=dict(payload.get("env", {}) or {}),
                        cwd=payload.get("cwd", ""),
                        revision=max(int(payload.get("revision", 0) or 0), 0),
                    )
                    data = {"runId": payload.get("runId", "")}
                elif method == "StopToolRun":
                    await service.stop_tool_run(
                        payload.get("nodeId", ""),
                        payload.get("runId", ""),
                        grace_ms=max(int(payload.get("graceMs", 0) or 0), 0),
                    )
                    data = {"runId": payload.get("runId", ""), "stopped": True}
                elif method == "ListActiveToolRuns":
                    from .toolrun_inventory import node_tool_runs

                    data = {"toolRuns": node_tool_runs(service, payload.get("nodeId", ""))}
                elif method == "ManageNodeEnvironment":
                    data = await service.manage_environment(
                        payload.get("nodeId", ""),
                        payload.get("envId", ""),
                        payload.get("action", ""),
                    )
                elif method == "SyncNodeEnvironment":
                    data = await service.sync_environment(
                        payload.get("nodeId", ""),
                        payload.get("envId", ""),
                        list(payload.get("skills", []) or []),
                        list(payload.get("plugins", []) or []),
                    )
                elif method == "InspectNodeEnvironment":
                    data = await service.inspect_environment(
                        payload.get("nodeId", ""),
                        payload.get("envId", ""),
                    )
                elif method == "InspectNodeSystemEnv":
                    data = await service.inspect_system_env(
                        payload.get("nodeId", ""),
                        payload.get("provider", ""),
                    )
                elif method == "SyncNodeSystemEnv":
                    data = await service.sync_system_env(
                        payload.get("nodeId", ""),
                        list(payload.get("skills", []) or []),
                        list(payload.get("plugins", []) or []),
                        bool(payload.get("overwrite", False)),
                        list(payload.get("remove", []) or []),
                    )
                elif method == "ArchiveNodeSystemEnvResource":
                    data = await service.archive_system_env_resource(
                        payload.get("nodeId", ""),
                        payload.get("kind", ""),
                        payload.get("name", ""),
                        payload.get("uploadUrl", ""),
                        payload.get("uploadToken", ""),
                    )
                elif method == "IosDiscover":
                    data = await service.ios_discover(payload.get("nodeId", ""))
                elif method == "IosClaimDevice":
                    data = await service.ios_claim_device(
                        payload.get("nodeId", ""),
                        payload.get("udid", ""),
                        payload.get("deviceLabel", ""),
                        payload.get("pairingCode", ""),
                    )
                elif method == "IosReleaseDevice":
                    data = await service.ios_release_device(
                        payload.get("nodeId", ""),
                        payload.get("deviceId", ""),
                        payload.get("udid", ""),
                        delete_credential=bool(payload.get("deleteCredential", False)),
                    )
                elif method == "IosConfigureDevice":
                    data = await service.ios_configure_device(
                        payload.get("nodeId", ""),
                        payload.get("deviceId", ""),
                        payload.get("udid", ""),
                        max(int(payload.get("configRevision", 0) or 0), 0),
                        transport=payload.get("transport", ""),
                        wda_bundle_id=payload.get("wdaBundleId", ""),
                        xctest_config_name=payload.get("xctestConfigName", ""),
                        auto_prepare=bool(payload.get("autoPrepare", False)),
                        renew_before_days=int(payload.get("renewBeforeDays", 0) or 0) or 14,
                    )
                elif method == "GetIosDevices":
                    data = await service.get_ios_devices(payload.get("nodeId", ""))
                elif method == "IosStartWdaJob":
                    data = await service.ios_start_wda_job(
                        payload.get("nodeId", ""),
                        payload.get("jobId", ""),
                        payload.get("udid", ""),
                        payload.get("deviceId", ""),
                        payload.get("action", ""),
                        artifact=payload.get("artifact"),
                        signing_profile=payload.get("signingProfile"),
                        wda_bundle_id=payload.get("wdaBundleId", ""),
                        xctest_config_name=payload.get("xctestConfigName", ""),
                    )
                elif method == "IosCancelWdaJob":
                    data = await service.ios_cancel_wda_job(
                        payload.get("nodeId", ""),
                        payload.get("jobId", ""),
                    )
                elif method == "GetIosWdaJobStatus":
                    data = await service.get_ios_wda_job_status(
                        payload.get("nodeId", ""),
                        payload.get("jobId", ""),
                    )
                elif method == "StartNodeBuild":
                    data = await service.start_node_build(
                        payload.get("nodeId", ""),
                        payload.get("buildId", ""),
                        recipe_kind=payload.get("recipeKind", ""),
                        source_url=payload.get("sourceUrl", ""),
                        source_ref=payload.get("sourceRef", ""),
                        steps=[str(s) for s in (payload.get("steps") or [])],
                        artifact_glob=payload.get("artifactGlob", ""),
                        upload_url=payload.get("uploadUrl", ""),
                        upload_token=payload.get("uploadToken", ""),
                        timeout_seconds=max(int(payload.get("timeoutSeconds", 0) or 0), 0),
                        artifact_name=payload.get("artifactName", ""),
                        artifact_version=payload.get("artifactVersion", ""),
                    )
                elif method == "GetNodeBuildStatus":
                    data = await service.get_node_build_status(
                        payload.get("nodeId", ""),
                        payload.get("buildId", ""),
                    )
                elif method == "CancelNodeBuild":
                    data = await service.cancel_node_build(
                        payload.get("nodeId", ""),
                        payload.get("buildId", ""),
                    )
                else:
                    req = pb.NodeHostExecRequest(
                        node_id=payload.get("nodeId", ""),
                        command=payload.get("command", ""),
                        cwd=payload.get("cwd", ""),
                        timeout_ms=max(int(payload.get("timeoutMs", 0) or 0), 0),
                        max_output_bytes=max(int(payload.get("maxOutputBytes", 0) or 0), 0),
                    )
                    data = json_format.MessageToDict(await service.host_exec(req), preserving_proto_field_name=False)
                return JSONResponse(content=data)
            if method == "SetNodeCapacity":
                import json

                payload = json.loads((body or b"{}").decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise RPCError(Code.INVALID_ARGUMENT, "request body must be an object")
                record = await service.store.set_node_capacity(payload.get("nodeId", ""), payload.get("capacity") or {})
                return JSONResponse(content={"nodeId": record.id, "capacity": dict(record.capacity or {})})
            if method == "HostFileUpload":
                # The upload chunk carries a `bytes data` field; Connect JSON
                # base64-encodes it. json_format.ParseDict decodes base64 into
                # the proto bytes field, so we round-trip through it rather than
                # hand-building the message like the plain-string commands above.
                import json

                payload = json.loads((body or b"{}").decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise RPCError(Code.INVALID_ARGUMENT, "request body must be an object")
                req = pb.HostFileUploadRequest()
                json_format.ParseDict(payload, req, ignore_unknown_fields=True)
                data = json_format.MessageToDict(
                    await service.host_file_upload(req), preserving_proto_field_name=False
                )
                return JSONResponse(content=data)
            if entry is None:
                return _connect_error(RPCError(Code.NOT_FOUND, f"unknown method {method}"))
            req_cls, handler = entry
            msg = _parse_request(body, req_cls())
            resp = await handler(msg)
            data = json_format.MessageToDict(resp, preserving_proto_field_name=False, use_integers_for_enums=False)
            if method == "ListNodes":
                node_ids = [node.get("nodeId", "") for node in data.get("nodes", []) if node.get("nodeId")]
                capacities = await service.store.get_node_capacities(node_ids)
                for node in data.get("nodes", []):
                    node["capacity"] = capacities.get(node.get("nodeId", ""), {})
            return JSONResponse(content=data)
        except RPCError as err:
            return _connect_error(err)
        except Exception as exc:  # noqa: BLE001
            logger.exception("[nodeserver] {} failed", method)
            return _connect_error(RPCError(Code.INTERNAL, str(exc)))

    # One catch-all route for the whole service surface keeps the wiring compact
    # and matches the Connect path scheme exactly.
    @router.post("/" + _SERVICE + "/{method}")
    async def _rpc_entry(method: str, request: Request) -> JSONResponse:  # noqa: ANN202
        return await _dispatch(method, request)

    return router
