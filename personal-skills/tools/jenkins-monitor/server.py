import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from jenkins_client import JenkinsClient

mcp_app = Server("jenkins-monitor")

JOB_PARAM = {
    "job": {
        "type": "string",
        "description": "Jenkins job name, e.g. H2Sync-Android-CI-Develop-EC-Diary-Hint",
    }
}

BUILD_NUM_PARAM = {
    "build_number": {
        "type": "integer",
        "description": "Build number (optional, defaults to latest build)",
    }
}


@mcp_app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_jobs",
            description="List all available Jenkins jobs so you can pick one.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="trigger_build",
            description="Trigger a Jenkins job with a specific branch name and optional ProductFlavor.",
            inputSchema={
                "type": "object",
                "properties": {
                    **JOB_PARAM,
                    "branch": {"type": "string", "description": "Git branch name"},
                    "product_flavor": {
                        "type": "string",
                        "enum": ["Alpha", "Beta"],
                        "description": "Build flavor (Alpha or Beta). Omit to use the job's default.",
                    },
                },
                "required": ["job", "branch"],
            },
        ),
        types.Tool(
            name="get_build_status",
            description="Get the status of a build (SUCCESS / FAILURE / in progress).",
            inputSchema={
                "type": "object",
                "properties": {**JOB_PARAM, **BUILD_NUM_PARAM},
                "required": ["job"],
            },
        ),
        types.Tool(
            name="get_build_log",
            description="Get the console log of a build to diagnose failures. Returns the last 200 lines.",
            inputSchema={
                "type": "object",
                "properties": {
                    **JOB_PARAM,
                    **BUILD_NUM_PARAM,
                    "max_lines": {"type": "integer", "description": "Max lines to return (default 200)"},
                },
                "required": ["job"],
            },
        ),
        types.Tool(
            name="get_failed_tests",
            description="Get failed test details from a build's test report.",
            inputSchema={
                "type": "object",
                "properties": {**JOB_PARAM, **BUILD_NUM_PARAM},
                "required": ["job"],
            },
        ),
        types.Tool(
            name="rename_job",
            description="Rename a Jenkins job. Use when the branch name doesn't match the job name suffix.",
            inputSchema={
                "type": "object",
                "properties": {
                    **JOB_PARAM,
                    "new_name": {"type": "string", "description": "New job name, e.g. H2Sync-Android-CI-Develop-Fibet-And-Sodium"},
                },
                "required": ["job", "new_name"],
            },
        ),
        types.Tool(
            name="update_job_parameter",
            description="Update a job parameter's default value. Use to change BranchName (String) or ProductFlavor (Choice: Alpha/Beta) before triggering a build.",
            inputSchema={
                "type": "object",
                "properties": {
                    **JOB_PARAM,
                    "param_name": {"type": "string", "description": "Parameter name, e.g. BranchName or ProductFlavor"},
                    "value": {"type": "string", "description": "New default value"},
                },
                "required": ["job", "param_name", "value"],
            },
        ),
    ]


@mcp_app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    client = JenkinsClient()

    if name == "list_jobs":
        jobs = client.list_jobs()
        return [types.TextContent(type="text", text=json.dumps(jobs, indent=2))]

    job = arguments["job"]

    if name == "trigger_build":
        queue_num = client.trigger_build(job, arguments["branch"], arguments.get("product_flavor"))
        result = {
            "status": "queued",
            "queue_number": queue_num,
            "job": job,
            "branch": arguments["branch"],
            "message": "Build queued. Use get_build_status to check progress.",
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    if name == "get_build_status":
        build_number = arguments.get("build_number", "lastBuild")
        info = client.get_build_info(job, build_number)
        result = {
            "number": info.get("number"),
            "result": info.get("result"),
            "building": info.get("building"),
            "duration_ms": info.get("duration"),
            "url": info.get("url"),
            "display_name": info.get("displayName"),
        }
        for action in info.get("actions", []):
            for p in action.get("parameters", []):
                if "branch" in p.get("name", "").lower():
                    result["branch"] = p.get("value")
                if p.get("name") == "ProductFlavor":
                    result["product_flavor"] = p.get("value")
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    if name == "get_build_log":
        build_number = arguments.get("build_number", "lastBuild")
        max_lines = arguments.get("max_lines", 200)
        log = client.get_build_log(job, build_number, max_lines)
        return [types.TextContent(type="text", text=log)]

    if name == "get_failed_tests":
        build_number = arguments.get("build_number", "lastBuild")
        report = client.get_test_report(job, build_number)
        if not report:
            return [types.TextContent(type="text", text="No test report found for this build.")]
        failed = [
            {
                "class": case["className"],
                "test": case["name"],
                "error": case.get("errorDetails", ""),
                "duration": case.get("duration"),
            }
            for suite in report.get("suites", [])
            for case in suite.get("cases", [])
            if case.get("status") in ("FAILED", "ERROR")
        ]
        result = {
            "total": report.get("totalCount"),
            "failed": report.get("failCount"),
            "skipped": report.get("skipCount"),
            "failed_tests": failed,
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    if name == "rename_job":
        client.rename_job(job, arguments["new_name"])
        result = {"status": "renamed", "old_name": job, "new_name": arguments["new_name"]}
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    if name == "update_job_parameter":
        client.update_job_parameter(job, arguments["param_name"], arguments["value"])
        result = {
            "status": "updated",
            "job": job,
            "param_name": arguments["param_name"],
            "new_value": arguments["value"],
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await mcp_app.run(read_stream, write_stream, mcp_app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
